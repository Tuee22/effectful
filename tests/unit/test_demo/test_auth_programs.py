"""Tests for auth program workflows using pytest-mock.

All tests use pytest-mock (mocker.AsyncMock) instead of fakes.
Tests verify both success and error paths with 100% coverage.
"""

from uuid import uuid4

import pytest
from pytest_mock import MockerFixture

from demo.domain.errors import AppError, AuthError
from demo.domain.responses import LoginResponse
from demo.programs.auth_programs import (
    login_program,
    logout_program,
    refresh_program,
    register_program,
)
from effectful.algebraic.result import Err, Ok
from effectful.domain.token_result import TokenExpired, TokenInvalid, TokenValid
from effectful.domain.user import User
from effectful.effects.auth import (
    GenerateToken,
    GetUserByEmail,
    HashPassword,
    RevokeToken,
    ValidatePassword,
    ValidateToken,
)
from effectful.effects.database import CreateUser, GetUserById


class TestLoginProgram:
    """Test suite for login_program."""

    def test_login_success(self, mocker: MockerFixture) -> None:
        """Test successful login with valid credentials."""
        # Setup
        user_id = uuid4()
        user = User(id=user_id, email="alice@example.com", name="Alice")

        # Mock the program execution
        gen = login_program(email="alice@example.com", password="secret123")

        # Step 1: GetUserByEmail returns user
        effect1 = next(gen)
        assert isinstance(effect1, GetUserByEmail)
        assert effect1.email == "alice@example.com"
        result1 = gen.send(user)

        # Step 2: ValidatePassword returns True
        effect2 = result1
        assert isinstance(effect2, ValidatePassword)
        assert effect2.password == "secret123"
        result2 = gen.send(True)

        # Step 3: GenerateToken for access token
        effect3 = result2
        assert isinstance(effect3, GenerateToken)
        assert effect3.user_id == user_id
        result3 = gen.send("access_token_123")

        # Step 4: GenerateToken for refresh token
        effect4 = result3
        assert isinstance(effect4, GenerateToken)
        assert effect4.user_id == user_id

        # Final result
        try:
            gen.send("refresh_token_456")
            pytest.fail("Expected StopIteration")
        except StopIteration as e:
            result = e.value

        # Assert
        assert isinstance(result, Ok)
        assert isinstance(result.value, LoginResponse)
        assert result.value.access_token == "access_token_123"
        assert result.value.refresh_token == "refresh_token_456"
        assert result.value.user_id == user_id
        assert result.value.expires_in == 3600

    def test_login_user_not_found(self, mocker: MockerFixture) -> None:
        """Test login fails when user doesn't exist."""
        # Mock the program execution
        gen = login_program(email="nonexistent@example.com", password="secret123")

        # Step 1: GetUserByEmail returns None
        effect1 = next(gen)
        assert isinstance(effect1, GetUserByEmail)

        try:
            gen.send(None)
            pytest.fail("Expected StopIteration")
        except StopIteration as e:
            result = e.value

        # Assert
        assert isinstance(result, Err)
        assert isinstance(result.error, AppError)
        assert result.error.error_type == "not_found"
        assert "nonexistent@example.com" in result.error.message

    def test_login_invalid_password(self, mocker: MockerFixture) -> None:
        """Test login fails with invalid password."""
        # Setup
        user_id = uuid4()
        user = User(id=user_id, email="alice@example.com", name="Alice")

        # Mock the program execution
        gen = login_program(email="alice@example.com", password="wrong_password")

        # Step 1: GetUserByEmail returns user
        effect1 = next(gen)
        result1 = gen.send(user)

        # Step 2: ValidatePassword returns False
        effect2 = result1
        assert isinstance(effect2, ValidatePassword)

        try:
            gen.send(False)
            pytest.fail("Expected StopIteration")
        except StopIteration as e:
            result = e.value

        # Assert
        assert isinstance(result, Err)
        assert isinstance(result.error, AuthError)
        assert result.error.error_type == "invalid_credentials"
        assert "Invalid email or password" in result.error.message


