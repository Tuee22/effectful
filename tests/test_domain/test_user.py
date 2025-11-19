"""Tests for User domain model.

Tests cover:
- Immutability (frozen dataclass)
- Construction
- Type safety
"""

from dataclasses import FrozenInstanceError
from uuid import uuid4

import pytest

from functional_effects.domain.user import User


class TestUser:
    """Test User domain model."""

    def test_user_creates_with_all_fields(self) -> None:
        """User should be constructable with id, name, email."""
        user_id = uuid4()
        user = User(id=user_id, name="Alice", email="alice@example.com")
        assert user.id == user_id
        assert user.name == "Alice"
        assert user.email == "alice@example.com"

    def test_user_is_immutable(self) -> None:
        """User should be frozen (immutable)."""
        user = User(id=uuid4(), name="Alice", email="alice@example.com")
        with pytest.raises(FrozenInstanceError):
            user.name = "Bob"  # type: ignore[misc]

    def test_user_id_is_immutable(self) -> None:
        """User id should be immutable."""
        user = User(id=uuid4(), name="Alice", email="alice@example.com")
        with pytest.raises(FrozenInstanceError):
            user.id = uuid4()  # type: ignore[misc]

    def test_user_email_is_immutable(self) -> None:
        """User email should be immutable."""
        user = User(id=uuid4(), name="Alice", email="alice@example.com")
        with pytest.raises(FrozenInstanceError):
            user.email = "bob@example.com"  # type: ignore[misc]

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
