"""Unit tests for Redis auth adapter.

Tests RedisAuthService using pytest-mock with AsyncMock.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest
from pytest_mock import MockerFixture

from effectful.adapters.redis_auth import RedisAuthService
from effectful.domain.token_result import TokenExpired, TokenInvalid, TokenValid


class TestRedisAuthServiceValidateToken:
    """Tests for RedisAuthService.validate_token."""

    @pytest.mark.asyncio
    async def test_validate_token_returns_valid_for_good_token(self, mocker: MockerFixture) -> None:
        """Test valid token returns TokenValid with user_id and claims."""
        # Setup
        user_id = uuid4()
        secret = "test-secret"
        exp = datetime.now(UTC) + timedelta(hours=1)

        token = jwt.encode(
            {"user_id": str(user_id), "exp": exp, "role": "admin"},
            secret,
            algorithm="HS256",
        )

        mock_redis = mocker.AsyncMock()
        mock_redis.exists.return_value = 0  # Not blacklisted

        auth_service = RedisAuthService(mock_redis, secret)

        # Execute
        result = await auth_service.validate_token(token)

        # Assert
        assert isinstance(result, TokenValid)
        assert result.user_id == user_id
        assert result.claims["role"] == "admin"

        # Verify blacklist check
        mock_redis.exists.assert_called_once_with(f"auth:blacklist:{token}")

    @pytest.mark.asyncio
    async def test_validate_token_returns_invalid_for_revoked_token(
        self, mocker: MockerFixture
    ) -> None:
        """Test revoked token returns TokenInvalid with reason 'revoked'."""
        # Setup
        user_id = uuid4()
        secret = "test-secret"
        exp = datetime.now(UTC) + timedelta(hours=1)

        token = jwt.encode(
            {"user_id": str(user_id), "exp": exp},
            secret,
            algorithm="HS256",
        )

        mock_redis = mocker.AsyncMock()
        mock_redis.exists.return_value = 1  # Blacklisted

        auth_service = RedisAuthService(mock_redis, secret)

        # Execute
        result = await auth_service.validate_token(token)

        # Assert
        assert isinstance(result, TokenInvalid)
        assert result.token == token
        assert result.reason == "revoked"

    @pytest.mark.asyncio
    async def test_validate_token_returns_expired_for_expired_token(
        self, mocker: MockerFixture
    ) -> None:
        """Test expired token returns TokenExpired with expiration time."""
        # Setup
        user_id = uuid4()
        secret = "test-secret"
        exp = datetime.now(UTC) - timedelta(hours=1)  # Expired

        token = jwt.encode(
            {"user_id": str(user_id), "exp": exp},
            secret,
            algorithm="HS256",
        )

        mock_redis = mocker.AsyncMock()
        auth_service = RedisAuthService(mock_redis, secret)

        # Execute
        result = await auth_service.validate_token(token)

        # Assert
        assert isinstance(result, TokenExpired)
        assert result.token == token
        # expired_at should be close to our exp time
        time_diff = abs((result.expired_at - exp).total_seconds())
        assert time_diff < 2  # Within 2 seconds

    @pytest.mark.asyncio
    async def test_validate_token_returns_invalid_for_bad_signature(
        self, mocker: MockerFixture
    ) -> None:
        """Test token with wrong signature returns TokenInvalid."""
        # Setup
        user_id = uuid4()
        secret = "test-secret"
        wrong_secret = "wrong-secret"
        exp = datetime.now(UTC) + timedelta(hours=1)

        token = jwt.encode(
            {"user_id": str(user_id), "exp": exp},
            wrong_secret,  # Signed with wrong secret
            algorithm="HS256",
        )

        mock_redis = mocker.AsyncMock()
        auth_service = RedisAuthService(mock_redis, secret)

        # Execute
        result = await auth_service.validate_token(token)

        # Assert
        assert isinstance(result, TokenInvalid)
        assert result.token == token
        assert "Signature" in result.reason or "signature" in result.reason

    @pytest.mark.asyncio
    async def test_validate_token_returns_invalid_for_malformed_token(
        self, mocker: MockerFixture
    ) -> None:
        """Test malformed token returns TokenInvalid."""
        # Setup
        mock_redis = mocker.AsyncMock()
        auth_service = RedisAuthService(mock_redis, "test-secret")

        # Execute
        result = await auth_service.validate_token("not-a-valid-jwt")

        # Assert
        assert isinstance(result, TokenInvalid)
        assert result.token == "not-a-valid-jwt"


class TestRedisAuthServiceGenerateToken:
    """Tests for RedisAuthService.generate_token."""

    @pytest.mark.asyncio
    async def test_generate_token_creates_valid_jwt(self, mocker: MockerFixture) -> None:
        """Test generating token creates a valid JWT."""
        # Setup
        user_id = uuid4()
        secret = "test-secret"
        claims = {"role": "user", "permission": "read"}
        ttl_seconds = 3600

        mock_redis = mocker.AsyncMock()
        auth_service = RedisAuthService(mock_redis, secret)

        # Execute
        token = await auth_service.generate_token(user_id, claims, ttl_seconds)

        # Assert - decode and verify
        decoded = jwt.decode(token, secret, algorithms=["HS256"])
        assert decoded["user_id"] == str(user_id)
        assert decoded["role"] == "user"
        assert decoded["permission"] == "read"
        assert "exp" in decoded

    @pytest.mark.asyncio
    async def test_generate_token_stores_session_in_redis(self, mocker: MockerFixture) -> None:
        """Test generating token stores session in Redis."""
        # Setup
        user_id = uuid4()
        ttl_seconds = 3600

        mock_redis = mocker.AsyncMock()
        auth_service = RedisAuthService(mock_redis, "test-secret")

        # Execute
        token = await auth_service.generate_token(user_id, {}, ttl_seconds)

        # Assert
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert call_args.args[0] == f"auth:session:{user_id}"
        assert call_args.args[1] == ttl_seconds
        assert call_args.args[2] == token

    @pytest.mark.asyncio
    async def test_generate_token_sets_correct_expiration(self, mocker: MockerFixture) -> None:
        """Test token has correct expiration time."""
        # Setup
        user_id = uuid4()
        secret = "test-secret"
        ttl_seconds = 7200  # 2 hours

        mock_redis = mocker.AsyncMock()
        auth_service = RedisAuthService(mock_redis, secret)

        before_time = datetime.now(UTC)

        # Execute
        token = await auth_service.generate_token(user_id, {}, ttl_seconds)

        after_time = datetime.now(UTC)

        # Assert
        decoded = jwt.decode(token, secret, algorithms=["HS256"])
        exp_timestamp = decoded["exp"]
        exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=UTC)

        # Expiration should be within the expected range (with 1 second tolerance for truncation)
        expected_min = before_time + timedelta(seconds=ttl_seconds - 1)
        expected_max = after_time + timedelta(seconds=ttl_seconds + 1)

        assert expected_min <= exp_datetime <= expected_max


class TestRedisAuthServiceRefreshToken:
    """Tests for RedisAuthService.refresh_token."""

    @pytest.mark.asyncio
    async def test_refresh_token_returns_new_token_for_valid_refresh(
        self, mocker: MockerFixture
    ) -> None:
        """Test refreshing valid token returns new token."""
        # Setup
        user_id = uuid4()
        secret = "test-secret"
        # Use a specific expiration that's different from what refresh generates (1 hour)
        exp = datetime.now(UTC) + timedelta(minutes=30)

        refresh_token = jwt.encode(
            {"user_id": str(user_id), "exp": exp, "role": "user"},
            secret,
            algorithm="HS256",
        )

        mock_redis = mocker.AsyncMock()
        mock_redis.exists.return_value = 0  # Not blacklisted

        auth_service = RedisAuthService(mock_redis, secret)

        # Execute
        new_token = await auth_service.refresh_token(refresh_token)

        # Assert
        assert isinstance(new_token, str)
        # New token will have different expiration (1 hour from now vs 30 minutes)
        # so it should be different
        decoded_old = jwt.decode(refresh_token, secret, algorithms=["HS256"])
        decoded_new = jwt.decode(new_token, secret, algorithms=["HS256"])
        assert decoded_new["exp"] > decoded_old["exp"]

        # Verify new token has correct claims
        assert decoded_new["user_id"] == str(user_id)
        assert decoded_new["role"] == "user"

    @pytest.mark.asyncio
    async def test_refresh_token_returns_none_for_expired_token(
        self, mocker: MockerFixture
    ) -> None:
        """Test refreshing expired token returns None."""
        # Setup
        user_id = uuid4()
        secret = "test-secret"
        exp = datetime.now(UTC) - timedelta(hours=1)  # Expired

        refresh_token = jwt.encode(
            {"user_id": str(user_id), "exp": exp},
            secret,
            algorithm="HS256",
        )

        mock_redis = mocker.AsyncMock()
        auth_service = RedisAuthService(mock_redis, secret)

        # Execute
        result = await auth_service.refresh_token(refresh_token)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_refresh_token_returns_none_for_invalid_token(
        self, mocker: MockerFixture
    ) -> None:
        """Test refreshing invalid token returns None."""
        # Setup
        mock_redis = mocker.AsyncMock()
        auth_service = RedisAuthService(mock_redis, "test-secret")

        # Execute
        result = await auth_service.refresh_token("invalid-token")

        # Assert
        assert result is None


class TestRedisAuthServiceRevokeToken:
    """Tests for RedisAuthService.revoke_token."""

    @pytest.mark.asyncio
    async def test_revoke_token_adds_to_blacklist(self, mocker: MockerFixture) -> None:
        """Test revoking token adds it to Redis blacklist."""
        # Setup
        user_id = uuid4()
        secret = "test-secret"
        exp = datetime.now(UTC) + timedelta(hours=1)

        token = jwt.encode(
            {"user_id": str(user_id), "exp": exp},
            secret,
            algorithm="HS256",
        )

        mock_redis = mocker.AsyncMock()
        auth_service = RedisAuthService(mock_redis, secret)

        # Execute
        await auth_service.revoke_token(token)

        # Assert
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert call_args.args[0] == f"auth:blacklist:{token}"
        assert call_args.args[2] == "revoked"
        # TTL should be positive (remaining time until expiration)
        assert call_args.args[1] > 0

    @pytest.mark.asyncio
    async def test_revoke_token_uses_fallback_ttl_for_invalid_token(
        self, mocker: MockerFixture
    ) -> None:
        """Test revoking invalid token uses 24 hour fallback TTL."""
        # Setup
        mock_redis = mocker.AsyncMock()
        auth_service = RedisAuthService(mock_redis, "test-secret")

        # Execute
        await auth_service.revoke_token("not-a-valid-jwt")

        # Assert
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert call_args.args[1] == 86400  # 24 hours