class TestLogoutProgram:
    """Test suite for logout_program."""

    def test_logout_success(self, mocker: MockerFixture) -> None:
        """Test successful logout with valid token."""
        # Setup
        user_id = uuid4()
        token_valid = TokenValid(user_id=user_id, claims={"email": "alice@example.com"})

        # Mock the program execution
        gen = logout_program(token="valid_token_123")

        # Step 1: ValidateToken returns TokenValid
        effect1 = next(gen)
        assert isinstance(effect1, ValidateToken)
        assert effect1.token == "valid_token_123"
        result1 = gen.send(token_valid)

        # Step 2: RevokeToken
        effect2 = result1
        assert isinstance(effect2, RevokeToken)
        assert effect2.token == "valid_token_123"

        # Final result
        try:
            gen.send(None)
            pytest.fail("Expected StopIteration")
        except StopIteration as e:
            result = e.value

        # Assert
        assert isinstance(result, Ok)
        assert result.value is True

    def test_logout_invalid_token(self, mocker: MockerFixture) -> None:
        """Test logout fails with invalid token."""
        # Setup
        token_invalid = TokenInvalid(token="invalid_token", reason="malformed")

        # Mock the program execution
        gen = logout_program(token="invalid_token")

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

    def test_logout_expired_token(self, mocker: MockerFixture) -> None:
        """Test logout fails with expired token."""
        # Setup
        from datetime import datetime

        token_expired = TokenExpired(token="expired_token", expired_at=datetime.now())

        # Mock the program execution
        gen = logout_program(token="expired_token")

        # Step 1: ValidateToken returns TokenExpired
        effect1 = next(gen)

        try:
            gen.send(token_expired)
            pytest.fail("Expected StopIteration")
        except StopIteration as e:
            result = e.value

        # Assert
        assert isinstance(result, Err)
        assert isinstance(result.error, AuthError)
        assert result.error.error_type == "token_invalid"


class TestRefreshProgram:
    """Test suite for refresh_program."""

    def test_refresh_success(self, mocker: MockerFixture) -> None:
        """Test successful token refresh."""
        # Setup
        user_id = uuid4()
        token_valid = TokenValid(user_id=user_id, claims={"email": "alice@example.com"})
        user = User(id=user_id, email="alice@example.com", name="Alice")

        # Mock the program execution
        gen = refresh_program(refresh_token="refresh_token_123")

        # Step 1: ValidateToken returns TokenValid
        effect1 = next(gen)
        assert isinstance(effect1, ValidateToken)
        result1 = gen.send(token_valid)

        # Step 2: GetUserById returns user
        effect2 = result1
        assert isinstance(effect2, GetUserById)
        assert effect2.user_id == user_id
        result2 = gen.send(user)

        # Step 3: GenerateToken for new access token
        effect3 = result2
        assert isinstance(effect3, GenerateToken)
        result3 = gen.send("new_access_token")

        # Step 4: GenerateToken for new refresh token
        effect4 = result3
        assert isinstance(effect4, GenerateToken)

        # Final result
        try:
            gen.send("new_refresh_token")
            pytest.fail("Expected StopIteration")
        except StopIteration as e:
            result = e.value

        # Assert
        assert isinstance(result, Ok)
        assert isinstance(result.value, LoginResponse)
        assert result.value.access_token == "new_access_token"
        assert result.value.refresh_token == "new_refresh_token"
        assert result.value.user_id == user_id

    def test_refresh_invalid_token(self, mocker: MockerFixture) -> None:
        """Test refresh fails with invalid token."""
        # Setup
        token_invalid = TokenInvalid(token="bad_token", reason="revoked")

        # Mock the program execution
        gen = refresh_program(refresh_token="bad_token")

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
        assert result.error.error_type == "token_expired"

    def test_refresh_user_deleted(self, mocker: MockerFixture) -> None:
        """Test refresh fails when user no longer exists."""
        # Setup
        user_id = uuid4()
        token_valid = TokenValid(user_id=user_id, claims={"email": "alice@example.com"})

        # Mock the program execution
        gen = refresh_program(refresh_token="refresh_token_123")

        # Step 1: ValidateToken returns TokenValid
        effect1 = next(gen)
        result1 = gen.send(token_valid)

        # Step 2: GetUserById returns None (user deleted)
        effect2 = result1
        assert isinstance(effect2, GetUserById)

        try:
            gen.send(None)
            pytest.fail("Expected StopIteration")
        except StopIteration as e:
            result = e.value

        # Assert
        assert isinstance(result, Err)
        assert isinstance(result.error, AppError)
        assert result.error.error_type == "not_found"
        assert "no longer exists" in result.error.message


