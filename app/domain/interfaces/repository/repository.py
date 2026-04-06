from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from uuid import UUID

T = TypeVar("T")


class IRepository(ABC, Generic[T]):
    """Generic repository interface.

    Type parameter T represents the domain entity type managed by this repository.

    Example:
        class RequestRepository(IRepository[Request]):
            async def save(self, item: Request) -> UUID: ...
            async def get_by_id(self, _id: UUID) -> Request | None: ...
    """

    @abstractmethod
    async def save(
        self,
        item: T,
    ) -> UUID:
        """Persist a domain entity and return its UUID."""
        ...

    @abstractmethod
    async def get_by_id(
        self,
        _id: UUID,
    ) -> T | None:
        """Retrieve a domain entity by its UUID. Returns None if not found."""
        ...
