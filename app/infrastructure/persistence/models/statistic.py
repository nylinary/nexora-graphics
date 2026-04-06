"""SQLAlchemy models for statistic tables (read-only, no FKs — existing DB)."""

import uuid
from datetime import datetime

from sqlalchemy import UUID, Boolean, DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.database import Base


# ── statistic_fields ──


class StatisticFieldModel(Base):
    __tablename__ = "statistic_fields"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1023), nullable=True)
    abbreviation: Mapped[str] = mapped_column(String(63), nullable=False)
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    aggregation: Mapped[dict] = mapped_column(JSONB, nullable=False)
    reverse_trend: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


# ── statistic_values (partitioned monthly — mapped to parent table) ──


class StatisticValueModel(Base):
    __tablename__ = "statistic_values"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    field_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    value: Mapped[str] = mapped_column(String(1023), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


# ── statistic_filter_fields ──


class StatisticFilterFieldModel(Base):
    __tablename__ = "statistic_filter_fields"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1023), nullable=True)
    icon_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    multiple: Mapped[bool | None] = mapped_column(Boolean, nullable=True, default=True)
    is_visible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


# ── statistic_filter_values ──


class StatisticFilterValueModel(Base):
    __tablename__ = "statistic_filter_values"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    filter_field_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    value: Mapped[str] = mapped_column(String(255), nullable=False)
    icon_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)


# ── statistic_value_to_filter_values (partitioned monthly) ──


class StatisticValueToFilterValueModel(Base):
    __tablename__ = "statistic_value_to_filter_values"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    statistic_value_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    filter_value_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    statistic_recorded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


# ── Entity tables (queries, clusters, pages) ──


class QueryModel(Base):
    __tablename__ = "queries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    query: Mapped[str] = mapped_column(String(511), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    cluster_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)


class ClusterModel(Base):
    __tablename__ = "clusters"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1023), nullable=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    page_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)


class PageModel(Base):
    __tablename__ = "pages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    url_full: Mapped[str] = mapped_column(Text, nullable=False)
    is_competitor: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)


# ── alert_entity_history ──


class AlertEntityHistoryModel(Base):
    __tablename__ = "alert_entity_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    monitored_alert_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(16), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    change: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    triggered_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    previous_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    new_status: Mapped[str] = mapped_column(String(16), nullable=False)
    status_changed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    event_type: Mapped[str] = mapped_column(String(16), nullable=False)
