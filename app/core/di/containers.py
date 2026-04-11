"""Dependency injection container."""

from dependency_injector import containers, providers

from app.application.graphics.metric_resolver import MetricResolver
from app.application.graphics.service import GraphicsService
from app.application.services.health_service import HealthService
from app.application.services.service import Service
from app.core.config.database import DatabaseSettings
from app.core.config.nats import NATSSettings
from app.core.logging import setup_async_logging
from app.infrastructure.cache.redis_client import AsyncRedisCache
from app.infrastructure.messaging.message_handler import DefaultMessageHandler
from app.infrastructure.messaging.nats_consumer import NATSConsumer
from app.infrastructure.messaging.nats_publisher import NATSPublisher
from app.infrastructure.messaging.nats_statistics_client import NatsStatisticsClient
from app.infrastructure.persistence.database import DatabaseManager
from app.infrastructure.persistence.request_repository import RequestRepository
from app.infrastructure.persistence.uow import SqlAlchemyUnitOfWork
from app.infrastructure.providers.mock_config import MockProjectConfigProvider
from app.infrastructure.providers.nats_alert import NATSAlertProvider
from app.infrastructure.providers.nats_statistics_rpc import NATSStatisticsRPCProvider
from app.infrastructure.providers.nats_timeseries import NATSTimeseriesProvider


class Container(containers.DeclarativeContainer):
    """Application DI container."""

    wiring_config = containers.WiringConfiguration(
        modules=[
            "app.interfaces.api.routes.service",
            "app.interfaces.api.routes.health",
            "app.interfaces.api.routes.graphics",
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

    # Statistics service NATS client
    nats_statistics_client = providers.Singleton(
        NatsStatisticsClient,
        nats_url=nats_settings.provided.hosts,
        timeout_sec=30.0,
    )

    # Graphics — providers (via NATS → statistics-service)
    timeseries_provider = providers.Factory(
        NATSTimeseriesProvider, client=nats_statistics_client
    )
    alert_provider = providers.Factory(NATSAlertProvider, client=nats_statistics_client)
    statistics_rpc = providers.Factory(
        NATSStatisticsRPCProvider, client=nats_statistics_client
    )
    config_provider = providers.Factory(MockProjectConfigProvider)
    metric_resolver = providers.Factory(
        MetricResolver, provider=timeseries_provider
    )

    # Graphics — service
    graphics_service = providers.Factory(
        GraphicsService,
        timeseries_provider=timeseries_provider,
        alert_provider=alert_provider,
        config_provider=config_provider,
    )
