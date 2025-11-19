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

from functional_effects.algebraic.effect_return import EffectReturn
from functional_effects.algebraic.result import Err, Ok
from functional_effects.domain.message import ChatMessage
from functional_effects.domain.user import User, UserFound, UserNotFound
from functional_effects.effects.database import (
    GetUserById,
    ListMessagesForUser,
    SaveChatMessage,
)
from functional_effects.effects.websocket import SendText
from functional_effects.infrastructure.repositories import ChatMessageRepository, UserRepository
from functional_effects.interpreters.database import DatabaseInterpreter
from functional_effects.interpreters.errors import DatabaseError, UnhandledEffectError


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

        # Verify result
        match result:
            case Ok(EffectReturn(value=None, effect_name="GetUserById")):
                pass  # Success
            case _:
                pytest.fail(f"Expected Ok with None, got {result}")

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
                assert all(m.user_id == user_id for m in msgs)
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
            interpreter.user_repo = mocker.AsyncMock(spec=UserRepository)  # type: ignore[misc]

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
