"""Graphics API route — POST /api/v1/graphics/build."""

from typing import Annotated

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends

from app.application.commands import (
    BuildGraphicsCommand,
    CompareSpec,
    PeriodSpec,
    SeriesRequestItem,
)
from app.application.graphics.service import GraphicsService
from app.core.di.containers import Container
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
