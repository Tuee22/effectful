"""Token validation domain models.

This module defines token-related domain objects including:
- TokenValidationResult: ADT for token validation outcomes

Uses ADTs to eliminate Optional types and make illegal states unrepresentable.
All possible validation outcomes are explicitly modeled:
- TokenValid: Token is valid and not expired
- TokenExpired: Token has expired
- TokenInvalid: Token is malformed, revoked, or otherwise invalid
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class TokenValid:
    """Token is valid and authenticated.

    Attributes:
        user_id: UUID of the authenticated user
        claims: Token claims/metadata (role, permissions, etc.)
    """

    user_id: UUID
    claims: dict[str, str]


@dataclass(frozen=True)
class TokenExpired:
    """Token has expired.

    Attributes:
        token: The expired token (for logging/debugging)
        expired_at: When the token expired
    """

    token: str
    expired_at: datetime


@dataclass(frozen=True)
class TokenInvalid:
    """Token is invalid (malformed, revoked, or signature mismatch).

    Attributes:
        token: The invalid token (for logging/debugging)
        reason: Why the token is invalid (e.g., "revoked", "invalid_signature", "malformed")
    """

    token: str
    reason: str


# ADT: Union of all token validation results (no Optional!) using PEP 695 type statement
type TokenValidationResult = TokenValid | TokenExpired | TokenInvalid
