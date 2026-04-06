"""Timeseries data provider interface (Layer 1 adapter contract)."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from datetime import date

from app.domain.models.graphics import MetricField, TimeseriesDataset


class ITimeseriesProvider(ABC):
    """Contract for fetching timeseries data from any storage backend.

    Implementations: PostgresTimeseriesProvider (now), ClickHouse (future).
    """

    @abstractmethod
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
        """Fetch timeseries datasets for a given metric and entity type."""

    @abstractmethod
    async def fetch_metric_fields(
        self,
        *,
        abbreviations: list[str] | None = None,
    ) -> list[MetricField]:
        """Fetch metric field definitions, optionally filtered by abbreviation."""

    @abstractmethod
    async def resolve_entity_ids(
        self,
        *,
        project_id: uuid.UUID,
        entity_type: str,
    ) -> list[uuid.UUID]:
        """Resolve all entity IDs belonging to a project for a given entity type."""
