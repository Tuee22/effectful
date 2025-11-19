"""Profile domain models.

This module defines profile-related domain objects including:
- ProfileData: Cached user profile information
- ProfileLookupResult: ADT for profile lookup (found or not found)

Uses ADTs to eliminate Optional types and make illegal states unrepresentable.
"""

from dataclasses import dataclass
from typing import Literal
from uuid import UUID


@dataclass(frozen=True)
class ProfileData:
    """Profile data for caching.

    Contains minimal user information suitable for caching.

    Attributes:
        id: User ID as string (for JSON serialization)
        name: User's display name
    """

    id: str
    name: str


# ProfileLookupResult ADT - replaces Optional[ProfileData]


@dataclass(frozen=True)
class ProfileFound:
    """Profile was found (either in cache or database).

    Attributes:
        profile: The profile data
        source: Where the profile was found ("cache" or "database")
    """

    profile: ProfileData
    source: Literal["cache", "database"]


@dataclass(frozen=True)
class ProfileNotFound:
    """Profile was not found.

    Attributes:
        user_id: The user ID that was looked up
        reason: Why the profile wasn't found
    """

    user_id: UUID
    reason: Literal["no_cache_no_user", "cache_miss_no_user"]


# ADT: Union of profile lookup results (no Optional!) using PEP 695 type statement
type ProfileLookupResult = ProfileFound | ProfileNotFound
