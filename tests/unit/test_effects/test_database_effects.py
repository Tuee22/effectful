"""Tests for Database effects.

Tests cover:
- Immutability (frozen dataclasses)
- Construction of each effect variant
- Type safety with UUIDs
"""

from dataclasses import FrozenInstanceError
from uuid import UUID, uuid4

import pytest

from effectful.domain.optional_value import Absent, Provided
from effectful.effects.database import (
    CreateUser,
    DeleteUser,
    GetUserById,
    ListMessagesForUser,
    ListUsers,
    SaveChatMessage,
    UpdateUser,
)


class TestGetUserById:
    """Test GetUserById effect."""

    def test_get_user_by_id_creates_effect(self) -> None:
        """GetUserById should wrap user_id."""
        user_id = uuid4()
        effect = GetUserById(user_id)
        assert effect.user_id == user_id

    def test_get_user_by_id_is_immutable(self) -> None:
        """GetUserById should be frozen (immutable)."""
        effect = GetUserById(uuid4())
        with pytest.raises(FrozenInstanceError):
            setattr(effect, "user_id", uuid4())

    def test_get_user_by_id_requires_uuid(self) -> None:
        """GetUserById user_id should be UUID type."""
        user_id = uuid4()
        effect = GetUserById(user_id)
        assert isinstance(effect.user_id, UUID)


class TestSaveChatMessage:
    """Test SaveChatMessage effect."""

    def test_save_chat_message_creates_effect(self) -> None:
        """SaveChatMessage should wrap user_id and text."""
        user_id = uuid4()
        effect = SaveChatMessage(user_id, "Hello, World!")
        assert effect.user_id == user_id
        assert effect.text == "Hello, World!"

    def test_save_chat_message_is_immutable(self) -> None:
        """SaveChatMessage should be frozen (immutable)."""
        effect = SaveChatMessage(uuid4(), "Hello")
        with pytest.raises(FrozenInstanceError):
            setattr(effect, "text", "Goodbye")

    def test_save_chat_message_user_id_is_immutable(self) -> None:
        """SaveChatMessage user_id should be immutable."""
        effect = SaveChatMessage(uuid4(), "Hello")
        with pytest.raises(FrozenInstanceError):
            setattr(effect, "user_id", uuid4())


class TestListMessagesForUser:
    """Test ListMessagesForUser effect."""

    def test_list_messages_for_user_creates_effect(self) -> None:
        """ListMessagesForUser should wrap user_id."""
        user_id = uuid4()
        effect = ListMessagesForUser(user_id)
        assert effect.user_id == user_id

    def test_list_messages_for_user_is_immutable(self) -> None:
        """ListMessagesForUser should be frozen (immutable)."""
        effect = ListMessagesForUser(uuid4())
        with pytest.raises(FrozenInstanceError):
            setattr(effect, "user_id", uuid4())

    def test_list_messages_for_user_requires_uuid(self) -> None:
        """ListMessagesForUser user_id should be UUID type."""
        user_id = uuid4()
        effect = ListMessagesForUser(user_id)
        assert isinstance(effect.user_id, UUID)


class TestListUsers:
    """Test ListUsers effect."""

    def test_list_users_creates_effect(self) -> None:
        """ListUsers should wrap limit and offset."""
        effect = ListUsers(limit=50, offset=10)
        assert effect.limit == Provided(value=50)
        assert effect.offset == Provided(value=10)

    def test_list_users_has_default_values(self) -> None:
        """ListUsers should have default limit=None and offset=None."""
        effect = ListUsers()
        assert effect.limit == Absent()
        assert effect.offset == Absent()

    def test_list_users_is_immutable(self) -> None:
        """ListUsers should be frozen (immutable)."""
        effect = ListUsers()
        with pytest.raises(FrozenInstanceError):
            setattr(effect, "limit", 200)

    def test_list_users_offset_is_immutable(self) -> None:
        """ListUsers offset should be immutable."""
        effect = ListUsers()
        with pytest.raises(FrozenInstanceError):
            setattr(effect, "offset", 50)


class TestCreateUser:
    """Test CreateUser effect."""

    def test_create_user_creates_effect(self) -> None:
        """CreateUser should wrap email, name, and password_hash."""
        effect = CreateUser(email="alice@example.com", name="Alice", password_hash="$2b$12$hash")
        assert effect.email == "alice@example.com"
        assert effect.name == "Alice"
        assert effect.password_hash == "$2b$12$hash"

    def test_create_user_is_immutable(self) -> None:
        """CreateUser should be frozen (immutable)."""
        effect = CreateUser(email="alice@example.com", name="Alice", password_hash="$2b$12$hash")
        with pytest.raises(FrozenInstanceError):
            setattr(effect, "email", "bob@example.com")

    def test_create_user_name_is_immutable(self) -> None:
        """CreateUser name should be immutable."""
        effect = CreateUser(email="alice@example.com", name="Alice", password_hash="$2b$12$hash")
        with pytest.raises(FrozenInstanceError):
            setattr(effect, "name", "Bob")

    def test_create_user_password_hash_is_immutable(self) -> None:
        """CreateUser password_hash should be immutable."""
        effect = CreateUser(email="alice@example.com", name="Alice", password_hash="$2b$12$hash")
        with pytest.raises(FrozenInstanceError):
            setattr(effect, "password_hash", "$2b$12$newhash")


class TestUpdateUser:
    """Test UpdateUser effect."""

    def test_update_user_creates_effect(self) -> None:
        """UpdateUser should wrap user_id, email, and name."""
        user_id = uuid4()
        effect = UpdateUser(user_id=user_id, email="new@example.com", name="New Name")
        assert effect.user_id == user_id
        assert effect.email == Provided(value="new@example.com")
        assert effect.name == Provided(value="New Name")

    def test_update_user_optional_fields(self) -> None:
        """UpdateUser should allow optional email and name."""
        user_id = uuid4()
        effect = UpdateUser(user_id=user_id)
        assert effect.user_id == user_id
        assert effect.email == Absent()
        assert effect.name == Absent()

    def test_update_user_is_immutable(self) -> None:
        """UpdateUser should be frozen (immutable)."""
        user_id = uuid4()
        effect = UpdateUser(user_id=user_id, name="Alice")
        with pytest.raises(FrozenInstanceError):
            setattr(effect, "name", "Bob")

    def test_update_user_user_id_requires_uuid(self) -> None:
        """UpdateUser user_id should be UUID type."""
        user_id = uuid4()
        effect = UpdateUser(user_id=user_id)
        assert isinstance(effect.user_id, UUID)


class TestDeleteUser:
    """Test DeleteUser effect."""

    def test_delete_user_creates_effect(self) -> None:
        """DeleteUser should wrap user_id."""
        user_id = uuid4()
        effect = DeleteUser(user_id=user_id)
        assert effect.user_id == user_id

    def test_delete_user_is_immutable(self) -> None:
        """DeleteUser should be frozen (immutable)."""
        effect = DeleteUser(user_id=uuid4())
        with pytest.raises(FrozenInstanceError):
            setattr(effect, "user_id", uuid4())

    def test_delete_user_requires_uuid(self) -> None:
        """DeleteUser user_id should be UUID type."""
        user_id = uuid4()
        effect = DeleteUser(user_id=user_id)
        assert isinstance(effect.user_id, UUID)
