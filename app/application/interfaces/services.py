"""Application-layer service interfaces.

Lives in application/ (not domain/) because service contracts reference
application-layer Commands, which belong to the application layer.

Domain interfaces (IRepository, ICacheClient, IMessageHandler) remain in
domain/ because they only reference domain primitives (entities, UUIDs, etc.).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from app.application.commands import BuildGraphicsCommand, CreateRequestCommand
from app.domain.models.graphics import GraphicsResult


class IService(ABC):
    """Abstract interface for the application service."""

    @abstractmethod
    async def create_request(
        self,
        command: CreateRequestCommand,
    ) -> UUID:
        """Process and persist a new request.

        Args:
            command: Typed and validated CreateRequestCommand

        Returns:
            UUID of the persisted request

        Raises:
            DuplicateRequestError: If a request with this ID already exists
        """
        ...


class IGraphicsService(ABC):
    """Abstract interface for the graphics service."""

    @abstractmethod
    async def build(self, command: BuildGraphicsCommand) -> GraphicsResult:
        """Build graphics from a unified request."""
        ...
