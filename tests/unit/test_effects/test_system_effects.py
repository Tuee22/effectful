"""Tests for System effects.

Tests cover:
- Immutability (frozen dataclasses)
- Construction of GetCurrentTime and GenerateUUID effects
"""

from dataclasses import FrozenInstanceError

import pytest

from effectful.effects.system import GenerateUUID, GetCurrentTime


class TestGetCurrentTime:
    """Test GetCurrentTime effect."""

    def test_get_current_time_creates_effect(self) -> None:
        """GetCurrentTime should create an effect with no parameters."""
        effect = GetCurrentTime()
        assert isinstance(effect, GetCurrentTime)

    def test_get_current_time_is_immutable(self) -> None:
        """GetCurrentTime should be frozen (immutable)."""
        effect = GetCurrentTime()
        with pytest.raises(FrozenInstanceError):
            setattr(effect, "dummy", "value")


class TestGenerateUUID:
    """Test GenerateUUID effect."""

    def test_generate_uuid_creates_effect(self) -> None:
        """GenerateUUID should create an effect with no parameters."""
        effect = GenerateUUID()
        assert isinstance(effect, GenerateUUID)

    def test_generate_uuid_is_immutable(self) -> None:
        """GenerateUUID should be frozen (immutable)."""
        effect = GenerateUUID()
        with pytest.raises(FrozenInstanceError):
            setattr(effect, "dummy", "value")
