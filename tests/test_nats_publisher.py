"""Tests for NATS publisher."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.config.nats import NATSSettings
from app.infrastructure.messaging.nats_publisher import NATSPublisher


@pytest.fixture
def nats_settings() -> NATSSettings:
    """Create NATS settings for testing."""
    return NATSSettings(
        hosts="nats://localhost:4222",
        subject="test.>",
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
def nats_publisher(nats_settings: NATSSettings, mock_logger: AsyncMock) -> NATSPublisher:
    """Create NATS publisher instance for testing."""
    return NATSPublisher(
        settings=nats_settings,
        logger=mock_logger,
    )


@pytest.mark.asyncio
async def test_nats_publisher_initialization(nats_publisher: NATSPublisher):
    """Test NATS publisher initialization."""
    assert nats_publisher._settings is not None
    assert nats_publisher._logger is not None
    assert nats_publisher._nats_client is None
    assert nats_publisher._js is None
    assert nats_publisher._connected is False


@pytest.mark.asyncio
async def test_connect_success(nats_publisher: NATSPublisher, nats_settings: NATSSettings):
    """Test successful connection to NATS."""
    mock_client = MagicMock()
    mock_js = MagicMock()
    mock_client.jetstream.return_value = mock_js
    mock_js.add_stream = AsyncMock()

    with patch(
        "app.infrastructure.messaging.nats_publisher.nats.connect",
        new_callable=AsyncMock,
        return_value=mock_client,
    ):
        await nats_publisher.connect()

    assert nats_publisher._nats_client == mock_client
    assert nats_publisher._js == mock_js
    assert nats_publisher._connected is True
    mock_js.add_stream.assert_called_once()


@pytest.mark.asyncio
async def test_connect_failure(nats_publisher: NATSPublisher):
    """Test connection failure handling."""
    with patch(
        "app.infrastructure.messaging.nats_publisher.nats.connect",
        new_callable=AsyncMock,
        side_effect=Exception("Connection failed"),
    ):
        with pytest.raises(Exception, match="Connection failed"):
            await nats_publisher.connect()


@pytest.mark.asyncio
async def test_publish_success(nats_publisher: NATSPublisher, mock_logger: AsyncMock):
    """Test successful message publishing."""
    mock_client = MagicMock()
    mock_js = MagicMock()
    mock_ack = MagicMock()
    mock_ack.stream = "test"
    mock_ack.seq = 1
    mock_js.publish = AsyncMock(return_value=mock_ack)
    mock_client.jetstream.return_value = mock_js

    nats_publisher._nats_client = mock_client
    nats_publisher._js = mock_js
    nats_publisher._connected = True

    test_message = {"test": "data", "id": "123"}
    await nats_publisher.publish("test.subject", test_message)

    mock_js.publish.assert_called_once()
    call_args = mock_js.publish.call_args[0]
    assert call_args[0] == "test.subject"
    assert json.loads(call_args[1].decode()) == test_message
    mock_logger.debug.assert_called()


@pytest.mark.asyncio
async def test_publish_not_connected(nats_publisher: NATSPublisher):
    """Test publishing when not connected (should reconnect)."""
    mock_client = MagicMock()
    mock_js = MagicMock()
    mock_ack = MagicMock()
    mock_ack.stream = "test"
    mock_ack.seq = 1
    mock_js.publish = AsyncMock(return_value=mock_ack)
    mock_client.jetstream.return_value = mock_js

    with patch(
        "app.infrastructure.messaging.nats_publisher.nats.connect",
        new_callable=AsyncMock,
        return_value=mock_client,
    ):
        nats_publisher._js = mock_js
        test_message = {"test": "data"}
        await nats_publisher.publish("test.subject", test_message)

    mock_js.publish.assert_called_once()


@pytest.mark.asyncio
async def test_publish_error_with_retry(nats_publisher: NATSPublisher, mock_logger: AsyncMock):
    """Test publishing with error and retry after reconnection."""
    mock_client = MagicMock()
    mock_js = MagicMock()
    mock_ack = MagicMock()
    mock_ack.stream = "test"
    mock_ack.seq = 1

    # First call fails, second succeeds
    mock_js.publish = AsyncMock(side_effect=[Exception("Publish failed"), mock_ack])
    mock_client.jetstream.return_value = mock_js

    nats_publisher._nats_client = mock_client
    nats_publisher._js = mock_js
    nats_publisher._connected = True

    test_message = {"test": "data"}
    await nats_publisher.publish("test.subject", test_message)

    # Should be called twice (original + retry)
    assert mock_js.publish.call_count == 2
    mock_logger.error.assert_called()
    mock_logger.info.assert_called()


@pytest.mark.asyncio
async def test_disconnect(nats_publisher: NATSPublisher, mock_logger: AsyncMock):
    """Test disconnecting from NATS."""
    mock_client = MagicMock()
    mock_client.close = AsyncMock()
    nats_publisher._nats_client = mock_client
    nats_publisher._js = MagicMock()
    nats_publisher._connected = True

    await nats_publisher.disconnect()

    assert nats_publisher._nats_client is None
    assert nats_publisher._js is None
    assert nats_publisher._connected is False
    mock_client.close.assert_called_once()
    mock_logger.info.assert_called()


@pytest.mark.asyncio
async def test_setup_jetstream_stream(nats_publisher: NATSPublisher):
    """Test JetStream stream setup."""
    mock_js = MagicMock()
    mock_js.add_stream = AsyncMock()
    nats_publisher._js = mock_js

    await nats_publisher._setup_jetstream_stream()

    mock_js.add_stream.assert_called_once()
