"""Shared retry logic utilities for interpreters.

This module provides reusable error classification for retry decisions
across all interpreters, eliminating code duplication.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class RetryPatterns:
    """Configuration for determining error retryability.

    Attributes:
        retryable: Patterns that indicate transient, retryable errors
        non_retryable: Patterns that indicate permanent errors (checked first)
        default: Default retryability when no patterns match
    """

    retryable: tuple[str, ...]
    non_retryable: tuple[str, ...] = ()
    default: bool = False


# Common patterns shared across interpreters
COMMON_RETRY_PATTERNS = RetryPatterns(
    retryable=(
        "connection",
        "timeout",
        "unavailable",
        "network",
    ),
)

# Database-specific patterns
DATABASE_RETRY_PATTERNS = RetryPatterns(
    retryable=(
        "connection",
        "timeout",
        "deadlock",
        "lock",
        "unavailable",
    ),
)

# Cache-specific patterns (same as common)
CACHE_RETRY_PATTERNS = COMMON_RETRY_PATTERNS

# Auth-specific patterns with non-retryable token errors
AUTH_RETRY_PATTERNS = RetryPatterns(
    retryable=(
        "connection",
        "timeout",
        "unavailable",
        "network",
        "redis",
    ),
    non_retryable=(
        "invalid signature",
        "malformed",
        "decode error",
        "encoding error",
    ),
)

# Storage-specific patterns with more categories
STORAGE_RETRY_PATTERNS = RetryPatterns(
    retryable=(
        "connection",
        "timeout",
        "unavailable",
        "throttl",
        "rate limit",
        "slow down",
        "500",
        "503",
        "network",
    ),
    non_retryable=(
        "configuration",
        "invalid",
        "authentication",
        "authorization",
        "access denied",
        "bucket not found",
        "404",
        "403",
        "400",
    ),
    default=True,
)

# Messaging-specific patterns
MESSAGING_RETRY_PATTERNS = RetryPatterns(
    retryable=(
        "connection",
        "timeout",
        "unavailable",
        "backpressure",
    ),
)


def is_retryable_error(error: Exception, patterns: RetryPatterns) -> bool:
    """Determine if an error is retryable based on pattern matching.

    Checks non-retryable patterns first (for specificity), then retryable patterns,
    then falls back to default.

    Args:
        error: The exception that was raised
        patterns: RetryPatterns configuration for the interpreter

    Returns:
        True if error might succeed on retry, False otherwise
    """
    error_str = str(error).lower()

    # Check non-retryable first (more specific)
    if any(pattern in error_str for pattern in patterns.non_retryable):
        return False

    # Check retryable patterns
    if any(pattern in error_str for pattern in patterns.retryable):
        return True

    # Fall back to default
    return patterns.default
