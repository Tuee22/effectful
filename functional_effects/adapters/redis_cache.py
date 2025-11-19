"""Redis implementation of cache protocol.

This module provides a Redis-based implementation of the ProfileCache protocol.
This is a production-ready adapter that connects to real Redis instances.

For testing, use pytest mocks instead of this real implementation.
"""

import json
from uuid import UUID

from redis.asyncio import Redis

from functional_effects.domain.cache_result import CacheHit, CacheLookupResult, CacheMiss
from functional_effects.domain.profile import ProfileData
from functional_effects.infrastructure.cache import ProfileCache


class RedisProfileCache(ProfileCache):
    """Redis-based profile cache.

    Implements ProfileCache protocol using Redis via redis-py async client.
    Stores ProfileData as JSON with TTL support.

    Attributes:
        _redis: Redis async client connection
    """

    def __init__(self, redis_client: Redis) -> None:
        """Initialize cache with Redis connection.

        Args:
            redis_client: Active Redis async client
        """
        self._redis = redis_client

    async def get_profile(self, user_id: UUID) -> CacheLookupResult[ProfileData]:
        """Get cached profile from Redis.

        Args:
            user_id: UUID of the user

        Returns:
            CacheHit with ProfileData and TTL if found
            CacheMiss with key and reason if not found or expired
        """
        key = f"profile:{user_id}"
        data = await self._redis.get(key)

        if data is None:
            return CacheMiss(key=key, reason="not_found")

        # Parse JSON to ProfileData
        profile_dict = json.loads(data)
        profile = ProfileData(id=profile_dict["id"], name=profile_dict["name"])

        # Get remaining TTL
        ttl = await self._redis.ttl(key)
        if ttl == -1:
            # No expiration set (shouldn't happen but handle gracefully)
            ttl = 0
        elif ttl == -2:
            # Key doesn't exist (race condition between get and ttl)
            return CacheMiss(key=key, reason="expired")

        return CacheHit(value=profile, ttl_remaining=ttl)

    async def put_profile(self, user_id: UUID, data: ProfileData, ttl_seconds: int) -> None:
        """Store profile in Redis with TTL.

        Args:
            user_id: UUID of the user
            data: ProfileData to cache
            ttl_seconds: Time-to-live in seconds
        """
        key = f"profile:{user_id}"

        # Serialize ProfileData to JSON
        profile_json = json.dumps({"id": data.id, "name": data.name})

        # Store with TTL
        await self._redis.setex(key, ttl_seconds, profile_json)
