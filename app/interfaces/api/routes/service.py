from typing import Annotated

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends

from app.application.commands import CreateRequestCommand
from app.application.services.service import Service
from app.core.di.containers import Container
from app.interfaces.api.schemas.requests import RequestCreateRequest
from app.interfaces.api.schemas.responses import SuccessResponse

router = APIRouter(
    prefix="/service",
    tags=["service"],
)


@router.post(
    "/request",
    response_model=SuccessResponse,
    status_code=201,
)
@inject
async def create_request(
    body: RequestCreateRequest,
    service: Annotated[Service, Depends(Provide[Container.service])],
) -> SuccessResponse:
    """Create a new request and persist it.

    Args:
        body: Validated request payload (id, user_id, payload)
        service: Injected application service

    Returns:
        SuccessResponse with the persisted request_id

    Raises:
        409: If a request with this id already exists
        422: If the request body fails validation
        500: On unexpected errors
    """
    command = CreateRequestCommand(
        id=body.id,
        user_id=body.user_id,
        payload=body.payload,
    )
    request_id = await service.create_request(command=command)
    return SuccessResponse(
        status="success",
        data={"request_id": str(request_id)},
        message="Request created successfully",
    )
