"""PostgreSQL implementations of repository protocols.

This module provides asyncpg-based implementations for user and message repositories.
These are production-ready adapters that connect to real PostgreSQL databases.

For testing, use pytest mocks instead of these real implementations.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import asyncpg

from effectful.domain.message import ChatMessage
from effectful.domain.user import User, UserFound, UserLookupResult, UserNotFound
from effectful.infrastructure.repositories import (
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

        row_id = row["id"]
        row_email = row["email"]
        row_name = row["name"]

        if not isinstance(row_id, UUID):
            raise RuntimeError(f"Invalid row id type: {type(row_id)}")
        if not isinstance(row_email, str):
            raise RuntimeError(f"Invalid row email type: {type(row_email)}")
        if not isinstance(row_name, str):
            raise RuntimeError(f"Invalid row name type: {type(row_name)}")

        user = User(id=row_id, email=row_email, name=row_name)
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

        if row is None:
            raise RuntimeError("INSERT RETURNING returned no row")

        row_id = row["id"]
        row_user_id = row["user_id"]
        row_text = row["text"]
        row_created_at = row["created_at"]

        if not isinstance(row_id, UUID):
            raise RuntimeError(f"Invalid row id type: {type(row_id)}")
        if not isinstance(row_user_id, UUID):
            raise RuntimeError(f"Invalid row user_id type: {type(row_user_id)}")
        if not isinstance(row_text, str):
            raise RuntimeError(f"Invalid row text type: {type(row_text)}")
        if not isinstance(row_created_at, datetime):
            raise RuntimeError(f"Invalid row created_at type: {type(row_created_at)}")

        return ChatMessage(
            id=row_id,
            user_id=row_user_id,
            text=row_text,
            created_at=row_created_at,
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

        messages: list[ChatMessage] = []
        for row in rows:
            row_id = row["id"]
            row_user_id = row["user_id"]
            row_text = row["text"]
            row_created_at = row["created_at"]

            if not isinstance(row_id, UUID):
                continue
            if not isinstance(row_user_id, UUID):
                continue
            if not isinstance(row_text, str):
                continue
            if not isinstance(row_created_at, datetime):
                continue

            messages.append(
                ChatMessage(
                    id=row_id,
                    user_id=row_user_id,
                    text=row_text,
                    created_at=row_created_at,
                )
            )

        return messages
