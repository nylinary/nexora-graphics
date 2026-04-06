"""Mock implementation of IProjectConfigProvider.

Returns a permissive config — all products/entities/metrics allowed.
Will be replaced with real ProductConfig Service calls later.
"""

from __future__ import annotations

import uuid

from app.domain.interfaces.providers.graphics_config import IProjectConfigProvider
from app.domain.models.graphics import ProjectConfig


class MockProjectConfigProvider(IProjectConfigProvider):
    """Always returns a config that allows everything."""

    async def get_config(self, project_id: uuid.UUID) -> ProjectConfig:
        return ProjectConfig(
            project_id=project_id,
            supported_products=["metrics", "projects", "alerts"],
            supported_entities=["query", "cluster", "page", "project"],
            supported_metrics=[],  # empty = all allowed
            supported_filters=[],  # empty = all allowed
        )
