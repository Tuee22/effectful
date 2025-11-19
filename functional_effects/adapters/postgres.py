"""PostgreSQL implementations of repository protocols.

This module provides asyncpg-based implementations for user and message repositories.
These are production-ready adapters that connect to real PostgreSQL databases.

For testing, use pytest mocks instead of these real implementations.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import asyncpg

from functional_effects.domain.message import ChatMessage
from functional_effects.domain.user import User, UserFound, UserLookupResult, UserNotFound
from functional_effects.infrastructure.repositories import (
    ChatMessageRepository,
    UserRepository,
)


class PostgresUserRepository(UserRepository):
    """asyncpg-based user repository.

    Implements UserRepository protocol using PostgreSQL via asyncpg.

    Attributes:
        _conn: asyncpg connection to PostgreSQL database
    """

    def __init__(self, connection: asyncpg.Connection) -> None:
        """Initialize repository with database connection.

        Args:
            connection: Active asyncpg connection
        """
        self._conn = connection

    async def get_by_id(self, user_id: UUID) -> UserLookupResult:
        """Fetch user by ID from PostgreSQL.

        Args:
            user_id: UUID of the user to fetch

        Returns:
            UserFound if user exists with source="database"
            UserNotFound with reason="does_not_exist" if not found
        """
        row = await self._conn.fetchrow("SELECT id, email, name FROM users WHERE id = $1", user_id)

        if row is None:
            return UserNotFound(user_id=user_id, reason="does_not_exist")

        user = User(id=row["id"], email=row["email"], name=row["name"])
        return UserFound(user=user, source="database")


class PostgresChatMessageRepository(ChatMessageRepository):
    """asyncpg-based chat message repository.

    Implements ChatMessageRepository protocol using PostgreSQL via asyncpg.

    Attributes:
        _conn: asyncpg connection to PostgreSQL database
    """

    def __init__(self, connection: asyncpg.Connection) -> None:
        """Initialize repository with database connection.

        Args:
            connection: Active asyncpg connection
        """
        self._conn = connection

    async def save_message(self, user_id: UUID, text: str) -> ChatMessage:
        """Save a new chat message to PostgreSQL.

        Args:
            user_id: UUID of the user sending the message
            text: Message content

        Returns:
            The saved ChatMessage with generated ID and timestamp
        """
        row = await self._conn.fetchrow(
            """
            INSERT INTO chat_messages (id, user_id, text, created_at)
            VALUES ($1, $2, $3, $4)
            RETURNING id, user_id, text, created_at
            """,
            uuid4(),
            user_id,
            text,
            datetime.now(UTC),
        )

        return ChatMessage(
            id=row["id"],
            user_id=row["user_id"],
            text=row["text"],
            created_at=row["created_at"],
        )

    async def list_messages_for_user(self, user_id: UUID) -> list[ChatMessage]:
        """List all messages for a given user from PostgreSQL.

        Args:
            user_id: UUID of the user

        Returns:
            List of ChatMessages ordered by created_at (may be empty)
        """
        rows = await self._conn.fetch(
            """
            SELECT id, user_id, text, created_at
            FROM chat_messages
            WHERE user_id = $1
            ORDER BY created_at ASC
            """,
            user_id,
        )

        return [
            ChatMessage(
                id=row["id"],
                user_id=row["user_id"],
                text=row["text"],
                created_at=row["created_at"],
            )
            for row in rows
        ]
