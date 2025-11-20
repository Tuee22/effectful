"""Tests for chat program workflows (all 6 infrastructure types) using pytest-mock.

All tests use pytest-mock (mocker.AsyncMock) instead of fakes.
Tests verify the complex workflow using all 6 infrastructure types.
"""

from uuid import uuid4

import pytest
from pytest_mock import MockerFixture

from demo.domain.errors import AppError, AuthError
from demo.domain.responses import MessageResponse
from demo.programs.chat_programs import send_authenticated_message_with_storage_program
from effectful.algebraic.result import Err, Ok
from effectful.domain.token_result import TokenInvalid, TokenValid
from effectful.domain.user import User
from effectful.effects.auth import ValidateToken
from effectful.effects.cache import GetCachedValue, PutCachedValue
from effectful.effects.database import GetUserById
from effectful.effects.messaging import PublishMessage
from effectful.effects.storage import PutObject
from effectful.effects.websocket import SendText


class TestSendAuthenticatedMessageWithStorageProgram:
    """Test suite for send_authenticated_message_with_storage_program (all 6 infra types)."""

    def test_send_authenticated_message_success(self, mocker: MockerFixture) -> None:
        """Test successful message send using all 6 infrastructure types."""
        # Setup
        user_id = uuid4()
        token_valid = TokenValid(user_id=user_id, claims={"email": "alice@example.com"})
        user = User(id=user_id, email="alice@example.com", name="Alice")
        message_text = "Hello from all 6 infrastructure types!"

        # Mock the program execution
        gen = send_authenticated_message_with_storage_program(
            token="valid_token_123", text=message_text
        )

        # Step 1: [Auth] ValidateToken
        effect1 = next(gen)
        assert isinstance(effect1, ValidateToken)
        assert effect1.token == "valid_token_123"
        result1 = gen.send(token_valid)

        # Step 2: [Cache] GetCachedValue (cache miss)
        effect2 = result1
        assert isinstance(effect2, GetCachedValue)
        assert f"user:{user_id}" in effect2.key
        result2 = gen.send(None)  # Cache miss

        # Step 3: [Database] GetUserById
        effect3 = result2
        assert isinstance(effect3, GetUserById)
        assert effect3.user_id == user_id
        result3 = gen.send(user)

        # Step 4: [Cache] PutCachedValue
        effect4 = result3
        assert isinstance(effect4, PutCachedValue)
        assert f"user:{user_id}" in effect4.key
        assert effect4.ttl_seconds == 300
        result4 = gen.send(True)

        # Step 5: [Storage] PutObject to S3
        effect5 = result4
        assert isinstance(effect5, PutObject)
        assert effect5.bucket == "chat-archive"
        assert b"Hello from all 6 infrastructure types!" in effect5.content
        # PutObject returns the key as a string
        result5 = gen.send(effect5.key)

        # Step 6: [Messaging] PublishMessage to Pulsar
        effect6 = result5
        assert isinstance(effect6, PublishMessage)
        assert effect6.topic == "chat-messages"
        assert b"Hello from all 6 infrastructure types!" in effect6.payload
        result6 = gen.send("pulsar_message_id_123")

        # Step 7: [WebSocket] SendText
        effect7 = result6
        assert isinstance(effect7, SendText)
        assert "Message sent:" in effect7.text

        try:
            gen.send(None)
            pytest.fail("Expected StopIteration")
        except StopIteration as e:
            result = e.value

        # Assert
        assert isinstance(result, Ok)
        assert isinstance(result.value, MessageResponse)
        assert result.value.user_id == user_id
        assert result.value.text == message_text

    def test_send_authenticated_message_invalid_token(
        self, mocker: MockerFixture
    ) -> None:
        """Test send fails with invalid token."""
        # Setup
        token_invalid = TokenInvalid(token="bad_token", reason="malformed")

        # Mock the program execution
        gen = send_authenticated_message_with_storage_program(
            token="bad_token", text="Hello"
        )

        # Step 1: ValidateToken returns TokenInvalid
        effect1 = next(gen)

        try:
            gen.send(token_invalid)
            pytest.fail("Expected StopIteration")
        except StopIteration as e:
            result = e.value

        # Assert
        assert isinstance(result, Err)
        assert isinstance(result.error, AuthError)
        assert result.error.error_type == "token_invalid"

    def test_send_authenticated_message_user_not_found(
        self, mocker: MockerFixture
    ) -> None:
        """Test send fails when user doesn't exist."""
        # Setup
        user_id = uuid4()
        token_valid = TokenValid(user_id=user_id, claims={"email": "alice@example.com"})

        # Mock the program execution
        gen = send_authenticated_message_with_storage_program(
            token="valid_token_123", text="Hello"
        )

        # Step 1: ValidateToken
        effect1 = next(gen)
        result1 = gen.send(token_valid)

        # Step 2: GetCachedValue
        effect2 = result1
        result2 = gen.send(None)

        # Step 3: GetUserById returns None
        effect3 = result2

        try:
            gen.send(None)
            pytest.fail("Expected StopIteration")
        except StopIteration as e:
            result = e.value

        # Assert
        assert isinstance(result, Err)
        assert isinstance(result.error, AppError)
        assert result.error.error_type == "not_found"

    def test_send_authenticated_message_empty_text(self, mocker: MockerFixture) -> None:
        """Test send fails with empty message text."""
        # Setup
        user_id = uuid4()
        token_valid = TokenValid(user_id=user_id, claims={"email": "alice@example.com"})
        user = User(id=user_id, email="alice@example.com", name="Alice")

        # Mock the program execution
        gen = send_authenticated_message_with_storage_program(
            token="valid_token_123", text=""
        )

        # Step 1: ValidateToken
        effect1 = next(gen)
        result1 = gen.send(token_valid)

        # Step 2: GetCachedValue
        effect2 = result1
        result2 = gen.send(None)

        # Step 3: GetUserById
        effect3 = result2
        result3 = gen.send(user)

        # Step 4: PutCachedValue
        effect4 = result3

        try:
            gen.send(True)
            pytest.fail("Expected StopIteration")
        except StopIteration as e:
            result = e.value

        # Assert
        assert isinstance(result, Err)
        assert isinstance(result.error, AppError)
        assert result.error.error_type == "validation_error"
        assert "empty" in result.error.message.lower()

    def test_send_authenticated_message_text_too_long(
        self, mocker: MockerFixture
    ) -> None:
        """Test send fails when message text exceeds max length."""
        # Setup
        user_id = uuid4()
        token_valid = TokenValid(user_id=user_id, claims={"email": "alice@example.com"})
        user = User(id=user_id, email="alice@example.com", name="Alice")
        long_text = "x" * 10001  # Exceeds 10000 character limit

        # Mock the program execution
        gen = send_authenticated_message_with_storage_program(
            token="valid_token_123", text=long_text
        )

        # Step 1: ValidateToken
        effect1 = next(gen)
        result1 = gen.send(token_valid)

        # Step 2: GetCachedValue
        effect2 = result1
        result2 = gen.send(None)

        # Step 3: GetUserById
        effect3 = result2
        result3 = gen.send(user)

        # Step 4: PutCachedValue
        effect4 = result3

        try:
            gen.send(True)
            pytest.fail("Expected StopIteration")
        except StopIteration as e:
            result = e.value

        # Assert
        assert isinstance(result, Err)
        assert isinstance(result.error, AppError)
        assert result.error.error_type == "validation_error"
        assert "10000" in result.error.message
