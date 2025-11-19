"""Cache operation result ADTs.

This module defines ADTs for cache operations to eliminate Optional types.
Using ADTs makes cache hits/misses explicit and type-safe.
"""

from dataclasses import dataclass
from typing import Literal

# Generic cache lookup ADT - replaces Optional[T]


@dataclass(frozen=True)
class CacheHit[T]:
    """Value was found in cache.

    Attributes:
        value: The cached value
        ttl_remaining: Seconds until expiration (for monitoring)
    """

    value: T
    ttl_remaining: int


@dataclass(frozen=True)
class CacheMiss:
    """Value was not found in cache.

    Attributes:
        key: The cache key that was searched
        reason: Why the value wasn't in cache
    """

    key: str
    reason: Literal["not_found", "expired", "evicted"]


# ADT: Union of cache lookup results (no Optional!) using PEP 695 type statement
type CacheLookupResult[T] = CacheHit[T] | CacheMiss
