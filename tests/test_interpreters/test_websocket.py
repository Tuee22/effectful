"""Tests for WebSocket interpreter.

This module tests the WebSocketInterpreter using pytest mocks (via pytest-mock).
Tests cover:
- Sending text messages
- Receiving text messages
- Closing connections
- Connection state validation
- Unhandled effects
- Immutability
"""

from dataclasses import FrozenInstanceError
from uuid import uuid4

import pytest
from pytest_mock import MockerFixture

from functional_effects.algebraic.effect_return import EffectReturn
from functional_effects.algebraic.result import Err, Ok
from functional_effects.effects.database import GetUserById
from functional_effects.effects.websocket import (
    Close,
    CloseNormal,
    CloseProtocolError,
    ReceiveText,
    SendText,
)
from functional_effects.infrastructure.websocket import WebSocketConnection
from functional_effects.interpreters.errors import UnhandledEffectError, WebSocketClosedError
from functional_effects.interpreters.websocket import WebSocketInterpreter


class TestWebSocketInterpreter:
    """Tests for WebSocketInterpreter."""

    @pytest.mark.asyncio()
    async def test_send_text_success(self, mocker: MockerFixture) -> None:
        """Interpreter should send text when connection is open."""
        # Create mock
        mock_conn = mocker.AsyncMock(spec=WebSocketConnection)
        mock_conn.is_open.return_value = True

        interpreter = WebSocketInterpreter(connection=mock_conn)

        effect = SendText(text="hello")
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Ok(EffectReturn(value=None, effect_name="SendText")):
                pass  # Success
            case _:
                pytest.fail(f"Expected Ok, got {result}")

        # Verify mock calls
        mock_conn.is_open.assert_called_once()
        mock_conn.send_text.assert_called_once_with("hello")

    @pytest.mark.asyncio()
    async def test_send_text_when_closed(self, mocker: MockerFixture) -> None:
        """Interpreter should return error when connection is closed."""
        # Create mock
        mock_conn = mocker.AsyncMock(spec=WebSocketConnection)
        mock_conn.is_open.return_value = False

        interpreter = WebSocketInterpreter(connection=mock_conn)

        effect = SendText(text="hello")
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Err(
                WebSocketClosedError(
                    effect=e, close_code=1006, reason="Connection closed before send"
                )
            ):
                assert e == effect
            case _:
                pytest.fail(f"Expected WebSocketClosedError, got {result}")

        # Verify mock calls
        mock_conn.is_open.assert_called_once()
        mock_conn.send_text.assert_not_called()

    @pytest.mark.asyncio()
    async def test_receive_text_success(self, mocker: MockerFixture) -> None:
        """Interpreter should receive text when connection is open."""
        # Create mock
        mock_conn = mocker.AsyncMock(spec=WebSocketConnection)
        mock_conn.is_open.return_value = True
        mock_conn.receive_text.return_value = "hello"

        interpreter = WebSocketInterpreter(connection=mock_conn)

        effect = ReceiveText()
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Ok(EffectReturn(value="hello", effect_name="ReceiveText")):
                pass  # Success
            case _:
                pytest.fail(f"Expected Ok with 'hello', got {result}")

        # Verify mock calls
        mock_conn.is_open.assert_called_once()
        mock_conn.receive_text.assert_called_once()

    @pytest.mark.asyncio()
    async def test_receive_text_when_closed(self, mocker: MockerFixture) -> None:
        """Interpreter should return error when connection is closed."""
        # Create mock
        mock_conn = mocker.AsyncMock(spec=WebSocketConnection)
        mock_conn.is_open.return_value = False

        interpreter = WebSocketInterpreter(connection=mock_conn)

        effect = ReceiveText()
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Err(
                WebSocketClosedError(
                    effect=e, close_code=1006, reason="Connection closed before receive"
                )
            ):
                assert e == effect
            case _:
                pytest.fail(f"Expected WebSocketClosedError, got {result}")

        # Verify mock calls
        mock_conn.is_open.assert_called_once()
        mock_conn.receive_text.assert_not_called()

    @pytest.mark.asyncio()
    async def test_close_success(self, mocker: MockerFixture) -> None:
        """Interpreter should close connection successfully."""
        # Create mock
        mock_conn = mocker.AsyncMock(spec=WebSocketConnection)

        interpreter = WebSocketInterpreter(connection=mock_conn)

        effect = Close(reason=CloseNormal())
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Ok(EffectReturn(value=None, effect_name="Close")):
                pass  # Success
            case _:
                pytest.fail(f"Expected Ok, got {result}")

        # Verify mock calls
        mock_conn.close.assert_called_once()

    @pytest.mark.asyncio()
    async def test_close_when_already_closed(self, mocker: MockerFixture) -> None:
        """Interpreter should handle close when already closed."""
        # Create mock
        mock_conn = mocker.AsyncMock(spec=WebSocketConnection)

        interpreter = WebSocketInterpreter(connection=mock_conn)

        effect = Close(reason=CloseProtocolError(reason="test"))
        result = await interpreter.interpret(effect)

        # Verify result - Close always succeeds
        match result:
            case Ok(EffectReturn(value=None, effect_name="Close")):
                pass  # Success
            case _:
                pytest.fail(f"Expected Ok, got {result}")

        # Verify mock calls
        mock_conn.close.assert_called_once()

    @pytest.mark.asyncio()
    async def test_unhandled_effect(self, mocker: MockerFixture) -> None:
        """Interpreter should return error for non-WebSocket effects."""
        # Create mock
        mock_conn = mocker.AsyncMock(spec=WebSocketConnection)

        interpreter = WebSocketInterpreter(connection=mock_conn)

        effect = GetUserById(user_id=uuid4())
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Err(
                UnhandledEffectError(effect=e, available_interpreters=["WebSocketInterpreter"])
            ):
                assert e == effect
            case _:
                pytest.fail(f"Expected UnhandledEffectError, got {result}")

        # Verify no WebSocket methods were called
        mock_conn.send_text.assert_not_called()
        mock_conn.receive_text.assert_not_called()
        mock_conn.close.assert_not_called()

    def test_interpreter_is_immutable(self, mocker: MockerFixture) -> None:
        """WebSocketInterpreter should be frozen."""
        mock_conn = mocker.AsyncMock(spec=WebSocketConnection)
        interpreter = WebSocketInterpreter(connection=mock_conn)

        with pytest.raises(FrozenInstanceError):
            interpreter.connection = mocker.AsyncMock(spec=WebSocketConnection)  # type: ignore[misc]
