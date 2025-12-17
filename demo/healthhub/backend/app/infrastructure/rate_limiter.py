"""Rate limiting infrastructure using Redis sliding window algorithm."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta
from typing import Annotated, AsyncIterator

from fastapi import Depends, HTTPException, Request, status
import redis.asyncio as redis

from app.container import ApplicationContainer
from app.config import Settings


class RedisWrapper:
    """Minimal wrapper to provide typed Redis commands used by the rate limiter."""

    def __init__(self, client: redis.Redis[bytes]) -> None:
        self._client = client

    async def zremrangebyscore(self, *args: object, **kwargs: object) -> int:
        return int(await getattr(self._client, "zremrangebyscore")(*args, **kwargs))

    async def zcard(self, *args: object, **kwargs: object) -> int:
        return int(await getattr(self._client, "zcard")(*args, **kwargs))

    async def zadd(self, *args: object, **kwargs: object) -> int:
        result = await getattr(self._client, "zadd")(*args, **kwargs)
        return int(result) if isinstance(result, (int, float)) else 0

    async def expire(self, *args: object, **kwargs: object) -> bool:
        result = await getattr(self._client, "expire")(*args, **kwargs)
        return bool(result)

    async def close(self) -> None:
        """Close underlying Redis connection."""
        await self._client.aclose()


class RateLimiter:
    """Redis-based rate limiter with sliding window algorithm."""

    def __init__(self, redis_client: RedisWrapper) -> None:
        self.redis_client = redis_client

    async def check_rate_limit(self, key: str, max_requests: int, window_seconds: int) -> bool:
        """Check if request is within rate limit using sliding window.

        Args:
            key: Unique identifier for the rate limit (e.g., "login:192.168.1.1")
            max_requests: Maximum number of requests allowed in window
            window_seconds: Time window in seconds

        Returns:
            True if within limit, False if rate limit exceeded
        """
        now = datetime.now()
        window_start = now - timedelta(seconds=window_seconds)

        # Use sorted set to store timestamps
        # Sequential ops keep the logic simple and avoid missing pipeline typing in redis stubs
        await self.redis_client.zremrangebyscore(key, 0, window_start.timestamp())
        current_count = await self.redis_client.zcard(key)
        await self.redis_client.zadd(key, {str(now.timestamp()): now.timestamp()})
        await self.redis_client.expire(key, window_seconds)

        return int(current_count) < max_requests


async def get_rate_limiter(
    request: Request,
) -> AsyncIterator[RateLimiter]:
    """Dependency to get rate limiter instance using container-managed factory."""
    container: ApplicationContainer = request.app.state.container
    async with container.redis_factory.managed() as client:
        yield RateLimiter(RedisWrapper(client))


def rate_limit(
    max_requests: int, window_seconds: int
) -> Callable[[Request, RateLimiter], Awaitable[None]]:
    """Dependency factory for rate limiting.

    Args:
        max_requests: Maximum number of requests allowed in window
        window_seconds: Time window in seconds

    Returns:
        Dependency function that raises HTTPException if rate limit exceeded
    """

    async def rate_limit_dependency(
        request: Request,
        limiter: Annotated[RateLimiter, Depends(get_rate_limiter)],
    ) -> None:
        settings: Settings | None = getattr(request.app.state, "settings", None)
        if settings is not None and settings.app_env != "production":
            return None
        # Use IP address as rate limit key
        ip_address = request.client.host if request.client else "unknown"
        endpoint = request.url.path
        key = f"rate_limit:{endpoint}:{ip_address}"

        allowed = await limiter.check_rate_limit(key, max_requests, window_seconds)

        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Max {max_requests} requests per {window_seconds} seconds.",
            )

    return rate_limit_dependency
