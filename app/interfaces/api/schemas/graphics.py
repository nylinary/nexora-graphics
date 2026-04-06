"""Request/response schemas for graphics API."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field


# ── Request ──


class PeriodRequest(BaseModel):
    date_from: date = Field(..., alias="from", description="Start date (inclusive)")
    date_to: date = Field(..., alias="to", description="End date (inclusive)")
    granularity: str = Field("day", description="day | week | month")

    model_config = {"populate_by_name": True}


class SeriesRequest(BaseModel):
    series_kind: Literal["metric", "alert"] = Field(..., description="metric or alert")
    metric_code: str | None = Field(None, description="Metric abbreviation")
    alert_code: str | None = Field(None, description="Alert type code")
    mode: str | None = Field(None, description="e.g. cumulative")
    grouping: str | None = Field(None, description="Override grouping")


class CompareRequest(BaseModel):
    enabled: bool = False
    mode: str | None = None


class GraphicsBuildRequest(BaseModel):
    """POST /api/v1/graphics/build request body."""

    project_id: uuid.UUID = Field(..., description="Target project UUID")
    product: str = Field(..., description="metrics | projects | alerts")
    entity: str = Field(..., description="query | cluster | page | project")
    period: PeriodRequest
    filters: dict[str, list[str]] = Field(default_factory=dict)
    requested_series: list[SeriesRequest]
    compare: CompareRequest = Field(default_factory=CompareRequest)
    requested_visualizations: list[str] = Field(default_factory=lambda: ["line"])


# ── Response ──


class PointResponse(BaseModel):
    x: date
    y: float | None = None
    raw_value: float | None = None
    is_missing: bool = False


class SeriesResponse(BaseModel):
    id: str
    type: str
    label: str
    unit: str = ""
    render_type: str = "line"
    points: list[PointResponse] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)


class GraphicsBuildResponse(BaseModel):
    """POST /api/v1/graphics/build response body."""

    status: str = "success"
    data: GraphicsBuildData


class GraphicsBuildData(BaseModel):
    series: list[SeriesResponse] = Field(default_factory=list)
    diagrams: list[dict[str, Any]] = Field(default_factory=list)
    annotations: list[dict[str, Any]] = Field(default_factory=list)
    events: list[dict[str, Any]] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)
