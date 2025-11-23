"""Tests for ChatMessage domain model."""

from dataclasses import FrozenInstanceError
from datetime import datetime
from uuid import uuid4

import pytest

from effectful.domain.message import ChatMessage


class TestChatMessage:
    """Test ChatMessage domain model."""

    def test_chat_message_creates_with_all_fields(self) -> None:
        """ChatMessage should be constructable with all fields."""
        msg_id = uuid4()
        user_id = uuid4()
        now = datetime.now()
        msg = ChatMessage(id=msg_id, user_id=user_id, text="Hello", created_at=now)
        assert msg.id == msg_id
        assert msg.user_id == user_id
        assert msg.text == "Hello"
        assert msg.created_at == now

    def test_chat_message_is_immutable(self) -> None:
        """ChatMessage should be frozen (immutable)."""
        msg = ChatMessage(id=uuid4(), user_id=uuid4(), text="Hello", created_at=datetime.now())
        with pytest.raises(FrozenInstanceError):
            setattr(msg, "text", "Goodbye")

    def test_chat_message_is_hashable(self) -> None:
        """ChatMessage should be hashable."""
        msg = ChatMessage(id=uuid4(), user_id=uuid4(), text="Hello", created_at=datetime.now())
        hash(msg)
        assert msg in {msg}
