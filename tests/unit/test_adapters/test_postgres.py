"""Unit tests for PostgreSQL adapters.

Tests PostgresUserRepository and PostgresChatMessageRepository using pytest-mock.
All tests use AsyncMock with spec to ensure type safety.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from pytest_mock import MockerFixture
import asyncpg

from effectful.adapters.postgres import (
    PostgresChatMessageRepository,
    PostgresUserRepository,
)
from effectful.domain.message import ChatMessage
from effectful.domain.user import User, UserFound, UserNotFound


class TestPostgresUserRepository:
    """Tests for PostgresUserRepository."""

    @pytest.mark.asyncio
    async def test_get_by_id_returns_user_found_when_exists(self, mocker: MockerFixture) -> None:
        """Test successful user lookup returns UserFound."""
        # Setup
        user_id = uuid4()
        mock_conn = mocker.AsyncMock(spec=asyncpg.Connection)
        mock_row = {
            "id": user_id,
            "email": "test@example.com",
            "name": "Test User",
        }
        mock_conn.fetchrow.return_value = mock_row

        repo = PostgresUserRepository(mock_conn)

        # Execute
        result = await repo.get_by_id(user_id)

        # Assert
        assert isinstance(result, UserFound)
        assert result.user.id == user_id
        assert result.user.email == "test@example.com"
        assert result.user.name == "Test User"
        assert result.source == "database"

        # Verify query
        mock_conn.fetchrow.assert_called_once()
        call_args = mock_conn.fetchrow.call_args
        assert "SELECT id, email, name FROM users WHERE id = $1" in call_args.args[0]
        assert call_args.args[1] == user_id

    @pytest.mark.asyncio
    async def test_get_by_id_returns_user_not_found_when_missing(
        self, mocker: MockerFixture
    ) -> None:
        """Test user lookup returns UserNotFound when user doesn't exist."""
        # Setup
        user_id = uuid4()
        mock_conn = mocker.AsyncMock(spec=asyncpg.Connection)
        mock_conn.fetchrow.return_value = None

        repo = PostgresUserRepository(mock_conn)

        # Execute
        result = await repo.get_by_id(user_id)

        # Assert
        assert isinstance(result, UserNotFound)
        assert result.user_id == user_id
        assert result.reason == "does_not_exist"

    @pytest.mark.asyncio
    async def test_get_by_id_raises_on_invalid_id_type(self, mocker: MockerFixture) -> None:
        """Test that invalid row types raise RuntimeError."""
        # Setup
        user_id = uuid4()
        mock_conn = mocker.AsyncMock(spec=asyncpg.Connection)
        mock_row = {
            "id": "not-a-uuid",  # Invalid type
            "email": "test@example.com",
            "name": "Test User",
        }
        mock_conn.fetchrow.return_value = mock_row

        repo = PostgresUserRepository(mock_conn)

        # Execute & Assert
        with pytest.raises(RuntimeError, match="Invalid row id type"):
            await repo.get_by_id(user_id)

    @pytest.mark.asyncio
    async def test_get_by_id_raises_on_invalid_email_type(self, mocker: MockerFixture) -> None:
        """Test that invalid email type raises RuntimeError."""
        # Setup
        user_id = uuid4()
        mock_conn = mocker.AsyncMock(spec=asyncpg.Connection)
        mock_row = {
            "id": user_id,
            "email": 123,  # Invalid type
            "name": "Test User",
        }
        mock_conn.fetchrow.return_value = mock_row

        repo = PostgresUserRepository(mock_conn)

        # Execute & Assert
        with pytest.raises(RuntimeError, match="Invalid row email type"):
            await repo.get_by_id(user_id)

    @pytest.mark.asyncio
    async def test_get_by_id_raises_on_invalid_name_type(self, mocker: MockerFixture) -> None:
        """Test that invalid name type raises RuntimeError."""
        # Setup
        user_id = uuid4()
        mock_conn = mocker.AsyncMock(spec=asyncpg.Connection)
        mock_row = {
            "id": user_id,
            "email": "test@example.com",
            "name": None,  # Invalid type
        }
        mock_conn.fetchrow.return_value = mock_row

        repo = PostgresUserRepository(mock_conn)

        # Execute & Assert
        with pytest.raises(RuntimeError, match="Invalid row name type"):
            await repo.get_by_id(user_id)


