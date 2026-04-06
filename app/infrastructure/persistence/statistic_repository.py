"""Statistic repository — ported 3-tier SQL aggregation pipeline from main-be.

Tier 1: source entity aggregation (_build_base_query)
Tier 2: cross-entity join and re-aggregation (_build_target_stmt)
Tier 3: label resolution (resolve_entity_labels)

Uses SA Core expressions against ORM-mapped tables for raw SQL flexibility.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import datetime
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.graphics import FieldType, MetricField
from app.infrastructure.persistence.database import DatabaseManager
from app.infrastructure.persistence.models.statistic import (
    ClusterModel,
    PageModel,
    QueryModel,
    StatisticFieldModel,
    StatisticFilterValueModel,
    StatisticValueModel,
    StatisticValueToFilterValueModel,
)

# SA Core table references from ORM models
_sv = StatisticValueModel.__table__
_sfv = StatisticFilterValueModel.__table__
_sv2fv = StatisticValueToFilterValueModel.__table__
_queries = QueryModel.__table__
_clusters = ClusterModel.__table__
_pages = PageModel.__table__


class StatisticRepository:
    """Read-only repository for timeseries statistics.

    Implements the same 3-tier aggregation pipeline as main-be's
    ``statistic_repository.get_timeseries``.
    """

    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    # ── Public API ──

    async def get_timeseries(
        self,
        *,
        field_id: UUID,
        field_type: str,
        source_entity_type: str,
        source_aggregation: str,
        target_entity_type: str,
        target_aggregation: str,
        target_ids: Sequence[UUID] | None,
        date_from: datetime,
        date_to: datetime,
        filter_value_ids: Sequence[UUID] | None,
        grouping: str,
        session: AsyncSession | None = None,
    ) -> list[dict[str, object]]:
        """Execute the 3-tier aggregation pipeline and return raw rows.

        Returns list of dicts with keys: entity_id, day, value, aggregated_at.
        """
        if target_ids is not None and not target_ids:
            return []

        async def _run(sess: AsyncSession) -> list[dict[str, object]]:
            filter_groups, has_missing = await self._prepare_filter_groups(
                sess, filter_value_ids
            )
            if has_missing:
                return []

            base_q = self._build_base_query(
                field_id=field_id,
                field_type=field_type,
                source_entity_type=source_entity_type,
                source_aggregation=source_aggregation,
                date_from=date_from,
                date_to=date_to,
                filter_groups=filter_groups,
                grouping=grouping,
            )
            stmt = self._build_target_stmt(
                base_query=base_q,
                field_type=field_type,
                source_entity_type=source_entity_type,
                target_entity_type=target_entity_type,
                target_aggregation=target_aggregation,
                target_ids=target_ids,
            )

            result = await sess.execute(stmt)
            return [dict(row) for row in result.mappings().all()]

        if session:
            return await _run(session)
        async with self._db.session() as sess:
            return await _run(sess)

    async def get_metric_fields(
        self,
        *,
        abbreviations: list[str] | None = None,
        session: AsyncSession | None = None,
    ) -> list[MetricField]:
        """Fetch statistic field definitions."""
        async def _run(sess: AsyncSession) -> list[MetricField]:
            stmt = select(StatisticFieldModel)
            if abbreviations:
                stmt = stmt.where(StatisticFieldModel.abbreviation.in_(abbreviations))
            result = await sess.execute(stmt)
            rows = result.scalars().all()
            return [
                MetricField(
                    id=row.id,
                    name=row.name,
                    abbreviation=row.abbreviation,
                    field_type=FieldType(row.type),
                    source_id=row.source_id,
                    aggregation=row.aggregation,
                    reverse_trend=row.reverse_trend,
                )
                for row in rows
            ]

        if session:
            return await _run(session)
        async with self._db.session() as sess:
            return await _run(sess)

    async def resolve_entity_ids(
        self,
        *,
        project_id: UUID,
        entity_type: str,
        session: AsyncSession | None = None,
    ) -> list[UUID]:
        """Resolve entity IDs for a project."""
        async def _run(sess: AsyncSession) -> list[UUID]:
            if entity_type == "project":
                return [project_id]
            if entity_type == "query":
                stmt = select(QueryModel.id).where(
                    QueryModel.project_id == project_id,
                    QueryModel.is_deleted.is_(False),
                )
            elif entity_type == "cluster":
                stmt = select(ClusterModel.id).where(
                    ClusterModel.project_id == project_id,
                    ClusterModel.is_deleted.is_(False),
                )
            elif entity_type == "page":
                stmt = select(PageModel.id).where(
                    PageModel.project_id == project_id,
                    PageModel.is_deleted.is_(False),
                )
            else:
                return []
            result = await sess.execute(stmt)
            return list(result.scalars().all())

        if session:
            return await _run(session)
        async with self._db.session() as sess:
            return await _run(sess)

    async def resolve_entity_labels(
        self,
        *,
        entity_type: str,
        entity_ids: Sequence[UUID],
        session: AsyncSession | None = None,
    ) -> dict[UUID, str]:
        """Resolve entity IDs to human-readable labels."""
        if not entity_ids:
            return {}

        async def _run(sess: AsyncSession) -> dict[UUID, str]:
            if entity_type == "project":
                return {eid: str(eid) for eid in entity_ids}
            if entity_type == "query":
                stmt = select(QueryModel.id, QueryModel.query).where(
                    QueryModel.id.in_(list(entity_ids))
                )
                result = await sess.execute(stmt)
                return {row[0]: row[1] for row in result.all()}
            if entity_type == "cluster":
                stmt = select(ClusterModel.id, ClusterModel.name).where(
                    ClusterModel.id.in_(list(entity_ids))
                )
                result = await sess.execute(stmt)
                return {row[0]: row[1] for row in result.all()}
            if entity_type == "page":
                stmt = select(PageModel.id, PageModel.url_full).where(
                    PageModel.id.in_(list(entity_ids))
                )
                result = await sess.execute(stmt)
                return {row[0]: row[1] for row in result.all()}
            return {}

        if session:
            return await _run(session)
        async with self._db.session() as sess:
            return await _run(sess)

    # ── Filter preparation ──

    async def _prepare_filter_groups(
        self,
        session: AsyncSession,
        filter_value_ids: Sequence[UUID] | None,
    ) -> tuple[Mapping[UUID, Sequence[UUID]] | None, bool]:
        """Group filter_value_ids by filter_field_id (OR within, AND between)."""
        if not filter_value_ids:
            return None, False

        stmt = select(
            _sfv.c.id,
            _sfv.c.filter_field_id,
        ).where(_sfv.c.id.in_(list(filter_value_ids)))

        result = await session.execute(stmt)
        groups: defaultdict[UUID, list[UUID]] = defaultdict(list)
        found: set[UUID] = set()

        for row in result.mappings().all():
            fv_id: UUID = row["id"]
            ff_id: UUID = row["filter_field_id"]
            groups[ff_id].append(fv_id)
            found.add(fv_id)

        missing = set(filter_value_ids) - found
        return dict(groups), bool(missing)

    # ── Tier 1: source entity aggregation ──

    def _build_base_query(
        self,
        *,
        field_id: UUID,
        field_type: str,
        source_entity_type: str,
        source_aggregation: str,
        date_from: datetime,
        date_to: datetime,
        filter_groups: Mapping[UUID, Sequence[UUID]] | None,
        grouping: str,
    ) -> sa.Select:
        """Build base query: aggregate values at source entity level per time bucket."""
        values = _sv.alias("sv_source")
        ts_col = sa.func.coalesce(values.c.recorded_at, values.c.updated_at, values.c.created_at)
        day_col = sa.func.date_trunc(grouping, ts_col)

        filters: list[sa.ColumnElement[bool]] = [
            values.c.field_id == field_id,
            values.c.entity_type == source_entity_type,
            values.c.recorded_at.isnot(None),
            values.c.recorded_at >= date_from,
            values.c.recorded_at <= date_to,
        ]

        # Filter joins (AND between groups, OR within group)
        if filter_groups:
            for idx, value_ids in enumerate(filter_groups.values()):
                if not value_ids:
                    filters.append(sa.literal(False))
                    continue
                link = _sv2fv.alias(f"sv2fv_{idx}")
                filters.append(
                    sa.exists()
                    .where(link.c.statistic_value_id == values.c.id)
                    .where(link.c.filter_value_id.in_(value_ids))
                )

        if source_aggregation == "list":
            raise ValueError("list aggregation is not supported for timeseries")

        # single_value: ROW_NUMBER to pick latest per entity+day
        if source_aggregation == "single_value":
            ordering = [
                ts_col.desc().nullslast(),
                values.c.updated_at.desc().nullslast(),
                values.c.created_at.desc().nullslast(),
                values.c.id.desc(),
            ]
            rn = sa.func.row_number().over(
                partition_by=(values.c.entity_id, day_col),
                order_by=ordering,
            )
            subq = (
                sa.select(
                    values.c.entity_id.label("entity_id"),
                    day_col.label("day"),
                    values.c.value.label("aggregated_value"),
                    ts_col.label("aggregated_at"),
                    rn.label("rn"),
                )
                .where(*filters)
                .subquery()
            )
            return sa.select(
                subq.c.entity_id,
                subq.c.day,
                subq.c.aggregated_value,
                subq.c.aggregated_at,
            ).where(subq.c.rn == 1)

        # Numeric aggregation (total/average/max/min)
        casted = self._cast_value(values.c.value, field_type)
        agg_expr = self._apply_aggregation(source_aggregation, casted)
        agg_ts = sa.func.max(ts_col)

        return (
            sa.select(
                values.c.entity_id.label("entity_id"),
                day_col.label("day"),
                agg_expr.label("aggregated_value"),
                agg_ts.label("aggregated_at"),
            )
            .where(*filters)
            .group_by(values.c.entity_id, day_col)
        )

    # ── Tier 2: cross-entity re-aggregation ──

    def _build_target_stmt(
        self,
        *,
        base_query: sa.Select,
        field_type: str,
        source_entity_type: str,
        target_entity_type: str,
        target_aggregation: str,
        target_ids: Sequence[UUID] | None,
    ) -> sa.Select:
        """Re-aggregate from source entity to target entity."""
        base = base_query.subquery("ts_values")

        # Same entity — pass through
        if source_entity_type == target_entity_type:
            stmt = sa.select(
                base.c.entity_id.label("entity_id"),
                base.c.day.label("day"),
                base.c.aggregated_value.label("value"),
                base.c.aggregated_at.label("aggregated_at"),
            ).select_from(base)
            if target_ids:
                stmt = stmt.where(base.c.entity_id.in_(list(target_ids)))
            return stmt

        join_clause, target_col = self._build_join_clause(
            base, source_entity_type, target_entity_type
        )

        # single_value at target level
        if target_aggregation == "single_value":
            rn = sa.func.row_number().over(
                partition_by=(target_col, base.c.day),
                order_by=[
                    base.c.aggregated_at.desc().nullslast(),
                    base.c.entity_id.asc(),
                ],
            )
            sel = (
                sa.select(
                    target_col.label("entity_id"),
                    base.c.day.label("day"),
                    base.c.aggregated_value.label("value"),
                    base.c.aggregated_at.label("aggregated_at"),
                    rn.label("rn"),
                )
                .select_from(join_clause)
                .where(target_col.isnot(None))
            )
            if target_ids:
                sel = sel.where(target_col.in_(list(target_ids)))
            sel_sub = sel.subquery()
            return sa.select(
                sel_sub.c.entity_id,
                sel_sub.c.day,
                sel_sub.c.value,
                sel_sub.c.aggregated_at,
            ).where(sel_sub.c.rn == 1)

        # Numeric re-aggregation
        value_col = self._cast_value(base.c.aggregated_value, field_type)
        agg_expr = self._apply_aggregation(target_aggregation, value_col)
        agg_ts = sa.func.max(base.c.aggregated_at)

        stmt = (
            sa.select(
                target_col.label("entity_id"),
                base.c.day.label("day"),
                agg_expr.label("value"),
                agg_ts.label("aggregated_at"),
            )
            .select_from(join_clause)
            .where(target_col.isnot(None))
            .group_by(target_col, base.c.day)
        )
        if target_ids:
            stmt = stmt.where(target_col.in_(list(target_ids)))
        return stmt

    # ── Join clause builder ──

    @staticmethod
    def _build_join_clause(
        base: sa.FromClause,
        source: str,
        target: str,
    ) -> tuple[sa.FromClause, sa.ColumnElement]:
        """Build the cross-entity join path."""
        if source == "page" and target == "project":
            p = _pages.alias("p_for_proj")
            return base.join(p, base.c.entity_id == p.c.id), p.c.project_id

        if source == "query" and target == "project":
            q = _queries.alias("q_for_proj")
            return base.join(q, base.c.entity_id == q.c.id), q.c.project_id

        if source == "cluster" and target == "project":
            c = _clusters.alias("c_for_proj")
            return base.join(c, base.c.entity_id == c.c.id), c.c.project_id

        if source == "query" and target == "cluster":
            q = _queries.alias("q_for_cluster")
            return base.join(q, base.c.entity_id == q.c.id), q.c.cluster_id

        if source == "query" and target == "page":
            q = _queries.alias("q_for_page")
            c = _clusters.alias("c_link_q_to_page")
            j = base.join(q, base.c.entity_id == q.c.id).join(
                c, q.c.cluster_id == c.c.id
            )
            return j, c.c.page_id

        if source == "page" and target == "cluster":
            p = _pages.alias("p_for_cluster")
            c = _clusters.alias("c_for_page")
            j = base.join(p, base.c.entity_id == p.c.id).join(
                c, c.c.page_id == p.c.id
            )
            return j, c.c.id

        if source == "cluster" and target == "page":
            c = _clusters.alias("c_for_page_src")
            return base.join(c, base.c.entity_id == c.c.id), c.c.page_id

        raise ValueError(f"Unsupported aggregation path: {source} → {target}")

    # ── Aggregation helpers ──

    @staticmethod
    def _apply_aggregation(aggregation: str, column: sa.ColumnElement) -> sa.ColumnElement:
        agg_map = {
            "total": sa.func.sum,
            "average": sa.func.avg,
            "max": sa.func.max,
            "min": sa.func.min,
        }
        fn = agg_map.get(aggregation)
        if fn is None:
            raise ValueError(f"Unsupported aggregation: {aggregation}")
        return fn(column)

    @staticmethod
    def _cast_value(column: sa.ColumnElement, field_type: str) -> sa.ColumnElement:
        """Cast VARCHAR value column to appropriate numeric type (regex-safe)."""
        numeric_re = r"^\s*-?\d+(?:\.\d+)?\s*$"
        text_col = sa.cast(column, sa.Text)

        if field_type == "integer":
            return sa.case(
                (text_col.op("~")(numeric_re), sa.cast(sa.cast(column, sa.Float), sa.Integer)),
                else_=sa.null(),
            )
        if field_type == "float":
            return sa.case(
                (text_col.op("~")(numeric_re), sa.cast(column, sa.Numeric(precision=38, scale=10))),
                else_=sa.null(),
            )
        if field_type == "boolean":
            return sa.cast(column, sa.Boolean)
        if field_type == "datetime":
            return sa.cast(column, sa.DateTime(timezone=True))
        if field_type == "date":
            return sa.cast(column, sa.Date())
        return column
