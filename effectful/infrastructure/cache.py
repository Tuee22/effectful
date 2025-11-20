"""Cache protocol for profile data.

This module defines Protocol interface (port) for cache operations.
Concrete implementations (adapters) like Redis are provided elsewhere.
Uses ADTs instead of Optional for type safety.
"""

from typing import Protocol
from uuid import UUID

from effectful.domain.cache_result import CacheLookupResult
from effectful.domain.profile import ProfileData


class ProfileCache(Protocol):
    """Protocol for profile caching operations."""

    async def get_profile(self, user_id: UUID) -> CacheLookupResult[ProfileData]:
        """Get cached profile for user.

        Args:
            user_id: UUID of the user

        Returns:
            CacheHit with ProfileData if cached, CacheMiss if not found/expired
            (ADT eliminates Optional and makes cache state explicit)
        """
        ...

    async def put_profile(self, user_id: UUID, data: ProfileData, ttl_seconds: int) -> None:
        """Store profile in cache with TTL.

        Args:
            user_id: UUID of the user
            data: ProfileData to cache
            ttl_seconds: Time-to-live in seconds
        """
        ...
