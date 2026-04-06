"""Unit of Work interface.

UnitOfWork groups multiple repository operations into a single atomic transaction.
The application service uses it to ensure consistency across multiple writes.

Usage pattern in a service:
    async with self._uow:
        await self._uow.requests.save(request_a)
        await self._uow.requests.save(request_b)
        await self._uow.commit()
        # If any line above raises — rollback happens automatically on __aexit__

Concrete implementation: app.infrastructure.persistence.uow.SqlAlchemyUnitOfWork
"""

from abc import ABC, abstractmethod

from app.domain.interfaces.repository.repository import IRepository


class IUnitOfWork(ABC):
    """Abstract Unit of Work."""

    requests: IRepository  # type-annotated in concrete UoW subclasses

    async def __aenter__(self) -> "IUnitOfWork":
        return self

    async def __aexit__(self, exc_type: type | None, *args: object) -> None:
        if exc_type is not None:
            await self.rollback()

    @abstractmethod
    async def commit(self) -> None:
        """Commit the current transaction."""
        ...

    @abstractmethod
    async def rollback(self) -> None:
        """Roll back the current transaction."""
        ...
