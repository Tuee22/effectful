"""Redis client factory using application settings."""

from __future__ import annotations

import redis.asyncio as redis

from app.config import settings


def create_redis_client() -> redis.Redis[bytes]:
    """Create a Redis client configured from settings."""
    return redis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
        decode_responses=False,
    )
