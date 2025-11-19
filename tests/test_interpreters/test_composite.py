"""Tests for Composite interpreter.

This module tests the CompositeInterpreter using pytest mocks (via pytest-mock).
Tests cover:
- Delegation to WebSocket interpreter
- Delegation to Database interpreter
- Delegation to Cache interpreter
- Unhandled effects
- Factory function
- Immutability
"""

from dataclasses import FrozenInstanceError, dataclass
from datetime import datetime
from uuid import uuid4

import pytest
from pytest_mock import MockerFixture

from functional_effects.algebraic.effect_return import EffectReturn
from functional_effects.algebraic.result import Err, Ok
from functional_effects.domain.cache_result import CacheHit
from functional_effects.domain.message import ChatMessage
from functional_effects.domain.profile import ProfileData
from functional_effects.domain.user import User, UserFound
from functional_effects.effects.cache import GetCachedProfile, PutCachedProfile
from functional_effects.effects.database import GetUserById, SaveChatMessage
from functional_effects.effects.websocket import Close, CloseNormal, ReceiveText, SendText
from functional_effects.infrastructure.cache import ProfileCache
from functional_effects.infrastructure.repositories import ChatMessageRepository, UserRepository
from functional_effects.infrastructure.websocket import WebSocketConnection
from functional_effects.interpreters.composite import (
    CompositeInterpreter,
    create_composite_interpreter,
)
from functional_effects.interpreters.errors import UnhandledEffectError


