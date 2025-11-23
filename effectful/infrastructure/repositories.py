"""Repository protocols for data access.

This module defines Protocol interfaces (ports) for repositories.
Concrete implementations (adapters) are provided elsewhere.
Uses ADTs instead of Optional for type safety.
"""

from typing import Protocol
from uuid import UUID

from effectful.domain.message import ChatMessage
from effectful.domain.user import User, UserLookupResult


class UserRepository(Protocol):
    """Protocol for user repository operations."""

    async def get_by_id(self, user_id: UUID) -> UserLookupResult:
        """Fetch user by ID.

        Args:
            user_id: UUID of the user to fetch

        Returns:
            UserFound if user exists, UserNotFound otherwise
            (ADT eliminates Optional and makes outcomes explicit)
        """
        ...

    async def get_by_email(self, email: str) -> UserLookupResult:
        """Fetch user by email.

        Args:
            email: Email address to search for

        Returns:
            UserFound if user exists, UserNotFound otherwise
        """
        ...

    async def list_users(self, limit: int | None, offset: int | None) -> list[User]:
        """List all users with optional pagination.

        Args:
            limit: Maximum number of users to return
            offset: Number of users to skip

        Returns:
            List of User objects (may be empty)
        """
        ...

    async def create_user(self, email: str, name: str, password_hash: str) -> User:
        """Create new user.

        Args:
            email: User email address
            name: User name
            password_hash: Bcrypt password hash

        Returns:
            The created User with generated ID
        """
        ...

    async def update_user(
        self, user_id: UUID, email: str | None, name: str | None
    ) -> UserLookupResult:
        """Update user fields.

        Args:
            user_id: UUID of user to update
            email: New email (None to keep current)
            name: New name (None to keep current)

        Returns:
            UserFound with updated user, UserNotFound if not found
        """
        ...

    async def delete_user(self, user_id: UUID) -> None:
        """Delete user by ID.

        Args:
            user_id: UUID of user to delete
        """
        ...


class ChatMessageRepository(Protocol):
    """Protocol for chat message repository operations."""

    async def save_message(self, user_id: UUID, text: str) -> ChatMessage:
        """Save a new chat message.

        Args:
            user_id: UUID of the user sending the message
            text: Message content

        Returns:
            The saved ChatMessage with generated ID and timestamp
        """
        ...

    async def list_messages_for_user(self, user_id: UUID) -> list[ChatMessage]:
        """List all messages for a given user.

        Args:
            user_id: UUID of the user

        Returns:
            List of ChatMessages (may be empty)
        """
        ...
