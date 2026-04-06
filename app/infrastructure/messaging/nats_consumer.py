"""NATS consumer for processing messages."""

import asyncio
import json
from typing import Optional

import nats
from aiologger import Logger  # type: ignore
from nats.aio.client import Client as NATSClient
from nats.aio.msg import Msg
from nats.js import JetStreamContext
from nats.js.api import AckPolicy, ConsumerConfig, RetentionPolicy, StorageType, StreamConfig

from app.core.config.nats import NATSSettings
from app.domain.interfaces.messaging.message_handler import IMessageHandler


class NATSConsumer:
    """NATS consumer for processing messages via JetStream.

    Subscribes to NATS subject using JetStream and processes incoming messages.
    All dependencies injected via DI.
    """

    def __init__(
        self,
        settings: NATSSettings,
        message_handler: IMessageHandler,
        logger: Logger,
    ):
        """Initialize NATS consumer.

        Args:
            settings: NATS settings injected via DI
            message_handler: Handler for processing messages injected via DI
            logger: Logger instance
        """
        self._settings = settings
        self._message_handler = message_handler
        self._logger = logger
        self._nats_client: Optional[NATSClient] = None
        self._js: JetStreamContext | None = None
        self._psub = None
        self._running = False
        self._active_tasks: set[asyncio.Task] = set()

    async def start(self) -> None:
        """Start consuming messages from NATS via JetStream.

        Connects to NATS, sets up JetStream, and starts message processing loop.
        Retries connection with exponential backoff if NATS is not available.
        """
        max_retries = 5
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                await self._connect()
                await self._subscribe()
                await self._logger.info(
                    f"NATSConsumer started (subject: {self._settings.subject})",
                    extra={"component": "nats_consumer", "subject": self._settings.subject},
                )
                return
            except Exception as e:
                if attempt < max_retries - 1:
                    await self._logger.warning(
                        f"Failed to connect to NATS "
                        f"(attempt {attempt + 1}/{max_retries}), "
                        f"retrying in {retry_delay}s: {e}",
                        extra={"component": "nats_consumer", "attempt": attempt + 1},
                    )
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    await self._logger.error(
                        f"Failed to start NATSConsumer after {max_retries} attempts: {e}",
                        extra={"component": "nats_consumer"},
                        exc_info=True,
                    )
                    raise

    async def stop(self) -> None:
        """Stop consuming messages and disconnect from NATS."""
        self._running = False

        # Wait for active tasks to complete
        if self._active_tasks:
            await self._logger.info(
                f"Waiting for {len(self._active_tasks)} active message processing tasks to complete...",
                extra={"component": "nats_consumer", "active_tasks": len(self._active_tasks)},
            )
            # Wait for all tasks with timeout
            await asyncio.wait(self._active_tasks, timeout=30.0)

        if self._nats_client:
            await self._nats_client.close()
            self._nats_client = None
            await self._logger.info(
                "NATSConsumer stopped",
                extra={"component": "nats_consumer"},
            )

    async def _connect(self) -> None:
        """Connect to NATS server and setup JetStream."""
        try:
            self._nats_client = await nats.connect(
                self._settings.hosts,
                name="template-service-consumer",
                verbose=False,
                allow_reconnect=True,
                max_reconnect_attempts=-1,
                reconnect_time_wait=2,
            )

            # Always use JetStream
            self._js = self._nats_client.jetstream()
            await self._setup_jetstream_stream()

            await self._logger.info(
                f"Connected to NATS server at {self._settings.hosts} (JetStream enabled)",
                extra={"component": "nats_consumer"},
            )
        except Exception as e:
            await self._logger.error(
                f"Failed to connect to NATS server: {e}",
                extra={"component": "nats_consumer"},
                exc_info=True,
            )
            raise

    async def _setup_jetstream_stream(self) -> None:
        """Setup JetStream stream."""
        try:
            await self._js.add_stream(  # type: ignore
                StreamConfig(
                    name=self._settings.stream_name,
                    subjects=[f"{self._settings.stream_name}.*"],
                    description=f"{self._settings.stream_name.capitalize()} processing stream",
                    max_age=self._settings.stream_max_age,
                    max_bytes=self._settings.stream_max_bytes if self._settings.stream_max_bytes > 0 else None,
                    max_msgs=self._settings.stream_max_messages if self._settings.stream_max_messages > 0 else None,
                    storage=(StorageType.FILE if self._settings.stream_storage_type == "file" else StorageType.MEMORY),
                    retention=RetentionPolicy.LIMITS,
                )
            )

            await self._logger.info(
                f"Created/verified JetStream stream: {self._settings.stream_name}",
                extra={"component": "nats_consumer", "stream": self._settings.stream_name},
            )

        except Exception as e:
            await self._logger.debug(
                f"Stream {self._settings.stream_name} might already exist: {e}",
                extra={"component": "nats_consumer"},
            )

    async def _subscribe(self) -> None:
        """Subscribe to NATS subject using JetStream and start processing messages."""
        if not self._nats_client:
            raise RuntimeError("NATS client not connected")

        if not self._js:
            raise RuntimeError("JetStream not initialized")

        # JetStream pull subscription
        try:
            self._psub = await self._js.pull_subscribe(  # type: ignore
                subject=self._settings.subject,
                durable=self._settings.consumer_durable,
                config=ConsumerConfig(
                    ack_policy=AckPolicy.EXPLICIT,
                    ack_wait=self._settings.consumer_ack_wait,
                    max_deliver=self._settings.consumer_max_deliver,
                ),
            )

            await self._logger.info(
                f"Subscribed to {self._settings.subject} with JetStream",
                extra={"component": "nats_consumer"},
            )

            # Start message processing loop
            self._running = True
            asyncio.create_task(self._message_processing_loop())

        except Exception as e:
            await self._logger.error(
                f"Failed to subscribe to {self._settings.subject}: {e}",
                extra={"component": "nats_consumer"},
                exc_info=True,
            )
            raise

    async def _message_processing_loop(self) -> None:
        """Main message processing loop for JetStream pull subscription."""
        while self._running:
            try:
                if not self._nats_client or not self._nats_client.is_connected:
                    await self._logger.warning(
                        "Lost NATS connection, waiting to reconnect...",
                        extra={"component": "nats_consumer"},
                    )
                    await asyncio.sleep(4)
                    await self._connect()
                    self._psub = await self._js.pull_subscribe(  # type: ignore
                        subject=self._settings.subject,
                        durable=self._settings.consumer_durable,
                        config=ConsumerConfig(
                            ack_policy=AckPolicy.EXPLICIT,
                            ack_wait=self._settings.consumer_ack_wait,
                            max_deliver=self._settings.consumer_max_deliver,
                        ),
                    )
                    await self._logger.info(
                        "Reconnected to NATS",
                        extra={"component": "nats_consumer"},
                    )
                    continue

                if not self._psub:
                    await asyncio.sleep(1)
                    continue

                # Fetch batch of messages
                messages = await self._psub.fetch(self._settings.fetch_batch_size, timeout=1.0)

                if messages:
                    await self._logger.debug(
                        f"Fetched {len(messages)} messages",
                        extra={"component": "nats_consumer", "batch_size": len(messages)},
                    )

                # Process messages in parallel
                for msg in messages:
                    task = asyncio.create_task(self._handle_message_jetstream(msg))
                    self._active_tasks.add(task)
                    # Remove from active_tasks when done
                    task.add_done_callback(self._active_tasks.discard)

            except nats.errors.TimeoutError:
                # Timeout is normal, continue waiting
                continue
            except Exception as e:
                await self._logger.error(
                    f"Error in message processing loop: {e}",
                    extra={"component": "nats_consumer"},
                    exc_info=True,
                )
                await asyncio.sleep(1)

    async def _handle_message_jetstream(self, msg: Msg) -> None:
        """Handle message in JetStream mode."""
        try:
            raw_data = msg.data.decode() if msg.data else ""
            await self._logger.debug(
                f"Received raw message: {raw_data[:200]}...",
                extra={"component": "nats_consumer"},
            )

            # Process message
            await self._process_message(raw_data)

            # Acknowledge message
            await msg.ack()
            await self._logger.debug(
                "Processed and acknowledged message",
                extra={"component": "nats_consumer"},
            )

        except Exception as e:
            await self._logger.error(
                f"Error processing message: {e}",
                extra={"component": "nats_consumer"},
                exc_info=True,
            )
            await msg.nak()  # Reject for retry

    async def _process_message(self, raw_data: str) -> None:
        """Process raw message data.

        Args:
            raw_data: Raw JSON string from NATS message
        """
        try:
            message_data = json.loads(raw_data)

            await self._logger.info(
                f"Received NATS message: {message_data}",
                extra={"component": "nats_consumer"},
            )

            # Delegate to injected message handler
            await self._message_handler.handle(message_data)

        except json.JSONDecodeError as e:
            await self._logger.error(
                f"Failed to parse NATS message as JSON: {e}",
                extra={"component": "nats_consumer"},
                exc_info=True,
            )
            raise
        except Exception as e:
            await self._logger.error(
                f"Failed to process NATS message: {e}",
                extra={"component": "nats_consumer"},
                exc_info=True,
            )
            raise
