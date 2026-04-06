"""Database implementation of Repository."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.domain.exceptions import DuplicateRequestError
from app.domain.interfaces.repository.repository import IRepository
from app.domain.models.request import Request
from app.infrastructure.persistence.database import DatabaseManager
from app.infrastructure.persistence.models.request import RequestModel


class RequestRepository(IRepository[Request]):
    """Database implementation of RequestRepository.

    Supports two modes:
    1. Standalone — creates its own session per operation (via DatabaseManager).
    2. UoW-managed — uses an externally provided AsyncSession (shared transaction).

    When used inside SqlAlchemyUnitOfWork, commit/rollback are managed by the UoW.
    When used standalone, each write operation commits immediately.
    """

    def __init__(
        self,
        db: DatabaseManager,
        session: AsyncSession | None = None,
    ) -> None:
        self._db = db
        self._external_session = session

    @asynccontextmanager
    async def _open_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Yield the external UoW session or open a fresh one."""
        if self._external_session is not None:
            yield self._external_session
        else:
            async with self._db.session() as session:
                yield session

    async def get_by_id(self, _id: UUID) -> Request | None:
        """Get request by its UUID."""
        async with self._open_session() as session:
            result = await session.execute(select(RequestModel).where(RequestModel.id == _id))
            request = result.scalar_one_or_none()
            return request.to_domain() if request else None

    async def get_list(
        self,
        request_ids: list[UUID],
        limit: int = 10,
        offset: int = 0,
    ) -> list[Request]:
        """Return requests matching the given UUIDs (or all if list is empty)."""
        query = select(RequestModel)
        if request_ids:
            query = query.where(RequestModel.id.in_(request_ids))
        query = query.offset(offset).limit(limit)

        async with self._open_session() as session:
            result = await session.execute(query)
            return [r.to_domain() for r in result.scalars().all()]

    async def save(self, request: Request) -> UUID:
        """Persist a request.

        Returns:
            UUID of the saved request

        Raises:
            DuplicateRequestError: If a request with this ID already exists
        """
        async with self._open_session() as session:
            request_model = RequestModel.from_domain(request)
            session.add(request_model)
            try:
                # flush() sends the INSERT to the DB within the current transaction
                # and raises IntegrityError immediately — works in both standalone
                # and UoW-managed modes without committing.
                await session.flush()
                if self._external_session is None:
                    await session.commit()
            except IntegrityError as e:
                if self._external_session is None:
                    await session.rollback()
                if "duplicate key" in str(e.orig).lower() or "unique constraint" in str(e.orig).lower():
                    raise DuplicateRequestError(
                        request_id=str(request_model.id),
                        message=f"Request with ID {request_model.id} already exists in the database",
                    ) from e
                raise

            return request_model.id
