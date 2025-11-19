"""Domain error types.

This module defines domain-level errors as immutable ADTs.
These represent business logic errors, not infrastructure failures.
"""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class UserNotFoundError:
    """User does not exist in the system.

    Attributes:
        user_id: The user ID that was not found
    """

    user_id: UUID


@dataclass(frozen=True)
class InvalidMessageError:
    """Message validation failed.

    Attributes:
        text: The invalid message text
        reason: Why the message is invalid
    """

    text: str
    reason: str


# ADT: Union of all domain errors
DomainError = UserNotFoundError | InvalidMessageError
