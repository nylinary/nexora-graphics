"""NATS-based implementation of ITimeseriesProvider.

Delegates to statistics-service via NatsStatisticsClient RPC.
"""

from __future__ import annotations

import uuid
from datetime import date

from app.domain.interfaces.providers.timeseries_provider import ITimeseriesProvider
from app.domain.models.graphics import MetricField, TimeseriesDataset
from app.infrastructure.messaging.nats_statistics_client import NatsStatisticsClient


class NATSTimeseriesProvider(ITimeseriesProvider):
    """Fetches timeseries data from statistics-service via NATS."""

    def __init__(self, client: NatsStatisticsClient) -> None:
        self._client = client

    async def fetch_timeseries(
        self,
        *,
        entity_type: str,
        project_id: uuid.UUID,
        field: MetricField,
        date_from: date,
        date_to: date,
        grouping: str,
        filter_value_ids: list[uuid.UUID] | None = None,
        entity_ids: list[uuid.UUID] | None = None,
    ) -> list[TimeseriesDataset]:
        data = await self._client.request("timeseries.fetch", {
            "entity_type": entity_type,
            "project_id": str(project_id),
            "field": field.model_dump(mode="json"),
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
            "grouping": grouping,
            "filter_value_ids": [str(x) for x in filter_value_ids] if filter_value_ids else None,
            "entity_ids": [str(x) for x in entity_ids] if entity_ids else None,
        })
        return [TimeseriesDataset.model_validate(d) for d in data["datasets"]]

    async def fetch_metric_fields(
        self,
        *,
        abbreviations: list[str] | None = None,
    ) -> list[MetricField]:
        data = await self._client.request("metrics.list", {
            "abbreviations": abbreviations,
        })
        return [MetricField.model_validate(f) for f in data["fields"]]

    async def resolve_entity_ids(
        self,
        *,
        project_id: uuid.UUID,
        entity_type: str,
    ) -> list[uuid.UUID]:
        data = await self._client.request("entities.resolve", {
            "project_id": str(project_id),
            "entity_type": entity_type,
        })
        return [uuid.UUID(x) for x in data["entity_ids"]]
