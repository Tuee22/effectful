"""Tests for program runners.

This module tests the run_ws_program function which executes effect programs
to completion. Tests cover:
- Successful program completion with return values
- Error propagation (database, websocket, cache errors)
- Type safety (return value preservation through generics)
- Generator protocol (next/send/StopIteration)
- Fail-fast behavior on errors
"""

from collections.abc import Generator
from datetime import datetime
from uuid import uuid4

import pytest
from pytest_mock import MockerFixture

from effectful.algebraic.result import Err, Ok
from effectful.domain.message import ChatMessage
from effectful.domain.user import User, UserFound, UserNotFound
from effectful.effects.database import GetUserById, SaveChatMessage
from effectful.effects.websocket import Close, CloseNormal, SendText
from effectful.infrastructure.cache import ProfileCache
from effectful.infrastructure.repositories import ChatMessageRepository, UserRepository
from effectful.infrastructure.websocket import WebSocketConnection
from effectful.interpreters.composite import create_composite_interpreter
from effectful.interpreters.errors import DatabaseError, WebSocketClosedError
from effectful.programs.program_types import AllEffects, EffectResult
from effectful.programs.runners import run_ws_program


class TestRunWSProgramSuccess:
    """Tests for successful program execution."""

    @pytest.mark.asyncio()
    async def test_simple_program_returns_value(self, mocker: MockerFixture) -> None:
        """run_ws_program should return Ok with program's final value."""
        # Create mocks
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
        mock_cache = mocker.AsyncMock(spec=ProfileCache)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=mock_cache,
        )

        # Simple program that yields SendText and returns 42
        def test_program() -> Generator[AllEffects, EffectResult, int]:
            yield SendText(text="Hello")
            return 42

        # Act
        result = await run_ws_program(test_program(), interpreter)

        # Assert
        match result:
            case Ok(value):
                assert value == 42
                mock_ws.send_text.assert_called_once_with("Hello")
            case Err(error):
                pytest.fail(f"Expected Ok(42), got Err({error})")

    @pytest.mark.asyncio()
    async def test_program_with_multiple_effects(self, mocker: MockerFixture) -> None:
        """run_ws_program should handle multiple effects in sequence."""
        # Create mocks
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
        mock_cache = mocker.AsyncMock(spec=ProfileCache)

        user_id = uuid4()
        saved_message = ChatMessage(
            id=uuid4(), user_id=user_id, text="Test message", created_at=datetime.now()
        )
        mock_msg_repo.save_message.return_value = saved_message

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=mock_cache,
        )

        # Program with multiple effects
        def multi_effect_program() -> Generator[AllEffects, EffectResult, str]:
            yield SendText(text="Starting...")
            message = yield SaveChatMessage(user_id=user_id, text="Test message")
            # Type narrowing for message
            assert isinstance(message, ChatMessage)
            yield SendText(text=f"Saved: {message.text}")
            yield Close(reason=CloseNormal())
            return "completed"

        # Act
        result = await run_ws_program(multi_effect_program(), interpreter)

        # Assert
        match result:
            case Ok(value):
                assert value == "completed"
                assert mock_ws.send_text.call_count == 2
                mock_ws.send_text.assert_any_call("Starting...")
                mock_ws.send_text.assert_any_call("Saved: Test message")
                mock_msg_repo.save_message.assert_called_once_with(user_id, "Test message")
                mock_ws.close.assert_called_once()
            case Err(error):
                pytest.fail(f"Expected Ok('completed'), got Err({error})")

    @pytest.mark.asyncio()
    async def test_program_receives_effect_results(self, mocker: MockerFixture) -> None:
        """run_ws_program should send effect results back to program."""
        # Create mocks
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
        mock_cache = mocker.AsyncMock(spec=ProfileCache)

        user_id = uuid4()
        user = User(id=user_id, email="test@example.com", name="Alice")
        mock_user_repo.get_by_id.return_value = UserFound(user=user, source="database")

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=mock_cache,
        )

        # Program that uses effect results
        def result_using_program() -> Generator[AllEffects, EffectResult, bool]:
            # GetUserById returns UserFound | UserNotFound (ADT)
            # Interpreter unwraps to User | None for EffectResult
            user_result = yield GetUserById(user_id=user_id)

            # Pattern match on user_result
            match user_result:
                case None:
                    yield SendText(text="User not found")
                    return False
                case User(name=name):
                    yield SendText(text=f"Hello {name}!")
                    return True
                case _:
                    # Unreachable but satisfies mypy exhaustiveness
                    return False

        # Act
        result = await run_ws_program(result_using_program(), interpreter)

        # Assert
        match result:
            case Ok(value):
                assert value is True
                mock_ws.send_text.assert_called_once_with("Hello Alice!")
            case Err(error):
                pytest.fail(f"Expected Ok(True), got Err({error})")

    @pytest.mark.asyncio()
    async def test_program_with_no_effects_returns_immediately(self, mocker: MockerFixture) -> None:
        """run_ws_program should handle programs with zero effects."""
        # Create mocks
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
        mock_cache = mocker.AsyncMock(spec=ProfileCache)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=mock_cache,
        )

        # Program that returns immediately with minimal effects
        def immediate_program() -> Generator[AllEffects, EffectResult, str]:
            # Use a no-op pattern: yield from empty sequence
            yield from ()
            return "instant"

        # Act
        result = await run_ws_program(immediate_program(), interpreter)

        # Assert
        match result:
            case Ok(value):
                assert value == "instant"
            case Err(error):
                pytest.fail(f"Expected Ok('instant'), got Err({error})")


