"""Product strategies — product-specific orchestration logic.

Each strategy knows how to build series and diagrams for its product type
(metrics, projects, alerts). The GraphicsService delegates to the appropriate
strategy based on BuildGraphicsCommand.product.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.application.commands import BuildGraphicsCommand
from app.application.graphics.data_processor import DataProcessor
from app.application.graphics.metric_resolver import MetricResolver
from app.application.graphics.series_builder import (
    AlertSeriesBuilder,
    MetricSeriesBuilder,
)
from app.application.graphics.visualization_builder import get_visualization_builder
from app.domain.interfaces.providers.alert_provider import IAlertProvider
from app.domain.interfaces.providers.timeseries_provider import ITimeseriesProvider
from app.domain.models.graphics import GraphicsResult, SeriesData


class IProductStrategy(ABC):
    """Base interface for product strategies."""

    @abstractmethod
    async def execute(self, command: BuildGraphicsCommand) -> GraphicsResult:
        ...


class MetricsStrategy(IProductStrategy):
    """Strategy for 'metrics' product — line charts of metric timeseries.

    This is the priority deliverable: line charts in "показатели".
    """

    def __init__(
        self,
        timeseries_provider: ITimeseriesProvider,
        data_processor: DataProcessor,
        metric_resolver: MetricResolver,
    ) -> None:
        self._ts = timeseries_provider
        self._processor = data_processor
        self._resolver = metric_resolver

    async def execute(self, command: BuildGraphicsCommand) -> GraphicsResult:
        all_series: list[SeriesData] = []
        all_diagrams: list[dict[str, Any]] = []
        builder = MetricSeriesBuilder()

        for req in command.requested_series:
            if req.series_kind != "metric" or not req.metric_code:
                continue

            field = await self._resolver.resolve(req.metric_code, command.entity)

            grouping = req.grouping or command.period.granularity

            datasets = await self._ts.fetch_timeseries(
                entity_type=command.entity,
                project_id=command.project_id,
                field=field,
                date_from=command.period.date_from,
                date_to=command.period.date_to,
                grouping=grouping,
                filter_value_ids=self._flatten_filters(command),
                entity_ids=None,
            )

            datasets = self._processor.process(datasets, compute_deltas=True)

            # Build line series
            for ds in datasets:
                series = builder.build(
                    dataset=ds,
                    metric_code=req.metric_code,
                    render_type=req.mode or "line",
                )
                all_series.append(series)

            # Build visualization diagrams (pie, histogram, etc.)
            for vis_type in command.requested_visualizations:
                vis_builder = get_visualization_builder(vis_type)
                if vis_builder is not None and datasets:
                    diagram = vis_builder.build(
                        datasets,
                        reverse_trend=field.reverse_trend,
                    )
                    all_diagrams.append(diagram)

        return GraphicsResult(
            series=all_series,
            diagrams=all_diagrams,
            meta={
                "product": "metrics",
                "entity": command.entity,
                "period": {
                    "from": command.period.date_from.isoformat(),
                    "to": command.period.date_to.isoformat(),
                    "granularity": command.period.granularity,
                },
            },
        )

    @staticmethod
    def _flatten_filters(command: BuildGraphicsCommand) -> list | None:
        """Convert filter dict to flat list of filter_value_ids (UUIDs)."""
        if not command.filters:
            return None
        import uuid

        result = []
        for ids in command.filters.values():
            for id_str in ids:
                try:
                    result.append(uuid.UUID(id_str))
                except ValueError:
                    continue
        return result or None


class AlertsStrategy(IProductStrategy):
    """Strategy for 'alerts' product — alert event markers."""

    def __init__(
        self,
        alert_provider: IAlertProvider,
    ) -> None:
        self._alerts = alert_provider

    async def execute(self, command: BuildGraphicsCommand) -> GraphicsResult:
        events = await self._alerts.fetch_alert_history(
            project_id=command.project_id,
            entity_type=command.entity,
            date_from=command.period.date_from,
            date_to=command.period.date_to,
        )

        builder = AlertSeriesBuilder()
        series = builder.build(events=events, alert_code="default")

        return GraphicsResult(
            series=[series] if events else [],
            meta={"product": "alerts", "entity": command.entity},
        )


# ── Strategy registry ──

_STRATEGIES: dict[str, type[IProductStrategy]] = {
    "metrics": MetricsStrategy,
    "alerts": AlertsStrategy,
}


def get_strategy_class(product: str) -> type[IProductStrategy] | None:
    return _STRATEGIES.get(product)
