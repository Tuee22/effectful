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


def _extract_user_from_row(row: asyncpg.Record) -> User:
    """Extract and validate User from asyncpg row with type checking.

    Args:
        row: asyncpg Record containing id, email, name columns

    Returns:
        Validated User instance

    Raises:
        RuntimeError: If any column has unexpected type
    """
    row_id = row["id"]
    row_email = row["email"]
    row_name = row["name"]

    if not isinstance(row_id, UUID):
        raise RuntimeError(f"Invalid row id type: {type(row_id)}")
    if not isinstance(row_email, str):
        raise RuntimeError(f"Invalid row email type: {type(row_email)}")
    if not isinstance(row_name, str):
        raise RuntimeError(f"Invalid row name type: {type(row_name)}")

    return User(id=row_id, email=row_email, name=row_name)


def _extract_chat_message_from_row(row: asyncpg.Record) -> ChatMessage:
    """Extract and validate ChatMessage from asyncpg row with type checking.

    Args:
        row: asyncpg Record containing id, user_id, text, created_at columns

    Returns:
        Validated ChatMessage instance

    Raises:
        RuntimeError: If any column has unexpected type
    """
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

        return UserFound(user=_extract_user_from_row(row), source="database")

    async def get_by_email(self, email: str) -> UserLookupResult:
        """Fetch user by email from PostgreSQL.

        Args:
            email: Email address to search for

        Returns:
            UserFound if user exists, UserNotFound otherwise
        """
        row = await self._conn.fetchrow("SELECT id, email, name FROM users WHERE email = $1", email)

        if row is None:
            # Use uuid4() as placeholder since we don't have a user_id
            return UserNotFound(user_id=uuid4(), reason="does_not_exist")

        return UserFound(user=_extract_user_from_row(row), source="database")

    async def list_users(self, limit: int | None, offset: int | None) -> list[User]:
        """List all users with optional pagination.

        Args:
            limit: Maximum number of users to return
            offset: Number of users to skip

        Returns:
            List of User objects
        """
        # Build query with pure pattern - tuple of optional parts
        query_parts = (
            "SELECT id, email, name FROM users ORDER BY name",
            f" LIMIT $1" if limit is not None else "",
            f" OFFSET ${2 if limit is not None else 1}" if offset is not None else "",
        )
        query = "".join(query_parts)
        params = tuple(p for p in (limit, offset) if p is not None)

        rows = await self._conn.fetch(query, *params)

        # Pure list comprehension with type validation
        return [
            User(id=row["id"], email=row["email"], name=row["name"])
            for row in rows
            if (
                isinstance(row["id"], UUID)
                and isinstance(row["email"], str)
                and isinstance(row["name"], str)
            )
        ]

    async def create_user(self, email: str, name: str, password_hash: str) -> User:
        """Create new user in PostgreSQL.

        Args:
            email: User email address
            name: User name
            password_hash: Bcrypt password hash

        Returns:
            The created User with generated ID
        """
        user_id = uuid4()
        row = await self._conn.fetchrow(
            """
            INSERT INTO users (id, email, name, password_hash)
            VALUES ($1, $2, $3, $4)
            RETURNING id, email, name
            """,
            user_id,
            email,
            name,
            password_hash,
        )

        if row is None:
            raise RuntimeError("INSERT RETURNING returned no row")

        return _extract_user_from_row(row)

    async def update_user(
        self, user_id: UUID, email: str | None, name: str | None
    ) -> UserLookupResult:
        """Update user fields in PostgreSQL.

        Args:
            user_id: UUID of user to update
            email: New email (None to keep current)
            name: New name (None to keep current)

        Returns:
            UserFound with updated user, UserNotFound if not found
        """
        # Build dynamic update with pure pattern - filter None values
        fields = tuple(
            (field, value)
            for field, value in (("email", email), ("name", name))
            if value is not None
        )

        if not fields:
            # No updates, just return current user
            return await self.get_by_id(user_id)

        # Build update clause with enumerate for parameter indices
        updates = ", ".join(f"{field} = ${i + 1}" for i, (field, _) in enumerate(fields))
        params: tuple[str | UUID, ...] = tuple(value for _, value in fields) + (user_id,)
        query = f"""
            UPDATE users SET {updates}
            WHERE id = ${len(fields) + 1}
            RETURNING id, email, name
        """

        row = await self._conn.fetchrow(query, *params)

        if row is None:
            return UserNotFound(user_id=user_id, reason="does_not_exist")

        return UserFound(user=_extract_user_from_row(row), source="database")

    async def delete_user(self, user_id: UUID) -> None:
        """Delete user from PostgreSQL.

        Args:
            user_id: UUID of user to delete
        """
        await self._conn.execute("DELETE FROM users WHERE id = $1", user_id)


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

        return _extract_chat_message_from_row(row)

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

        # Pure list comprehension with type validation
        return [
            ChatMessage(
                id=row["id"],
                user_id=row["user_id"],
                text=row["text"],
                created_at=row["created_at"],
            )
            for row in rows
            if (
                isinstance(row["id"], UUID)
                and isinstance(row["user_id"], UUID)
                and isinstance(row["text"], str)
                and isinstance(row["created_at"], datetime)
            )
        ]
