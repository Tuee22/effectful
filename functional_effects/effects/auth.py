"""Auth effect DSL.

This module defines effects for JWT authentication operations:
- ValidateToken: Verify JWT token and extract claims
- GenerateToken: Create new JWT token with claims
- RefreshToken: Refresh an existing token
- RevokeToken: Blacklist/invalidate a token
- GetUserByEmail: Get user by email address
- ValidatePassword: Validate password against hash
- HashPassword: Hash password with bcrypt

All effects are immutable (frozen dataclasses).
"""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class ValidateToken:
    """Effect: Validate JWT token and extract user claims.

    Returns TokenValidationResult ADT:
    - TokenValid(user_id, claims) if token is valid
    - TokenExpired(token, expired_at) if token has expired
    - TokenInvalid(token, reason) if token is invalid/revoked

    Attributes:
        token: The JWT token to validate
    """

    token: str


@dataclass(frozen=True)
class GenerateToken:
    """Effect: Generate new JWT token for user.

    Returns the encoded JWT token as a string.

    Attributes:
        user_id: UUID of the user to generate token for
        metadata: Additional metadata to include in the token
    """

    user_id: UUID
    metadata: dict[str, str]


@dataclass(frozen=True)
class RefreshToken:
    """Effect: Refresh an existing token to extend its validity.

    Returns new JWT token as string, or None if refresh token is invalid/expired.

    Attributes:
        refresh_token: The refresh token to exchange for new access token
    """

    refresh_token: str


@dataclass(frozen=True)
class RevokeToken:
    """Effect: Revoke/blacklist a token to prevent further use.

    Returns None (fire-and-forget operation).

    Attributes:
        token: The JWT token to revoke
    """

    token: str


@dataclass(frozen=True)
class GetUserByEmail:
    """Effect: Get user by email address.

    Returns User object if found, None otherwise.

    Attributes:
        email: Email address to search for
    """

    email: str


@dataclass(frozen=True)
class ValidatePassword:
    """Effect: Validate password against bcrypt hash.

    Returns True if password matches hash, False otherwise.

    Attributes:
        password: Plain text password to validate
        password_hash: Bcrypt hash to validate against
    """

    password: str
    password_hash: str


@dataclass(frozen=True)
class HashPassword:
    """Effect: Hash password with bcrypt.

    Returns bcrypt hash as string.

    Attributes:
        password: Plain text password to hash
    """

    password: str


# ADT: Union of all auth effects using PEP 695 type statement
type AuthEffect = (
    ValidateToken
    | GenerateToken
    | RefreshToken
    | RevokeToken
    | GetUserByEmail
    | ValidatePassword
    | HashPassword
)
