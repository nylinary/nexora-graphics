"""Project configuration provider interface."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from app.domain.models.graphics import ProjectConfig


class IProjectConfigProvider(ABC):
    """Contract for fetching project configuration (mocked for now)."""

    @abstractmethod
    async def get_config(self, project_id: uuid.UUID) -> ProjectConfig:
        """Get project configuration for graphics service."""
