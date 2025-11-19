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

from functional_effects.domain.profile import ProfileData
from functional_effects.effects.cache import GetCachedProfile, PutCachedProfile


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
            effect.user_id = uuid4()  # type: ignore[misc]


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
            effect.ttl_seconds = 600  # type: ignore[misc]

    def test_put_cached_profile_user_id_is_immutable(self) -> None:
        """PutCachedProfile user_id should be immutable."""
        user_id = uuid4()
        profile = ProfileData(id=str(user_id), name="Alice")
        effect = PutCachedProfile(user_id, profile)
        with pytest.raises(FrozenInstanceError):
            effect.user_id = uuid4()  # type: ignore[misc]

    def test_put_cached_profile_data_is_immutable(self) -> None:
        """PutCachedProfile profile_data should be immutable."""
        user_id = uuid4()
        profile = ProfileData(id=str(user_id), name="Alice")
        effect = PutCachedProfile(user_id, profile)
        with pytest.raises(FrozenInstanceError):
            effect.profile_data = ProfileData(id="123", name="Bob")  # type: ignore[misc]
