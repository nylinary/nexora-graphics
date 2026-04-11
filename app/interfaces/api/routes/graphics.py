"""Graphics API routes."""

from typing import Annotated

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Query

from app.application.commands import (
    BuildGraphicsCommand,
    CompareSpec,
    PeriodSpec,
    SeriesRequestItem,
)
from app.application.graphics.metric_resolver import MetricResolver
from app.application.graphics.service import GraphicsService
from app.application.graphics.strategy import POSITION_METRICS
from app.core.di.containers import Container
from app.infrastructure.providers.nats_statistics_rpc import NATSStatisticsRPCProvider
from app.interfaces.api.schemas.graphics import (
    GraphicsBuildData,
    GraphicsBuildRequest,
    GraphicsBuildResponse,
    PointResponse,
    SeriesResponse,
)

router = APIRouter(
    prefix="/graphics",
    tags=["graphics"],
)


@router.get("/metrics", status_code=200)
@inject
async def list_metrics(
    resolver: Annotated[
        MetricResolver, Depends(Provide[Container.metric_resolver])
    ],
    entity_type: str | None = Query(None, description="Filter by entity type"),
) -> dict:
    """Return available metrics, optionally filtered by entity type."""
    fields = await resolver._load_fields()
    result = []
    for abbr, field in sorted(fields.items(), key=lambda x: x[1].name):
        supported = list(field.aggregation.keys())
        if entity_type and entity_type not in field.aggregation:
            continue
        result.append({
            "code": abbr,
            "name": field.name,
            "type": field.field_type,
            "supported_entities": supported,
            "is_position": abbr in POSITION_METRICS,
        })
    return {"status": "success", "data": result}


@router.get("/projects/search", status_code=200)
@inject
async def search_projects(
    rpc: Annotated[
        NATSStatisticsRPCProvider, Depends(Provide[Container.statistics_rpc])
    ],
    q: str = Query("", description="Search query (name or domain)"),
    limit: int = Query(10, ge=1, le=50),
) -> dict:
    """Search projects by name or domain."""
    if not q.strip():
        return {"status": "success", "data": []}
    results = await rpc.search_projects(query=q.strip(), limit=limit)
    return {"status": "success", "data": results}


@router.get("/filters/fields", status_code=200)
@inject
async def list_filter_fields(
    rpc: Annotated[
        NATSStatisticsRPCProvider, Depends(Provide[Container.statistics_rpc])
    ],
) -> dict:
    """Return available filter fields."""
    fields = await rpc.get_filter_fields()
    return {"status": "success", "data": fields}


@router.get("/filters/values", status_code=200)
@inject
async def list_filter_values(
    rpc: Annotated[
        NATSStatisticsRPCProvider, Depends(Provide[Container.statistics_rpc])
    ],
    field_id: str = Query(..., description="Filter field UUID"),
) -> dict:
    """Return values for a given filter field."""
    from uuid import UUID as _UUID

    values = await rpc.get_filter_values(field_id=_UUID(field_id))
    return {"status": "success", "data": values}


@router.post(
    "/build",
    response_model=GraphicsBuildResponse,
    status_code=200,
)
@inject
async def build_graphics(
    body: GraphicsBuildRequest,
    graphics_service: Annotated[
        GraphicsService, Depends(Provide[Container.graphics_service])
    ],
) -> GraphicsBuildResponse:
    """Build graphics data for a project.

    Accepts a unified request and returns structured chart data
    (series + points) in a format-agnostic JSON format.
    """
    command = BuildGraphicsCommand(
        project_id=body.project_id,
        product=body.product,
        entity=body.entity,
        period=PeriodSpec(
            date_from=body.period.date_from,
            date_to=body.period.date_to,
            granularity=body.period.granularity,
        ),
        filters=body.filters,
        requested_series=[
            SeriesRequestItem(
                series_kind=s.series_kind,
                metric_code=s.metric_code,
                alert_code=s.alert_code,
                mode=s.mode,
                grouping=s.grouping,
            )
            for s in body.requested_series
        ],
        compare=CompareSpec(
            enabled=body.compare.enabled,
            mode=body.compare.mode,
        ),
        requested_visualizations=body.requested_visualizations,
    )

    result = await graphics_service.build(command)

    return GraphicsBuildResponse(
        status="success",
        data=GraphicsBuildData(
            series=[
                SeriesResponse(
                    id=s.id,
                    type=s.type,
                    label=s.label,
                    unit=s.unit,
                    render_type=s.render_type,
                    points=[
                        PointResponse(
                            x=p.x,
                            y=p.y,
                            raw_value=p.raw_value,
                            is_missing=p.is_missing,
                        )
                        for p in s.points
                    ],
                    meta=s.meta,
                )
                for s in result.series
            ],
            diagrams=result.diagrams,
            annotations=result.annotations,
            events=result.events,
            meta=result.meta,
        ),
    )