class TestPostgresChatMessageRepository:
    """Tests for PostgresChatMessageRepository."""

    @pytest.mark.asyncio
    async def test_save_message_returns_chat_message(self, mocker: MockerFixture) -> None:
        """Test saving a message returns ChatMessage with generated fields."""
        # Setup
        user_id = uuid4()
        message_id = uuid4()
        created_at = datetime.now(UTC)
        text = "Hello, World!"

        mock_conn = mocker.AsyncMock(spec=asyncpg.Connection)
        mock_row = {
            "id": message_id,
            "user_id": user_id,
            "text": text,
            "created_at": created_at,
        }
        mock_conn.fetchrow.return_value = mock_row

        repo = PostgresChatMessageRepository(mock_conn)

        # Execute
        result = await repo.save_message(user_id, text)

        # Assert
        assert isinstance(result, ChatMessage)
        assert result.id == message_id
        assert result.user_id == user_id
        assert result.text == text
        assert result.created_at == created_at

        # Verify INSERT query
        mock_conn.fetchrow.assert_called_once()
        call_args = mock_conn.fetchrow.call_args
        assert "INSERT INTO chat_messages" in call_args.args[0]
        assert "RETURNING" in call_args.args[0]

    @pytest.mark.asyncio
    async def test_save_message_raises_on_no_returning_row(self, mocker: MockerFixture) -> None:
        """Test that missing RETURNING row raises RuntimeError."""
        # Setup
        user_id = uuid4()
        mock_conn = mocker.AsyncMock(spec=asyncpg.Connection)
        mock_conn.fetchrow.return_value = None

        repo = PostgresChatMessageRepository(mock_conn)

        # Execute & Assert
        with pytest.raises(RuntimeError, match="INSERT RETURNING returned no row"):
            await repo.save_message(user_id, "Hello")

    @pytest.mark.asyncio
    async def test_save_message_raises_on_invalid_id_type(self, mocker: MockerFixture) -> None:
        """Test that invalid id type in result raises RuntimeError."""
        # Setup
        user_id = uuid4()
        mock_conn = mocker.AsyncMock(spec=asyncpg.Connection)
        mock_row = {
            "id": "not-uuid",
            "user_id": user_id,
            "text": "Hello",
            "created_at": datetime.now(UTC),
        }
        mock_conn.fetchrow.return_value = mock_row

        repo = PostgresChatMessageRepository(mock_conn)

        # Execute & Assert
        with pytest.raises(RuntimeError, match="Invalid row id type"):
            await repo.save_message(user_id, "Hello")

    @pytest.mark.asyncio
    async def test_list_messages_for_user_returns_messages(self, mocker: MockerFixture) -> None:
        """Test listing messages returns list of ChatMessages."""
        # Setup
        user_id = uuid4()
        msg1_id = uuid4()
        msg2_id = uuid4()
        created_at1 = datetime.now(UTC)
        created_at2 = datetime.now(UTC)

        mock_conn = mocker.AsyncMock(spec=asyncpg.Connection)
        mock_rows = [
            {
                "id": msg1_id,
                "user_id": user_id,
                "text": "First message",
                "created_at": created_at1,
            },
            {
                "id": msg2_id,
                "user_id": user_id,
                "text": "Second message",
                "created_at": created_at2,
            },
        ]
        mock_conn.fetch.return_value = mock_rows

        repo = PostgresChatMessageRepository(mock_conn)

        # Execute
        result = await repo.list_messages_for_user(user_id)

        # Assert
        assert len(result) == 2
        assert all(isinstance(msg, ChatMessage) for msg in result)
        assert result[0].id == msg1_id
        assert result[0].text == "First message"
        assert result[1].id == msg2_id
        assert result[1].text == "Second message"

        # Verify query
        mock_conn.fetch.assert_called_once()
        call_args = mock_conn.fetch.call_args
        assert "SELECT id, user_id, text, created_at" in call_args.args[0]
        assert "WHERE user_id = $1" in call_args.args[0]
        assert "ORDER BY created_at ASC" in call_args.args[0]

    @pytest.mark.asyncio
    async def test_list_messages_for_user_returns_empty_list(self, mocker: MockerFixture) -> None:
        """Test listing messages for user with no messages returns empty list."""
        # Setup
        user_id = uuid4()
        mock_conn = mocker.AsyncMock(spec=asyncpg.Connection)
        mock_conn.fetch.return_value = []

        repo = PostgresChatMessageRepository(mock_conn)

        # Execute
        result = await repo.list_messages_for_user(user_id)

        # Assert
        assert result == []

    @pytest.mark.asyncio
    async def test_list_messages_skips_invalid_rows(self, mocker: MockerFixture) -> None:
        """Test that rows with invalid types are skipped."""
        # Setup
        user_id = uuid4()
        msg_id = uuid4()
        created_at = datetime.now(UTC)

        mock_conn = mocker.AsyncMock(spec=asyncpg.Connection)
        mock_rows = [
            {
                "id": "invalid",  # Invalid UUID
                "user_id": user_id,
                "text": "Bad message",
                "created_at": created_at,
            },
            {
                "id": msg_id,
                "user_id": user_id,
                "text": "Good message",
                "created_at": created_at,
            },
        ]
        mock_conn.fetch.return_value = mock_rows

        repo = PostgresChatMessageRepository(mock_conn)

        # Execute
        result = await repo.list_messages_for_user(user_id)

        # Assert - only valid row returned
        assert len(result) == 1
        assert result[0].id == msg_id
        assert result[0].text == "Good message"
