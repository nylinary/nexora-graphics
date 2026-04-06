from uuid import UUID

from aiologger import Logger

from app.application.commands import CreateRequestCommand
from app.application.interfaces.services import IService
from app.core.logging import setup_async_logging
from app.domain.exceptions import DuplicateRequestError
from app.domain.interfaces.cache.cache_client import ICacheClient
from app.domain.interfaces.repository.repository import IRepository
from app.domain.models.request import Request


class Service(IService):
    """Application service for managing requests."""

    def __init__(
        self,
        cache_client: ICacheClient,
        repository: IRepository[Request],
        logger: Logger | None = None,
    ) -> None:
        self._cache_client = cache_client
        self._repository = repository
        self._logger = logger or setup_async_logging()

    async def create_request(
        self,
        command: CreateRequestCommand,
    ) -> UUID:
        """Process and persist a new request.

        Args:
            command: Typed CreateRequestCommand with id, user_id, payload

        Returns:
            UUID of the persisted request

        Raises:
            DuplicateRequestError: If a request with this ID already exists
        """
        domain_request = Request(
            id=command.id,
            user_id=command.user_id,
            payload=command.payload,
        )
        try:
            request_id = await self._repository.save(domain_request)
            await self._logger.info(
                f"Request saved successfully: {request_id}",
                extra={"request_id": str(request_id), "user_id": str(command.user_id)},
            )
            return request_id
        except DuplicateRequestError as e:
            await self._logger.warning(
                "Duplicate request detected",
                extra={"request_id": e.request_id, "user_id": str(command.user_id)},
            )
            raise
