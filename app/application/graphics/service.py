"""GraphicsService — top-level orchestrator.

Validates the request, resolves the product strategy, and delegates execution.
"""

from __future__ import annotations

from app.application.commands import BuildGraphicsCommand
from app.application.graphics.data_processor import DataProcessor
from app.application.graphics.metric_resolver import MetricResolver
from app.application.graphics.strategy import (
    AlertsStrategy,
    MetricsStrategy,
    ProjectsStrategy,
    get_strategy_class,
)
from app.application.interfaces.services import IGraphicsService
from app.domain.exceptions import GraphicsConfigError, GraphicsValidationError
from app.domain.interfaces.providers.alert_provider import IAlertProvider
from app.domain.interfaces.providers.graphics_config import IProjectConfigProvider
from app.domain.interfaces.providers.timeseries_provider import ITimeseriesProvider
from app.domain.models.graphics import GraphicsResult


class GraphicsService(IGraphicsService):
    """Orchestrates the full graphics build pipeline.

    1. Validate product + entity against project config
    2. Select product strategy
    3. Delegate to strategy.execute()
    """

    def __init__(
        self,
        timeseries_provider: ITimeseriesProvider,
        alert_provider: IAlertProvider,
        config_provider: IProjectConfigProvider,
    ) -> None:
        self._ts = timeseries_provider
        self._alerts = alert_provider
        self._config = config_provider

    async def build(self, command: BuildGraphicsCommand) -> GraphicsResult:
        # Validate project config
        config = await self._config.get_config(command.project_id)

        if config.supported_products and command.product not in config.supported_products:
            raise GraphicsValidationError(
                message=f"Product '{command.product}' is not supported for this project",
                code=GraphicsValidationError.UNKNOWN_PRODUCT,
            )

        if config.supported_entities and command.entity not in config.supported_entities:
            raise GraphicsValidationError(
                message=f"Entity '{command.entity}' is not supported for this project",
                code=GraphicsValidationError.UNKNOWN_ENTITY,
            )

        # Resolve strategy
        strategy_cls = get_strategy_class(command.product)
        if strategy_cls is None:
            raise GraphicsValidationError(
                message=f"No strategy for product '{command.product}'",
                code=GraphicsValidationError.UNKNOWN_PRODUCT,
            )

        # Build strategy with dependencies
        strategy = self._build_strategy(command.product)

        return await strategy.execute(command)

    def _build_strategy(self, product: str):
        """Instantiate the correct strategy with its dependencies."""
        if product in ("metrics", "projects"):
            resolver = MetricResolver(self._ts)
            processor = DataProcessor()
            cls = MetricsStrategy if product == "metrics" else ProjectsStrategy
            return cls(self._ts, processor, resolver)

        if product == "alerts":
            return AlertsStrategy(self._alerts)

        raise GraphicsValidationError(
            message=f"No strategy for product '{product}'",
            code=GraphicsValidationError.UNKNOWN_PRODUCT,
        )
