"""Centralized FastAPI exception handlers.

Register all domain → HTTP exception mappings here.
Routes should NOT contain try/except for domain exceptions —
they bubble up and are caught by these handlers automatically.

Registration in app.py:
    from app.core.exception_handlers import register_exception_handlers
    register_exception_handlers(app)
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.domain.exceptions import (
    DomainException,
    DuplicateRequestError,
    GraphicsConfigError,
    GraphicsDataError,
    GraphicsPermissionError,
    GraphicsValidationError,
    RequestNotFoundError,
)


def _error_body(code: str, message: str, details: dict | None = None) -> dict:
    body: dict = {"status": "error", "error": {"code": code, "message": message}}
    if details:
        body["error"]["details"] = details
    return body


def register_exception_handlers(app: FastAPI) -> None:
    """Attach all domain exception handlers to the FastAPI application."""

    @app.exception_handler(DuplicateRequestError)
    async def duplicate_request_handler(request: Request, exc: DuplicateRequestError) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content=_error_body(
                code=exc.code or "DUPLICATE_REQUEST",
                message=exc.message,
                details={"request_id": exc.request_id},
            ),
        )

    @app.exception_handler(RequestNotFoundError)
    async def request_not_found_handler(request: Request, exc: RequestNotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content=_error_body(
                code=exc.code or "REQUEST_NOT_FOUND",
                message=exc.message,
                details={"request_id": exc.request_id},
            ),
        )

    @app.exception_handler(GraphicsValidationError)
    async def graphics_validation_handler(request: Request, exc: GraphicsValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=_error_body(
                code=exc.code or "GRAPHICS_VALIDATION_ERROR",
                message=exc.message,
            ),
        )

    @app.exception_handler(GraphicsPermissionError)
    async def graphics_permission_handler(request: Request, exc: GraphicsPermissionError) -> JSONResponse:
        return JSONResponse(
            status_code=403,
            content=_error_body(
                code=exc.code or "ACCESS_DENIED",
                message=exc.message,
            ),
        )

    @app.exception_handler(GraphicsConfigError)
    async def graphics_config_handler(request: Request, exc: GraphicsConfigError) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content=_error_body(
                code=exc.code or "PROJECT_CONFIG_NOT_FOUND",
                message=exc.message,
            ),
        )

    @app.exception_handler(GraphicsDataError)
    async def graphics_data_handler(request: Request, exc: GraphicsDataError) -> JSONResponse:
        return JSONResponse(
            status_code=502,
            content=_error_body(
                code=exc.code or "DATA_SOURCE_ERROR",
                message=exc.message,
            ),
        )

    @app.exception_handler(DomainException)
    async def domain_exception_handler(request: Request, exc: DomainException) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content=_error_body(
                code=exc.code or "DOMAIN_ERROR",
                message=exc.message,
            ),
        )

    @app.exception_handler(ValidationError)
    async def validation_error_handler(request: Request, exc: ValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=_error_body(
                code="VALIDATION_ERROR",
                message="Request validation failed",
                details={"errors": exc.errors()},
            ),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content=_error_body(
                code="INTERNAL_ERROR",
                message="An unexpected error occurred",
                details={"error_type": type(exc).__name__},
            ),
        )
