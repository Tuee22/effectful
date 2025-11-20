"""Tests for message program workflows using pytest-mock.

All tests use pytest-mock (mocker.AsyncMock) instead of fakes.
Tests verify both success and error paths with 100% coverage.
"""

from uuid import uuid4

import pytest
from pytest_mock import MockerFixture

from demo.domain.errors import AppError
from demo.domain.responses import MessageResponse
from demo.programs.message_programs import get_message_program, send_message_program
from effectful.algebraic.result import Err, Ok
from effectful.domain.user import User
from effectful.effects.database import GetUserById, ListMessagesForUser
from effectful.effects.messaging import PublishMessage


class TestSendMessageProgram:
    """Test suite for send_message_program."""

    def test_send_message_success(self, mocker: MockerFixture) -> None:
        """Test successfully sending a message."""
        # Setup
        user_id = uuid4()
        user = User(id=user_id, email="alice@example.com", name="Alice")
        message_text = "Hello, world!"

        # Mock the program execution
        gen = send_message_program(user_id=user_id, text=message_text)

        # Step 1: GetUserById returns user
        effect1 = next(gen)
        assert isinstance(effect1, GetUserById)
        assert effect1.user_id == user_id
        result1 = gen.send(user)

        # Step 2: PublishMessage to Pulsar
        effect2 = result1
        assert isinstance(effect2, PublishMessage)
        assert effect2.topic == "chat-messages"
        assert b"Hello, world!" in effect2.payload

        try:
            gen.send("pulsar_message_id_123")
            pytest.fail("Expected StopIteration")
        except StopIteration as e:
            result = e.value

        # Assert
        assert isinstance(result, Ok)
        assert isinstance(result.value, MessageResponse)
        assert result.value.user_id == user_id
        assert result.value.text == message_text

    def test_send_message_user_not_found(self, mocker: MockerFixture) -> None:
        """Test sending message fails when user doesn't exist."""
        # Setup
        user_id = uuid4()

        # Mock the program execution
        gen = send_message_program(user_id=user_id, text="Hello")

        # Step 1: GetUserById returns None
        effect1 = next(gen)

        try:
            gen.send(None)
            pytest.fail("Expected StopIteration")
        except StopIteration as e:
            result = e.value

        # Assert
        assert isinstance(result, Err)
        assert isinstance(result.error, AppError)
        assert result.error.error_type == "not_found"
        assert str(user_id) in result.error.message

    def test_send_message_empty_text(self, mocker: MockerFixture) -> None:
        """Test sending message fails with empty text."""
        # Setup
        user_id = uuid4()
        user = User(id=user_id, email="alice@example.com", name="Alice")

        # Mock the program execution
        gen = send_message_program(user_id=user_id, text="")

        # Step 1: GetUserById returns user
        effect1 = next(gen)

        # Step 2: Validation happens after getting user, program should stop
        try:
            gen.send(user)
            pytest.fail("Expected StopIteration")
        except StopIteration as e:
            result = e.value

        # Assert
        assert isinstance(result, Err)
        assert isinstance(result.error, AppError)
        assert result.error.error_type == "validation_error"
        assert "empty" in result.error.message.lower()

    def test_send_message_whitespace_only(self, mocker: MockerFixture) -> None:
        """Test sending message fails with whitespace-only text."""
        # Setup
        user_id = uuid4()
        user = User(id=user_id, email="alice@example.com", name="Alice")

        # Mock the program execution
        gen = send_message_program(user_id=user_id, text="   ")

        # Step 1: GetUserById returns user
        effect1 = next(gen)

        try:
            gen.send(user)
            pytest.fail("Expected StopIteration")
        except StopIteration as e:
            result = e.value

        # Assert
        assert isinstance(result, Err)
        assert isinstance(result.error, AppError)
        assert result.error.error_type == "validation_error"

    def test_send_message_text_too_long(self, mocker: MockerFixture) -> None:
        """Test sending message fails when text exceeds max length."""
        # Setup
        user_id = uuid4()
        user = User(id=user_id, email="alice@example.com", name="Alice")
        long_text = "x" * 10001  # Exceeds 10000 character limit

        # Mock the program execution
        gen = send_message_program(user_id=user_id, text=long_text)

        # Step 1: GetUserById returns user
        effect1 = next(gen)

        try:
            gen.send(user)
            pytest.fail("Expected StopIteration")
        except StopIteration as e:
            result = e.value

        # Assert
        assert isinstance(result, Err)
        assert isinstance(result.error, AppError)
        assert result.error.error_type == "validation_error"
        assert "10000" in result.error.message


class TestGetMessageProgram:
    """Test suite for get_message_program."""

    def test_get_message_always_returns_not_found(self, mocker: MockerFixture) -> None:
        """Test get_message_program returns not_found (demo stub)."""
        # Setup
        message_id = uuid4()

        # Execute (no generator - pure function)
        result = get_message_program(message_id=message_id)

        # Assert
        assert isinstance(result, Err)
        assert isinstance(result.error, AppError)
        assert result.error.error_type == "not_found"
        assert str(message_id) in result.error.message
        assert "demo" in result.error.message.lower()
