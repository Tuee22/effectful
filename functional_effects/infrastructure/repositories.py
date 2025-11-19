"""Repository protocols for data access.

This module defines Protocol interfaces (ports) for repositories.
Concrete implementations (adapters) are provided elsewhere.
Uses ADTs instead of Optional for type safety.
"""

from typing import Protocol
from uuid import UUID

from functional_effects.domain.message import ChatMessage
from functional_effects.domain.user import UserLookupResult


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
