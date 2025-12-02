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


@dataclass(frozen=True)
class ListUsers:
    """Effect: List all users with optional pagination.

    Attributes:
        limit: Maximum number of users to return
        offset: Number of users to skip
    """

    limit: int | None = None
    offset: int | None = None


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


@dataclass(frozen=True)
class UpdateUser:
    """Effect: Update user fields.

    Attributes:
        user_id: UUID of user to update
        email: New email (None to keep current)
        name: New name (None to keep current)
    """

    user_id: UUID
    email: str | None = None
    name: str | None = None


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
