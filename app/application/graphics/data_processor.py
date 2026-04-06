"""DataProcessor — transforms raw TimeseriesDataset into presentation-ready data.

Handles:
- Delta calculation (absolute difference between consecutive points)
- Gap filling (missing dates → None)
- Normalization (optional, e.g. percentage of first value)
"""

from __future__ import annotations

from app.domain.models.graphics import TimeseriesDataset


class DataProcessor:
    """Stateless processor that transforms TimeseriesDataset objects."""

    def compute_deltas(self, dataset: TimeseriesDataset) -> TimeseriesDataset:
        """Compute absolute deltas between consecutive values."""
        values = dataset.values
        deltas: list[float | None] = [None]  # first point has no delta

        for i in range(1, len(values)):
            prev, curr = values[i - 1], values[i]
            if prev is not None and curr is not None:
                deltas.append(round(curr - prev, 6))
            else:
                deltas.append(None)

        return dataset.model_copy(update={"deltas": deltas})

    def fill_gaps(
        self, datasets: list[TimeseriesDataset]
    ) -> list[TimeseriesDataset]:
        """Ensure all datasets cover the same date grid (already done by provider)."""
        # The PostgresTimeseriesProvider already aligns to a date grid,
        # so this is a pass-through for now. Future: cross-dataset alignment.
        return datasets

    def normalize_to_percentage(
        self, dataset: TimeseriesDataset
    ) -> TimeseriesDataset:
        """Normalize values as percentage of the first non-None value."""
        base = next((v for v in dataset.values if v is not None), None)
        if base is None or base == 0:
            return dataset

        normalized = [
            round(v / base * 100, 2) if v is not None else None
            for v in dataset.values
        ]
        return dataset.model_copy(update={"values": normalized})

    def process(
        self,
        datasets: list[TimeseriesDataset],
        *,
        compute_deltas: bool = True,
        normalize: bool = False,
    ) -> list[TimeseriesDataset]:
        """Run the full processing pipeline on a list of datasets."""
        datasets = self.fill_gaps(datasets)

        result: list[TimeseriesDataset] = []
        for ds in datasets:
            if compute_deltas:
                ds = self.compute_deltas(ds)
            if normalize:
                ds = self.normalize_to_percentage(ds)
            result.append(ds)

        return result
