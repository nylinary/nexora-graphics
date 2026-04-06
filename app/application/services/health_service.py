"""Health check service.

Checks connectivity to all infrastructure dependencies.
Lives in application/ because it orchestrates multiple infrastructure checks
without containing any domain business logic.
"""

from app.domain.interfaces.cache.cache_client import ICacheClient
from app.infrastructure.persistence.database import DatabaseManager


class HealthService:
    """Checks liveness of infrastructure dependencies."""

    def __init__(self, db: DatabaseManager, cache: ICacheClient) -> None:
        self._db = db
        self._cache = cache

    async def check(self) -> dict[str, str]:
        """Return liveness status for each dependency."""
        from sqlalchemy import text

        status: dict[str, str] = {
            "api": "up",
            "postgresql": "unknown",
            "redis": "unknown",
        }

        try:
            async with self._db.session() as session:
                await session.execute(text("SELECT 1"))
            status["postgresql"] = "up"
        except Exception:
            status["postgresql"] = "down"

        try:
            await self._cache.exists("__health__")
            status["redis"] = "up"
        except Exception:
            status["redis"] = "down"

        return status
