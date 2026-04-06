"""MetricResolver — resolves metric codes to MetricField and validates entity support."""

from __future__ import annotations

from app.domain.exceptions import GraphicsValidationError
from app.domain.interfaces.providers.timeseries_provider import ITimeseriesProvider
from app.domain.models.graphics import MetricField


class MetricResolver:
    """Resolves metric abbreviations to MetricField objects.

    Caches fields per request lifecycle (no cross-request caching here;
    Redis caching can be added at the provider level).
    """

    def __init__(self, provider: ITimeseriesProvider) -> None:
        self._provider = provider
        self._cache: dict[str, MetricField] | None = None

    async def resolve(self, abbreviation: str, entity_type: str) -> MetricField:
        """Resolve a metric abbreviation to a MetricField.

        Raises GraphicsValidationError if metric not found or not supported
        for the given entity type.
        """
        fields = await self._load_fields()
        field = fields.get(abbreviation)
        if field is None:
            raise GraphicsValidationError(
                message=f"Unknown metric: {abbreviation}",
                code=GraphicsValidationError.UNKNOWN_METRIC,
            )

        if entity_type not in field.aggregation:
            raise GraphicsValidationError(
                message=f"Metric '{abbreviation}' does not support entity type '{entity_type}'",
                code=GraphicsValidationError.UNKNOWN_ENTITY,
            )

        return field

    async def resolve_many(
        self, abbreviations: list[str], entity_type: str
    ) -> list[MetricField]:
        """Resolve multiple metric abbreviations."""
        return [await self.resolve(abbr, entity_type) for abbr in abbreviations]

    async def _load_fields(self) -> dict[str, MetricField]:
        if self._cache is None:
            all_fields = await self._provider.fetch_metric_fields()
            self._cache = {f.abbreviation: f for f in all_fields}
        return self._cache
