"""SQLAlchemy implementation of Unit of Work."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.interfaces.uow import IUnitOfWork
from app.infrastructure.persistence.database import DatabaseManager
from app.infrastructure.persistence.request_repository import RequestRepository


class SqlAlchemyUnitOfWork(IUnitOfWork):
    """Wraps a single SQLAlchemy AsyncSession shared across all repositories.

    All repository operations inside the same `async with uow:` block
    share one session and one transaction.

    Example:
        async with SqlAlchemyUnitOfWork(db) as uow:
            await uow.requests.save(entity)
            await uow.commit()
    """

    def __init__(self, db: DatabaseManager) -> None:
        self._db = db
        self._session: AsyncSession | None = None

    async def __aenter__(self) -> "SqlAlchemyUnitOfWork":
        self._session = self._db.session_factory()
        self.requests = RequestRepository(db=self._db, session=self._session)
        return self

    async def __aexit__(self, exc_type: type | None, *args: object) -> None:
        if exc_type is not None:
            await self.rollback()
        if self._session:
            await self._session.close()
            self._session = None

    async def commit(self) -> None:
        if self._session:
            await self._session.commit()

    async def rollback(self) -> None:
        if self._session:
            await self._session.rollback()
