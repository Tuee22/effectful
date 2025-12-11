"""Tests for User domain model.

Tests cover:
- Immutability (frozen dataclass)
- Construction
- Type safety
"""

from dataclasses import FrozenInstanceError
from uuid import uuid4

import pytest

from effectful.domain.user import User


class TestUser:
    """Test User domain model."""

    def test_user_creates_with_all_fields(self) -> None:
        """User should be constructable with id, name, email."""
        user_id = uuid4()
        user = User(id=user_id, name="Alice", email="alice@example.com")
        assert user.id == user_id
        assert user.name == "Alice"
        assert user.email == "alice@example.com"

    @pytest.mark.parametrize(
        ("field", "new_value"),
        [
            ("name", "Bob"),
            ("id", uuid4()),
            ("email", "bob@example.com"),
        ],
    )
    def test_user_fields_are_immutable(self, field: str, new_value: object) -> None:
        """User should be frozen (immutable)."""
        user = User(id=uuid4(), name="Alice", email="alice@example.com")
        with pytest.raises(FrozenInstanceError):
            setattr(user, field, new_value)

    def test_user_equality(self) -> None:
        """Users with same values should be equal."""
        user_id = uuid4()
        user1 = User(id=user_id, name="Alice", email="alice@example.com")
        user2 = User(id=user_id, name="Alice", email="alice@example.com")
        assert user1 == user2

    def test_user_is_hashable(self) -> None:
        """User should be hashable (frozen dataclass)."""
        user = User(id=uuid4(), name="Alice", email="alice@example.com")
        # Should not raise
        hash(user)
        # Can be used in sets
        user_set = {user}
        assert user in user_set
