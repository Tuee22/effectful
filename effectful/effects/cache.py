"""Cache effect DSL.

This module defines effects for cache operations:
- GetCachedProfile: Fetch profile from cache
- PutCachedProfile: Store profile in cache with TTL
- InvalidateCache: Invalidate cache entry by key
- GetCachedValue: Get cached value by key (generic)
- PutCachedValue: Put value in cache

All effects are immutable (frozen dataclasses).
"""

from dataclasses import dataclass
from uuid import UUID

from effectful.domain.profile import ProfileData


@dataclass(frozen=True)
class GetCachedProfile:
    """Effect: Fetch user profile from cache.

    Attributes:
        user_id: UUID of the user whose profile to fetch
    """

    user_id: UUID


@dataclass(frozen=True)
class PutCachedProfile:
    """Effect: Store user profile in cache with TTL.

    Attributes:
        user_id: UUID of the user
        profile_data: The profile data to cache
        ttl_seconds: Time-to-live in seconds (default: 300)
    """

    user_id: UUID
    profile_data: ProfileData
    ttl_seconds: int = 300


@dataclass(frozen=True)
class InvalidateCache:
    """Effect: Invalidate cache entry by key.

    Attributes:
        key: Cache key to invalidate
    """

    key: str


@dataclass(frozen=True)
class GetCachedValue:
    """Effect: Get cached value by key (generic).

    Returns CacheLookupResult ADT:
    - CacheHit(data=bytes) if key exists
    - CacheMiss() if key not found

    Attributes:
        key: Cache key to retrieve
    """

    key: str


@dataclass(frozen=True)
class PutCachedValue:
    """Effect: Put value in cache with TTL.

    Attributes:
        key: Cache key
        value: Value to cache (bytes)
        ttl_seconds: Time-to-live in seconds
    """

    key: str
    value: bytes
    ttl_seconds: int


# ADT: Union of all cache effects using PEP 695 type statement
type CacheEffect = (
    GetCachedProfile | PutCachedProfile | InvalidateCache | GetCachedValue | PutCachedValue
)
