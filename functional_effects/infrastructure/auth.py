"""Auth service protocol for JWT token operations.

This module defines Protocol interface (port) for authentication operations.
Concrete implementations (adapters) like RedisAuthService are provided elsewhere.
Uses ADTs instead of Optional for type safety.
"""

from typing import Protocol
from uuid import UUID

from functional_effects.domain.token_result import TokenValidationResult


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

    async def generate_token(
        self, user_id: UUID, claims: dict[str, str], ttl_seconds: int
    ) -> str:
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
