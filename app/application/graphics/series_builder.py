"""Series builders — convert TimeseriesDataset to SeriesData.

Each builder knows how to transform a dataset into a specific series type
(metric line, alert markers, etc.).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.models.graphics import (
    AlertEvent,
    PointValue,
    SeriesData,
    TimeseriesDataset,
)


class ISeriesBuilder(ABC):
    """Base interface for series builders."""

    @abstractmethod
    def build(self, **kwargs) -> SeriesData:
        ...


class MetricSeriesBuilder(ISeriesBuilder):
    """Builds a line series from a TimeseriesDataset."""

    def build(
        self,
        *,
        dataset: TimeseriesDataset,
        metric_code: str,
        unit: str = "",
        render_type: str = "line",
        **kwargs,
    ) -> SeriesData:
        points = [
            PointValue(
                x=d,
                y=v,
                raw_value=v,
                is_missing=v is None,
            )
            for d, v in zip(dataset.dates, dataset.values)
        ]

        delta_map = {}
        if dataset.deltas:
            delta_map = {
                d.isoformat(): dv
                for d, dv in zip(dataset.dates, dataset.deltas)
                if dv is not None
            }

        return SeriesData(
            id=f"{metric_code}_{dataset.entity_id}",
            type="metric",
            label=dataset.entity_label,
            unit=unit,
            render_type=render_type,
            points=points,
            meta={
                "metric_code": metric_code,
                "entity_id": str(dataset.entity_id),
                "deltas": delta_map,
            },
        )


class AlertSeriesBuilder(ISeriesBuilder):
    """Builds marker series from alert events."""

    def build(
        self,
        *,
        events: list[AlertEvent],
        alert_code: str = "alert",
        **kwargs,
    ) -> SeriesData:
        points = [
            PointValue(
                x=ev.triggered_at,
                y=1.0,
                raw_value=None,
            )
            for ev in events
        ]

        return SeriesData(
            id=f"alert_{alert_code}",
            type="alert",
            label=f"Alerts ({alert_code})",
            render_type="scatter",
            points=points,
            meta={
                "alert_code": alert_code,
                "events": [
                    {
                        "entity_id": str(ev.entity_id),
                        "entity_label": ev.entity_label,
                        "event_type": ev.event_type,
                        "new_status": ev.new_status,
                        "triggered_at": ev.triggered_at.isoformat(),
                    }
                    for ev in events
                ],
            },
        )


# ── Registry ──

_SERIES_BUILDERS: dict[str, type[ISeriesBuilder]] = {
    "metric": MetricSeriesBuilder,
    "alert": AlertSeriesBuilder,
}


def get_series_builder(kind: str) -> ISeriesBuilder:
    """Get a series builder instance by kind."""
    cls = _SERIES_BUILDERS.get(kind)
    if cls is None:
        raise ValueError(f"Unknown series kind: {kind}")
    return cls()
