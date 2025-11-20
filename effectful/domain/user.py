"""User domain model.

This module defines the User entity and UserLookupResult ADT.
All domain models are immutable and use ADTs to eliminate Optional types.
"""

from dataclasses import dataclass
from typing import Literal
from uuid import UUID


@dataclass(frozen=True)
class User:
    """User entity.

    Represents a user in the system with immutable attributes.

    Attributes:
        id: Unique identifier for the user
        name: User's display name
        email: User's email address
    """

    id: UUID
    name: str
    email: str


# UserLookupResult ADT - replaces Optional[User]


@dataclass(frozen=True)
class UserFound:
    """User was found in the repository.

    Attributes:
        user: The user entity
        source: Where the user was found (for telemetry/debugging)
    """

    user: User
    source: Literal["database", "cache"]


@dataclass(frozen=True)
class UserNotFound:
    """User was not found in the repository.

    Attributes:
        user_id: The user ID that was searched for
        reason: Why the user wasn't found
    """

    user_id: UUID
    reason: Literal["does_not_exist", "deleted"]


# ADT: Union of user lookup results (no Optional!) using PEP 695 type statement
type UserLookupResult = UserFound | UserNotFound
