"""Tests for Domain errors."""

from dataclasses import FrozenInstanceError
from uuid import uuid4

import pytest

from effectful.domain.errors import InvalidMessageError, UserNotFoundError


class TestUserNotFoundError:
    """Test UserNotFoundError."""

    def test_user_not_found_error_wraps_user_id(self) -> None:
        """UserNotFoundError should wrap user_id."""
        user_id = uuid4()
        error = UserNotFoundError(user_id=user_id)
        assert error.user_id == user_id

    def test_user_not_found_error_is_immutable(self) -> None:
        """UserNotFoundError should be frozen."""
        error = UserNotFoundError(user_id=uuid4())
        with pytest.raises(FrozenInstanceError):
            error.user_id = uuid4()  # type: ignore[misc]


class TestInvalidMessageError:
    """Test InvalidMessageError."""

    def test_invalid_message_error_wraps_text_and_reason(self) -> None:
        """InvalidMessageError should wrap text and reason."""
        error = InvalidMessageError(text="", reason="empty message")
        assert error.text == ""
        assert error.reason == "empty message"

    def test_invalid_message_error_is_immutable(self) -> None:
        """InvalidMessageError should be frozen."""
        error = InvalidMessageError(text="", reason="empty")
        with pytest.raises(FrozenInstanceError):
            error.reason = "other"  # type: ignore[misc]
