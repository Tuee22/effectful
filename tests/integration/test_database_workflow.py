"""Integration tests for database workflows with real PostgreSQL.

This module tests database effect workflows using run_ws_program
with real PostgreSQL infrastructure. Each test uses clean_db fixture
for declarative, idempotent test isolation.
"""

from collections.abc import Generator
from uuid import UUID, uuid4

import asyncpg
import pytest
from pytest_mock import MockerFixture

from effectful.adapters.postgres import PostgresChatMessageRepository, PostgresUserRepository
from effectful.algebraic.result import Err, Ok
from effectful.domain.message import ChatMessage
from effectful.domain.user import User, UserNotFound
from effectful.effects.database import (
    CreateUser,
    DeleteUser,
    GetUserById,
    ListMessagesForUser,
    ListUsers,
    SaveChatMessage,
    UpdateUser,
)
from effectful.effects.websocket import SendText
from effectful.infrastructure.cache import ProfileCache
from effectful.infrastructure.websocket import WebSocketConnection
from effectful.interpreters.composite import create_composite_interpreter
from effectful.interpreters.errors import DatabaseError
from effectful.programs.program_types import AllEffects, EffectResult
from effectful.programs.runners import run_ws_program


class TestDatabaseWorkflowIntegration:
    """Integration tests for database workflows with real PostgreSQL."""

    @pytest.mark.asyncio
    async def test_get_user_workflow_found(
        self, clean_db: asyncpg.Connection, mocker: MockerFixture
    ) -> None:
        """Workflow retrieves existing user from real PostgreSQL."""
        # Seed test data
        user_id = uuid4()
        await clean_db.execute(
            "INSERT INTO users (id, email, name) VALUES ($1, $2, $3)",
            user_id,
            "alice@example.com",
            "Alice",
        )

        # Create interpreter with real DB, mocked WebSocket
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_cache = mocker.AsyncMock(spec=ProfileCache)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=PostgresUserRepository(clean_db),
            message_repo=PostgresChatMessageRepository(clean_db),
            cache=mock_cache,
        )

        # Define workflow
        def get_user_program(
            uid: UUID,
        ) -> Generator[AllEffects, EffectResult, str]:
            user_result = yield GetUserById(user_id=uid)

            match user_result:
                case User(name=name):
                    yield SendText(text=f"Found: {name}")
                    return name
                case UserNotFound():
                    yield SendText(text="Not found")
                    return "not_found"
                case _:
                    return "error"

        # Act
        result = await run_ws_program(get_user_program(user_id), interpreter)

        # Assert
        match result:
            case Ok(name):
                assert name == "Alice"
                mock_ws.send_text.assert_called_once_with("Found: Alice")
            case Err(error):
                pytest.fail(f"Expected Ok, got Err({error})")

    @pytest.mark.asyncio
    async def test_get_user_workflow_not_found(
        self, clean_db: asyncpg.Connection, mocker: MockerFixture
    ) -> None:
        """Workflow handles user not found gracefully."""
        # No seeding - user doesn't exist
        user_id = uuid4()

        # Create interpreter with real DB
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_cache = mocker.AsyncMock(spec=ProfileCache)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=PostgresUserRepository(clean_db),
            message_repo=PostgresChatMessageRepository(clean_db),
            cache=mock_cache,
        )

        # Define workflow
        def get_user_program(
            uid: UUID,
        ) -> Generator[AllEffects, EffectResult, str]:
            user_result = yield GetUserById(user_id=uid)

            match user_result:
                case UserNotFound(user_id=not_found_id):
                    yield SendText(text=f"User {not_found_id} not found")
                    return "not_found"
                case User(name=name):
                    return name
                case _:
                    return "error"

        # Act
        result = await run_ws_program(get_user_program(user_id), interpreter)

        # Assert
        match result:
            case Ok(outcome):
                assert outcome == "not_found"
                mock_ws.send_text.assert_called_once()
            case Err(error):
                pytest.fail(f"Expected Ok('not_found'), got Err({error})")

    @pytest.mark.asyncio
    async def test_save_message_workflow(
        self, clean_db: asyncpg.Connection, mocker: MockerFixture
    ) -> None:
        """Workflow saves message to real PostgreSQL."""
        # Seed user first (foreign key constraint)
        user_id = uuid4()
        await clean_db.execute(
            "INSERT INTO users (id, email, name) VALUES ($1, $2, $3)",
            user_id,
            "bob@example.com",
            "Bob",
        )

        # Create interpreter
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_cache = mocker.AsyncMock(spec=ProfileCache)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=PostgresUserRepository(clean_db),
            message_repo=PostgresChatMessageRepository(clean_db),
            cache=mock_cache,
        )

        # Define workflow
        def save_message_program(uid: UUID, text: str) -> Generator[AllEffects, EffectResult, str]:
            message = yield SaveChatMessage(user_id=uid, text=text)
            assert isinstance(message, ChatMessage)

            yield SendText(text=f"Saved message: {message.id}")
            return str(message.id)

        # Act
        result = await run_ws_program(save_message_program(user_id, "Hello, World!"), interpreter)

        # Assert - check result and verify in real DB
        match result:
            case Ok(message_id):
                # Verify in real PostgreSQL
                row = await clean_db.fetchrow(
                    "SELECT * FROM chat_messages WHERE user_id = $1", user_id
                )
                assert row is not None
                assert row["text"] == "Hello, World!"
                assert str(row["id"]) == message_id
            case Err(error):
                pytest.fail(f"Expected Ok, got Err({error})")

    @pytest.mark.asyncio
    async def test_list_messages_workflow(
        self, clean_db: asyncpg.Connection, mocker: MockerFixture
    ) -> None:
        """Workflow lists messages from real PostgreSQL."""
        # Seed user and messages
        user_id = uuid4()
        await clean_db.execute(
            "INSERT INTO users (id, email, name) VALUES ($1, $2, $3)",
            user_id,
            "charlie@example.com",
            "Charlie",
        )

        message_repo = PostgresChatMessageRepository(clean_db)
        await message_repo.save_message(user_id, "First message")
        await message_repo.save_message(user_id, "Second message")
        await message_repo.save_message(user_id, "Third message")

        # Create interpreter
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_cache = mocker.AsyncMock(spec=ProfileCache)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=PostgresUserRepository(clean_db),
            message_repo=message_repo,
            cache=mock_cache,
        )

        # Define workflow
        def list_messages_program(
            uid: UUID,
        ) -> Generator[AllEffects, EffectResult, int]:
            messages = yield ListMessagesForUser(user_id=uid)
            assert isinstance(messages, list)

            yield SendText(text=f"Found {len(messages)} messages")
            return len(messages)

        # Act
        result = await run_ws_program(list_messages_program(user_id), interpreter)

        # Assert
        match result:
            case Ok(count):
                assert count == 3
                mock_ws.send_text.assert_called_once_with("Found 3 messages")
            case Err(error):
                pytest.fail(f"Expected Ok(3), got Err({error})")

    @pytest.mark.asyncio
    async def test_multi_step_database_workflow(
        self, clean_db: asyncpg.Connection, mocker: MockerFixture
    ) -> None:
        """Workflow with multiple database operations."""
        # Seed user
        user_id = uuid4()
        await clean_db.execute(
            "INSERT INTO users (id, email, name) VALUES ($1, $2, $3)",
            user_id,
            "diana@example.com",
            "Diana",
        )

        # Create interpreter
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_cache = mocker.AsyncMock(spec=ProfileCache)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=PostgresUserRepository(clean_db),
            message_repo=PostgresChatMessageRepository(clean_db),
            cache=mock_cache,
        )

        # Define multi-step workflow
        def multi_step_program(
            uid: UUID,
        ) -> Generator[AllEffects, EffectResult, bool]:
            # Step 1: Lookup user
            user_result = yield GetUserById(user_id=uid)

            match user_result:
                case User() as user:
                    pass
                case _:
                    yield SendText(text="User not found")
                    return False

            # Step 2: Send greeting
            greeting = f"Hello, {user.name}!"
            yield SendText(text=greeting)

            # Step 3: Save greeting as message
            message = yield SaveChatMessage(user_id=uid, text=greeting)
            assert isinstance(message, ChatMessage)

            # Step 4: List all messages
            messages = yield ListMessagesForUser(user_id=uid)
            assert isinstance(messages, list)

            yield SendText(text=f"Total messages: {len(messages)}")
            return True

        # Act
        result = await run_ws_program(multi_step_program(user_id), interpreter)

        # Assert
        match result:
            case Ok(success):
                assert success is True
                # Verify multiple sends
                assert mock_ws.send_text.call_count == 2
                mock_ws.send_text.assert_any_call("Hello, Diana!")
                mock_ws.send_text.assert_any_call("Total messages: 1")

                # Verify in real DB
                row = await clean_db.fetchrow(
                    "SELECT * FROM chat_messages WHERE user_id = $1", user_id
                )
                assert row is not None
                assert row["text"] == "Hello, Diana!"
            case Err(error):
                pytest.fail(f"Expected Ok(True), got Err({error})")

    @pytest.mark.asyncio
    async def test_create_user_workflow(
        self, clean_db: asyncpg.Connection, mocker: MockerFixture
    ) -> None:
        """Workflow creates new user in real PostgreSQL."""
        # Create interpreter with real DB
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_cache = mocker.AsyncMock(spec=ProfileCache)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=PostgresUserRepository(clean_db),
            message_repo=PostgresChatMessageRepository(clean_db),
            cache=mock_cache,
        )

        # Define workflow
        def create_user_program(
            email: str, name: str, password_hash: str
        ) -> Generator[AllEffects, EffectResult, UUID]:
            user = yield CreateUser(email=email, name=name, password_hash=password_hash)
            assert isinstance(user, User)

            yield SendText(text=f"Created user: {user.name}")
            return user.id

        # Act
        result = await run_ws_program(
            create_user_program("new@example.com", "New User", "hashed_password"),
            interpreter,
        )

        # Assert
        match result:
            case Ok(user_id):
                # Verify in real PostgreSQL
                row = await clean_db.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
                assert row is not None
                assert row["email"] == "new@example.com"
                assert row["name"] == "New User"
                mock_ws.send_text.assert_called_once_with("Created user: New User")
            case Err(error):
                pytest.fail(f"Expected Ok, got Err({error})")

    @pytest.mark.asyncio
    async def test_update_user_workflow(
        self, clean_db: asyncpg.Connection, mocker: MockerFixture
    ) -> None:
        """Workflow updates existing user in real PostgreSQL."""
        # Seed user
        user_id = uuid4()
        await clean_db.execute(
            "INSERT INTO users (id, email, name) VALUES ($1, $2, $3)",
            user_id,
            "original@example.com",
            "Original Name",
        )

        # Create interpreter
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_cache = mocker.AsyncMock(spec=ProfileCache)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=PostgresUserRepository(clean_db),
            message_repo=PostgresChatMessageRepository(clean_db),
            cache=mock_cache,
        )

        # Define workflow
        def update_user_program(
            uid: UUID, new_name: str
        ) -> Generator[AllEffects, EffectResult, str]:
            user_result = yield UpdateUser(user_id=uid, name=new_name)

            match user_result:
                case User(name=name):
                    yield SendText(text=f"Updated user: {name}")
                    return name
                case UserNotFound():
                    yield SendText(text="User not found")
                    return "not_found"
                case _:
                    return "error"

        # Act
        result = await run_ws_program(update_user_program(user_id, "Updated Name"), interpreter)

        # Assert
        match result:
            case Ok(name):
                assert name == "Updated Name"
                # Verify in real PostgreSQL
                row = await clean_db.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
                assert row is not None
                assert row["name"] == "Updated Name"
                # Email should remain unchanged
                assert row["email"] == "original@example.com"
            case Err(error):
                pytest.fail(f"Expected Ok, got Err({error})")

    @pytest.mark.asyncio
    async def test_update_user_not_found_workflow(
        self, clean_db: asyncpg.Connection, mocker: MockerFixture
    ) -> None:
        """Workflow handles update of non-existent user."""
        user_id = uuid4()  # Does not exist

        # Create interpreter
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_cache = mocker.AsyncMock(spec=ProfileCache)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=PostgresUserRepository(clean_db),
            message_repo=PostgresChatMessageRepository(clean_db),
            cache=mock_cache,
        )

        # Define workflow
        def update_not_found_program(
            uid: UUID,
        ) -> Generator[AllEffects, EffectResult, str]:
            user_result = yield UpdateUser(user_id=uid, name="New Name")

            match user_result:
                case UserNotFound():
                    yield SendText(text="User not found")
                    return "not_found"
                case User():
                    return "found"
                case _:
                    return "error"

        # Act
        result = await run_ws_program(update_not_found_program(user_id), interpreter)

        # Assert
        match result:
            case Ok(outcome):
                assert outcome == "not_found"
                mock_ws.send_text.assert_called_once_with("User not found")
            case Err(error):
                pytest.fail(f"Expected Ok('not_found'), got Err({error})")

    @pytest.mark.asyncio
    async def test_delete_user_workflow(
        self, clean_db: asyncpg.Connection, mocker: MockerFixture
    ) -> None:
        """Workflow deletes user from real PostgreSQL."""
        # Seed user
        user_id = uuid4()
        await clean_db.execute(
            "INSERT INTO users (id, email, name) VALUES ($1, $2, $3)",
            user_id,
            "delete@example.com",
            "To Delete",
        )

        # Create interpreter
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_cache = mocker.AsyncMock(spec=ProfileCache)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=PostgresUserRepository(clean_db),
            message_repo=PostgresChatMessageRepository(clean_db),
            cache=mock_cache,
        )

        # Define workflow
        def delete_user_program(uid: UUID) -> Generator[AllEffects, EffectResult, bool]:
            yield DeleteUser(user_id=uid)
            yield SendText(text=f"Deleted user: {uid}")
            return True

        # Act
        result = await run_ws_program(delete_user_program(user_id), interpreter)

        # Assert
        match result:
            case Ok(success):
                assert success is True
                # Verify user is deleted
                row = await clean_db.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
                assert row is None
            case Err(error):
                pytest.fail(f"Expected Ok, got Err({error})")

    @pytest.mark.asyncio
    async def test_list_users_workflow(
        self, clean_db: asyncpg.Connection, mocker: MockerFixture
    ) -> None:
        """Workflow lists all users from real PostgreSQL."""
        # Seed users
        users_data = [
            (uuid4(), "alice@example.com", "Alice"),
            (uuid4(), "bob@example.com", "Bob"),
            (uuid4(), "charlie@example.com", "Charlie"),
        ]
        for uid, email, name in users_data:
            await clean_db.execute(
                "INSERT INTO users (id, email, name) VALUES ($1, $2, $3)",
                uid,
                email,
                name,
            )

        # Create interpreter
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_cache = mocker.AsyncMock(spec=ProfileCache)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=PostgresUserRepository(clean_db),
            message_repo=PostgresChatMessageRepository(clean_db),
            cache=mock_cache,
        )

        # Define workflow
        def list_users_program() -> Generator[AllEffects, EffectResult, int]:
            users = yield ListUsers()
            assert isinstance(users, list)

            yield SendText(text=f"Found {len(users)} users")
            return len(users)

        # Act
        result = await run_ws_program(list_users_program(), interpreter)

        # Assert
        match result:
            case Ok(count):
                assert count == 3
                mock_ws.send_text.assert_called_once_with("Found 3 users")
            case Err(error):
                pytest.fail(f"Expected Ok(3), got Err({error})")

    @pytest.mark.asyncio
    async def test_list_users_with_pagination_workflow(
        self, clean_db: asyncpg.Connection, mocker: MockerFixture
    ) -> None:
        """Workflow lists users with limit and offset."""
        # Seed 5 users
        users_data = [(uuid4(), f"user{i}@example.com", f"User {i}") for i in range(5)]
        for uid, email, name in users_data:
            await clean_db.execute(
                "INSERT INTO users (id, email, name) VALUES ($1, $2, $3)",
                uid,
                email,
                name,
            )

        # Create interpreter
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_cache = mocker.AsyncMock(spec=ProfileCache)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=PostgresUserRepository(clean_db),
            message_repo=PostgresChatMessageRepository(clean_db),
            cache=mock_cache,
        )

        # Define workflow
        def paginated_list_program(
            limit: int, offset: int
        ) -> Generator[AllEffects, EffectResult, int]:
            users = yield ListUsers(limit=limit, offset=offset)
            assert isinstance(users, list)

            yield SendText(text=f"Page returned {len(users)} users")
            return len(users)

        # Act - Get page with limit=2, offset=1
        result = await run_ws_program(paginated_list_program(limit=2, offset=1), interpreter)

        # Assert
        match result:
            case Ok(count):
                assert count == 2
                mock_ws.send_text.assert_called_once_with("Page returned 2 users")
            case Err(error):
                pytest.fail(f"Expected Ok(2), got Err({error})")

    @pytest.mark.asyncio
    async def test_crud_workflow(self, clean_db: asyncpg.Connection, mocker: MockerFixture) -> None:
        """Complete CRUD workflow: create, read, update, delete."""
        # Create interpreter
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_cache = mocker.AsyncMock(spec=ProfileCache)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=PostgresUserRepository(clean_db),
            message_repo=PostgresChatMessageRepository(clean_db),
            cache=mock_cache,
        )

        # Define CRUD workflow
        def crud_program() -> Generator[AllEffects, EffectResult, bool]:
            # Create
            user = yield CreateUser(
                email="crud@example.com", name="CRUD User", password_hash="hash"
            )
            assert isinstance(user, User)
            user_id = user.id
            yield SendText(text=f"Created: {user.name}")

            # Read
            lookup = yield GetUserById(user_id=user_id)
            match lookup:
                case User(name=name):
                    yield SendText(text=f"Read: {name}")
                case _:
                    return False

            # Update
            updated = yield UpdateUser(user_id=user_id, name="Updated CRUD User")
            match updated:
                case User(name=new_name):
                    yield SendText(text=f"Updated: {new_name}")
                case _:
                    return False

            # Delete
            yield DeleteUser(user_id=user_id)
            yield SendText(text="Deleted")

            # Verify deleted
            final_lookup = yield GetUserById(user_id=user_id)
            match final_lookup:
                case UserNotFound():
                    yield SendText(text="Verified deleted")
                    return True
                case _:
                    return False

        # Act
        result = await run_ws_program(crud_program(), interpreter)

        # Assert
        match result:
            case Ok(success):
                assert success is True
                assert mock_ws.send_text.call_count == 5
            case Err(error):
                pytest.fail(f"Expected Ok(True), got Err({error})")
