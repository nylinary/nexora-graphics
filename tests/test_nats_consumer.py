"""Tests for NATS consumer."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from nats.aio.msg import Msg

from app.core.config.nats import NATSSettings
from app.domain.interfaces.messaging.message_handler import IMessageHandler
from app.infrastructure.messaging.nats_consumer import NATSConsumer


class MockMessageHandler(IMessageHandler):
    """Mock message handler for testing."""

    def __init__(self):
        self.handled_messages = []
        self.should_raise = False

    async def handle(self, message_data: dict) -> None:
        """Handle message and store it for verification."""
        if self.should_raise:
            raise ValueError("Test error")
        self.handled_messages.append(message_data)


@pytest.fixture
def nats_settings() -> NATSSettings:
    """Create NATS settings for testing."""
    return NATSSettings(
        hosts="nats://localhost:4222",
        subject="test.>",
        consumer_durable="test-consumer",
        stream_name="test",
    )


@pytest.fixture
def mock_logger() -> AsyncMock:
    """Create mock logger."""
    logger = AsyncMock()
    logger.info = AsyncMock()
    logger.error = AsyncMock()
    logger.debug = AsyncMock()
    logger.warning = AsyncMock()
    return logger


@pytest.fixture
def message_handler() -> MockMessageHandler:
    """Create mock message handler."""
    return MockMessageHandler()


@pytest.fixture
def nats_consumer(
    nats_settings: NATSSettings, message_handler: MockMessageHandler, mock_logger: AsyncMock
) -> NATSConsumer:
    """Create NATS consumer instance for testing."""
    return NATSConsumer(
        settings=nats_settings,
        message_handler=message_handler,
        logger=mock_logger,
    )


@pytest.mark.asyncio
async def test_nats_consumer_initialization(nats_consumer: NATSConsumer):
    """Test NATS consumer initialization."""
    assert nats_consumer._settings is not None
    assert nats_consumer._message_handler is not None
    assert nats_consumer._logger is not None
    assert nats_consumer._nats_client is None
    assert nats_consumer._running is False


@pytest.mark.asyncio
async def test_connect_success(nats_consumer: NATSConsumer, nats_settings: NATSSettings):
    """Test successful connection to NATS."""
    mock_client = MagicMock()
    mock_js = MagicMock()
    mock_client.jetstream.return_value = mock_js
    mock_js.add_stream = AsyncMock()

    with patch(
        "app.infrastructure.messaging.nats_consumer.nats.connect", new_callable=AsyncMock, return_value=mock_client
    ):
        await nats_consumer._connect()

    assert nats_consumer._nats_client == mock_client
    assert nats_consumer._js == mock_js
    mock_js.add_stream.assert_called_once()


@pytest.mark.asyncio
async def test_connect_failure(nats_consumer: NATSConsumer):
    """Test connection failure handling."""
    with patch(
        "app.infrastructure.messaging.nats_consumer.nats.connect",
        new_callable=AsyncMock,
        side_effect=Exception("Connection failed"),
    ):
        with pytest.raises(Exception, match="Connection failed"):
            await nats_consumer._connect()


@pytest.mark.asyncio
async def test_process_message_success(nats_consumer: NATSConsumer, message_handler: MockMessageHandler):
    """Test successful message processing."""
    test_message = {"test": "data", "id": "123"}
    raw_data = json.dumps(test_message)

    await nats_consumer._process_message(raw_data)

    assert len(message_handler.handled_messages) == 1
    assert message_handler.handled_messages[0] == test_message


@pytest.mark.asyncio
async def test_process_message_invalid_json(nats_consumer: NATSConsumer, mock_logger: AsyncMock):
    """Test handling of invalid JSON message."""
    invalid_json = "{ invalid json }"

    with pytest.raises(json.JSONDecodeError):
        await nats_consumer._process_message(invalid_json)

    mock_logger.error.assert_called()


@pytest.mark.asyncio
async def test_process_message_handler_error(nats_consumer: NATSConsumer, message_handler: MockMessageHandler):
    """Test handling of errors in message handler."""
    message_handler.should_raise = True
    test_message = {"test": "data"}
    raw_data = json.dumps(test_message)

    with pytest.raises(ValueError, match="Test error"):
        await nats_consumer._process_message(raw_data)


@pytest.mark.asyncio
async def test_handle_message_jetstream_success(nats_consumer: NATSConsumer, message_handler: MockMessageHandler):
    """Test successful JetStream message handling."""
    test_message = {"test": "data"}
    raw_data = json.dumps(test_message).encode()

    mock_msg = MagicMock(spec=Msg)
    mock_msg.data = raw_data
    mock_msg.ack = AsyncMock()

    await nats_consumer._handle_message_jetstream(mock_msg)

    assert len(message_handler.handled_messages) == 1
    mock_msg.ack.assert_called_once()


@pytest.mark.asyncio
async def test_handle_message_jetstream_error(nats_consumer: NATSConsumer, message_handler: MockMessageHandler):
    """Test error handling in JetStream message processing."""
    message_handler.should_raise = True
    test_message = {"test": "data"}
    raw_data = json.dumps(test_message).encode()

    mock_msg = MagicMock(spec=Msg)
    mock_msg.data = raw_data
    mock_msg.ack = AsyncMock()
    mock_msg.nak = AsyncMock()

    await nats_consumer._handle_message_jetstream(mock_msg)

    mock_msg.ack.assert_not_called()
    mock_msg.nak.assert_called_once()


@pytest.mark.asyncio
async def test_stop(nats_consumer: NATSConsumer, mock_logger: AsyncMock):
    """Test stopping NATS consumer."""
    mock_client = MagicMock()
    mock_client.close = AsyncMock()
    nats_consumer._nats_client = mock_client
    nats_consumer._running = True

    await nats_consumer.stop()

    assert nats_consumer._running is False
    assert nats_consumer._nats_client is None
    mock_client.close.assert_called_once()
    mock_logger.info.assert_called()


@pytest.mark.asyncio
async def test_setup_jetstream_stream(nats_consumer: NATSConsumer):
    """Test JetStream stream setup."""
    mock_js = MagicMock()
    mock_js.add_stream = AsyncMock()
    nats_consumer._js = mock_js

    await nats_consumer._setup_jetstream_stream()

    mock_js.add_stream.assert_called_once()