class TestRunWSProgramErrorPropagation:
    """Tests for error propagation (fail-fast behavior)."""

    @pytest.mark.asyncio()
    async def test_database_error_propagates(self, mocker: MockerFixture) -> None:
        """run_ws_program should propagate DatabaseError immediately."""
        # Create mocks
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
        mock_cache = mocker.AsyncMock(spec=ProfileCache)

        # Configure repository to raise error
        mock_user_repo.get_by_id.side_effect = Exception("Connection timeout")

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=mock_cache,
        )

        # Program that will hit database error
        def failing_program() -> Generator[AllEffects, EffectResult, str]:
            user = yield GetUserById(user_id=uuid4())
            yield SendText(text=f"User: {user}")  # Never reached
            return "never"

        # Act
        result = await run_ws_program(failing_program(), interpreter)

        # Assert
        match result:
            case Err(DatabaseError(db_error="Connection timeout", is_retryable=True)):
                pass  # Expected
            case Ok(value):
                pytest.fail(f"Expected DatabaseError, got Ok({value})")
            case Err(other):
                pytest.fail(f"Expected DatabaseError, got {other}")

    @pytest.mark.asyncio()
    async def test_websocket_closed_error_propagates(self, mocker: MockerFixture) -> None:
        """run_ws_program should propagate WebSocketClosedError immediately."""
        # Create mocks
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = False  # Closed!
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
        mock_cache = mocker.AsyncMock(spec=ProfileCache)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=mock_cache,
        )

        # Program that will hit websocket error
        def failing_program() -> Generator[AllEffects, EffectResult, str]:
            yield SendText(text="Hello")  # Will fail - socket closed
            return "never"

        # Act
        result = await run_ws_program(failing_program(), interpreter)

        # Assert
        match result:
            case Err(WebSocketClosedError(close_code=1006)):
                pass  # Expected
            case Ok(value):
                pytest.fail(f"Expected WebSocketClosedError, got Ok({value})")
            case Err(other):
                pytest.fail(f"Expected WebSocketClosedError, got {other}")

    @pytest.mark.asyncio()
    async def test_error_stops_program_execution(self, mocker: MockerFixture) -> None:
        """run_ws_program should stop on first error (fail-fast)."""
        # Create mocks
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
        mock_cache = mocker.AsyncMock(spec=ProfileCache)

        # Configure user lookup to succeed
        mock_user_repo.get_by_id.return_value = UserNotFound(
            user_id=uuid4(), reason="does_not_exist"
        )

        # First send succeeds, then connection closes
        call_count = {"count": 0}

        def is_open_side_effect() -> bool:
            call_count["count"] += 1
            return call_count["count"] == 1  # First call: True, subsequent: False

        mock_ws.is_open.side_effect = is_open_side_effect

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=mock_cache,
        )

        # Program that fails midway
        def midway_fail_program() -> Generator[AllEffects, EffectResult, str]:
            yield SendText(text="First")  # Succeeds
            yield GetUserById(user_id=uuid4())  # Succeeds (returns None)
            yield SendText(text="Second")  # Fails!
            yield SendText(text="Never reached")
            return "never"

        # Act
        result = await run_ws_program(midway_fail_program(), interpreter)

        # Assert
        match result:
            case Err(WebSocketClosedError()):
                # Verify program stopped after error
                mock_ws.send_text.assert_called_once_with("First")  # Only first message sent
            case Ok(value):
                pytest.fail(f"Expected WebSocketClosedError, got Ok({value})")
            case Err(other):
                pytest.fail(f"Expected WebSocketClosedError, got {other}")


class TestRunWSProgramTypeSafety:
    """Tests for type safety and generic return values."""

    @pytest.mark.asyncio()
    async def test_return_type_preserved_bool(self, mocker: MockerFixture) -> None:
        """run_ws_program should preserve bool return type."""
        # Create mocks
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
        mock_cache = mocker.AsyncMock(spec=ProfileCache)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=mock_cache,
        )

        def bool_program() -> Generator[AllEffects, EffectResult, bool]:
            yield from ()
            return True

        # Act
        result = await run_ws_program(bool_program(), interpreter)

        # Assert - type checker verifies this
        match result:
            case Ok(value):
                assert isinstance(value, bool)
                assert value is True
            case Err(_):
                pytest.fail("Expected Ok(True)")

    @pytest.mark.asyncio()
    async def test_return_type_preserved_string(self, mocker: MockerFixture) -> None:
        """run_ws_program should preserve str return type."""
        # Create mocks
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
        mock_cache = mocker.AsyncMock(spec=ProfileCache)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=mock_cache,
        )

        def str_program() -> Generator[AllEffects, EffectResult, str]:
            yield from ()
            return "success"

        # Act
        result = await run_ws_program(str_program(), interpreter)

        # Assert
        match result:
            case Ok(value):
                assert isinstance(value, str)
                assert value == "success"
            case Err(_):
                pytest.fail("Expected Ok('success')")

    @pytest.mark.asyncio()
    async def test_return_type_preserved_none(self, mocker: MockerFixture) -> None:
        """run_ws_program should preserve None return type."""
        # Create mocks
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
        mock_cache = mocker.AsyncMock(spec=ProfileCache)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=mock_cache,
        )

        def none_program() -> Generator[AllEffects, EffectResult, None]:
            yield from ()
            return None

        # Act
        result = await run_ws_program(none_program(), interpreter)

        # Assert
        match result:
            case Ok(value):
                assert value is None
            case Err(_):
                pytest.fail("Expected Ok(None)")
