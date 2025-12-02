"""Rate limiting infrastructure using Redis sliding window algorithm."""

from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
import redis.asyncio as redis
from redis.asyncio.client import Pipeline


class RateLimiter:
    """Redis-based rate limiter with sliding window algorithm."""

    def __init__(self, redis_client: redis.Redis[bytes]) -> None:
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
        pipe: Pipeline[bytes] = self.redis_client.pipeline()

        # Remove old entries outside the window
        pipe.zremrangebyscore(key, 0, window_start.timestamp())

        # Count current requests in window
        pipe.zcard(key)

        # Add current request timestamp
        pipe.zadd(key, {str(now.timestamp()): now.timestamp()})

        # Set expiration on key
        pipe.expire(key, window_seconds)

        results = await pipe.execute()
        current_count = results[1]  # zcard result
        assert isinstance(current_count, int)

        return current_count < max_requests


def get_rate_limiter() -> RateLimiter:
    """Dependency to get rate limiter instance."""
    redis_client: redis.Redis[bytes] = redis.Redis(
        host="redis",
        port=6379,
        decode_responses=False,
    )
    return RateLimiter(redis_client)


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
