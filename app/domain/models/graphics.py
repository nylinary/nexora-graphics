"""Domain models for graphics service."""

from __future__ import annotations

import uuid
from datetime import date
from enum import StrEnum, auto
from typing import Any

from pydantic import BaseModel, Field


# ── Enums (ported from main-be core/entities/statistic.py) ──


class EntityType(StrEnum):
    project = auto()
    page = auto()
    query = auto()
    cluster = auto()


class FieldType(StrEnum):
    string = auto()
    integer = auto()
    float = auto()
    boolean = auto()
    datetime = auto()
    date = auto()


class AggregationType(StrEnum):
    single_value = auto()
    total = auto()
    average = auto()
    max = auto()
    min = auto()
    list = auto()
    use_cluster = auto()


class TimeseriesGrouping(StrEnum):
    day = auto()
    week = auto()
    month = auto()


# ── Layer 1 output: format-agnostic intermediate data ──


class MetricField(BaseModel):
    """Mirrors a row from statistic_fields table."""

    id: uuid.UUID
    name: str
    abbreviation: str
    field_type: FieldType
    source_id: uuid.UUID
    aggregation: dict[str, str] = Field(
        description="Aggregation rules per entity type, e.g. {'query': 'avg', 'page': 'use_cluster', 'project': 'total'}",
    )
    reverse_trend: bool = False


class TimeseriesDataset(BaseModel):
    """One entity's timeseries for one metric — format-agnostic intermediate representation.

    Mirrors main-be's StatisticTimeseriesItem.
    """

    entity_id: uuid.UUID
    entity_label: str
    values: list[float | None]
    dates: list[date]
    deltas: list[float | None] = Field(default_factory=list)


class AlertEvent(BaseModel):
    """Single alert event from alert_entity_history."""

    entity_id: uuid.UUID
    entity_label: str
    triggered_at: date
    event_type: str
    new_status: str
    alert_type: str
    priority: str = "normal"


# ── Layer 2/3 output: presentation models ──


class PointValue(BaseModel):
    """Single data point in a series."""

    x: date
    y: float | None = None
    raw_value: float | None = None
    is_missing: bool = False


class SeriesData(BaseModel):
    """One series of data points ready for rendering."""

    id: str
    type: str
    label: str
    unit: str = ""
    render_type: str = "line"
    points: list[PointValue] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)


class GraphicsResult(BaseModel):
    """Final output of the graphics pipeline."""

    series: list[SeriesData] = Field(default_factory=list)
    diagrams: list[dict[str, Any]] = Field(default_factory=list)
    annotations: list[dict[str, Any]] = Field(default_factory=list)
    events: list[dict[str, Any]] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)


# ── Config ──


class ProjectConfig(BaseModel):
    """Project configuration for graphics service (mocked for now)."""

    project_id: uuid.UUID
    supported_products: list[str] = Field(default_factory=list)
    supported_entities: list[str] = Field(default_factory=list)
    supported_metrics: list[str] = Field(default_factory=list)
    supported_filters: list[str] = Field(default_factory=list)
