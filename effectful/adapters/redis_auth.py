"""Redis implementation of auth service protocol.

This module provides a Redis-based implementation of the AuthService protocol.
This is a production-ready adapter that:
- Uses JWT (PyJWT library) for token encoding/decoding
- Uses Redis for ephemeral token storage and blacklisting
- Implements stateless authentication (no sticky sessions required)

For testing, use pytest mocks or FakeAuthService instead of this real implementation.
"""

import hashlib
import hmac
import jwt
import secrets
from datetime import datetime, timedelta, UTC
from uuid import UUID, uuid4

from redis.asyncio import Redis

from effectful.domain.token_result import (
    TokenExpired,
    TokenInvalid,
    TokenValid,
    TokenValidationResult,
)
from effectful.domain.user import UserLookupResult, UserNotFound
from effectful.infrastructure.auth import AuthService


class RedisAuthService(AuthService):
    """Redis-based JWT authentication service.

    Implements AuthService protocol using:
    - PyJWT for token encoding/decoding
    - Redis for ephemeral session storage and token blacklisting

    Token Structure:
        - user_id: UUID of the authenticated user
        - exp: Expiration timestamp (UTC)
        - Additional claims (role, permissions, etc.)

    Redis Keys:
        - auth:session:{user_id} - Active session token (optional tracking)
        - auth:blacklist:{token} - Revoked tokens (TTL = remaining token lifetime)

    Attributes:
        _redis: Redis async client connection
        _jwt_secret: Secret key for JWT signing/verification
        _jwt_algorithm: JWT algorithm (default: HS256)
    """

    def __init__(
        self,
        redis_client: Redis,
        jwt_secret: str,
        jwt_algorithm: str = "HS256",
    ) -> None:
        """Initialize auth service with Redis and JWT configuration.

        Args:
            redis_client: Active Redis async client
            jwt_secret: Secret key for JWT signing (should be strong random string)
            jwt_algorithm: JWT algorithm to use (default: HS256)
        """
        self._redis = redis_client
        self._jwt_secret = jwt_secret
        self._jwt_algorithm = jwt_algorithm

    async def validate_token(self, token: str) -> TokenValidationResult:
        """Validate JWT token and extract claims.

        Checks:
        1. JWT signature is valid
        2. Token has not expired
        3. Token is not in Redis blacklist (revoked)

        Args:
            token: JWT token string to validate

        Returns:
            TokenValid(user_id, claims) if valid
            TokenExpired(token, expired_at) if expired
            TokenInvalid(token, reason) if invalid/revoked
        """
        try:
            # Decode JWT (verifies signature and expiration)
            payload = jwt.decode(
                token,
                self._jwt_secret,
                algorithms=[self._jwt_algorithm],
            )

            # Check blacklist in Redis
            is_revoked = await self._redis.exists(f"auth:blacklist:{token}")
            if is_revoked:
                return TokenInvalid(token=token, reason="revoked")

            # Extract user_id and claims
            user_id = UUID(payload["user_id"])
            claims = {k: str(v) for k, v in payload.items() if k not in ("user_id", "exp")}

            return TokenValid(user_id=user_id, claims=claims)

        except jwt.ExpiredSignatureError:
            # Extract expiration time for error details
            try:
                payload = jwt.decode(
                    token,
                    options={"verify_signature": False, "verify_exp": False},
                )
                exp_timestamp = payload.get("exp", 0)
                expired_at = datetime.fromtimestamp(exp_timestamp, tz=UTC)
            except Exception:
                # If we can't decode, use current time as fallback
                expired_at = datetime.now(UTC)

            return TokenExpired(token=token, expired_at=expired_at)

        except jwt.InvalidTokenError as e:
            # Malformed token, invalid signature, etc.
            return TokenInvalid(token=token, reason=str(e))

    async def generate_token(self, user_id: UUID, claims: dict[str, str], ttl_seconds: int) -> str:
        """Generate new JWT token for user.

        Args:
            user_id: UUID of the user to generate token for
            claims: Additional claims to include (role, permissions, etc.)
            ttl_seconds: Time-to-live in seconds

        Returns:
            Encoded JWT token as string
        """
        # Calculate expiration time
        exp = datetime.now(UTC) + timedelta(seconds=ttl_seconds)

        # Build JWT payload
        payload = {
            "user_id": str(user_id),
            "exp": exp,
            **claims,
        }

        # Encode JWT
        token = jwt.encode(payload, self._jwt_secret, algorithm=self._jwt_algorithm)

        # Store in Redis for session management (optional - enables user session tracking)
        await self._redis.setex(f"auth:session:{user_id}", ttl_seconds, token)

        return token

    async def refresh_token(self, refresh_token: str) -> str | None:
        """Refresh an existing token to extend validity.

        Validates the refresh token and generates a new access token with extended TTL.

        Args:
            refresh_token: The refresh token to exchange

        Returns:
            New JWT access token, or None if refresh token is invalid/expired
        """
        # Validate refresh token
        validation_result = await self.validate_token(refresh_token)

        match validation_result:
            case TokenValid(user_id=user_id, claims=claims):
                # Generate new access token with same claims, extended TTL (1 hour)
                new_token = await self.generate_token(user_id, claims, ttl_seconds=3600)
                return new_token
            case TokenExpired() | TokenInvalid():
                # Refresh token invalid/expired - cannot refresh
                return None

    async def revoke_token(self, token: str) -> None:
        """Revoke/blacklist a token to prevent further use.

        Adds token to Redis blacklist with TTL equal to remaining token lifetime.
        After the token expires naturally, the blacklist entry auto-expires.

        Args:
            token: JWT token to revoke
        """
        try:
            # Decode token to get expiration time (don't verify - we're revoking it anyway)
            payload = jwt.decode(
                token,
                options={"verify_signature": False, "verify_exp": False},
            )
            exp_timestamp = payload.get("exp", 0)

            # Calculate TTL (remaining time until token expires naturally)
            now = datetime.now(UTC).timestamp()
            ttl = max(0, int(exp_timestamp - now))

            # Add to blacklist with TTL (auto-expire after token expiration)
            await self._redis.setex(f"auth:blacklist:{token}", ttl, "revoked")

        except Exception:
            # If we can't decode the token, blacklist it for 24 hours as fallback
            await self._redis.setex(f"auth:blacklist:{token}", 86400, "revoked")

    async def get_user_by_email(self, email: str) -> UserLookupResult:
        """Get user by email address.

        Note: This is a stub implementation. In production, this should delegate
        to a UserRepository. RedisAuthService is primarily for JWT token operations.

        Args:
            email: Email address to search for

        Returns:
            UserNotFound - This stub always returns not found
        """
        # This is a stub - in production, inject a UserRepository
        return UserNotFound(user_id=uuid4(), reason="does_not_exist")

    async def validate_password(self, password: str, password_hash: str) -> bool:
        """Validate password against hash.

        Uses PBKDF2-HMAC-SHA256 for secure password hashing.

        Args:
            password: Plain text password to validate
            password_hash: Hash in format "salt$hash" to validate against

        Returns:
            True if password matches hash, False otherwise
        """
        try:
            parts = password_hash.split("$")
            if len(parts) != 2:
                return False
            salt = bytes.fromhex(parts[0])
            stored_hash = parts[1]
            computed_hash = hashlib.pbkdf2_hmac(
                "sha256", password.encode("utf-8"), salt, 100000
            ).hex()
            return hmac.compare_digest(computed_hash, stored_hash)
        except (ValueError, IndexError):
            return False

    async def hash_password(self, password: str) -> str:
        """Hash password with PBKDF2-HMAC-SHA256.

        Args:
            password: Plain text password to hash

        Returns:
            Hash in format "salt$hash"
        """
        salt = secrets.token_bytes(32)
        hashed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000).hex()
        return f"{salt.hex()}${hashed}"
