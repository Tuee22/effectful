"""Tests for AuthInterpreter.

Tests cover all auth effect handling with both success and error paths.
Uses pytest-mock for type-safe mocking with spec=.
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pytest_mock import MockerFixture

from effectful.algebraic.result import Err, Ok
from effectful.domain.token_result import (
    TokenExpired,
    TokenInvalid,
    TokenRefreshRejected,
    TokenRefreshed,
    TokenValid,
)
from effectful.effects.auth import (
    GenerateToken,
    GetUserByEmail,
    HashPassword,
    RefreshToken,
    RevokeToken,
    ValidatePassword,
    ValidateToken,
)
from effectful.domain.user import User, UserFound, UserNotFound
from effectful.effects.websocket import SendText
from effectful.infrastructure.auth import AuthService
from effectful.interpreters.auth import AuthInterpreter
from effectful.interpreters.errors import AuthError, UnhandledEffectError


class TestValidateToken:
    """Tests for ValidateToken effect handling."""

    @pytest.mark.asyncio
    async def test_returns_token_valid(self, mocker: MockerFixture) -> None:
        """ValidateToken returns TokenValid when token is valid."""
        # Setup
        user_id = uuid4()
        claims = {"role": "admin"}
        expected = TokenValid(user_id=user_id, claims=claims)

        mock_auth = mocker.AsyncMock(spec=AuthService)
        mock_auth.validate_token.return_value = expected

        interpreter = AuthInterpreter(auth_service=mock_auth)
        effect = ValidateToken(token="valid.jwt.token")

        # Act
        result = await interpreter.interpret(effect)

        # Assert
        match result:
            case Ok(effect_return):
                assert effect_return.value == expected
                assert effect_return.effect_name == "ValidateToken"
            case Err(error):
                pytest.fail(f"Expected Ok, got Err({error})")

        mock_auth.validate_token.assert_called_once_with("valid.jwt.token")

    @pytest.mark.asyncio
    async def test_returns_token_expired(self, mocker: MockerFixture) -> None:
        """ValidateToken returns TokenExpired when token has expired."""
        # Setup
        expired_at = datetime.now(UTC)
        expected = TokenExpired(token="expired.jwt.token", expired_at=expired_at)

        mock_auth = mocker.AsyncMock(spec=AuthService)
        mock_auth.validate_token.return_value = expected

        interpreter = AuthInterpreter(auth_service=mock_auth)
        effect = ValidateToken(token="expired.jwt.token")

        # Act
        result = await interpreter.interpret(effect)

        # Assert
        match result:
            case Ok(effect_return):
                assert effect_return.value == expected
            case Err(error):
                pytest.fail(f"Expected Ok, got Err({error})")

    @pytest.mark.asyncio
    async def test_returns_token_invalid(self, mocker: MockerFixture) -> None:
        """ValidateToken returns TokenInvalid when token is malformed."""
        # Setup
        expected = TokenInvalid(token="bad.token", reason="malformed")

        mock_auth = mocker.AsyncMock(spec=AuthService)
        mock_auth.validate_token.return_value = expected

        interpreter = AuthInterpreter(auth_service=mock_auth)
        effect = ValidateToken(token="bad.token")

        # Act
        result = await interpreter.interpret(effect)

        # Assert
        match result:
            case Ok(effect_return):
                assert effect_return.value == expected
            case Err(error):
                pytest.fail(f"Expected Ok, got Err({error})")

    @pytest.mark.asyncio
    async def test_returns_auth_error_on_exception(self, mocker: MockerFixture) -> None:
        """ValidateToken returns AuthError when service raises exception."""
        # Setup
        mock_auth = mocker.AsyncMock(spec=AuthService)
        mock_auth.validate_token.side_effect = ConnectionError("Redis connection failed")

        interpreter = AuthInterpreter(auth_service=mock_auth)
        effect = ValidateToken(token="any.token")

        # Act
        result = await interpreter.interpret(effect)

        # Assert
        match result:
            case Err(AuthError(auth_error=error_msg, is_retryable=retryable)):
                assert "Redis connection failed" in error_msg
                assert retryable is True
            case Ok(value):
                pytest.fail(f"Expected Err, got Ok({value})")
            case _:
                pytest.fail("Unexpected error type")


class TestGenerateToken:
    """Tests for GenerateToken effect handling."""

    @pytest.mark.asyncio
    async def test_returns_token_string(self, mocker: MockerFixture) -> None:
        """GenerateToken returns JWT token string on success."""
        # Setup
        user_id = uuid4()
        claims = {"role": "user"}
        expected_token = "generated.jwt.token"

        mock_auth = mocker.AsyncMock(spec=AuthService)
        mock_auth.generate_token.return_value = expected_token

        interpreter = AuthInterpreter(auth_service=mock_auth)
        effect = GenerateToken(user_id=user_id, claims=claims, ttl_seconds=3600)

        # Act
        result = await interpreter.interpret(effect)

        # Assert
        match result:
            case Ok(effect_return):
                assert effect_return.value == expected_token
                assert effect_return.effect_name == "GenerateToken"
            case Err(error):
                pytest.fail(f"Expected Ok, got Err({error})")

        mock_auth.generate_token.assert_called_once_with(user_id, claims, 3600)

    @pytest.mark.asyncio
    async def test_returns_auth_error_on_exception(self, mocker: MockerFixture) -> None:
        """GenerateToken returns AuthError when service raises exception."""
        # Setup
        user_id = uuid4()

        mock_auth = mocker.AsyncMock(spec=AuthService)
        mock_auth.generate_token.side_effect = RuntimeError("Encoding error")

        interpreter = AuthInterpreter(auth_service=mock_auth)
        effect = GenerateToken(user_id=user_id, claims={}, ttl_seconds=3600)

        # Act
        result = await interpreter.interpret(effect)

        # Assert
        match result:
            case Err(AuthError(auth_error=error_msg, is_retryable=retryable)):
                assert "Encoding error" in error_msg
                assert retryable is False  # encoding errors are not retryable
            case Ok(value):
                pytest.fail(f"Expected Err, got Ok({value})")
            case _:
                pytest.fail("Unexpected error type")


class TestRefreshToken:
    """Tests for RefreshToken effect handling."""

    @pytest.mark.asyncio
    async def test_returns_new_token(self, mocker: MockerFixture) -> None:
        """RefreshToken returns new JWT token on success."""
        # Setup
        mock_auth = mocker.AsyncMock(spec=AuthService)
        mock_auth.refresh_token.return_value = TokenRefreshed(access_token="new.jwt.token")

        interpreter = AuthInterpreter(auth_service=mock_auth)
        effect = RefreshToken(refresh_token="old.refresh.token")

        # Act
        result = await interpreter.interpret(effect)

        # Assert
        match result:
            case Ok(effect_return):
                assert effect_return.value == TokenRefreshed(access_token="new.jwt.token")
                assert effect_return.effect_name == "RefreshToken"
            case Err(error):
                pytest.fail(f"Expected Ok, got Err({error})")

        mock_auth.refresh_token.assert_called_once_with("old.refresh.token")

    @pytest.mark.asyncio
    async def test_returns_rejection_for_invalid_refresh_token(self, mocker: MockerFixture) -> None:
        """RefreshToken returns TokenRefreshRejected when refresh token is invalid/expired."""
        # Setup
        mock_auth = mocker.AsyncMock(spec=AuthService)
        mock_auth.refresh_token.return_value = TokenRefreshRejected(reason="invalid_refresh_token")

        interpreter = AuthInterpreter(auth_service=mock_auth)
        effect = RefreshToken(refresh_token="invalid.refresh.token")

        # Act
        result = await interpreter.interpret(effect)

        # Assert
        match result:
            case Ok(effect_return):
                assert effect_return.value == TokenRefreshRejected(reason="invalid_refresh_token")
            case Err(error):
                pytest.fail(f"Expected Ok, got Err({error})")

    @pytest.mark.asyncio
    async def test_returns_auth_error_on_exception(self, mocker: MockerFixture) -> None:
        """RefreshToken returns AuthError when service raises exception."""
        # Setup
        mock_auth = mocker.AsyncMock(spec=AuthService)
        mock_auth.refresh_token.side_effect = TimeoutError("Connection timeout")

        interpreter = AuthInterpreter(auth_service=mock_auth)
        effect = RefreshToken(refresh_token="any.token")

        # Act
        result = await interpreter.interpret(effect)

        # Assert
        match result:
            case Err(AuthError(auth_error=error_msg, is_retryable=retryable)):
                assert "timeout" in error_msg.lower()
                assert retryable is True
            case Ok(value):
                pytest.fail(f"Expected Err, got Ok({value})")
            case _:
                pytest.fail("Unexpected error type")


class TestRevokeToken:
    """Tests for RevokeToken effect handling."""

    @pytest.mark.asyncio
    async def test_returns_none_on_success(self, mocker: MockerFixture) -> None:
        """RevokeToken returns None on success (fire-and-forget)."""
        # Setup
        mock_auth = mocker.AsyncMock(spec=AuthService)
        mock_auth.revoke_token.return_value = None

        interpreter = AuthInterpreter(auth_service=mock_auth)
        effect = RevokeToken(token="token.to.revoke")

        # Act
        result = await interpreter.interpret(effect)

        # Assert
        match result:
            case Ok(effect_return):
                assert effect_return.value is None
                assert effect_return.effect_name == "RevokeToken"
            case Err(error):
                pytest.fail(f"Expected Ok, got Err({error})")

        mock_auth.revoke_token.assert_called_once_with("token.to.revoke")

    @pytest.mark.asyncio
    async def test_returns_auth_error_on_exception(self, mocker: MockerFixture) -> None:
        """RevokeToken returns AuthError when service raises exception."""
        # Setup
        mock_auth = mocker.AsyncMock(spec=AuthService)
        mock_auth.revoke_token.side_effect = ConnectionError("Network unavailable")

        interpreter = AuthInterpreter(auth_service=mock_auth)
        effect = RevokeToken(token="any.token")

        # Act
        result = await interpreter.interpret(effect)

        # Assert
        match result:
            case Err(AuthError(auth_error=error_msg, is_retryable=retryable)):
                assert "unavailable" in error_msg.lower()
                assert retryable is True
            case Ok(value):
                pytest.fail(f"Expected Err, got Ok({value})")
            case _:
                pytest.fail("Unexpected error type")


class TestUnhandledEffect:
    """Tests for unhandled effect types."""

    @pytest.mark.asyncio
    async def test_returns_unhandled_effect_error(self, mocker: MockerFixture) -> None:
        """AuthInterpreter returns UnhandledEffectError for non-auth effects."""
        # Setup
        mock_auth = mocker.AsyncMock(spec=AuthService)
        interpreter = AuthInterpreter(auth_service=mock_auth)

        # Use a WebSocket effect which is not handled by AuthInterpreter
        effect = SendText(text="Hello")

        # Act
        result = await interpreter.interpret(effect)

        # Assert
        match result:
            case Err(UnhandledEffectError(available_interpreters=interpreters)):
                assert "AuthInterpreter" in interpreters
            case Ok(value):
                pytest.fail(f"Expected Err, got Ok({value})")
            case _:
                pytest.fail("Unexpected error type")


class TestIsRetryableError:
    """Tests for _is_retryable_error method."""

    @pytest.mark.asyncio
    async def test_connection_errors_are_retryable(self, mocker: MockerFixture) -> None:
        """Connection-related errors should be marked as retryable."""
        # Setup
        mock_auth = mocker.AsyncMock(spec=AuthService)
        mock_auth.validate_token.side_effect = Exception("Redis connection refused")

        interpreter = AuthInterpreter(auth_service=mock_auth)
        effect = ValidateToken(token="any.token")

        # Act
        result = await interpreter.interpret(effect)

        # Assert
        match result:
            case Err(AuthError(is_retryable=retryable)):
                assert retryable is True
            case _:
                pytest.fail("Expected AuthError")

    @pytest.mark.asyncio
    async def test_timeout_errors_are_retryable(self, mocker: MockerFixture) -> None:
        """Timeout errors should be marked as retryable."""
        # Setup
        mock_auth = mocker.AsyncMock(spec=AuthService)
        mock_auth.validate_token.side_effect = Exception("Operation timeout exceeded")

        interpreter = AuthInterpreter(auth_service=mock_auth)
        effect = ValidateToken(token="any.token")

        # Act
        result = await interpreter.interpret(effect)

        # Assert
        match result:
            case Err(AuthError(is_retryable=retryable)):
                assert retryable is True
            case _:
                pytest.fail("Expected AuthError")

    @pytest.mark.asyncio
    async def test_invalid_signature_not_retryable(self, mocker: MockerFixture) -> None:
        """Invalid signature errors should not be retryable."""
        # Setup
        mock_auth = mocker.AsyncMock(spec=AuthService)
        mock_auth.validate_token.side_effect = Exception("Invalid signature on token")

        interpreter = AuthInterpreter(auth_service=mock_auth)
        effect = ValidateToken(token="any.token")

        # Act
        result = await interpreter.interpret(effect)

        # Assert
        match result:
            case Err(AuthError(is_retryable=retryable)):
                assert retryable is False
            case _:
                pytest.fail("Expected AuthError")

    @pytest.mark.asyncio
    async def test_malformed_token_not_retryable(self, mocker: MockerFixture) -> None:
        """Malformed token errors should not be retryable."""
        # Setup
        mock_auth = mocker.AsyncMock(spec=AuthService)
        mock_auth.validate_token.side_effect = Exception("Token is malformed")

        interpreter = AuthInterpreter(auth_service=mock_auth)
        effect = ValidateToken(token="any.token")

        # Act
        result = await interpreter.interpret(effect)

        # Assert
        match result:
            case Err(AuthError(is_retryable=retryable)):
                assert retryable is False
            case _:
                pytest.fail("Expected AuthError")

    @pytest.mark.asyncio
    async def test_unknown_errors_not_retryable(self, mocker: MockerFixture) -> None:
        """Unknown errors should not be retryable by default."""
        # Setup
        mock_auth = mocker.AsyncMock(spec=AuthService)
        mock_auth.validate_token.side_effect = Exception("Some unknown error occurred")

        interpreter = AuthInterpreter(auth_service=mock_auth)
        effect = ValidateToken(token="any.token")

        # Act
        result = await interpreter.interpret(effect)

        # Assert
        match result:
            case Err(AuthError(is_retryable=retryable)):
                assert retryable is False
            case _:
                pytest.fail("Expected AuthError")


class TestGetUserByEmail:
    """Tests for GetUserByEmail effect handling."""

    @pytest.mark.asyncio
    async def test_returns_user_when_found(self, mocker: MockerFixture) -> None:
        """GetUserByEmail returns User when found."""
        # Setup
        user_id = uuid4()
        user = User(id=user_id, email="alice@example.com", name="Alice")
        expected = UserFound(user=user, source="database")

        mock_auth = mocker.AsyncMock(spec=AuthService)
        mock_auth.get_user_by_email.return_value = expected

        interpreter = AuthInterpreter(auth_service=mock_auth)
        effect = GetUserByEmail(email="alice@example.com")

        # Act
        result = await interpreter.interpret(effect)

        # Assert
        match result:
            case Ok(effect_return):
                assert effect_return.value == user
                assert effect_return.effect_name == "GetUserByEmail"
            case Err(error):
                pytest.fail(f"Expected Ok, got Err({error})")

        mock_auth.get_user_by_email.assert_called_once_with("alice@example.com")

    @pytest.mark.asyncio
    async def test_returns_user_not_found(self, mocker: MockerFixture) -> None:
        """GetUserByEmail returns UserNotFound when user doesn't exist."""
        # Setup
        user_id = uuid4()
        expected = UserNotFound(user_id=user_id, reason="does_not_exist")

        mock_auth = mocker.AsyncMock(spec=AuthService)
        mock_auth.get_user_by_email.return_value = expected

        interpreter = AuthInterpreter(auth_service=mock_auth)
        effect = GetUserByEmail(email="unknown@example.com")

        # Act
        result = await interpreter.interpret(effect)

        # Assert
        match result:
            case Ok(effect_return):
                assert isinstance(effect_return.value, UserNotFound)
                assert effect_return.effect_name == "GetUserByEmail"
            case Err(error):
                pytest.fail(f"Expected Ok, got Err({error})")

    @pytest.mark.asyncio
    async def test_returns_auth_error_on_exception(self, mocker: MockerFixture) -> None:
        """GetUserByEmail returns AuthError when service raises exception."""
        # Setup
        mock_auth = mocker.AsyncMock(spec=AuthService)
        mock_auth.get_user_by_email.side_effect = ConnectionError("Database unavailable")

        interpreter = AuthInterpreter(auth_service=mock_auth)
        effect = GetUserByEmail(email="alice@example.com")

        # Act
        result = await interpreter.interpret(effect)

        # Assert
        match result:
            case Err(AuthError(auth_error=error_msg, is_retryable=retryable)):
                assert "unavailable" in error_msg.lower()
                assert retryable is True
            case Ok(value):
                pytest.fail(f"Expected Err, got Ok({value})")
            case _:
                pytest.fail("Unexpected error type")


