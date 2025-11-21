"""Tests for Cache interpreter.

This module tests the CacheInterpreter using pytest mocks (via pytest-mock).
Tests cover:
- Profile cache hit/miss
- Profile caching with custom TTL
- Cache errors and retryability
- Unhandled effects
- Immutability
"""

from dataclasses import FrozenInstanceError
from uuid import uuid4

import pytest
from pytest_mock import MockerFixture

from effectful.algebraic.effect_return import EffectReturn
from effectful.algebraic.result import Err, Ok
from effectful.domain.cache_result import CacheHit, CacheMiss
from effectful.domain.profile import ProfileData
from effectful.effects.cache import GetCachedProfile, PutCachedProfile
from effectful.effects.websocket import SendText
from effectful.infrastructure.cache import ProfileCache
from effectful.interpreters.cache import CacheInterpreter
from effectful.interpreters.errors import CacheError, UnhandledEffectError


class TestCacheInterpreter:
    """Tests for CacheInterpreter."""

    @pytest.mark.asyncio()
    async def test_get_cached_profile_hit(self, mocker: MockerFixture) -> None:
        """Interpreter should return profile when cached."""
        user_id = uuid4()
        profile = ProfileData(id=str(user_id), name="Test User")

        # Create mock
        mock_cache = mocker.AsyncMock(spec=ProfileCache)
        mock_cache.get_profile.return_value = CacheHit(value=profile, ttl_remaining=300)

        interpreter = CacheInterpreter(cache=mock_cache)

        effect = GetCachedProfile(user_id=user_id)
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Ok(EffectReturn(value=p, effect_name="GetCachedProfile")):
                assert p == profile
            case _:
                pytest.fail(f"Expected Ok with profile, got {result}")

        # Verify mock was called correctly
        mock_cache.get_profile.assert_called_once_with(user_id)

    @pytest.mark.asyncio()
    async def test_get_cached_profile_miss(self, mocker: MockerFixture) -> None:
        """Interpreter should return None when profile not cached."""
        user_id = uuid4()

        # Create mock
        mock_cache = mocker.AsyncMock(spec=ProfileCache)
        mock_cache.get_profile.return_value = CacheMiss(key=str(user_id), reason="not_found")

        interpreter = CacheInterpreter(cache=mock_cache)

        effect = GetCachedProfile(user_id=user_id)
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Ok(EffectReturn(value=None, effect_name="GetCachedProfile")):
                pass  # Success
            case _:
                pytest.fail(f"Expected Ok with None, got {result}")

        # Verify mock was called correctly
        mock_cache.get_profile.assert_called_once_with(user_id)

    @pytest.mark.asyncio()
    async def test_get_cached_profile_cache_error(self, mocker: MockerFixture) -> None:
        """Interpreter should return CacheError when get fails."""
        user_id = uuid4()

        # Create mock
        mock_cache = mocker.AsyncMock(spec=ProfileCache)
        mock_cache.get_profile.side_effect = Exception("Redis connection timeout")

        interpreter = CacheInterpreter(cache=mock_cache)

        effect = GetCachedProfile(user_id=user_id)
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Err(
                CacheError(effect=e, cache_error="Redis connection timeout", is_retryable=True)
            ):
                assert e == effect
            case _:
                pytest.fail(f"Expected CacheError, got {result}")

        # Verify mock was called correctly
        mock_cache.get_profile.assert_called_once_with(user_id)

    @pytest.mark.asyncio()
    async def test_put_cached_profile_success(self, mocker: MockerFixture) -> None:
        """Interpreter should cache profile successfully."""
        user_id = uuid4()
        profile = ProfileData(id=str(user_id), name="New Name")

        # Create mock
        mock_cache = mocker.AsyncMock(spec=ProfileCache)

        interpreter = CacheInterpreter(cache=mock_cache)

        effect = PutCachedProfile(user_id=user_id, profile_data=profile, ttl_seconds=300)
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Ok(EffectReturn(value=None, effect_name="PutCachedProfile")):
                pass  # Success
            case _:
                pytest.fail(f"Expected Ok, got {result}")

        # Verify mock was called correctly
        mock_cache.put_profile.assert_called_once_with(user_id, profile, 300)

    @pytest.mark.asyncio()
    async def test_put_cached_profile_with_custom_ttl(self, mocker: MockerFixture) -> None:
        """Interpreter should handle custom TTL."""
        user_id = uuid4()
        profile = ProfileData(id=str(user_id), name="User Name")

        # Create mock
        mock_cache = mocker.AsyncMock(spec=ProfileCache)

        interpreter = CacheInterpreter(cache=mock_cache)

        effect = PutCachedProfile(user_id=user_id, profile_data=profile, ttl_seconds=600)
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Ok(EffectReturn(value=None, effect_name="PutCachedProfile")):
                pass  # Success
            case _:
                pytest.fail(f"Expected Ok, got {result}")

        # Verify mock was called with custom TTL
        mock_cache.put_profile.assert_called_once_with(user_id, profile, 600)

    @pytest.mark.asyncio()
    async def test_put_cached_profile_cache_error(self, mocker: MockerFixture) -> None:
        """Interpreter should return CacheError when put fails."""
        user_id = uuid4()
        profile = ProfileData(id=str(user_id), name="User Name")

        # Create mock
        mock_cache = mocker.AsyncMock(spec=ProfileCache)
        mock_cache.put_profile.side_effect = Exception("Network error")

        interpreter = CacheInterpreter(cache=mock_cache)

        effect = PutCachedProfile(user_id=user_id, profile_data=profile)
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Err(CacheError(effect=e, cache_error="Network error", is_retryable=True)):
                assert e == effect
            case _:
                pytest.fail(f"Expected CacheError, got {result}")

        # Verify mock was called correctly (default TTL = 300)
        mock_cache.put_profile.assert_called_once_with(user_id, profile, 300)

    @pytest.mark.asyncio()
    async def test_unhandled_effect(self, mocker: MockerFixture) -> None:
        """Interpreter should return error for non-Cache effects."""
        # Create mock
        mock_cache = mocker.AsyncMock(spec=ProfileCache)

        interpreter = CacheInterpreter(cache=mock_cache)

        effect = SendText(text="hello")
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Err(UnhandledEffectError(effect=e, available_interpreters=["CacheInterpreter"])):
                assert e == effect
            case _:
                pytest.fail(f"Expected UnhandledEffectError, got {result}")

        # Verify no cache methods were called
        mock_cache.get_profile.assert_not_called()
        mock_cache.put_profile.assert_not_called()

    def test_interpreter_is_immutable(self, mocker: MockerFixture) -> None:
        """CacheInterpreter should be frozen."""
        mock_cache = mocker.AsyncMock(spec=ProfileCache)
        interpreter = CacheInterpreter(cache=mock_cache)

        with pytest.raises(FrozenInstanceError):
            interpreter.cache = mocker.AsyncMock(spec=ProfileCache)  # type: ignore[misc]

    def test_is_retryable_error_detects_retryable_patterns(self, mocker: MockerFixture) -> None:
        """_is_retryable_error should detect retryable error patterns."""
        mock_cache = mocker.AsyncMock(spec=ProfileCache)
        interpreter = CacheInterpreter(cache=mock_cache)

        assert interpreter._is_retryable_error(Exception("Connection timeout"))
        assert interpreter._is_retryable_error(Exception("Network error"))
        assert interpreter._is_retryable_error(Exception("Redis unavailable"))

    def test_is_retryable_error_detects_non_retryable_patterns(self, mocker: MockerFixture) -> None:
        """_is_retryable_error should detect non-retryable error patterns."""
        mock_cache = mocker.AsyncMock(spec=ProfileCache)
        interpreter = CacheInterpreter(cache=mock_cache)

        assert not interpreter._is_retryable_error(Exception("Invalid key format"))
        assert not interpreter._is_retryable_error(Exception("Serialization error"))
        assert not interpreter._is_retryable_error(Exception("Unknown error"))
