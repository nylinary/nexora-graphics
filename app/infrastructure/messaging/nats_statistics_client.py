"""NATS client for statistics-service: request/reply via JetStream.

Follows the same pattern as NatsSemanticClient in vectorizing-service.
Publishes to statistics.request, subscribes to statistics.response via core NATS,
matches responses by correlation_id (UUID4) using asyncio.Future.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Any

import nats
from nats.aio.client import Client

from app.domain.exceptions import GraphicsDataError

logger = logging.getLogger(__name__)

STATISTICS_REQUEST_SUBJECT = "statistics.request"
STATISTICS_RESPONSE_SUBJECT = "statistics.response"


class NatsStatisticsClient:
    """Publish to statistics.request, collect from statistics.response."""

    def __init__(
        self,
        nats_url: str,
        request_subject: str = STATISTICS_REQUEST_SUBJECT,
        response_subject: str = STATISTICS_RESPONSE_SUBJECT,
        timeout_sec: float = 30.0,
    ) -> None:
        self._nats_url = nats_url
        self._request_subject = request_subject
        self._response_subject = response_subject
        self._timeout = timeout_sec
        self._nc: Client | None = None
        self._js: Any = None
        self._sub: Any = None
        self._pending: dict[str, asyncio.Future[dict[str, Any]]] = {}

    async def start(self) -> None:
        """Connect to NATS and subscribe to statistics.response."""
        self._nc = await nats.connect(self._nats_url, connect_timeout=10)
        self._js = self._nc.jetstream()

        self._sub = await self._nc.subscribe(
            self._response_subject, cb=self._handle_response
        )
        logger.info(
            "NatsStatisticsClient started, subscribed to %s",
            self._response_subject,
        )

    async def stop(self) -> None:
        """Unsubscribe and drain the NATS connection."""
        if self._sub is not None:
            await self._sub.unsubscribe()
            self._sub = None
        for future in self._pending.values():
            if not future.done():
                future.cancel()
        self._pending.clear()
        if self._nc is not None and not self._nc.is_closed:
            await self._nc.drain()
            self._nc = None
            self._js = None
        logger.info("NatsStatisticsClient stopped")

    async def _handle_response(self, msg: Any) -> None:
        try:
            payload = json.loads(msg.data.decode())
        except json.JSONDecodeError as e:
            logger.error("Invalid JSON in statistics.response: %s", e)
            return

        correlation_id = payload.get("correlation_id", "")
        future = self._pending.pop(correlation_id, None)
        if future is not None and not future.done():
            future.set_result(payload)

    async def request(
        self, method: str, data: dict, timeout: float | None = None
    ) -> dict:
        """Send a single RPC request and wait for the response."""
        if self._js is None or self._nc is None:
            raise GraphicsDataError(
                "NatsStatisticsClient not started",
                code="DATA_SOURCE_UNAVAILABLE",
            )

        cid = str(uuid.uuid4())
        loop = asyncio.get_running_loop()
        future: asyncio.Future[dict[str, Any]] = loop.create_future()
        self._pending[cid] = future

        body = {"method": method, "correlation_id": cid, **data}
        payload = json.dumps(body, default=str).encode()

        try:
            await self._js.publish(self._request_subject, payload)
        except Exception as e:
            self._pending.pop(cid, None)
            raise GraphicsDataError(
                f"Failed to publish statistics request: {e}",
                code="DATA_SOURCE_UNAVAILABLE",
            ) from e

        try:
            result = await asyncio.wait_for(
                future, timeout=timeout or self._timeout
            )
        except asyncio.TimeoutError:
            self._pending.pop(cid, None)
            raise GraphicsDataError(
                "Statistics service timeout",
                code="UPSTREAM_TIMEOUT",
            )

        if "error" in result:
            raise GraphicsDataError(
                result["error"],
                code=result.get("code", "UPSTREAM_ERROR"),
            )

        return result
