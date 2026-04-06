from fastapi import APIRouter

from app.interfaces.api.routes.base import root_router
from app.interfaces.api.routes.health import router as health_router
from app.interfaces.api.routes.nats import router as nats_router
from app.interfaces.api.routes.service import router as service_router

# Create main router with version prefix
main_router = APIRouter(
    prefix="/api/v1",
)

# Include domain-specific routers
main_router.include_router(service_router)
main_router.include_router(nats_router)
# other
main_router.include_router(health_router)
main_router.include_router(root_router)