class TestCompositeInterpreter:
    """Tests for CompositeInterpreter."""

    @pytest.mark.asyncio()
    async def test_interpret_websocket_effect(self, mocker: MockerFixture) -> None:
        """Composite interpreter should delegate WebSocket effects."""
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

        effect = SendText(text="hello")
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Ok(EffectReturn(value=None, effect_name="SendText")):
                pass  # Success
            case _:
                pytest.fail(f"Expected Ok with SendText, got {result}")

        # Verify WebSocket was used
        mock_ws.is_open.assert_called_once()
        mock_ws.send_text.assert_called_once_with("hello")

    @pytest.mark.asyncio()
    async def test_interpret_database_effect(self, mocker: MockerFixture) -> None:
        """Composite interpreter should delegate Database effects."""
        # Create mocks
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
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

        effect = SaveChatMessage(user_id=user_id, text="Test message")
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Ok(EffectReturn(value=msg, effect_name="SaveChatMessage")):
                assert isinstance(msg, ChatMessage)
                assert msg.text == "Test message"
                assert msg.user_id == user_id
                assert msg == saved_message
            case _:
                pytest.fail(f"Expected Ok with SaveChatMessage, got {result}")

        # Verify database was used
        mock_msg_repo.save_message.assert_called_once_with(user_id, "Test message")

    @pytest.mark.asyncio()
    async def test_interpret_cache_effect(self, mocker: MockerFixture) -> None:
        """Composite interpreter should delegate Cache effects."""
        # Create mocks
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
        mock_cache = mocker.AsyncMock(spec=ProfileCache)

        user_id = uuid4()
        profile = ProfileData(id=str(user_id), name="Test User")

        # Configure cache mock to return the profile
        mock_cache.get_profile.return_value = CacheHit(value=profile, ttl_remaining=300)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=mock_cache,
        )

        # Put profile in cache first
        put_effect = PutCachedProfile(user_id=user_id, profile_data=profile)
        put_result = await interpreter.interpret(put_effect)

        match put_result:
            case Ok(EffectReturn(value=None, effect_name="PutCachedProfile")):
                pass  # Success
            case _:
                pytest.fail(f"Expected Ok with PutCachedProfile, got {put_result}")

        # Get profile from cache
        get_effect = GetCachedProfile(user_id=user_id)
        get_result = await interpreter.interpret(get_effect)

        match get_result:
            case Ok(EffectReturn(value=p, effect_name="GetCachedProfile")):
                assert p == profile
            case _:
                pytest.fail(f"Expected Ok with GetCachedProfile, got {get_result}")

        # Verify cache was used
        mock_cache.put_profile.assert_called_once_with(user_id, profile, 300)
        mock_cache.get_profile.assert_called_once_with(user_id)

    @pytest.mark.asyncio()
    async def test_interpret_websocket_receive(self, mocker: MockerFixture) -> None:
        """Composite interpreter should handle ReceiveText effect."""
        # Create mocks
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_ws.receive_text.return_value = "message1"
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
        mock_cache = mocker.AsyncMock(spec=ProfileCache)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=mock_cache,
        )

        effect = ReceiveText()
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Ok(EffectReturn(value="message1", effect_name="ReceiveText")):
                pass  # Success
            case _:
                pytest.fail(f"Expected Ok with ReceiveText, got {result}")

        # Verify WebSocket was used
        mock_ws.is_open.assert_called_once()
        mock_ws.receive_text.assert_called_once()

    @pytest.mark.asyncio()
    async def test_interpret_websocket_close(self, mocker: MockerFixture) -> None:
        """Composite interpreter should handle Close effect."""
        # Create mocks
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
        mock_cache = mocker.AsyncMock(spec=ProfileCache)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=mock_cache,
        )

        effect = Close(reason=CloseNormal())
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Ok(EffectReturn(value=None, effect_name="Close")):
                pass  # Success
            case _:
                pytest.fail(f"Expected Ok with Close, got {result}")

        # Verify WebSocket was used
        mock_ws.close.assert_called_once()

    @pytest.mark.asyncio()
    async def test_interpret_database_get_user(self, mocker: MockerFixture) -> None:
        """Composite interpreter should handle GetUserById effect."""
        # Create mocks
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
        mock_cache = mocker.AsyncMock(spec=ProfileCache)

        # Configure user repository
        user_id = uuid4()
        user = User(id=user_id, email="test@example.com", name="Test")
        mock_user_repo.get_by_id.return_value = UserFound(user=user, source="database")

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=mock_cache,
        )

        effect = GetUserById(user_id=user_id)
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Ok(EffectReturn(value=u, effect_name="GetUserById")):
                assert u == user
            case _:
                pytest.fail(f"Expected Ok with GetUserById, got {result}")

        # Verify database was used
        mock_user_repo.get_by_id.assert_called_once_with(user_id)

    @pytest.mark.asyncio()
    async def test_unhandled_effect_returns_error(self, mocker: MockerFixture) -> None:
        """Composite interpreter should return UnhandledEffectError for unknown effects."""

        @dataclass(frozen=True)
        class UnknownEffect:
            """Custom effect not handled by any interpreter."""

            data: str

        # Create mocks
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
        mock_cache = mocker.AsyncMock(spec=ProfileCache)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=mock_cache,
        )

        # UnknownEffect doesn't implement Effect protocol - testing unhandled effect
        effect = UnknownEffect(data="test")
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Err(
                UnhandledEffectError(
                    effect=e,
                    available_interpreters=[
                        "WebSocketInterpreter",
                        "DatabaseInterpreter",
                        "CacheInterpreter",
                    ],
                )
            ):
                assert e == effect
            case _:
                pytest.fail(f"Expected UnhandledEffectError, got {result}")

    def test_composite_interpreter_is_immutable(self, mocker: MockerFixture) -> None:
        """CompositeInterpreter should be frozen."""
        # Create mocks
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
        mock_cache = mocker.AsyncMock(spec=ProfileCache)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=mock_cache,
        )

        with pytest.raises(FrozenInstanceError):
            interpreter.websocket = None  # type: ignore[assignment,misc]

    def test_create_composite_interpreter_factory(self, mocker: MockerFixture) -> None:
        """Factory function should create valid CompositeInterpreter."""
        # Create mocks
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
        mock_cache = mocker.AsyncMock(spec=ProfileCache)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=mock_cache,
        )

        assert isinstance(interpreter, CompositeInterpreter)
        assert interpreter.websocket is not None
        assert interpreter.database is not None
        assert interpreter.cache is not None
