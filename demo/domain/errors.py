"""Domain error types for demo app.

All errors are immutable ADTs using frozen dataclasses.
"""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class AuthError:
    """Authentication/authorization error.

    Attributes:
        message: Human-readable error message
        error_type: Type of auth error
    """

    message: str
    error_type: Literal[
        "invalid_credentials", "token_expired", "token_invalid", "unauthorized"
    ]


@dataclass(frozen=True)
class AppError:
    """Application-level error.

    Attributes:
        message: Human-readable error message
        error_type: Type of application error
    """

    message: str
    error_type: Literal["not_found", "validation_error", "conflict", "internal_error"]

    @staticmethod
    def not_found(message: str) -> "AppError":
        """Create a not found error."""
        return AppError(message=message, error_type="not_found")

    @staticmethod
    def validation_error(message: str) -> "AppError":
        """Create a validation error."""
        return AppError(message=message, error_type="validation_error")

    @staticmethod
    def conflict(message: str) -> "AppError":
        """Create a conflict error."""
        return AppError(message=message, error_type="conflict")

    @staticmethod
    def internal_error(message: str) -> "AppError":
        """Create an internal error."""
        return AppError(message=message, error_type="internal_error")
