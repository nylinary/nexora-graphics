"""PostgreSQL implementation of ITimeseriesProvider.

Wraps StatisticRepository and adds source entity resolution logic
ported from main-be's AggregationToolsMixin._resolve_source_entity_type.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import date, datetime, time, timezone

from app.domain.interfaces.providers.timeseries_provider import ITimeseriesProvider
from app.domain.models.graphics import MetricField, TimeseriesDataset
from app.infrastructure.persistence.statistic_repository import StatisticRepository

# Priority map for source entity resolution (ported from main-be)
_PRIORITY_MAP: dict[str, tuple[str, ...]] = {
    "project": ("page", "query", "cluster"),
    "cluster": ("query", "page"),
    "page": (),
    "query": (),
}


class PostgresTimeseriesProvider(ITimeseriesProvider):
    """Fetches timeseries data from PostgreSQL via StatisticRepository.

    This adapter handles:
    1. Source entity resolution (which entity type stores raw data)
    2. Converting date range to datetime
    3. Calling the 3-tier SQL pipeline
    4. Converting raw rows to TimeseriesDataset
    """

    def __init__(self, repo: StatisticRepository) -> None:
        self._repo = repo

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
        target_entity_type = entity_type
        target_agg = field.aggregation.get(target_entity_type)
        if target_agg is None:
            return []

        source_entity_type = self._resolve_source_entity(field, target_entity_type)
        source_agg = field.aggregation.get(source_entity_type, target_agg)

        # For use_cluster at target, the real aggregation comes from the source
        if target_agg == "use_cluster":
            target_agg = source_agg

        dt_from = datetime.combine(date_from, time.min, tzinfo=timezone.utc)
        dt_to = datetime.combine(date_to, time(23, 59, 59, 999999), tzinfo=timezone.utc)

        rows = await self._repo.get_timeseries(
            field_id=field.id,
            field_type=field.field_type.value,
            source_entity_type=source_entity_type,
            source_aggregation=source_agg,
            target_entity_type=target_entity_type,
            target_aggregation=target_agg,
            target_ids=entity_ids,
            date_from=dt_from,
            date_to=dt_to,
            filter_value_ids=filter_value_ids,
            grouping=grouping,
        )

        if not rows:
            return []

        # Resolve labels
        unique_ids = list({row["entity_id"] for row in rows})
        labels = await self._repo.resolve_entity_labels(
            entity_type=target_entity_type,
            entity_ids=unique_ids,
        )

        # Group rows by entity_id and build datasets
        return self._rows_to_datasets(rows, labels, date_from, date_to, grouping)

    async def fetch_metric_fields(
        self,
        *,
        abbreviations: list[str] | None = None,
    ) -> list[MetricField]:
        return await self._repo.get_metric_fields(abbreviations=abbreviations)

    async def resolve_entity_ids(
        self,
        *,
        project_id: uuid.UUID,
        entity_type: str,
    ) -> list[uuid.UUID]:
        return await self._repo.resolve_entity_ids(
            project_id=project_id,
            entity_type=entity_type,
        )

    # ── Source entity resolution (ported from AggregationToolsMixin) ──

    @staticmethod
    def _resolve_source_entity(field: MetricField, target_entity_type: str) -> str:
        """Determine which entity_type in statistic_values holds the raw data."""
        target_agg = field.aggregation.get(target_entity_type)
        if target_agg is None:
            return target_entity_type

        # use_cluster: delegate to cluster or query
        if target_agg == "use_cluster":
            if "cluster" in field.aggregation:
                if target_entity_type == "page" and "query" in field.aggregation:
                    return "query"
                return "cluster"
            return target_entity_type

        # Walk priority map to find the most granular source
        for candidate in _PRIORITY_MAP.get(target_entity_type, ()):
            cand_agg = field.aggregation.get(candidate)
            if cand_agg is not None and cand_agg != "use_cluster":
                return candidate

        return target_entity_type

    # ── Row → Dataset conversion ──

    @staticmethod
    def _rows_to_datasets(
        rows: list[dict[str, object]],
        labels: dict[uuid.UUID, str],
        date_from: date,
        date_to: date,
        grouping: str,
    ) -> list[TimeseriesDataset]:
        """Convert raw DB rows into TimeseriesDataset objects."""
        from collections import defaultdict

        by_entity: dict[uuid.UUID, dict[date, float | None]] = defaultdict(dict)

        for row in rows:
            eid = row["entity_id"]
            day_raw = row["day"]
            val = row["value"]

            if isinstance(day_raw, datetime):
                day = day_raw.date()
            elif isinstance(day_raw, date):
                day = day_raw
            else:
                day = date.fromisoformat(str(day_raw))

            if val is not None:
                try:
                    by_entity[eid][day] = float(val)
                except (ValueError, TypeError):
                    by_entity[eid][day] = None
            else:
                by_entity[eid][day] = None

        # Build date grid
        all_dates = _build_date_grid(date_from, date_to, grouping)

        datasets: list[TimeseriesDataset] = []
        for eid, day_map in by_entity.items():
            values = [day_map.get(d) for d in all_dates]
            datasets.append(
                TimeseriesDataset(
                    entity_id=eid,
                    entity_label=labels.get(eid, str(eid)),
                    values=values,
                    dates=all_dates,
                )
            )

        return datasets


def _build_date_grid(date_from: date, date_to: date, grouping: str) -> list[date]:
    """Generate the expected date points for the period."""
    from datetime import timedelta

    result: list[date] = []
    current = _normalize_period_start(date_from, grouping)
    end = _normalize_period_start(date_to, grouping)

    while current <= end:
        result.append(current)
        current = _next_period_start(current, grouping)
    return result


def _normalize_period_start(d: date, grouping: str) -> date:
    from datetime import timedelta

    if grouping == "week":
        return d - timedelta(days=d.weekday())
    if grouping == "month":
        return d.replace(day=1)
    return d


def _next_period_start(d: date, grouping: str) -> date:
    from datetime import timedelta

    if grouping == "week":
        return d + timedelta(weeks=1)
    if grouping == "month":
        if d.month == 12:
            return date(d.year + 1, 1, 1)
        return date(d.year, d.month + 1, 1)
    return d + timedelta(days=1)
