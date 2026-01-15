"""Redis client factory protocol.

Defines the interface for creating per-request Redis clients with automatic cleanup.
"""

from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    import redis.asyncio as redis


class RedisClientFactory(Protocol):
    """Protocol for creating per-request Redis clients.

    This protocol defines the interface for factories that create Redis clients
    with automatic resource management. Implementations should ensure proper
    connection cleanup to prevent resource leaks.

    Example usage:
        async with factory.managed() as client:
            await client.set("key", "value")
        # Client automatically closed after context
    """

    def create(self) -> "redis.Redis[bytes]":
        """Create new Redis client for single request.

        Returns:
            A new Redis client instance configured for the application.

        Note:
            Caller is responsible for closing the client when using this method.
            Consider using managed() for automatic cleanup.
        """
        ...

    def managed(self) -> "AbstractAsyncContextManager[redis.Redis[bytes]]":
        """Create Redis client with automatic cleanup.

        This context manager creates a Redis client and ensures it is properly
        closed when the context exits, even if an exception occurs.

        Yields:
            A Redis client instance that will be automatically closed.

        Example:
            async with factory.managed() as client:
                await client.set("key", "value")
        """
        ...
