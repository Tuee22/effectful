"""Tests for Cache effects.

Tests cover:
- Immutability (frozen dataclasses)
- Construction of each effect variant
- Default TTL value
- Type safety with ProfileData
"""

from dataclasses import FrozenInstanceError
from uuid import uuid4

import pytest

from effectful.domain.profile import ProfileData
from effectful.effects.cache import (
    GetCachedProfile,
    GetCachedValue,
    InvalidateCache,
    PutCachedProfile,
    PutCachedValue,
)


class TestGetCachedProfile:
    """Test GetCachedProfile effect."""

    def test_get_cached_profile_creates_effect(self) -> None:
        """GetCachedProfile should wrap user_id."""
        user_id = uuid4()
        effect = GetCachedProfile(user_id)
        assert effect.user_id == user_id

    def test_get_cached_profile_is_immutable(self) -> None:
        """GetCachedProfile should be frozen (immutable)."""
        effect = GetCachedProfile(uuid4())
        with pytest.raises(FrozenInstanceError):
            setattr(effect, "user_id", uuid4())


class TestPutCachedProfile:
    """Test PutCachedProfile effect."""

    def test_put_cached_profile_creates_effect(self) -> None:
        """PutCachedProfile should wrap user_id, profile_data, and ttl_seconds."""
        user_id = uuid4()
        profile = ProfileData(id=str(user_id), name="Alice")
        effect = PutCachedProfile(user_id, profile, ttl_seconds=600)
        assert effect.user_id == user_id
        assert effect.profile_data == profile
        assert effect.ttl_seconds == 600

    def test_put_cached_profile_has_default_ttl(self) -> None:
        """PutCachedProfile should have default TTL of 300 seconds."""
        user_id = uuid4()
        profile = ProfileData(id=str(user_id), name="Alice")
        effect = PutCachedProfile(user_id, profile)
        assert effect.ttl_seconds == 300

    def test_put_cached_profile_is_immutable(self) -> None:
        """PutCachedProfile should be frozen (immutable)."""
        user_id = uuid4()
        profile = ProfileData(id=str(user_id), name="Alice")
        effect = PutCachedProfile(user_id, profile)
        with pytest.raises(FrozenInstanceError):
            setattr(effect, "ttl_seconds", 600)

    def test_put_cached_profile_user_id_is_immutable(self) -> None:
        """PutCachedProfile user_id should be immutable."""
        user_id = uuid4()
        profile = ProfileData(id=str(user_id), name="Alice")
        effect = PutCachedProfile(user_id, profile)
        with pytest.raises(FrozenInstanceError):
            setattr(effect, "user_id", uuid4())

    def test_put_cached_profile_data_is_immutable(self) -> None:
        """PutCachedProfile profile_data should be immutable."""
        user_id = uuid4()
        profile = ProfileData(id=str(user_id), name="Alice")
        effect = PutCachedProfile(user_id, profile)
        with pytest.raises(FrozenInstanceError):
            setattr(effect, "profile_data", ProfileData(id="123", name="Bob"))


class TestGetCachedValue:
    """Test GetCachedValue effect."""

    def test_get_cached_value_creates_effect(self) -> None:
        """GetCachedValue should wrap key."""
        effect = GetCachedValue(key="session:123")
        assert effect.key == "session:123"

    def test_get_cached_value_is_immutable(self) -> None:
        """GetCachedValue should be frozen (immutable)."""
        effect = GetCachedValue(key="test_key")
        with pytest.raises(FrozenInstanceError):
            setattr(effect, "key", "new_key")


class TestPutCachedValue:
    """Test PutCachedValue effect."""

    def test_put_cached_value_creates_effect(self) -> None:
        """PutCachedValue should wrap key, value, and ttl_seconds."""
        effect = PutCachedValue(key="session:123", value=b"data", ttl_seconds=3600)
        assert effect.key == "session:123"
        assert effect.value == b"data"
        assert effect.ttl_seconds == 3600

    def test_put_cached_value_is_immutable(self) -> None:
        """PutCachedValue should be frozen (immutable)."""
        effect = PutCachedValue(key="test", value=b"data", ttl_seconds=300)
        with pytest.raises(FrozenInstanceError):
            setattr(effect, "key", "new_key")

    def test_put_cached_value_value_is_immutable(self) -> None:
        """PutCachedValue value should be immutable."""
        effect = PutCachedValue(key="test", value=b"data", ttl_seconds=300)
        with pytest.raises(FrozenInstanceError):
            setattr(effect, "value", b"new_data")

    def test_put_cached_value_ttl_is_immutable(self) -> None:
        """PutCachedValue ttl_seconds should be immutable."""
        effect = PutCachedValue(key="test", value=b"data", ttl_seconds=300)
        with pytest.raises(FrozenInstanceError):
            setattr(effect, "ttl_seconds", 600)


class TestInvalidateCache:
    """Test InvalidateCache effect."""

    def test_invalidate_cache_creates_effect(self) -> None:
        """InvalidateCache should wrap key."""
        effect = InvalidateCache(key="session:123")
        assert effect.key == "session:123"

    def test_invalidate_cache_is_immutable(self) -> None:
        """InvalidateCache should be frozen (immutable)."""
        effect = InvalidateCache(key="test_key")
        with pytest.raises(FrozenInstanceError):
            setattr(effect, "key", "new_key")
