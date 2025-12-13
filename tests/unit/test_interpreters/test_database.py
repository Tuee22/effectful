"""Tests for Database interpreter.

This module tests the DatabaseInterpreter using pytest mocks (via pytest-mock).
Tests cover:
- User lookup (found/not found)
- Message saving
- Message listing
- Database errors and retryability
- Unhandled effects
- Immutability
"""

from dataclasses import FrozenInstanceError
from datetime import datetime
from uuid import uuid4

import pytest
from pytest_mock import MockerFixture

from effectful.algebraic.effect_return import EffectReturn
from effectful.algebraic.result import Err, Ok
from effectful.domain.message import ChatMessage
from effectful.domain.optional_value import Absent, Provided
from effectful.domain.user import User, UserFound, UserNotFound
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
from effectful.infrastructure.repositories import ChatMessageRepository, UserRepository
from effectful.interpreters.database import DatabaseInterpreter
from effectful.interpreters.errors import DatabaseError, UnhandledEffectError


class TestDatabaseInterpreter:
    """Tests for DatabaseInterpreter."""

    @pytest.mark.asyncio()
    async def test_get_user_found(self, mocker: MockerFixture) -> None:
        """Interpreter should return user when found."""
        user_id = uuid4()
        user = User(id=user_id, email="test@example.com", name="Test User")

        # Create mocks
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_user_repo.get_by_id.return_value = UserFound(user=user, source="database")
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)

        interpreter = DatabaseInterpreter(user_repo=mock_user_repo, message_repo=mock_msg_repo)

        effect = GetUserById(user_id=user_id)
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Ok(EffectReturn(value=u, effect_name="GetUserById")):
                assert u == user
            case _:
                pytest.fail(f"Expected Ok with user, got {result}")

        # Verify mock was called correctly
        mock_user_repo.get_by_id.assert_called_once_with(user_id)

    @pytest.mark.asyncio()
    async def test_get_user_not_found(self, mocker: MockerFixture) -> None:
        """Interpreter should return None when user not found."""
        user_id = uuid4()

        # Create mocks
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_user_repo.get_by_id.return_value = UserNotFound(
            user_id=user_id, reason="does_not_exist"
        )
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)

        interpreter = DatabaseInterpreter(user_repo=mock_user_repo, message_repo=mock_msg_repo)

        effect = GetUserById(user_id=user_id)
        result = await interpreter.interpret(effect)

        # Verify result - UserNotFound ADT returned instead of None
        match result:
            case Ok(
                EffectReturn(
                    value=UserNotFound(user_id=_, reason="does_not_exist"),
                    effect_name="GetUserById",
                )
            ):
                pass  # Success
            case _:
                pytest.fail(f"Expected Ok with UserNotFound, got {result}")

        # Verify mock was called correctly
        mock_user_repo.get_by_id.assert_called_once_with(user_id)

    @pytest.mark.asyncio()
    async def test_get_user_database_error(self, mocker: MockerFixture) -> None:
        """Interpreter should return DatabaseError when repository fails."""
        user_id = uuid4()

        # Create mocks
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_user_repo.get_by_id.side_effect = Exception("Connection timeout")
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)

        interpreter = DatabaseInterpreter(user_repo=mock_user_repo, message_repo=mock_msg_repo)

        effect = GetUserById(user_id=user_id)
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Err(DatabaseError(effect=e, db_error="Connection timeout", is_retryable=True)):
                assert e == effect
            case _:
                pytest.fail(f"Expected DatabaseError, got {result}")

        # Verify mock was called correctly
        mock_user_repo.get_by_id.assert_called_once_with(user_id)

    @pytest.mark.asyncio()
    async def test_save_message_success(self, mocker: MockerFixture) -> None:
        """Interpreter should save message successfully."""
        user_id = uuid4()
        saved_message = ChatMessage(
            id=uuid4(), user_id=user_id, text="Hello world", created_at=datetime.now()
        )

        # Create mocks
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
        mock_msg_repo.save_message.return_value = saved_message

        interpreter = DatabaseInterpreter(user_repo=mock_user_repo, message_repo=mock_msg_repo)

        effect = SaveChatMessage(user_id=user_id, text="Hello world")
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Ok(EffectReturn(value=msg, effect_name="SaveChatMessage")):
                assert isinstance(msg, ChatMessage)
                assert msg.user_id == user_id
                assert msg.text == "Hello world"
                assert msg == saved_message
            case _:
                pytest.fail(f"Expected Ok with ChatMessage, got {result}")

        # Verify mock was called correctly
        mock_msg_repo.save_message.assert_called_once_with(user_id, "Hello world")

    @pytest.mark.asyncio()
    async def test_save_message_database_error(self, mocker: MockerFixture) -> None:
        """Interpreter should return DatabaseError when save fails."""
        user_id = uuid4()

        # Create mocks
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
        mock_msg_repo.save_message.side_effect = Exception("Deadlock detected")

        interpreter = DatabaseInterpreter(user_repo=mock_user_repo, message_repo=mock_msg_repo)

        effect = SaveChatMessage(user_id=user_id, text="test")
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Err(DatabaseError(effect=e, db_error="Deadlock detected", is_retryable=True)):
                assert e == effect
            case _:
                pytest.fail(f"Expected DatabaseError, got {result}")

        # Verify mock was called correctly
        mock_msg_repo.save_message.assert_called_once_with(user_id, "test")

    @pytest.mark.asyncio()
    async def test_list_messages_success(self, mocker: MockerFixture) -> None:
        """Interpreter should list messages successfully."""
        user_id = uuid4()
        messages = [
            ChatMessage(id=uuid4(), user_id=user_id, text="msg1", created_at=datetime.now()),
            ChatMessage(id=uuid4(), user_id=user_id, text="msg2", created_at=datetime.now()),
        ]

        # Create mocks
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
        mock_msg_repo.list_messages_for_user.return_value = messages

        interpreter = DatabaseInterpreter(user_repo=mock_user_repo, message_repo=mock_msg_repo)

        effect = ListMessagesForUser(user_id=user_id)
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Ok(EffectReturn(value=msgs, effect_name="ListMessagesForUser")):
                assert isinstance(msgs, list)
                assert len(msgs) == 2
                for m in msgs:
                    assert isinstance(m, ChatMessage)
                    assert m.user_id == user_id
                assert msgs == messages
            case _:
                pytest.fail(f"Expected Ok with messages, got {result}")

        # Verify mock was called correctly
        mock_msg_repo.list_messages_for_user.assert_called_once_with(user_id)

    @pytest.mark.asyncio()
    async def test_list_messages_empty(self, mocker: MockerFixture) -> None:
        """Interpreter should return empty list when no messages."""
        user_id = uuid4()

        # Create mocks
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
        mock_msg_repo.list_messages_for_user.return_value = []

        interpreter = DatabaseInterpreter(user_repo=mock_user_repo, message_repo=mock_msg_repo)

        effect = ListMessagesForUser(user_id=user_id)
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Ok(EffectReturn(value=[], effect_name="ListMessagesForUser")):
                pass  # Success
            case _:
                pytest.fail(f"Expected Ok with empty list, got {result}")

        # Verify mock was called correctly
        mock_msg_repo.list_messages_for_user.assert_called_once_with(user_id)

    @pytest.mark.asyncio()
    async def test_list_messages_database_error(self, mocker: MockerFixture) -> None:
        """Interpreter should return DatabaseError when list fails."""
        user_id = uuid4()

        # Create mocks
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
        mock_msg_repo.list_messages_for_user.side_effect = Exception("Lock timeout")

        interpreter = DatabaseInterpreter(user_repo=mock_user_repo, message_repo=mock_msg_repo)

        effect = ListMessagesForUser(user_id=user_id)
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Err(DatabaseError(effect=e, db_error="Lock timeout", is_retryable=True)):
                assert e == effect
            case _:
                pytest.fail(f"Expected DatabaseError, got {result}")

        # Verify mock was called correctly
        mock_msg_repo.list_messages_for_user.assert_called_once_with(user_id)

    @pytest.mark.asyncio()
    async def test_unhandled_effect(self, mocker: MockerFixture) -> None:
        """Interpreter should return error for non-Database effects."""
        # Create mocks
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)

        interpreter = DatabaseInterpreter(user_repo=mock_user_repo, message_repo=mock_msg_repo)

        effect = SendText(text="hello")
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Err(
                UnhandledEffectError(effect=e, available_interpreters=["DatabaseInterpreter"])
            ):
                assert e == effect
            case _:
                pytest.fail(f"Expected UnhandledEffectError, got {result}")

        # Verify no repository methods were called
        mock_user_repo.get_by_id.assert_not_called()
        mock_msg_repo.save_message.assert_not_called()
        mock_msg_repo.list_messages_for_user.assert_not_called()

    def test_interpreter_is_immutable(self, mocker: MockerFixture) -> None:
        """DatabaseInterpreter should be frozen."""
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
        interpreter = DatabaseInterpreter(user_repo=mock_user_repo, message_repo=mock_msg_repo)

        with pytest.raises(FrozenInstanceError):
            setattr(interpreter, "user_repo", mocker.AsyncMock(spec=UserRepository))

    def test_is_retryable_error_detects_retryable_patterns(self, mocker: MockerFixture) -> None:
        """_is_retryable_error should detect retryable error patterns."""
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
        interpreter = DatabaseInterpreter(user_repo=mock_user_repo, message_repo=mock_msg_repo)

        assert interpreter._is_retryable_error(Exception("Connection timeout"))
        assert interpreter._is_retryable_error(Exception("Deadlock detected"))
        assert interpreter._is_retryable_error(Exception("Lock wait timeout"))
        assert interpreter._is_retryable_error(Exception("Database unavailable"))

    def test_is_retryable_error_detects_non_retryable_patterns(self, mocker: MockerFixture) -> None:
        """_is_retryable_error should detect non-retryable error patterns."""
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
        interpreter = DatabaseInterpreter(user_repo=mock_user_repo, message_repo=mock_msg_repo)

        assert not interpreter._is_retryable_error(Exception("Invalid SQL syntax"))
        assert not interpreter._is_retryable_error(Exception("Foreign key violation"))
        assert not interpreter._is_retryable_error(Exception("Unknown error"))

    @pytest.mark.asyncio()
    async def test_list_users_success(self, mocker: MockerFixture) -> None:
        """Interpreter should list users successfully."""
        users = [
            User(id=uuid4(), email="alice@example.com", name="Alice"),
            User(id=uuid4(), email="bob@example.com", name="Bob"),
        ]

        # Create mocks
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_user_repo.list_users.return_value = users
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)

        interpreter = DatabaseInterpreter(user_repo=mock_user_repo, message_repo=mock_msg_repo)

        effect = ListUsers(limit=10, offset=0)
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Ok(EffectReturn(value=user_list, effect_name="ListUsers")):
                assert isinstance(user_list, list)
                assert len(user_list) == 2
                assert user_list == users
            case _:
                pytest.fail(f"Expected Ok with users list, got {result}")

        # Verify mock was called correctly
        mock_user_repo.list_users.assert_called_once_with(Provided(value=10), Provided(value=0))

    @pytest.mark.asyncio()
    async def test_list_users_empty(self, mocker: MockerFixture) -> None:
        """Interpreter should return empty list when no users."""
        # Create mocks
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_user_repo.list_users.return_value = []
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)

        interpreter = DatabaseInterpreter(user_repo=mock_user_repo, message_repo=mock_msg_repo)

        effect = ListUsers()
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Ok(EffectReturn(value=[], effect_name="ListUsers")):
                pass  # Success
            case _:
                pytest.fail(f"Expected Ok with empty list, got {result}")

        # Verify mock was called correctly
        mock_user_repo.list_users.assert_called_once_with(
            Absent(reason="not_provided"), Absent(reason="not_provided")
        )

    @pytest.mark.asyncio()
    async def test_list_users_database_error(self, mocker: MockerFixture) -> None:
        """Interpreter should return DatabaseError when list users fails."""
        # Create mocks
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_user_repo.list_users.side_effect = Exception("Connection refused")
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)

        interpreter = DatabaseInterpreter(user_repo=mock_user_repo, message_repo=mock_msg_repo)

        effect = ListUsers()
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Err(DatabaseError(effect=e, db_error="Connection refused", is_retryable=True)):
                assert e == effect
            case _:
                pytest.fail(f"Expected DatabaseError, got {result}")

    @pytest.mark.asyncio()
    async def test_create_user_success(self, mocker: MockerFixture) -> None:
        """Interpreter should create user successfully."""
        user_id = uuid4()
        created_user = User(id=user_id, email="new@example.com", name="New User")

        # Create mocks
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_user_repo.create_user.return_value = created_user
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)

        interpreter = DatabaseInterpreter(user_repo=mock_user_repo, message_repo=mock_msg_repo)

        effect = CreateUser(email="new@example.com", name="New User", password_hash="hash123")
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Ok(EffectReturn(value=user, effect_name="CreateUser")):
                assert isinstance(user, User)
                assert user.email == "new@example.com"
                assert user.name == "New User"
            case _:
                pytest.fail(f"Expected Ok with User, got {result}")

        # Verify mock was called correctly
        mock_user_repo.create_user.assert_called_once_with("new@example.com", "New User", "hash123")

    @pytest.mark.asyncio()
    async def test_create_user_database_error(self, mocker: MockerFixture) -> None:
        """Interpreter should return DatabaseError when create fails."""
        # Create mocks
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_user_repo.create_user.side_effect = Exception("Duplicate key violation")
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)

        interpreter = DatabaseInterpreter(user_repo=mock_user_repo, message_repo=mock_msg_repo)

        effect = CreateUser(email="dup@example.com", name="Dup User", password_hash="hash")
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Err(DatabaseError(effect=e, db_error="Duplicate key violation", is_retryable=_)):
                assert e == effect
            case _:
                pytest.fail(f"Expected DatabaseError, got {result}")

    @pytest.mark.asyncio()
    async def test_update_user_found(self, mocker: MockerFixture) -> None:
        """Interpreter should update user successfully."""
        user_id = uuid4()
        updated_user = User(id=user_id, email="updated@example.com", name="Updated")

        # Create mocks
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_user_repo.update_user.return_value = UserFound(user=updated_user, source="database")
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)

        interpreter = DatabaseInterpreter(user_repo=mock_user_repo, message_repo=mock_msg_repo)

        effect = UpdateUser(user_id=user_id, email="updated@example.com", name="Updated")
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Ok(EffectReturn(value=user, effect_name="UpdateUser")):
                assert isinstance(user, User)
                assert user.email == "updated@example.com"
            case _:
                pytest.fail(f"Expected Ok with User, got {result}")

        # Verify mock was called correctly
        mock_user_repo.update_user.assert_called_once_with(
            user_id, Provided(value="updated@example.com"), Provided(value="Updated")
        )

    @pytest.mark.asyncio()
    async def test_update_user_not_found(self, mocker: MockerFixture) -> None:
        """Interpreter should return UserNotFound when user doesn't exist."""
        user_id = uuid4()

        # Create mocks
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_user_repo.update_user.return_value = UserNotFound(
            user_id=user_id, reason="does_not_exist"
        )
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)

        interpreter = DatabaseInterpreter(user_repo=mock_user_repo, message_repo=mock_msg_repo)

        effect = UpdateUser(user_id=user_id, name="New Name")
        result = await interpreter.interpret(effect)

        # Verify result - UserNotFound ADT returned
        match result:
            case Ok(
                EffectReturn(
                    value=UserNotFound(user_id=_, reason="does_not_exist"),
                    effect_name="UpdateUser",
                )
            ):
                pass  # Success
            case _:
                pytest.fail(f"Expected Ok with UserNotFound, got {result}")

    @pytest.mark.asyncio()
    async def test_update_user_database_error(self, mocker: MockerFixture) -> None:
        """Interpreter should return DatabaseError when update fails."""
        user_id = uuid4()

        # Create mocks
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_user_repo.update_user.side_effect = Exception("Constraint violation")
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)

        interpreter = DatabaseInterpreter(user_repo=mock_user_repo, message_repo=mock_msg_repo)

        effect = UpdateUser(user_id=user_id, email="bad")
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Err(DatabaseError(effect=e, db_error="Constraint violation", is_retryable=_)):
                assert e == effect
            case _:
                pytest.fail(f"Expected DatabaseError, got {result}")

    @pytest.mark.asyncio()
    async def test_delete_user_success(self, mocker: MockerFixture) -> None:
        """Interpreter should delete user successfully."""
        user_id = uuid4()

        # Create mocks
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_user_repo.delete_user.return_value = None
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)

        interpreter = DatabaseInterpreter(user_repo=mock_user_repo, message_repo=mock_msg_repo)

        effect = DeleteUser(user_id=user_id)
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Ok(EffectReturn(value=None, effect_name="DeleteUser")):
                pass  # Success
            case _:
                pytest.fail(f"Expected Ok with None, got {result}")

        # Verify mock was called correctly
        mock_user_repo.delete_user.assert_called_once_with(user_id)

    @pytest.mark.asyncio()
    async def test_delete_user_database_error(self, mocker: MockerFixture) -> None:
        """Interpreter should return DatabaseError when delete fails."""
        user_id = uuid4()

        # Create mocks
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_user_repo.delete_user.side_effect = Exception("Foreign key constraint")
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)

        interpreter = DatabaseInterpreter(user_repo=mock_user_repo, message_repo=mock_msg_repo)

        effect = DeleteUser(user_id=user_id)
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Err(DatabaseError(effect=e, db_error="Foreign key constraint", is_retryable=_)):
                assert e == effect
            case _:
                pytest.fail(f"Expected DatabaseError, got {result}")
