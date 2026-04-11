"""Tests for position distribution.

Verifies that PositionDistributionBuilder correctly builds distribution
from a single metric's datasets, and that MetricsStrategy produces
position_distribution diagrams only for position-related metrics
(PY, PG, POS), one per metric.
"""

import uuid
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.application.commands import BuildGraphicsCommand, PeriodSpec, SeriesRequestItem
from app.application.graphics.data_processor import DataProcessor
from app.application.graphics.metric_resolver import MetricResolver
from app.application.graphics.strategy import MetricsStrategy
from app.application.graphics.visualization_builder import PositionDistributionBuilder
from app.domain.models.graphics import MetricField, TimeseriesDataset


# ── Helpers ──


def _ds(entity_id: uuid.UUID, values: list[float | None]) -> TimeseriesDataset:
    """Shorthand to build a TimeseriesDataset."""
    return TimeseriesDataset(
        entity_id=entity_id,
        entity_label=str(entity_id),
        values=values,
        dates=[date(2026, 1, 1 + i) for i in range(len(values))],
    )


def _field(abbr: str) -> MetricField:
    return MetricField(
        id=uuid.uuid4(),
        name=f"Metric {abbr}",
        abbreviation=abbr,
        field_type="float",
        source_id=uuid.uuid4(),
        aggregation={"query": "average", "project": "average"},
        reverse_trend=True,
    )


# ── PositionDistributionBuilder unit tests ──


class TestPositionDistributionBuilder:
    """Unit tests for the PositionDistributionBuilder itself."""

    def setup_method(self):
        self.builder = PositionDistributionBuilder()

    def test_single_source_counts(self):
        """Entities from one metric are bucketed correctly."""
        e1, e2, e3 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        datasets = [
            _ds(e1, [2.0, 2.0, 1.0]),   # position 2→1, bucket 1-3
            _ds(e2, [15.0, 12.0, 8.0]),  # position 15→8, bucket 1-10
            _ds(e3, [50.0, 55.0, 60.0]), # position 50→60, bucket 51-100
        ]

        result = self.builder.build(datasets)

        assert result["type"] == "position_distribution"
        assert result["total"] == 3

        by_label = {b["label"]: b for b in result["buckets"]}
        assert by_label["1-3"]["count"] == 1    # e1 ends at 1
        assert by_label["1-10"]["count"] == 2   # e1(1) + e2(8)
        assert by_label["51-100"]["count"] == 1  # e3 ends at 60

    def test_delta_calculation(self):
        """Deltas (end_count - start_count) are correct."""
        e1, e2 = uuid.uuid4(), uuid.uuid4()
        datasets = [
            _ds(e1, [5.0, 3.0, 1.0]),   # start=5 (1-10), end=1 (1-3)
            _ds(e2, [25.0, 15.0, 8.0]),  # start=25 (11-30), end=8 (1-10)
        ]

        result = self.builder.build(datasets)
        by_label = {b["label"]: b for b in result["buckets"]}

        # 1-3: start=0, end=1 → delta=+1
        assert by_label["1-3"]["delta"] == 1
        # 1-10: start=1(e1), end=2(e1+e2) → delta=+1
        assert by_label["1-10"]["delta"] == 1
        # 11-30: start=1(e2), end=0 → delta=-1
        assert by_label["11-30"]["delta"] == -1

    def test_percentages(self):
        """Percentages are based on total entity count."""
        entities = [uuid.uuid4() for _ in range(4)]
        datasets = [
            _ds(entities[0], [1.0]),   # 1-3, 1-10
            _ds(entities[1], [5.0]),   # 1-10
            _ds(entities[2], [20.0]),  # 11-30
            _ds(entities[3], [40.0]),  # 31-50
        ]

        result = self.builder.build(datasets)
        by_label = {b["label"]: b for b in result["buckets"]}

        assert result["total"] == 4
        assert by_label["1-3"]["percentage"] == 25   # 1/4 = 25%
        assert by_label["1-10"]["percentage"] == 50   # 2/4 = 50%
        assert by_label["11-30"]["percentage"] == 25  # 1/4 = 25%
        assert by_label["31-50"]["percentage"] == 25  # 1/4 = 25%

    def test_empty_datasets(self):
        """No datasets produces zero counts with total=1 (no division by zero)."""
        result = self.builder.build([])

        assert result["total"] == 1
        assert all(b["count"] == 0 for b in result["buckets"])
        assert all(b["delta"] == 0 for b in result["buckets"])

    def test_all_none_values(self):
        """Entities with only None values are excluded from distribution."""
        e1 = uuid.uuid4()
        result = self.builder.build([_ds(e1, [None, None, None])])

        assert result["total"] == 1  # fallback, no ends found
        assert all(b["count"] == 0 for b in result["buckets"])

    def test_series_id_passed_through(self):
        """series_id kwarg is included in output."""
        result = self.builder.build([_ds(uuid.uuid4(), [5.0])], series_id="PY")
        assert result["series_id"] == "PY"

    def test_series_id_defaults_to_empty(self):
        """When called without series_id, the output has empty series_id."""
        result = self.builder.build([_ds(uuid.uuid4(), [5.0])])
        assert result["series_id"] == ""

    def test_100_plus_bucket(self):
        """Entities with position > 100 fall into 100+ bucket."""
        e1 = uuid.uuid4()
        result = self.builder.build([_ds(e1, [150.0])])

        by_label = {b["label"]: b for b in result["buckets"]}
        assert by_label["100+"]["count"] == 1