class TestValidatePassword:
    """Tests for ValidatePassword effect handling."""

    @pytest.mark.asyncio
    async def test_returns_true_when_password_valid(self, mocker: MockerFixture) -> None:
        """ValidatePassword returns True when password matches hash."""
        # Setup
        mock_auth = mocker.AsyncMock(spec=AuthService)
        mock_auth.validate_password.return_value = True

        interpreter = AuthInterpreter(auth_service=mock_auth)
        effect = ValidatePassword(password="correct_password", password_hash="$2b$12$hash")

        # Act
        result = await interpreter.interpret(effect)

        # Assert
        match result:
            case Ok(effect_return):
                assert effect_return.value is True
                assert effect_return.effect_name == "ValidatePassword"
            case Err(error):
                pytest.fail(f"Expected Ok, got Err({error})")

        mock_auth.validate_password.assert_called_once_with("correct_password", "$2b$12$hash")

    @pytest.mark.asyncio
    async def test_returns_false_when_password_invalid(self, mocker: MockerFixture) -> None:
        """ValidatePassword returns False when password doesn't match hash."""
        # Setup
        mock_auth = mocker.AsyncMock(spec=AuthService)
        mock_auth.validate_password.return_value = False

        interpreter = AuthInterpreter(auth_service=mock_auth)
        effect = ValidatePassword(password="wrong_password", password_hash="$2b$12$hash")

        # Act
        result = await interpreter.interpret(effect)

        # Assert
        match result:
            case Ok(effect_return):
                assert effect_return.value is False
            case Err(error):
                pytest.fail(f"Expected Ok, got Err({error})")

    @pytest.mark.asyncio
    async def test_returns_auth_error_on_exception(self, mocker: MockerFixture) -> None:
        """ValidatePassword returns AuthError when service raises exception."""
        # Setup
        mock_auth = mocker.AsyncMock(spec=AuthService)
        mock_auth.validate_password.side_effect = RuntimeError("Bcrypt error")

        interpreter = AuthInterpreter(auth_service=mock_auth)
        effect = ValidatePassword(password="password", password_hash="invalid_hash")

        # Act
        result = await interpreter.interpret(effect)

        # Assert
        match result:
            case Err(AuthError(auth_error=error_msg)):
                assert "Bcrypt error" in error_msg
            case Ok(value):
                pytest.fail(f"Expected Err, got Ok({value})")
            case _:
                pytest.fail("Unexpected error type")


