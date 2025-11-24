"""Auth service fixtures for integration and e2e testing.

Provides fixtures for:
- Redis-backed auth service with JWT support
"""

import pytest_asyncio
from redis.asyncio import Redis

from effectful.adapters.redis_auth import RedisAuthService
from tests.fixtures.config import JWT_SECRET


@pytest_asyncio.fixture
async def auth_service(clean_redis: Redis) -> RedisAuthService:
    """Provide an auth service backed by real Redis.

    Uses clean_redis to ensure test isolation - the Redis database
    is flushed before each test.

    Args:
        clean_redis: Clean Redis async client

    Returns:
        RedisAuthService instance with empty blacklist/sessions
    """
    return RedisAuthService(
        redis_client=clean_redis,
        jwt_secret=JWT_SECRET,
        jwt_algorithm="HS256",
    )
