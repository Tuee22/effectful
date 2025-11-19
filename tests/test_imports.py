"""Tests for public API imports.

This module verifies that all exported symbols in functional_effects/__init__.py
are importable and have correct types. These tests ensure the public API contract
is maintained.
"""


import pytest
from pytest_mock import MockerFixture


class TestPublicAPIImports:
    """Tests that all public API symbols can be imported."""

    def test_import_core_execution(self) -> None:
        """run_ws_program should be importable from root."""
        from functional_effects import run_ws_program

        assert callable(run_ws_program)

    def test_import_result_types(self) -> None:
        """Result types (Ok, Err, Result, EffectReturn) should be importable."""
        from functional_effects import EffectReturn, Err, Ok, Result

        # Test Ok/Err constructors
        ok_result = Ok(42)
        assert ok_result.value == 42

        err_result: Result[int, str] = Err("failed")
        # Pattern match to narrow type for mypy
        match err_result:
            case Err(error):
                assert error == "failed"
            case Ok(_):
                pytest.fail("Expected Err, got Ok")

        # Test EffectReturn
        effect_return = EffectReturn(value="test", effect_name="TestEffect")
        assert effect_return.value == "test"
        assert effect_return.effect_name == "TestEffect"

    def test_import_websocket_effects(self) -> None:
        """WebSocket effects should be importable."""
        from functional_effects import (
            Close,
            CloseGoingAway,
            CloseNormal,
            ClosePolicyViolation,
            CloseProtocolError,
            SendText,
        )

        # Test effect constructors
        send = SendText(text="Hello")
        assert send.text == "Hello"

        close = Close(reason=CloseNormal())
        # CloseReason is a type alias, not a class, so we check the variant type
        assert isinstance(
            close.reason,
            CloseNormal | CloseGoingAway | CloseProtocolError | ClosePolicyViolation,
        )

    def test_import_database_effects(self) -> None:
        """Database effects should be importable."""
        from uuid import uuid4

        from functional_effects import GetUserById, SaveChatMessage

        user_id = uuid4()
        get_user = GetUserById(user_id=user_id)
        assert get_user.user_id == user_id

        save_msg = SaveChatMessage(user_id=user_id, text="Hello")
        assert save_msg.text == "Hello"

    def test_import_cache_effects(self) -> None:
        """Cache effects should be importable."""
        from uuid import uuid4

        from functional_effects import GetCachedProfile, PutCachedProfile
        from functional_effects.domain.profile import ProfileData

        user_id = uuid4()
        get_profile = GetCachedProfile(user_id=user_id)
        assert get_profile.user_id == user_id

        profile = ProfileData(id=str(user_id), name="Alice")
        put_profile = PutCachedProfile(user_id=user_id, profile_data=profile)
        assert put_profile.profile_data == profile

    def test_import_domain_models(self) -> None:
        """Domain models should be importable."""
        from uuid import uuid4

        from functional_effects import (
            ChatMessage,
            ProfileData,
            ProfileFound,
            ProfileNotFound,
            User,
            UserFound,
            UserNotFound,
        )

        # User
        user_id = uuid4()
        user = User(id=user_id, email="test@example.com", name="Alice")
        assert user.name == "Alice"

        # ChatMessage
        from datetime import datetime

        message = ChatMessage(id=user_id, user_id=user_id, text="Hello", created_at=datetime.now())
        assert message.text == "Hello"

        # ProfileData
        profile = ProfileData(id=str(user_id), name="Alice")
        assert profile.name == "Alice"

        # ADT variants (type aliases, not classes - just verify construction)
        user_found = UserFound(user=user, source="database")
        assert user_found.user == user

        user_not_found = UserNotFound(user_id=user_id, reason="does_not_exist")
        assert user_not_found.user_id == user_id

        profile_found = ProfileFound(profile=profile, source="cache")
        assert profile_found.profile == profile

        profile_not_found = ProfileNotFound(user_id=user_id, reason="cache_miss_no_user")
        assert profile_not_found.user_id == user_id

    def test_import_interpreters(self) -> None:
        """Interpreters should be importable."""
        from functional_effects import (
            CacheInterpreter,
            DatabaseInterpreter,
            WebSocketInterpreter,
            create_composite_interpreter,
        )

        assert callable(create_composite_interpreter)

        # Test interpreter classes exist
        assert CacheInterpreter is not None
        assert DatabaseInterpreter is not None
        assert WebSocketInterpreter is not None

    def test_import_errors(self) -> None:
        """Interpreter errors should be importable."""
        from uuid import uuid4

        from functional_effects import (
            CacheError,
            DatabaseError,
            WebSocketClosedError,
        )
        from functional_effects.effects.cache import GetCachedProfile

        # Test error construction (errors include 'effect' field)
        from functional_effects.effects.database import GetUserById
        from functional_effects.effects.websocket import SendText

        effect_db = GetUserById(user_id=uuid4())
        db_error = DatabaseError(effect=effect_db, db_error="Connection failed", is_retryable=True)
        assert db_error.db_error == "Connection failed"

        effect_ws = SendText(text="test")
        ws_error = WebSocketClosedError(effect=effect_ws, close_code=1006, reason="")
        assert ws_error.close_code == 1006

        effect_cache = GetCachedProfile(user_id=uuid4())
        cache_error = CacheError(effect=effect_cache, cache_error="Timeout", is_retryable=True)
        assert cache_error.cache_error == "Timeout"

        # InterpreterError is a type alias (union), not a class
        # Just verify error types are correct dataclasses
        assert db_error.effect == effect_db
        assert ws_error.effect == effect_ws
        assert cache_error.effect == effect_cache

    def test_import_program_types(self) -> None:
        """Program types should be importable."""
        from functional_effects import AllEffects, EffectResult, WSProgram

        # These are type aliases, so we can't instantiate them
        # Just verify they're importable
        assert AllEffects is not None
        assert EffectResult is not None
        assert WSProgram is not None

    def test_import_infrastructure_protocols(self) -> None:
        """Infrastructure protocols should be importable."""
        from functional_effects import (
            ChatMessageRepository,
            ProfileCache,
            UserRepository,
            WebSocketConnection,
        )

        # These are protocols (interfaces), verify they're importable
        assert WebSocketConnection is not None
        assert UserRepository is not None
        assert ChatMessageRepository is not None
        assert ProfileCache is not None


