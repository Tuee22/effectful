"""Tests for AuthInterpreter.

Tests cover all auth effect handling with both success and error paths.
Uses pytest-mock for type-safe mocking with spec=.
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pytest_mock import MockerFixture

from effectful.algebraic.result import Err, Ok
from effectful.domain.token_result import TokenExpired, TokenInvalid, TokenValid
from effectful.effects.auth import GenerateToken, RefreshToken, RevokeToken, ValidateToken
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
        new_token = "new.jwt.token"

        mock_auth = mocker.AsyncMock(spec=AuthService)
        mock_auth.refresh_token.return_value = new_token

        interpreter = AuthInterpreter(auth_service=mock_auth)
        effect = RefreshToken(refresh_token="old.refresh.token")

        # Act
        result = await interpreter.interpret(effect)

        # Assert
        match result:
            case Ok(effect_return):
                assert effect_return.value == new_token
                assert effect_return.effect_name == "RefreshToken"
            case Err(error):
                pytest.fail(f"Expected Ok, got Err({error})")

        mock_auth.refresh_token.assert_called_once_with("old.refresh.token")

    @pytest.mark.asyncio
    async def test_returns_none_for_invalid_refresh_token(self, mocker: MockerFixture) -> None:
        """RefreshToken returns None when refresh token is invalid/expired."""
        # Setup
        mock_auth = mocker.AsyncMock(spec=AuthService)
        mock_auth.refresh_token.return_value = None

        interpreter = AuthInterpreter(auth_service=mock_auth)
        effect = RefreshToken(refresh_token="invalid.refresh.token")

        # Act
        result = await interpreter.interpret(effect)

        # Assert
        match result:
            case Ok(effect_return):
                assert effect_return.value is None
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
