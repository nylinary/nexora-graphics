"""NATS publisher for sending messages via JetStream."""

import asyncio
import json
from typing import Optional

import nats
from aiologger import Logger  # type: ignore
from nats.aio.client import Client as NATSClient
from nats.js import JetStreamContext

from app.core.config.nats import NATSSettings


class NATSPublisher:
    """NATS publisher for sending messages via JetStream.

    Publishes messages to NATS subjects using JetStream.
    All dependencies injected via DI.
    """

    def __init__(
        self,
        settings: NATSSettings,
        logger: Logger,
    ):
        """Initialize NATS publisher.

        Args:
            settings: NATS settings injected via DI
            logger: Logger instance
        """
        self._settings = settings
        self._logger = logger
        self._nats_client: Optional[NATSClient] = None
        self._js: Optional[JetStreamContext] = None
        self._connected = False

    async def connect(self) -> None:
        """Connect to NATS server and setup JetStream.

        Retries connection with exponential backoff if NATS is not available.
        """
        max_retries = 5
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                self._nats_client = await nats.connect(
                    self._settings.hosts,
                    name="template-service-publisher",
                    verbose=False,
                    allow_reconnect=True,
                    max_reconnect_attempts=-1,
                    reconnect_time_wait=2,
                )

                # Always use JetStream
                self._js = self._nats_client.jetstream()
                await self._setup_jetstream_stream()

                self._connected = True
                await self._logger.info(
                    f"Connected to NATS server at {self._settings.hosts} (JetStream enabled)",
                    extra={"component": "nats_publisher"},
                )
                return

            except Exception as e:
                if attempt < max_retries - 1:
                    await self._logger.warning(
                        f"Failed to connect to NATS (attempt {attempt + 1}/{max_retries}): {e}. "
                        f"Retrying in {retry_delay}s...",
                        extra={"component": "nats_publisher"},
                    )
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    await self._logger.error(
                        f"Failed to connect to NATS server after {max_retries} attempts: {e}",
                        extra={"component": "nats_publisher"},
                        exc_info=True,
                    )
                    raise

    async def _setup_jetstream_stream(self) -> None:
        """Setup JetStream stream if it doesn't exist."""
        if not self._js:
            raise RuntimeError("JetStream not initialized")

        try:
            from nats.js.api import RetentionPolicy, StorageType, StreamConfig

            storage_type = StorageType.FILE if self._settings.stream_storage_type == "file" else StorageType.MEMORY

            await self._js.add_stream(
                StreamConfig(
                    name=self._settings.stream_name,
                    subjects=[self._settings.subject],
                    description=f"{self._settings.stream_name.capitalize()} processing stream",
                    max_age=self._settings.stream_max_age,
                    max_bytes=self._settings.stream_max_bytes,
                    max_msgs=self._settings.stream_max_messages,
                    storage=storage_type,
                    retention=RetentionPolicy.LIMITS,
                )
            )
            await self._logger.debug(
                f"JetStream stream '{self._settings.stream_name}' created/verified",
                extra={"component": "nats_publisher"},
            )
        except Exception as e:
            # Stream might already exist, that's OK
            if "stream name already in use" not in str(e).lower():
                await self._logger.warning(
                    f"Stream setup warning: {e}",
                    extra={"component": "nats_publisher"},
                )

    async def publish(self, subject: str, message_data: dict) -> None:
        """Publish message to NATS subject via JetStream.

        Args:
            subject: NATS subject to publish to
            message_data: Message data as dictionary (will be JSON-encoded)

        Raises:
            RuntimeError: If not connected to NATS
        """
        if not self._connected or not self._nats_client or not self._js:
            # Try to reconnect
            if not self._connected:
                await self.connect()
            else:
                raise RuntimeError("NATS publisher not connected")

        try:
            # Convert message to JSON
            message_json = json.dumps(message_data, default=str)
            message_bytes = message_json.encode()

            # Publish via JetStream
            if not self._js:
                raise RuntimeError("JetStream not initialized")
            ack = await self._js.publish(subject, message_bytes)

            await self._logger.debug(
                f"Published message to {subject}",
                extra={
                    "component": "nats_publisher",
                    "subject": subject,
                    "stream": ack.stream,
                    "sequence": ack.seq,
                },
            )

        except Exception as e:
            await self._logger.error(
                f"Failed to publish message to {subject}: {e}",
                extra={"component": "nats_publisher", "subject": subject},
                exc_info=True,
            )
            # Try to reconnect and retry once
            try:
                await self.connect()
                if not self._js:
                    raise RuntimeError("JetStream not initialized after reconnection")
                message_json = json.dumps(message_data, default=str)
                message_bytes = message_json.encode()
                await self._js.publish(subject, message_bytes)
                await self._logger.info(
                    f"Successfully published message to {subject} after reconnection",
                    extra={"component": "nats_publisher", "subject": subject},
                )
            except Exception as retry_error:
                await self._logger.error(
                    f"Failed to publish message to {subject} after reconnection: {retry_error}",
                    extra={"component": "nats_publisher", "subject": subject},
                    exc_info=True,
                )
                raise

    async def disconnect(self) -> None:
        """Disconnect from NATS server."""
        if self._nats_client:
            await self._nats_client.close()
            self._nats_client = None
            self._js = None
            self._connected = False
            await self._logger.info(
                "NATS publisher disconnected",
                extra={"component": "nats_publisher"},
            )