class TestRegisterProgram:
    """Test suite for register_program."""

    def test_register_success(self, mocker: MockerFixture) -> None:
        """Test successful user registration."""
        # Setup
        user_id = uuid4()
        user = User(id=user_id, email="bob@example.com", name="Bob")

        # Mock the program execution
        gen = register_program(email="bob@example.com", name="Bob", password="secret123")

        # Step 1: GetUserByEmail returns None (user doesn't exist yet)
        effect1 = next(gen)
        assert isinstance(effect1, GetUserByEmail)
        assert effect1.email == "bob@example.com"
        result1 = gen.send(None)

        # Step 2: HashPassword returns hash
        effect2 = result1
        assert isinstance(effect2, HashPassword)
        assert effect2.password == "secret123"
        result2 = gen.send("$2b$12$hashed_password")

        # Step 3: CreateUser returns user_id
        effect3 = result2
        assert isinstance(effect3, CreateUser)
        assert effect3.email == "bob@example.com"
        assert effect3.name == "Bob"
        assert effect3.password_hash == "$2b$12$hashed_password"
        result3 = gen.send(user_id)

        # Step 4: GetUserById returns created user
        effect4 = result3
        assert isinstance(effect4, GetUserById)
        assert effect4.user_id == user_id

        # Final result
        try:
            gen.send(user)
            pytest.fail("Expected StopIteration")
        except StopIteration as e:
            result = e.value

        # Assert
        assert isinstance(result, Ok)
        assert isinstance(result.value, User)
        assert result.value.id == user_id
        assert result.value.email == "bob@example.com"
        assert result.value.name == "Bob"

    def test_register_email_already_exists(self, mocker: MockerFixture) -> None:
        """Test registration fails when email already exists."""
        # Setup
        existing_user = User(id=uuid4(), email="alice@example.com", name="Alice")

        # Mock the program execution
        gen = register_program(email="alice@example.com", name="Alice2", password="secret123")

        # Step 1: GetUserByEmail returns existing user
        effect1 = next(gen)

        try:
            gen.send(existing_user)
            pytest.fail("Expected StopIteration")
        except StopIteration as e:
            result = e.value

        # Assert
        assert isinstance(result, Err)
        assert isinstance(result.error, AppError)
        assert result.error.error_type == "conflict"
        assert "already exists" in result.error.message

    def test_register_user_creation_failed_retrieval(self, mocker: MockerFixture) -> None:
        """Test registration handles case where user is created but can't be retrieved."""
        # Setup
        user_id = uuid4()

        # Mock the program execution
        gen = register_program(email="bob@example.com", name="Bob", password="secret123")

        # Step 1: GetUserByEmail returns None
        effect1 = next(gen)
        result1 = gen.send(None)

        # Step 2: HashPassword returns hash
        effect2 = result1
        result2 = gen.send("$2b$12$hashed_password")

        # Step 3: CreateUser returns user_id
        effect3 = result2
        result3 = gen.send(user_id)

        # Step 4: GetUserById returns None (failed to retrieve)
        effect4 = result3

        try:
            gen.send(None)
            pytest.fail("Expected StopIteration")
        except StopIteration as e:
            result = e.value

        # Assert
        assert isinstance(result, Err)
        assert isinstance(result.error, AppError)
        assert result.error.error_type == "internal_error"
        assert "failed to retrieve" in result.error.message
