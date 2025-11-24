"""Redis fixtures for integration and e2e testing.

Provides fixtures for:
- Redis client connections
- Cache cleanup
- Profile cache adapter
"""

from collections.abc import AsyncGenerator

import pytest_asyncio
from redis.asyncio import Redis

from effectful.adapters.redis_cache import RedisProfileCache
from tests.fixtures.config import REDIS_HOST, REDIS_PORT


@pytest_asyncio.fixture
async def redis_client() -> AsyncGenerator[Redis, None]:
    """Provide a Redis client for integration tests.

    Flushes the database between tests for isolation.

    Yields:
        Active Redis async client
    """
    client: Redis = Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

    # Clean up data before test
    await client.flushdb()

    try:
        yield client
    finally:
        await client.aclose()


@pytest_asyncio.fixture
async def clean_redis(redis_client: Redis) -> AsyncGenerator[Redis, None]:
    """Provide a clean Redis instance.

    Flushes the database before yielding, ensuring test isolation.
    Tests should seed their own data after receiving this fixture.

    Yields:
        Clean Redis client with empty database
    """
    await redis_client.flushdb()
    yield redis_client


@pytest_asyncio.fixture
async def profile_cache(redis_client: Redis) -> RedisProfileCache:
    """Provide a profile cache backed by real Redis.

    Args:
        redis_client: Active Redis async client

    Returns:
        RedisProfileCache instance
    """
    return RedisProfileCache(redis_client)
