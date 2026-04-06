"""Dependency injection container."""

from dependency_injector import containers, providers

from app.application.services.health_service import HealthService
from app.application.services.service import Service
from app.core.config.database import DatabaseSettings
from app.core.config.nats import NATSSettings
from app.core.logging import setup_async_logging
from app.infrastructure.cache.redis_client import AsyncRedisCache
from app.infrastructure.messaging.message_handler import DefaultMessageHandler
from app.infrastructure.messaging.nats_consumer import NATSConsumer
from app.infrastructure.messaging.nats_publisher import NATSPublisher
from app.infrastructure.persistence.database import DatabaseManager
from app.infrastructure.persistence.request_repository import RequestRepository
from app.infrastructure.persistence.uow import SqlAlchemyUnitOfWork


class Container(containers.DeclarativeContainer):
    """Application DI container."""

    wiring_config = containers.WiringConfiguration(
        modules=[
            "app.interfaces.api.routes.service",
            "app.interfaces.api.routes.health",
            "app.interfaces.api.routes.base",
            "app.interfaces.api.routes.nats",
            "app.infrastructure.messaging.nats_consumer",
            "app.app",
        ],
    )

    config = providers.Configuration()

    # Core infrastructure
    db_settings = providers.Singleton(DatabaseSettings)

    db = providers.Singleton(DatabaseManager, db_settings=db_settings)

    redis_client = providers.Singleton(
        AsyncRedisCache.from_url,
        url=config.redis.connection_url,
    )

    logger = providers.Singleton(setup_async_logging)

    # NATS settings
    nats_settings = providers.Singleton(NATSSettings)

    # Repositories
    request_repository = providers.Factory(RequestRepository, db=db)

    # Unit of Work
    unit_of_work = providers.Factory(SqlAlchemyUnitOfWork, db=db)

    # Message handler (replace with your own implementation)
    message_handler = providers.Factory(
        DefaultMessageHandler,
        logger=logger,
    )

    # NATS consumer
    nats_consumer = providers.Singleton(
        NATSConsumer,
        settings=nats_settings,
        message_handler=message_handler,
        logger=logger,
    )

    # NATS publisher
    nats_publisher = providers.Singleton(
        NATSPublisher,
        settings=nats_settings,
        logger=logger,
    )

    # Services
    health_service = providers.Factory(
        HealthService,
        db=db,
        cache=redis_client,
    )

    service = providers.Factory(
        Service,
        cache_client=redis_client,
        repository=request_repository,
        logger=logger,
    )
