"""Unit tests for Redis cache adapter.

Tests RedisProfileCache using pytest-mock with AsyncMock.
"""

import json
from uuid import uuid4

import pytest
from pytest_mock import MockerFixture

from effectful.adapters.redis_cache import RedisProfileCache
from effectful.domain.cache_result import CacheHit, CacheMiss
from effectful.domain.profile import ProfileData


class TestRedisProfileCache:
    """Tests for RedisProfileCache."""

    @pytest.mark.asyncio
    async def test_get_profile_returns_cache_hit_when_found(self, mocker: MockerFixture) -> None:
        """Test successful cache lookup returns CacheHit with ProfileData."""
        # Setup
        user_id = uuid4()
        profile_data = {"id": str(user_id), "name": "Test User"}
        cached_json = json.dumps(profile_data)

        mock_redis = mocker.AsyncMock()
        mock_redis.get.return_value = cached_json
        mock_redis.ttl.return_value = 300  # 5 minutes remaining

        cache = RedisProfileCache(mock_redis)

        # Execute
        result = await cache.get_profile(user_id)

        # Assert
        assert isinstance(result, CacheHit)
        assert isinstance(result.value, ProfileData)
        assert result.value.id == str(user_id)
        assert result.value.name == "Test User"
        assert result.ttl_remaining == 300

        # Verify Redis calls
        mock_redis.get.assert_called_once_with(f"profile:{user_id}")
        mock_redis.ttl.assert_called_once_with(f"profile:{user_id}")

    @pytest.mark.asyncio
    async def test_get_profile_returns_cache_miss_when_not_found(
        self, mocker: MockerFixture
    ) -> None:
        """Test cache lookup returns CacheMiss when key doesn't exist."""
        # Setup
        user_id = uuid4()
        mock_redis = mocker.AsyncMock()
        mock_redis.get.return_value = None

        cache = RedisProfileCache(mock_redis)

        # Execute
        result = await cache.get_profile(user_id)

        # Assert
        assert isinstance(result, CacheMiss)
        assert result.key == f"profile:{user_id}"
        assert result.reason == "not_found"

    @pytest.mark.asyncio
    async def test_get_profile_returns_cache_miss_when_expired(self, mocker: MockerFixture) -> None:
        """Test cache lookup returns CacheMiss when TTL indicates expired."""
        # Setup
        user_id = uuid4()
        profile_data = {"id": str(user_id), "name": "Test User"}
        cached_json = json.dumps(profile_data)

        mock_redis = mocker.AsyncMock()
        mock_redis.get.return_value = cached_json
        mock_redis.ttl.return_value = -2  # Key doesn't exist (race condition)

        cache = RedisProfileCache(mock_redis)

        # Execute
        result = await cache.get_profile(user_id)

        # Assert
        assert isinstance(result, CacheMiss)
        assert result.key == f"profile:{user_id}"
        assert result.reason == "expired"

    @pytest.mark.asyncio
    async def test_get_profile_handles_no_expiration(self, mocker: MockerFixture) -> None:
        """Test cache lookup handles -1 TTL (no expiration set)."""
        # Setup
        user_id = uuid4()
        profile_data = {"id": str(user_id), "name": "Test User"}
        cached_json = json.dumps(profile_data)

        mock_redis = mocker.AsyncMock()
        mock_redis.get.return_value = cached_json
        mock_redis.ttl.return_value = -1  # No expiration

        cache = RedisProfileCache(mock_redis)

        # Execute
        result = await cache.get_profile(user_id)

        # Assert
        assert isinstance(result, CacheHit)
        assert result.ttl_remaining == 0  # Normalized to 0

    @pytest.mark.asyncio
    async def test_put_profile_stores_with_ttl(self, mocker: MockerFixture) -> None:
        """Test storing profile sets correct key, value, and TTL."""
        # Setup
        user_id = uuid4()
        profile = ProfileData(id=str(user_id), name="Test User")
        ttl_seconds = 600

        mock_redis = mocker.AsyncMock()
        cache = RedisProfileCache(mock_redis)

        # Execute
        await cache.put_profile(user_id, profile, ttl_seconds)

        # Assert
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args

        expected_key = f"profile:{user_id}"
        expected_json = json.dumps({"id": str(user_id), "name": "Test User"})

        assert call_args.args[0] == expected_key
        assert call_args.args[1] == ttl_seconds
        assert call_args.args[2] == expected_json

    @pytest.mark.asyncio
    async def test_put_profile_serializes_profile_correctly(self, mocker: MockerFixture) -> None:
        """Test that profile is correctly serialized to JSON."""
        # Setup
        user_id = uuid4()
        profile = ProfileData(id="custom-id-123", name="Alice Smith")

        mock_redis = mocker.AsyncMock()
        cache = RedisProfileCache(mock_redis)

        # Execute
        await cache.put_profile(user_id, profile, 300)

        # Assert
        call_args = mock_redis.setex.call_args
        stored_json = call_args.args[2]
        stored_data = json.loads(stored_json)

        assert stored_data["id"] == "custom-id-123"
        assert stored_data["name"] == "Alice Smith"
