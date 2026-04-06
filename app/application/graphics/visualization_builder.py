"""Visualization builders — convert TimeseriesDatasets into diagram structures.

Generates format-agnostic JSON for pie charts, histograms, range summaries, etc.
Line charts are handled by SeriesBuilder, not here.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.domain.models.graphics import TimeseriesDataset


class IVisualizationBuilder(ABC):
    """Base interface for visualization builders."""

    @abstractmethod
    def build(self, datasets: list[TimeseriesDataset], **kwargs) -> dict[str, Any]:
        ...


class PieVisualizationBuilder(IVisualizationBuilder):
    """Classifies entities by growth/fall/no_change over the period."""

    def build(
        self,
        datasets: list[TimeseriesDataset],
        *,
        reverse_trend: bool = False,
        **kwargs,
    ) -> dict[str, Any]:
        growth_ids: list[str] = []
        fall_ids: list[str] = []
        no_change_ids: list[str] = []

        for ds in datasets:
            vals = ds.values
            if not vals:
                continue

            start_val = next((v for v in vals if v is not None), None)
            end_val = next((v for v in reversed(vals) if v is not None), None)

            if start_val is None or end_val is None:
                no_change_ids.append(str(ds.entity_id))
                continue

            delta = end_val - start_val
            eid = str(ds.entity_id)

            if reverse_trend:
                if start_val == 0 and end_val == 0:
                    no_change_ids.append(eid)
                elif start_val == 0:
                    growth_ids.append(eid)
                elif end_val == 0:
                    fall_ids.append(eid)
                elif delta > 0:
                    fall_ids.append(eid)
                elif delta < 0:
                    growth_ids.append(eid)
                else:
                    no_change_ids.append(eid)
            else:
                if delta > 0:
                    growth_ids.append(eid)
                elif delta < 0:
                    fall_ids.append(eid)
                else:
                    no_change_ids.append(eid)

        data = []
        if growth_ids:
            data.append({"id": "growth", "label": "Выросло", "value": len(growth_ids), "entity_ids": growth_ids})
        if no_change_ids:
            data.append({"id": "no_change", "label": "Не изменилось", "value": len(no_change_ids), "entity_ids": no_change_ids})
        if fall_ids:
            data.append({"id": "fall", "label": "Упало", "value": len(fall_ids), "entity_ids": fall_ids})

        return {"type": "pie", "legend": "Распределение по динамике", "data": data}


class HistogramVisualizationBuilder(IVisualizationBuilder):
    """Builds a histogram of latest values distribution."""

    def build(
        self,
        datasets: list[TimeseriesDataset],
        *,
        bucket_count: int = 10,
        **kwargs,
    ) -> dict[str, Any]:
        last_values: list[float] = []
        for ds in datasets:
            val = next((v for v in reversed(ds.values) if v is not None), None)
            if val is not None:
                last_values.append(val)

        if not last_values:
            return {"type": "histogram", "buckets": [], "stats": {}}

        min_val = min(last_values)
        max_val = max(last_values)

        if min_val == max_val:
            return {
                "type": "histogram",
                "buckets": [{"from": min_val, "to": max_val, "count": len(last_values)}],
                "stats": {"min": min_val, "max": max_val, "avg": min_val, "count": len(last_values)},
            }

        step = (max_val - min_val) / bucket_count
        buckets: list[dict[str, Any]] = []
        for i in range(bucket_count):
            lo = min_val + i * step
            hi = lo + step
            count = sum(1 for v in last_values if lo <= v < hi or (i == bucket_count - 1 and v == hi))
            buckets.append({"from": round(lo, 2), "to": round(hi, 2), "count": count})

        avg_val = sum(last_values) / len(last_values)
        return {
            "type": "histogram",
            "buckets": buckets,
            "stats": {
                "min": round(min_val, 2),
                "max": round(max_val, 2),
                "avg": round(avg_val, 2),
                "count": len(last_values),
            },
        }


# ── Registry ──

_VIS_BUILDERS: dict[str, type[IVisualizationBuilder]] = {
    "pie": PieVisualizationBuilder,
    "histogram": HistogramVisualizationBuilder,
}


def get_visualization_builder(vis_type: str) -> IVisualizationBuilder | None:
    """Get a visualization builder instance by type. Returns None for 'line' (handled by SeriesBuilder)."""
    if vis_type == "line":
        return None
    cls = _VIS_BUILDERS.get(vis_type)
    if cls is None:
        return None
    return cls()
