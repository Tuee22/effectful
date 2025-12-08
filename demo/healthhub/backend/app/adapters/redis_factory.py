"""Production Redis client factory implementation.

Provides concrete implementation of RedisClientFactory protocol for production use.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

import redis.asyncio as redis

from app.config import settings

if TYPE_CHECKING:
    from redis.asyncio import Redis


class ProductionRedisClientFactory:
    """Production factory creating real Redis clients.

    This factory creates Redis clients configured from application settings.
    Each client is independent and should be used for a single request to
    ensure proper resource isolation.

    The factory implements the RedisClientFactory protocol through structural
    typing, allowing for easy test mocking.

    Example usage:
        factory = ProductionRedisClientFactory()
        async with factory.managed() as client:
            await client.set("key", "value")
        # Client automatically closed
    """

    def create(self) -> "Redis[bytes]":
        """Create new Redis client for single request.

        Returns:
            A new Redis client instance configured from application settings.

        Note:
            Caller is responsible for closing the client when using this method.
            Consider using managed() for automatic cleanup.
        """
        return redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            decode_responses=False,
        )

    @asynccontextmanager
    async def managed(self) -> "AsyncIterator[Redis[bytes]]":
        """Create Redis client with automatic cleanup.

        This context manager creates a Redis client and ensures it is properly
        closed when the context exits, preventing connection leaks.

        Yields:
            A Redis client instance that will be automatically closed.

        Example:
            factory = ProductionRedisClientFactory()
            async with factory.managed() as client:
                await client.set("key", "value")
                value = await client.get("key")
        """
        client = self.create()
        try:
            yield client
        finally:
            await client.aclose()
