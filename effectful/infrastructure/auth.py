"""Auth service protocol for JWT token operations.

This module defines Protocol interface (port) for authentication operations.
Concrete implementations (adapters) like RedisAuthService are provided elsewhere.
Uses ADTs instead of Optional for type safety.
"""

from typing import Protocol
from uuid import UUID

from effectful.domain.token_result import TokenValidationResult
from effectful.domain.user import UserLookupResult


class AuthService(Protocol):
    """Protocol for JWT authentication operations."""

    async def validate_token(self, token: str) -> TokenValidationResult:
        """Validate JWT token and extract claims.

        Args:
            token: JWT token string to validate

        Returns:
            TokenValidationResult ADT:
            - TokenValid(user_id, claims) if token is valid
            - TokenExpired(token, expired_at) if token has expired
            - TokenInvalid(token, reason) if token is malformed/revoked
        """
        ...

    async def generate_token(self, user_id: UUID, claims: dict[str, str], ttl_seconds: int) -> str:
        """Generate new JWT token for user.

        Args:
            user_id: UUID of the user to generate token for
            claims: Additional claims to include in token
            ttl_seconds: Time-to-live in seconds

        Returns:
            Encoded JWT token as string
        """
        ...

    async def refresh_token(self, refresh_token: str) -> str | None:
        """Refresh an existing token to extend validity.

        Args:
            refresh_token: The refresh token to exchange

        Returns:
            New JWT access token, or None if refresh token is invalid/expired
        """
        ...

    async def revoke_token(self, token: str) -> None:
        """Revoke/blacklist a token to prevent further use.

        Args:
            token: JWT token to revoke
        """
        ...

    async def get_user_by_email(self, email: str) -> UserLookupResult:
        """Get user by email address.

        Args:
            email: Email address to search for

        Returns:
            UserFound if user exists, UserNotFound otherwise
        """
        ...

    async def validate_password(self, password: str, password_hash: str) -> bool:
        """Validate password against bcrypt hash.

        Args:
            password: Plain text password to validate
            password_hash: Bcrypt hash to validate against

        Returns:
            True if password matches hash, False otherwise
        """
        ...

    async def hash_password(self, password: str) -> str:
        """Hash password with bcrypt.

        Args:
            password: Plain text password to hash

        Returns:
            Bcrypt hash as string
        """
        ...
