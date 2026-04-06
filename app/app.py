from contextlib import asynccontextmanager
from typing import AsyncIterator

import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

from app.core.config.settings import settings
from app.core.di.containers import Container
from app.core.exception_handlers import register_exception_handlers
from app.core.logging import patch_uvicorn_loggers
from app.interfaces.api.routes import router

container = Container()
container.config.from_dict({"redis": {"connection_url": settings.redis.connection_url}})


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Sentry — инициализируем в lifespan, чтобы логгер уже был готов
    if settings.sentry.dsn:
        sentry_sdk.init(
            dsn=settings.sentry.dsn,
            environment=settings.sentry.environment,
            traces_sample_rate=settings.sentry.traces_sample_rate,
            profiles_sample_rate=settings.sentry.profiles_sample_rate,
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                LoggingIntegration(level=None, event_level=None),
            ],
        )

    logger = container.logger()
    patch_uvicorn_loggers(logger)

    # ========== START: Background services ==========
    # Start NATS consumer
    nats_consumer = container.nats_consumer()
    await nats_consumer.start()
    await logger.info("NATS consumer started")

    # Connect NATS publisher
    nats_publisher = container.nats_publisher()
    await nats_publisher.connect()
    await logger.info("NATS publisher connected")

    yield

    # ========== STOP: Background services ==========
    await logger.info("Stopping background services...")

    # Disconnect NATS publisher
    await nats_publisher.disconnect()

    # Stop NATS consumer
    await nats_consumer.stop()

    # Dispose and shutdown managed resources
    await container.db().dispose()
    await container.redis_client().close()
    logger.shutdown()


app = FastAPI(
    title=settings.app.name,
    version=settings.app.version,
    lifespan=lifespan,
)

app.container = container  # type: ignore

# Register centralized domain exception handlers
register_exception_handlers(app)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors.allow_origins,
    allow_credentials=settings.cors.allow_credentials,
    allow_methods=settings.cors.allow_methods,
    allow_headers=settings.cors.allow_headers,
)

# Include API routes
app.include_router(router)

# Add Prometheus metrics
Instrumentator().instrument(app).expose(app)
