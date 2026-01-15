"""Redis implementation of cache protocol.

This module provides a Redis-based implementation of the ProfileCache protocol.
This is a production-ready adapter that connects to real Redis instances.

For testing, use pytest mocks instead of this real implementation.
"""

import json
from uuid import UUID

from redis.asyncio import Redis

from effectful.domain.cache_result import CacheHit, CacheLookupResult, CacheMiss
from effectful.domain.optional_value import Absent, OptionalValue, Provided
from effectful.domain.profile import ProfileData
from effectful.infrastructure.cache import ProfileCache


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

    async def _get_ttl_or_expired(self, key: str) -> OptionalValue[int]:
        """Get TTL from Redis, returning explicit ADT for absence.

        Args:
            key: Cache key to check TTL for

        Returns:
            Provided TTL in seconds (0 if no expiration),
            Absent when key expired or missing
        """
        ttl = await self._redis.ttl(key)
        # Redis returns int but mypy doesn't know, so ensure it's int
        ttl_int = int(ttl)
        if ttl_int == -1:
            # No expiration set
            return Provided(0)
        elif ttl_int == -2:
            # Key doesn't exist (expired/deleted)
            return Absent(reason="expired_or_missing")
        return Provided(ttl_int)

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
        ttl = await self._get_ttl_or_expired(key)
        match ttl:
            case Provided(value=ttl_value):
                return CacheHit(value=profile, ttl_remaining=ttl_value)
            case Absent():
                # Key doesn't exist (race condition between get and ttl)
                return CacheMiss(key=key, reason="expired")

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

    async def get_value(self, key: str) -> CacheLookupResult[bytes]:
        """Get cached value by key from Redis.

        Args:
            key: Cache key to retrieve

        Returns:
            CacheHit with bytes if found, CacheMiss if not found/expired
        """
        data = await self._redis.get(key)

        if data is None:
            return CacheMiss(key=key, reason="not_found")

        # Ensure we return bytes
        if isinstance(data, str):
            data = data.encode("utf-8")

        # Get remaining TTL
        ttl = await self._get_ttl_or_expired(key)
        match ttl:
            case Provided(value=ttl_value):
                return CacheHit(value=data, ttl_remaining=ttl_value)
            case Absent():
                return CacheMiss(key=key, reason="expired")

    async def put_value(self, key: str, value: bytes, ttl_seconds: int) -> None:
        """Store value in Redis with TTL.

        Args:
            key: Cache key
            value: Value to cache (bytes)
            ttl_seconds: Time-to-live in seconds
        """
        await self._redis.setex(key, ttl_seconds, value)

    async def invalidate(self, key: str) -> bool:
        """Invalidate cache entry by key in Redis.

        Args:
            key: Cache key to invalidate

        Returns:
            True if key was found and deleted, False if not found
        """
        result = await self._redis.delete(key)
        # Redis delete returns int, but we need explicit bool conversion
        deleted_count = int(result) if isinstance(result, int) else 0
        return deleted_count > 0
