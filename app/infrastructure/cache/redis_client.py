from typing import Any, cast

from redis.asyncio import Redis

from app.domain.interfaces.cache.cache_client import ICacheClient


class AsyncRedisCache(ICacheClient):
    """Asynchronous Redis cache implementation."""

    def __init__(
        self,
        host: str,
        port: int,
        db: int = 0,
        password: str | None = None,
    ):
        self._client: Redis = Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=True,
        )

    @classmethod
    def from_url(
        cls,
        url: str,
    ) -> "AsyncRedisCache":
        """Create Redis client from URL."""
        client = Redis.from_url(
            url,
            decode_responses=True,
        )
        instance = cls.__new__(cls)
        instance._client = client
        return instance

    async def ping(self) -> bool:
        """Test connection with PING command."""
        return bool(await self._client.ping())  # type: ignore

    async def set(
        self,
        key: str,
        value: Any,
        ex: int | None = None,
    ) -> None:
        """Set cache value with optional expiration."""
        await self._client.set(key, value, ex=ex)

    async def get(
        self,
        key: str,
    ) -> Any | None:
        """Get cached value."""
        return await self._client.get(key)

    async def lrange(
        self,
        name: str,
        start: int,
        end: int,
    ) -> list[bytes]:
        return await self._client.lrange(name, start, end)  # type: ignore

    async def exists(
        self,
        key: str,
    ) -> bool:
        """Check if key exists in cache."""
        return bool(await self._client.exists(key))

    async def delete(
        self,
        key: str,
    ) -> None:
        """Delete cached value."""
        await self._client.delete(key)

    async def keys(
        self,
        pattern: str,
    ) -> list[str]:
        """Get all keys matching pattern."""
        return cast(list[str], await self._client.keys(pattern))

    async def flush_db(self) -> None:
        """Flush the current database."""
        await self._client.flushdb()

    async def close(self) -> None:
        """Close Redis connection."""
        await self._client.close()
