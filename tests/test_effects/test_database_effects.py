"""Tests for Database effects.

Tests cover:
- Immutability (frozen dataclasses)
- Construction of each effect variant
- Type safety with UUIDs
"""

from dataclasses import FrozenInstanceError
from uuid import UUID, uuid4

import pytest

from effectful.effects.database import GetUserById, ListMessagesForUser, SaveChatMessage


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
            effect.user_id = uuid4()  # type: ignore[misc]

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
            effect.text = "Goodbye"  # type: ignore[misc]

    def test_save_chat_message_user_id_is_immutable(self) -> None:
        """SaveChatMessage user_id should be immutable."""
        effect = SaveChatMessage(uuid4(), "Hello")
        with pytest.raises(FrozenInstanceError):
            effect.user_id = uuid4()  # type: ignore[misc]


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
            effect.user_id = uuid4()  # type: ignore[misc]

    def test_list_messages_for_user_requires_uuid(self) -> None:
        """ListMessagesForUser user_id should be UUID type."""
        user_id = uuid4()
        effect = ListMessagesForUser(user_id)
        assert isinstance(effect.user_id, UUID)
