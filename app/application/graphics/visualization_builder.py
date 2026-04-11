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

        series_id = kwargs.get("series_id", "")
        legend = "Распределение по динамике"
        if series_id:
            legend = f"{series_id} — {legend}"
        return {"type": "pie", "legend": legend, "series_id": series_id, "data": data}


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

        series_id = kwargs.get("series_id", "")

        if not last_values:
            return {"type": "histogram", "series_id": series_id, "buckets": [], "stats": {}}

        min_val = min(last_values)
        max_val = max(last_values)

        if min_val == max_val:
            return {
                "type": "histogram",
                "series_id": series_id,
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
            "series_id": series_id,
            "buckets": buckets,
            "stats": {
                "min": round(min_val, 2),
                "max": round(max_val, 2),
                "avg": round(avg_val, 2),
                "count": len(last_values),
            },
        }


class PositionDistributionBuilder(IVisualizationBuilder):
    """Distributes entities into fixed position buckets with deltas."""

    BUCKETS = [
        (1, 3, "1-3", "#1890ff"),
        (1, 10, "1-10", "#52c41a"),
        (11, 30, "11-30", "#52c41a"),
        (31, 50, "31-50", "#faad14"),
        (51, 100, "51-100", "#faad14"),
        (101, float("inf"), "100+", "#8c8c8c"),
    ]

    def build(
        self,
        datasets: list[TimeseriesDataset],
        **kwargs,
    ) -> dict[str, Any]:
        series_id = kwargs.get("series_id", "")

        # Gather first and last non-null value per entity
        starts: list[float] = []
        ends: list[float] = []
        for ds in datasets:
            vals = ds.values
            if not vals:
                continue
            start = next((v for v in vals if v is not None), None)
            end = next((v for v in reversed(vals) if v is not None), None)
            if start is not None:
                starts.append(start)
            if end is not None:
                ends.append(end)

        total = len(ends) or 1

        buckets: list[dict[str, Any]] = []
        for lo, hi, label, color in self.BUCKETS:
            count_end = sum(1 for v in ends if lo <= v <= hi) if hi != float("inf") else sum(1 for v in ends if v >= lo)
            count_start = sum(1 for v in starts if lo <= v <= hi) if hi != float("inf") else sum(1 for v in starts if v >= lo)
            pct = round(count_end / total * 100) if total else 0
            delta = count_end - count_start
            buckets.append({
                "label": label,
                "color": color,
                "percentage": pct,
                "count": count_end,
                "delta": delta,
            })

        return {
            "type": "position_distribution",
            "series_id": series_id,
            "buckets": buckets,
            "total": total,
        }


# ── Registry ──

_VIS_BUILDERS: dict[str, type[IVisualizationBuilder]] = {
    "pie": PieVisualizationBuilder,
    "histogram": HistogramVisualizationBuilder,
    "position_distribution": PositionDistributionBuilder,
}


def get_visualization_builder(vis_type: str) -> IVisualizationBuilder | None:
    """Get a visualization builder instance by type. Returns None for 'line' (handled by SeriesBuilder)."""
    if vis_type == "line":
        return None
    cls = _VIS_BUILDERS.get(vis_type)
    if cls is None:
        return None
    return cls()