class TestPublicAPIUsage:
    """Tests that demonstrate typical public API usage patterns."""

    @pytest.mark.asyncio()
    async def test_simple_program_with_public_api(self, mocker: "MockerFixture") -> None:
        """Verify a simple program can be written using only public API."""
        from collections.abc import Generator

        from functional_effects import (
            AllEffects,
            EffectResult,
            Err,
            Ok,
            SendText,
            create_composite_interpreter,
            run_ws_program,
        )
        from functional_effects.infrastructure.cache import ProfileCache
        from functional_effects.infrastructure.repositories import (
            ChatMessageRepository,
            UserRepository,
        )
        from functional_effects.infrastructure.websocket import WebSocketConnection

        # Create mocks
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
        mock_cache = mocker.AsyncMock(spec=ProfileCache)

        # Create interpreter
        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=mock_cache,
        )

        # Define program using public types
        def hello_program() -> Generator[AllEffects, EffectResult, str]:
            yield SendText(text="Hello from public API!")
            return "completed"

        # Run program
        result = await run_ws_program(hello_program(), interpreter)

        # Verify result
        match result:
            case Ok(value):
                assert value == "completed"
                mock_ws.send_text.assert_called_once_with("Hello from public API!")
            case Err(error):
                pytest.fail(f"Unexpected error: {error}")

    def test_version_attribute(self) -> None:
        """Package should export __version__."""
        import functional_effects

        assert hasattr(functional_effects, "__version__")
        assert isinstance(functional_effects.__version__, str)
        assert functional_effects.__version__ == "0.1.0"

    def test_all_exports_in_module(self) -> None:
        """Verify __all__ matches actual exports."""
        import functional_effects

        # All items in __all__ should be importable
        for name in functional_effects.__all__:
            assert hasattr(functional_effects, name), f"Missing export: {name}"

    def test_no_unwanted_exports(self) -> None:
        """Verify we don't accidentally export internal modules."""
        import functional_effects

        # These should NOT be in __all__
        unwanted = [
            "dataclass",
            "frozen",
            "UUID",
            "typing",
            "collections",
            "abc",
        ]

        for name in unwanted:
            assert name not in functional_effects.__all__, f"Unwanted export: {name}"
