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

from effectful.algebraic.effect_return import EffectReturn
from effectful.algebraic.result import Err, Ok
from effectful.domain.cache_result import CacheHit
from effectful.domain.message import ChatMessage
from effectful.domain.profile import ProfileData
from effectful.domain.user import User, UserFound
from effectful.domain.message_envelope import MessageEnvelope, PublishSuccess
from effectful.domain.optional_value import Absent
from effectful.domain.s3_object import PutSuccess, S3Object
from effectful.domain.token_result import TokenValid
from effectful.effects.auth import ValidateToken
from effectful.effects.cache import GetCachedProfile, PutCachedProfile
from effectful.effects.database import GetUserById, SaveChatMessage
from effectful.effects.messaging import PublishMessage
from effectful.effects.storage import GetObject, PutObject
from effectful.effects.websocket import Close, CloseNormal, ReceiveText, SendText
from effectful.infrastructure.auth import AuthService
from effectful.infrastructure.cache import ProfileCache
from effectful.infrastructure.messaging import MessageConsumer, MessageProducer
from effectful.infrastructure.repositories import ChatMessageRepository, UserRepository
from effectful.infrastructure.storage import ObjectStorage
from effectful.infrastructure.websocket import WebSocketConnection
from effectful.interpreters.composite import (
    CompositeInterpreter,
    create_composite_interpreter,
)
from effectful.interpreters.cache import CacheInterpreter
from effectful.interpreters.database import DatabaseInterpreter
from effectful.interpreters.metrics import MetricsInterpreter
from effectful.interpreters.system import SystemInterpreter
from effectful.interpreters.websocket import WebSocketInterpreter
from effectful.interpreters.errors import UnhandledEffectError


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
    async def test_metrics_interpreter_unhandled_passes_through(
        self, mocker: MockerFixture
    ) -> None:
        """Composite should fall through when metrics interpreter cannot handle effect."""
        mock_ws = mocker.AsyncMock(spec=WebSocketInterpreter)
        mock_db = mocker.AsyncMock(spec=DatabaseInterpreter)
        mock_cache = mocker.AsyncMock(spec=CacheInterpreter)
        mock_system = mocker.AsyncMock(spec=SystemInterpreter)
        mock_metrics = mocker.AsyncMock(spec=MetricsInterpreter)
        dummy_effect = SendText(text="no interpreter")
        unhandled = Err(UnhandledEffectError(effect=dummy_effect, available_interpreters=["Test"]))
        mock_ws.interpret.return_value = unhandled
        mock_db.interpret.return_value = unhandled
        mock_cache.interpret.return_value = unhandled
        mock_system.interpret.return_value = unhandled
        mock_metrics.interpret.return_value = Err(
            UnhandledEffectError(effect=dummy_effect, available_interpreters=["MetricsInterpreter"])
        )

        interpreter = CompositeInterpreter(
            websocket=mock_ws,
            database=mock_db,
            cache=mock_cache,
            messaging=None,
            storage=None,
            auth=None,
            metrics=mock_metrics,
            system=mock_system,
        )

        result = await interpreter.interpret(dummy_effect)

        match result:
            case Err(UnhandledEffectError(effect=e, available_interpreters=available)):
                assert e == dummy_effect
                assert available == [
                    "WebSocketInterpreter",
                    "DatabaseInterpreter",
                    "CacheInterpreter",
                    "SystemInterpreter",
                    "MetricsInterpreter",
                ]
            case _:
                pytest.fail(f"Expected UnhandledEffectError, got {result}")

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
                        "SystemInterpreter",
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
            setattr(interpreter, "websocket", None)

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
        from effectful.interpreters.websocket import WebSocketInterpreter
        from effectful.interpreters.database import DatabaseInterpreter
        from effectful.interpreters.cache import CacheInterpreter

        assert isinstance(interpreter.websocket, WebSocketInterpreter)
        assert isinstance(interpreter.database, DatabaseInterpreter)
        assert isinstance(interpreter.cache, CacheInterpreter)

    @pytest.mark.asyncio()
    async def test_interpret_messaging_effect(self, mocker: MockerFixture) -> None:
        """Composite interpreter should delegate Messaging effects when configured."""
        # Create mocks
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
        mock_cache = mocker.AsyncMock(spec=ProfileCache)
        mock_producer = mocker.AsyncMock(spec=MessageProducer)
        mock_consumer = mocker.AsyncMock(spec=MessageConsumer)

        # Configure producer mock
        mock_producer.publish.return_value = PublishSuccess(
            message_id="msg-123", topic="test-topic"
        )

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=mock_cache,
            message_producer=mock_producer,
            message_consumer=mock_consumer,
        )

        effect = PublishMessage(topic="test-topic", payload=b"test data")
        result = await interpreter.interpret(effect)

        # Verify result - messaging interpreter returns message_id string, not PublishSuccess
        match result:
            case Ok(EffectReturn(value=msg_id, effect_name="PublishMessage")):
                assert msg_id == "msg-123"
            case _:
                pytest.fail(f"Expected Ok with PublishMessage, got {result}")

        # Verify producer was used
        mock_producer.publish.assert_called_once_with("test-topic", b"test data", properties=None)

    @pytest.mark.asyncio()
    async def test_interpret_storage_effect(self, mocker: MockerFixture) -> None:
        """Composite interpreter should delegate Storage effects when configured."""
        # Create mocks
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
        mock_cache = mocker.AsyncMock(spec=ProfileCache)
        mock_storage = mocker.AsyncMock(spec=ObjectStorage)

        # Configure storage mock
        mock_storage.put_object.return_value = PutSuccess(
            key="test-key", bucket="test-bucket", version_id="v1"
        )

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=mock_cache,
            object_storage=mock_storage,
        )

        effect = PutObject(bucket="test-bucket", key="test-key", content=b"test content")
        result = await interpreter.interpret(effect)

        # Verify result - storage interpreter returns PutSuccess ADT
        match result:
            case Ok(EffectReturn(value=PutSuccess(key="test-key"), effect_name="PutObject")):
                pass  # Success
            case _:
                pytest.fail(f"Expected Ok with PutSuccess, got {result}")

        # Verify storage was used
        mock_storage.put_object.assert_called_once_with(
            "test-bucket", "test-key", b"test content", Absent(), Absent()
        )

    @pytest.mark.asyncio()
    async def test_interpret_auth_effect(self, mocker: MockerFixture) -> None:
        """Composite interpreter should delegate Auth effects when configured."""
        # Create mocks
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
        mock_cache = mocker.AsyncMock(spec=ProfileCache)
        mock_auth = mocker.AsyncMock(spec=AuthService)

        # Configure auth mock
        user_id = uuid4()
        mock_auth.validate_token.return_value = TokenValid(
            user_id=user_id, claims={"role": "admin"}
        )

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=mock_cache,
            auth_service=mock_auth,
        )

        effect = ValidateToken(token="test.jwt.token")
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Ok(EffectReturn(value=token_result, effect_name="ValidateToken")):
                assert isinstance(token_result, TokenValid)
                assert token_result.user_id == user_id
            case _:
                pytest.fail(f"Expected Ok with ValidateToken, got {result}")

        # Verify auth service was used
        mock_auth.validate_token.assert_called_once_with("test.jwt.token")

    @pytest.mark.asyncio()
    async def test_unhandled_effect_with_all_interpreters(self, mocker: MockerFixture) -> None:
        """Unhandled effect should list all configured interpreters."""

        @dataclass(frozen=True)
        class UnknownEffect:
            """Custom effect not handled by any interpreter."""

            data: str

        # Create all mocks including optional ones
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
        mock_cache = mocker.AsyncMock(spec=ProfileCache)
        mock_producer = mocker.AsyncMock(spec=MessageProducer)
        mock_consumer = mocker.AsyncMock(spec=MessageConsumer)
        mock_storage = mocker.AsyncMock(spec=ObjectStorage)
        mock_auth = mocker.AsyncMock(spec=AuthService)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=mock_cache,
            message_producer=mock_producer,
            message_consumer=mock_consumer,
            object_storage=mock_storage,
            auth_service=mock_auth,
        )

        effect = UnknownEffect(data="test")
        result = await interpreter.interpret(effect)

        # Verify all interpreters are listed
        match result:
            case Err(UnhandledEffectError(available_interpreters=interpreters)):
                assert "WebSocketInterpreter" in interpreters
                assert "DatabaseInterpreter" in interpreters
                assert "CacheInterpreter" in interpreters
                assert "MessagingInterpreter" in interpreters
                assert "StorageInterpreter" in interpreters
                assert "AuthInterpreter" in interpreters
            case _:
                pytest.fail(f"Expected UnhandledEffectError, got {result}")

    def test_create_composite_interpreter_with_all_optional(self, mocker: MockerFixture) -> None:
        """Factory function should configure all optional interpreters."""
        # Create all mocks
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
        mock_cache = mocker.AsyncMock(spec=ProfileCache)
        mock_producer = mocker.AsyncMock(spec=MessageProducer)
        mock_consumer = mocker.AsyncMock(spec=MessageConsumer)
        mock_storage = mocker.AsyncMock(spec=ObjectStorage)
        mock_auth = mocker.AsyncMock(spec=AuthService)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=mock_cache,
            message_producer=mock_producer,
            message_consumer=mock_consumer,
            object_storage=mock_storage,
            auth_service=mock_auth,
        )

        assert isinstance(interpreter, CompositeInterpreter)
        from effectful.interpreters.messaging import MessagingInterpreter
        from effectful.interpreters.storage import StorageInterpreter
        from effectful.interpreters.auth import AuthInterpreter

        assert isinstance(interpreter.messaging, MessagingInterpreter)
        assert isinstance(interpreter.storage, StorageInterpreter)
        assert isinstance(interpreter.auth, AuthInterpreter)
