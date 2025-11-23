"""Tests for Profile domain models."""

from dataclasses import FrozenInstanceError
from uuid import uuid4

import pytest

from effectful.domain.profile import (
    ProfileData,
    ProfileFound,
    ProfileLookupResult,
    ProfileNotFound,
)


class TestProfileData:
    """Test ProfileData value object."""

    def test_profile_data_creates_with_fields(self) -> None:
        """ProfileData should be constructable."""
        profile = ProfileData(id="123", name="Alice")
        assert profile.id == "123"
        assert profile.name == "Alice"

    def test_profile_data_is_immutable(self) -> None:
        """ProfileData should be frozen."""
        profile = ProfileData(id="123", name="Alice")
        with pytest.raises(FrozenInstanceError):
            setattr(profile, "name", "Bob")


class TestProfileFound:
    """Test ProfileFound ADT variant."""

    def test_profile_found_wraps_profile_and_source(self) -> None:
        """ProfileFound should wrap profile and source."""
        profile = ProfileData(id="123", name="Alice")
        found = ProfileFound(profile=profile, source="cache")
        assert found.profile == profile
        assert found.source == "cache"

    def test_profile_found_is_immutable(self) -> None:
        """ProfileFound should be frozen."""
        profile = ProfileData(id="123", name="Alice")
        found = ProfileFound(profile=profile, source="cache")
        with pytest.raises(FrozenInstanceError):
            setattr(found, "source", "database")


class TestProfileNotFound:
    """Test ProfileNotFound ADT variant."""

    def test_profile_not_found_wraps_user_id_and_reason(self) -> None:
        """ProfileNotFound should wrap user_id and reason."""
        user_id = uuid4()
        not_found = ProfileNotFound(user_id=user_id, reason="no_cache_no_user")
        assert not_found.user_id == user_id
        assert not_found.reason == "no_cache_no_user"

    def test_profile_not_found_is_immutable(self) -> None:
        """ProfileNotFound should be frozen."""
        not_found = ProfileNotFound(user_id=uuid4(), reason="no_cache_no_user")
        with pytest.raises(FrozenInstanceError):
            setattr(not_found, "reason", "cache_miss_no_user")


class TestProfileLookupResultExhaustiveness:
    """Test exhaustive matching on ProfileLookupResult ADT."""

    def test_all_profile_lookup_results_handled(self) -> None:
        """Pattern matching should handle all ProfileLookupResult variants."""
        profile = ProfileData(id="123", name="Alice")
        results: list[ProfileLookupResult] = [
            ProfileFound(profile=profile, source="cache"),
            ProfileNotFound(user_id=uuid4(), reason="no_cache_no_user"),
        ]

        def match_result(result: ProfileLookupResult) -> str:
            match result:
                case ProfileFound(profile=p, source=s):
                    return f"found:{p.name}:{s}"
                case ProfileNotFound(user_id=_, reason=r):
                    return f"not_found:{r}"

        matched = [match_result(r) for r in results]
        assert matched[0] == "found:Alice:cache"
        assert matched[1] == "not_found:no_cache_no_user"