class TestHashPassword:
    """Tests for HashPassword effect handling."""

    @pytest.mark.asyncio
    async def test_returns_hashed_password(self, mocker: MockerFixture) -> None:
        """HashPassword returns bcrypt hash string."""
        # Setup
        expected_hash = "$2b$12$saltsaltsaltsaltsaltsohashhashhashhashhashhashhas"

        mock_auth = mocker.AsyncMock(spec=AuthService)
        mock_auth.hash_password.return_value = expected_hash

        interpreter = AuthInterpreter(auth_service=mock_auth)
        effect = HashPassword(password="my_password")

        # Act
        result = await interpreter.interpret(effect)

        # Assert
        match result:
            case Ok(effect_return):
                assert effect_return.value == expected_hash
                assert effect_return.effect_name == "HashPassword"
            case Err(error):
                pytest.fail(f"Expected Ok, got Err({error})")

        mock_auth.hash_password.assert_called_once_with("my_password")

    @pytest.mark.asyncio
    async def test_returns_auth_error_on_exception(self, mocker: MockerFixture) -> None:
        """HashPassword returns AuthError when service raises exception."""
        # Setup
        mock_auth = mocker.AsyncMock(spec=AuthService)
        mock_auth.hash_password.side_effect = RuntimeError("Hash generation failed")

        interpreter = AuthInterpreter(auth_service=mock_auth)
        effect = HashPassword(password="password")

        # Act
        result = await interpreter.interpret(effect)

        # Assert
        match result:
            case Err(AuthError(auth_error=error_msg)):
                assert "Hash generation failed" in error_msg
            case Ok(value):
                pytest.fail(f"Expected Err, got Ok({value})")
            case _:
                pytest.fail("Unexpected error type")
