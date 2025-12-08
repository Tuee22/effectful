"""Database effect DSL.

This module defines effects for database operations:
- GetUserById: Fetch user by ID
- SaveChatMessage: Persist chat message
- ListMessagesForUser: Retrieve all messages for a user
- ListUsers: List all users
- CreateUser: Create new user
- UpdateUser: Update user fields
- DeleteUser: Delete user

All effects are immutable (frozen dataclasses).
"""

from dataclasses import dataclass
from typing import TypeVar

from effectful.domain.optional_value import Absent, OptionalValue, Provided, to_optional_value

T_co = TypeVar("T_co")


def _normalize_optional_value(
    value: T_co | OptionalValue[T_co] | None,
) -> OptionalValue[T_co]:
    if isinstance(value, (Provided, Absent)):
        return value
    return to_optional_value(value)


from uuid import UUID


@dataclass(frozen=True)
class GetUserById:
    """Effect: Fetch user from database by ID.

    Attributes:
        user_id: UUID of the user to fetch
    """

    user_id: UUID


@dataclass(frozen=True)
class SaveChatMessage:
    """Effect: Save chat message to database.

    Attributes:
        user_id: UUID of the user sending the message
        text: Content of the message
    """

    user_id: UUID
    text: str


@dataclass(frozen=True)
class ListMessagesForUser:
    """Effect: List all messages for a given user.

    Attributes:
        user_id: UUID of the user whose messages to retrieve
    """

    user_id: UUID


@dataclass(frozen=True)
class GetChatMessages:
    """Alias effect: List all chat messages for a user (documented name).

    This mirrors ListMessagesForUser for compatibility with documentation examples.
    """

    user_id: UUID


@dataclass(frozen=True, init=False)
class ListUsers:
    """Effect: List all users with optional pagination.

    Attributes:
        limit: Maximum number of users to return
        offset: Number of users to skip
    """

    limit: OptionalValue[int]
    offset: OptionalValue[int]

    def __init__(
        self,
        limit: int | OptionalValue[int] | None = None,
        offset: int | OptionalValue[int] | None = None,
    ) -> None:
        object.__setattr__(self, "limit", _normalize_optional_value(limit))
        object.__setattr__(self, "offset", _normalize_optional_value(offset))


@dataclass(frozen=True)
class CreateUser:
    """Effect: Create new user.

    Attributes:
        email: User email address
        name: User name
        password_hash: Bcrypt password hash
    """

    email: str
    name: str
    password_hash: str


@dataclass(frozen=True, init=False)
class UpdateUser:
    """Effect: Update user fields.

    Attributes:
        user_id: UUID of user to update
        email: New email (None to keep current)
        name: New name (None to keep current)
    """

    user_id: UUID
    email: OptionalValue[str]
    name: OptionalValue[str]

    def __init__(
        self,
        user_id: UUID,
        email: str | OptionalValue[str] | None = None,
        name: str | OptionalValue[str] | None = None,
    ) -> None:
        object.__setattr__(self, "user_id", user_id)
        object.__setattr__(self, "email", _normalize_optional_value(email))
        object.__setattr__(self, "name", _normalize_optional_value(name))


@dataclass(frozen=True)
class DeleteUser:
    """Effect: Delete user by ID.

    Attributes:
        user_id: UUID of user to delete
    """

    user_id: UUID


# ADT: Union of all database effects using PEP 695 type statement
type DatabaseEffect = (
    GetUserById
    | SaveChatMessage
    | ListMessagesForUser
    | GetChatMessages
    | ListUsers
    | CreateUser
    | UpdateUser
    | DeleteUser
)
