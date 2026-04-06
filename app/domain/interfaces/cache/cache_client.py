from abc import ABC, abstractmethod
from typing import Any


class ICacheClient(ABC):
    """Abstract cache client interface.

    Defines only generic cache operations independent of any specific
    cache backend (Redis, Memcached, in-memory, etc.).

    Backend-specific operations (e.g. Redis lists, sorted sets) must
    NOT be added here — extend the concrete implementation instead.
    """

    @abstractmethod
    async def get(
        self,
        key: str,
    ) -> Any | None:
        """Return the value stored at key, or None if not found."""
        ...

    @abstractmethod
    async def set(
        self,
        key: str,
        value: Any,
        ex: int | None = None,
    ) -> None:
        """Store value at key with optional TTL in seconds."""
        ...

    @abstractmethod
    async def exists(
        self,
        key: str,
    ) -> bool:
        """Return True if key exists in the cache."""
        ...

    @abstractmethod
    async def delete(
        self,
        key: str,
    ) -> None:
        """Delete key from the cache."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Close the cache connection."""
        ...
