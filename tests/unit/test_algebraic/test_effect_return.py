"""Tests for EffectReturn[T] wrapper.

This module provides comprehensive tests for the EffectReturn wrapper including:
- Construction with value and effect_name
- Immutability (frozen dataclass)
- Functor operations (map)
- Type safety verification
"""

from dataclasses import FrozenInstanceError

import pytest

from effectful.algebraic.effect_return import EffectReturn


class TestEffectReturnConstruction:
    """Test EffectReturn construction and immutability."""

    def test_effect_return_wraps_value_and_name(self) -> None:
        """EffectReturn should wrap both value and effect_name."""
        result = EffectReturn(42, "GetCount")
        assert result.value == 42
        assert result.effect_name == "GetCount"

    def test_effect_return_is_immutable(self) -> None:
        """EffectReturn should be frozen (immutable)."""
        result = EffectReturn(42, "GetCount")
        with pytest.raises(FrozenInstanceError):
            result.value = 100  # type: ignore[misc]

    def test_effect_return_effect_name_is_immutable(self) -> None:
        """EffectReturn.effect_name should be immutable."""
        result = EffectReturn(42, "GetCount")
        with pytest.raises(FrozenInstanceError):
            result.effect_name = "NewName"  # type: ignore[misc]


class TestEffectReturnMap:
    """Test EffectReturn functor operations."""

    def test_map_applies_function_to_value(self) -> None:
        """map() should apply function to the wrapped value."""
        result = EffectReturn(42, "GetCount")
        mapped = result.map(lambda x: x * 2)
        assert mapped.value == 84

    def test_map_preserves_effect_name(self) -> None:
        """map() should preserve the effect_name."""
        result = EffectReturn(42, "GetCount")
        mapped = result.map(lambda x: x * 2)
        assert mapped.effect_name == "GetCount"

    def test_map_changes_type(self) -> None:
        """map() can change the type of the wrapped value."""
        result = EffectReturn(42, "GetCount")
        mapped = result.map(str)
        assert mapped.value == "42"
        assert isinstance(mapped.value, str)

    def test_map_chains(self) -> None:
        """map() calls can be chained."""
        result = EffectReturn(42, "GetCount")
        mapped = result.map(lambda x: x * 2).map(lambda x: x + 10).map(str)
        assert mapped.value == "94"
        assert mapped.effect_name == "GetCount"


class TestEffectReturnWithDifferentTypes:
    """Test EffectReturn with various types."""

    def test_effect_return_with_none(self) -> None:
        """EffectReturn can wrap None."""
        result = EffectReturn(None, "SendText")
        assert result.value is None
        assert result.effect_name == "SendText"

    def test_effect_return_with_string(self) -> None:
        """EffectReturn can wrap strings."""
        result = EffectReturn("hello", "ReceiveText")
        assert result.value == "hello"
        assert result.effect_name == "ReceiveText"

    def test_effect_return_with_list(self) -> None:
        """EffectReturn can wrap lists."""
        result = EffectReturn([1, 2, 3], "GetItems")
        assert result.value == [1, 2, 3]
        assert result.effect_name == "GetItems"

    def test_effect_return_with_dict(self) -> None:
        """EffectReturn can wrap dictionaries."""
        result = EffectReturn({"key": "value"}, "GetConfig")
        assert result.value == {"key": "value"}
        assert result.effect_name == "GetConfig"


class TestEffectReturnEquality:
    """Test EffectReturn equality and hashing."""

    def test_equal_effect_returns_are_equal(self) -> None:
        """Two EffectReturns with same value and name should be equal."""
        result1 = EffectReturn(42, "GetCount")
        result2 = EffectReturn(42, "GetCount")
        assert result1 == result2

    def test_different_values_are_not_equal(self) -> None:
        """EffectReturns with different values should not be equal."""
        result1 = EffectReturn(42, "GetCount")
        result2 = EffectReturn(100, "GetCount")
        assert result1 != result2

    def test_different_names_are_not_equal(self) -> None:
        """EffectReturns with different names should not be equal."""
        result1 = EffectReturn(42, "GetCount")
        result2 = EffectReturn(42, "GetTotal")
        assert result1 != result2

    def test_effect_return_is_hashable(self) -> None:
        """EffectReturn should be hashable (frozen dataclass)."""
        result = EffectReturn(42, "GetCount")
        # Should not raise
        hash(result)
        # Can be used in sets
        result_set = {result}
        assert result in result_set
