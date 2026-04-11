"""NATS-based provider for statistics RPC calls (projects, filters).

Wraps NatsStatisticsClient for endpoints that were previously served
directly by StatisticRepository in graphics routes.
"""

from __future__ import annotations

from uuid import UUID

from app.infrastructure.messaging.nats_statistics_client import NatsStatisticsClient


class NATSStatisticsRPCProvider:
    """Proxy for projects.search, filters.fields, filters.values via NATS."""

    def __init__(self, client: NatsStatisticsClient) -> None:
        self._client = client

    async def search_projects(self, query: str, limit: int = 10) -> list[dict]:
        data = await self._client.request("projects.search", {
            "query": query,
            "limit": limit,
        })
        return data["projects"]

    async def get_filter_fields(self) -> list[dict]:
        data = await self._client.request("filters.fields", {})
        return data["fields"]

    async def get_filter_values(self, field_id: UUID) -> list[dict]:
        data = await self._client.request("filters.values", {
            "field_id": str(field_id),
        })
        return data["values"]