# ── MetricsStrategy integration tests ──


class TestMetricsStrategyPositionDistribution:
    """Tests that MetricsStrategy produces position_distribution diagrams
    only for position-related metrics, one per metric."""

    def _make_strategy(self, datasets_per_metric: dict[str, list[TimeseriesDataset]]):
        """Build a MetricsStrategy with mocked providers."""
        ts_provider = AsyncMock()

        field_map: dict[str, MetricField] = {}
        for abbr in datasets_per_metric:
            field_map[abbr] = _field(abbr)

        resolver = AsyncMock(spec=MetricResolver)
        resolver.resolve = AsyncMock(side_effect=lambda code, entity: field_map[code])

        async def mock_fetch(**kwargs):
            field = kwargs["field"]
            return datasets_per_metric.get(field.abbreviation, [])

        ts_provider.fetch_timeseries = AsyncMock(side_effect=mock_fetch)

        processor = DataProcessor()
        return MetricsStrategy(
            timeseries_provider=ts_provider,
            data_processor=processor,
            metric_resolver=resolver,
        )

    def _make_command(self, metric_codes: list[str], visualizations: list[str]):
        return BuildGraphicsCommand(
            project_id=uuid.uuid4(),
            product="metrics",
            entity="query",
            period=PeriodSpec(
                date_from=date(2026, 3, 1),
                date_to=date(2026, 3, 10),
                granularity="day",
            ),
            requested_series=[
                SeriesRequestItem(series_kind="metric", metric_code=code)
                for code in metric_codes
            ],
            requested_visualizations=visualizations,
        )

    @pytest.mark.asyncio
    async def test_position_metrics_get_distributions(self):
        """Position metrics (PY, PG) each get their own distribution."""
        e1, e2 = uuid.uuid4(), uuid.uuid4()

        strategy = self._make_strategy({
            "PY": [_ds(e1, [2.0] * 10)],
            "PG": [_ds(e2, [15.0] * 10)],
        })
        command = self._make_command(["PY", "PG"], ["position_distribution"])
        result = await strategy.execute(command)

        pos_diagrams = [d for d in result.diagrams if d.get("type") == "position_distribution"]
        assert len(pos_diagrams) == 2

        series_ids = {d["series_id"] for d in pos_diagrams}
        assert series_ids == {"PY", "PG"}

    @pytest.mark.asyncio
    async def test_non_position_metric_no_distribution(self):
        """Non-position metrics (e.g. CTR) do NOT get position_distribution."""
        e1, e2 = uuid.uuid4(), uuid.uuid4()

        strategy = self._make_strategy({
            "PY": [_ds(e1, [5.0] * 10)],
            "CTR": [_ds(e2, [0.5] * 10)],
        })
        command = self._make_command(["PY", "CTR"], ["position_distribution"])
        result = await strategy.execute(command)

        pos_diagrams = [d for d in result.diagrams if d.get("type") == "position_distribution"]
        assert len(pos_diagrams) == 1
        assert pos_diagrams[0]["series_id"] == "PY"

    @pytest.mark.asyncio
    async def test_only_non_position_metrics_no_distribution(self):
        """If only non-position metrics are selected, no distribution is built."""
        e1, e2 = uuid.uuid4(), uuid.uuid4()

        strategy = self._make_strategy({
            "CTR": [_ds(e1, [0.5] * 10)],
            "IMP": [_ds(e2, [100.0] * 10)],
        })
        command = self._make_command(["CTR", "IMP"], ["position_distribution"])
        result = await strategy.execute(command)

        pos_diagrams = [d for d in result.diagrams if d.get("type") == "position_distribution"]
        assert len(pos_diagrams) == 0

    @pytest.mark.asyncio
    async def test_single_position_metric(self):
        """1 position metric → exactly 1 position_distribution diagram."""
        e1 = uuid.uuid4()

        strategy = self._make_strategy({
            "PY": [_ds(e1, [5.0] * 10)],
        })
        command = self._make_command(["PY"], ["position_distribution"])
        result = await strategy.execute(command)

        pos_diagrams = [d for d in result.diagrams if d.get("type") == "position_distribution"]
        assert len(pos_diagrams) == 1
        assert pos_diagrams[0]["series_id"] == "PY"
        assert pos_diagrams[0]["total"] == 1

    @pytest.mark.asyncio
    async def test_pie_still_per_series(self):
        """Pie diagrams are still generated per-series for all metrics."""
        e1, e2 = uuid.uuid4(), uuid.uuid4()

        strategy = self._make_strategy({
            "PY": [_ds(e1, [2.0, 3.0, 1.0] + [None] * 7)],
            "CTR": [_ds(e2, [0.5, 0.6, 0.7] + [None] * 7)],
        })
        command = self._make_command(["PY", "CTR"], ["pie", "position_distribution"])
        result = await strategy.execute(command)

        pie_diagrams = [d for d in result.diagrams if d.get("type") == "pie"]
        pos_diagrams = [d for d in result.diagrams if d.get("type") == "position_distribution"]

        assert len(pie_diagrams) == 2  # one per metric
        assert len(pos_diagrams) == 1  # only PY (position metric)

    @pytest.mark.asyncio
    async def test_no_position_distribution_when_not_requested(self):
        """If position_distribution not in requested_visualizations, none is built."""
        e1 = uuid.uuid4()

        strategy = self._make_strategy({
            "PY": [_ds(e1, [5.0] * 10)],
        })
        command = self._make_command(["PY"], ["pie"])
        result = await strategy.execute(command)

        pos_diagrams = [d for d in result.diagrams if d.get("type") == "position_distribution"]
        assert len(pos_diagrams) == 0

    @pytest.mark.asyncio
    async def test_no_data_no_distribution(self):
        """If position metric returns empty datasets, no distribution is built."""
        strategy = self._make_strategy({
            "PY": [],
        })
        command = self._make_command(["PY"], ["position_distribution"])
        result = await strategy.execute(command)

        pos_diagrams = [d for d in result.diagrams if d.get("type") == "position_distribution"]
        assert len(pos_diagrams) == 0

    @pytest.mark.asyncio
    async def test_three_position_metrics_three_distributions(self):
        """3 position metrics → 3 separate position_distribution diagrams."""
        e1, e2, e3 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()

        strategy = self._make_strategy({
            "PY": [_ds(e1, [2.0] * 10)],
            "PG": [_ds(e2, [15.0] * 10)],
            "POS": [_ds(e3, [50.0] * 10)],
        })
        command = self._make_command(["PY", "PG", "POS"], ["position_distribution"])
        result = await strategy.execute(command)

        pos_diagrams = [d for d in result.diagrams if d.get("type") == "position_distribution"]
        assert len(pos_diagrams) == 3

        series_ids = {d["series_id"] for d in pos_diagrams}
        assert series_ids == {"PY", "PG", "POS"}

    @pytest.mark.asyncio
    async def test_each_distribution_has_own_entity_count(self):
        """Each metric's distribution reflects only its own entities."""
        py_entities = [uuid.uuid4() for _ in range(5)]
        pg_entities = [uuid.uuid4() for _ in range(3)]

        strategy = self._make_strategy({
            "PY": [_ds(e, [float(i + 1)] * 10) for i, e in enumerate(py_entities)],
            "PG": [_ds(e, [float(20 + i)] * 10) for i, e in enumerate(pg_entities)],
        })
        command = self._make_command(["PY", "PG"], ["position_distribution"])
        result = await strategy.execute(command)

        pos_diagrams = [d for d in result.diagrams if d.get("type") == "position_distribution"]
        by_series = {d["series_id"]: d for d in pos_diagrams}

        assert by_series["PY"]["total"] == 5
        assert by_series["PG"]["total"] == 3
