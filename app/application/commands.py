"""Application-layer commands (input DTOs for use cases).

Commands represent the intent of a caller. They are immutable,
fully typed, and validated by Pydantic before reaching any service.

Naming convention: <Verb><Entity>Command
  - CreateRequestCommand  — создать новый Request
  - UpdateRequestCommand  — обновить Request
  - DeleteRequestCommand  — удалить Request
"""

import uuid
from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class CreateRequestCommand(BaseModel):
    """Command to create a new Request.

    Passed from the API layer into Service.create_request().
    Validated by Pydantic before the service is called.
    """

    id: uuid.UUID = Field(..., description="Client-generated idempotency UUID")
    user_id: uuid.UUID = Field(..., description="UUID of the user who owns the request")
    payload: dict[str, Any] = Field(..., description="Arbitrary request payload")


# ── Graphics commands ──


class PeriodSpec(BaseModel):
    """Date range with granularity for timeseries queries."""

    model_config = ConfigDict(populate_by_name=True)

    date_from: date = Field(..., alias="from", description="Start date (inclusive)")
    date_to: date = Field(..., alias="to", description="End date (inclusive)")
    granularity: str = Field("day", description="Grouping: day | week | month")


class SeriesRequestItem(BaseModel):
    """Single series request within a graphics build command."""

    series_kind: Literal["metric", "alert"] = Field(..., description="metric or alert")
    metric_code: str | None = Field(None, description="Metric abbreviation (e.g. 'PY')")
    alert_code: str | None = Field(None, description="Alert type code")
    mode: str | None = Field(None, description="Optional mode (e.g. 'cumulative')")
    grouping: str | None = Field(None, description="Override grouping for this series")


class CompareSpec(BaseModel):
    """Period comparison configuration."""

    enabled: bool = False
    mode: str | None = None


class BuildGraphicsCommand(BaseModel):
    """Command to build graphics for a project."""

    project_id: uuid.UUID = Field(..., description="Target project UUID")
    product: str = Field(..., description="Product type: metrics | projects | alerts")
    entity: str = Field(..., description="Entity type: query | cluster | page | project")
    period: PeriodSpec = Field(..., description="Date range and granularity")
    filters: dict[str, list[str]] = Field(default_factory=dict, description="Filters: {filter_name: [values]}")
    requested_series: list[SeriesRequestItem] = Field(..., description="Series to build")
    compare: CompareSpec = Field(default_factory=CompareSpec, description="Comparison settings")
    requested_visualizations: list[str] = Field(default_factory=lambda: ["line"], description="Visualization types")
