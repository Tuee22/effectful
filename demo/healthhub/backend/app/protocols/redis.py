"""Redis client protocol for dependency injection."""

from typing import Protocol, Union


class RedisClient(Protocol):
    """Protocol for Redis operations (cache + pub/sub).

    Matches redis.asyncio.Redis[bytes] interface for structural typing.

    Testing: Use pytest-mock with spec=RedisClient or pass real redis.asyncio.Redis[bytes]
    """

    async def get(self, name: str) -> str | bytes | None:
        """Get value for key.

        Args:
            name: Key name (matches redis.asyncio parameter)

        Returns:
            Value as str or bytes (redis.asyncio.Redis[bytes] can return either)
        """
        ...

    async def set(
        self,
        name: str,
        value: Union[str, bytes, int, float],
        ex: int | None = None,
        px: int | None = None,
        nx: bool = False,
        xx: bool = False,
        keepttl: bool = False,
        get: bool = False,
        exat: int | None = None,
        pxat: int | None = None,
    ) -> bool | None:
        """Set key to value with optional expiration.

        Args:
            name: Key name (matches redis.asyncio parameter)
            value: Value to set
            ex: Expire time in seconds
            (other params match redis.asyncio.Redis.set signature)

        Returns:
            True if operation succeeded, None if condition not met
        """
        ...

    async def delete(self, *names: str) -> int:
        """Delete one or more keys from cache.

        Args:
            *names: Key names to delete

        Returns:
            Number of keys deleted
        """
        ...

    async def publish(self, channel: str, message: str | bytes) -> int:
        """Publish message to channel.

        Returns:
            Number of subscribers that received the message
        """
        ...

    async def aclose(self) -> None:
        """Close the Redis connection."""
        ...
