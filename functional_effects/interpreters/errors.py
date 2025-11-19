"""Interpreter error types.

This module defines interpreter-level errors as immutable ADTs.
These represent failures during effect interpretation (infrastructure errors).
"""

from dataclasses import dataclass

from functional_effects.effects.base import Effect


@dataclass(frozen=True)
class UnhandledEffectError:
    """No interpreter could handle the effect.

    Attributes:
        effect: The effect that couldn't be handled
        available_interpreters: List of interpreter names that were tried
    """

    effect: Effect
    available_interpreters: list[str]


@dataclass(frozen=True)
class WebSocketClosedError:
    """WebSocket connection closed unexpectedly.

    Attributes:
        effect: The effect that was being interpreted
        close_code: WebSocket close code
        reason: Close reason
    """

    effect: Effect
    close_code: int
    reason: str


@dataclass(frozen=True)
class DatabaseError:
    """Database operation failed.

    Attributes:
        effect: The effect that was being interpreted
        db_error: Error message from database
        is_retryable: Whether the error might succeed on retry
    """

    effect: Effect
    db_error: str
    is_retryable: bool


@dataclass(frozen=True)
class CacheError:
    """Cache operation failed.

    Attributes:
        effect: The effect that was being interpreted
        cache_error: Error message from cache
        is_retryable: Whether the error might succeed on retry
    """

    effect: Effect
    cache_error: str
    is_retryable: bool


@dataclass(frozen=True)
class MessagingError:
    """Messaging operation failed.

    This error type represents infrastructure-level failures when executing
    messaging effects (connection errors, broker unavailable, etc.).

    Domain-level failures (publish timeout, topic not found) are handled via
    PublishResult ADT, not this error type.

    Attributes:
        effect: The messaging effect that was being interpreted
        messaging_error: Error message from Pulsar or infrastructure
        is_retryable: Whether retry might succeed (connection/timeout vs config error)

    Example:
        >>> match result:
        ...     case Err(MessagingError(messaging_error=msg, is_retryable=True)):
        ...         # Retry with backoff
        ...         await retry_with_backoff(program)
        ...     case Err(MessagingError(messaging_error=msg, is_retryable=False)):
        ...         # Permanent failure - log and alert
        ...         logger.error(f"Non-retryable error: {msg}")
    """

    effect: Effect
    messaging_error: str
    is_retryable: bool


@dataclass(frozen=True)
class StorageError:
    """Storage operation failed.

    This error type represents infrastructure-level failures when executing
    storage effects (network errors, S3 unavailable, etc.).

    Domain-level failures (quota exceeded, permission denied) are handled via
    PutResult ADT, not this error type.

    Attributes:
        effect: The storage effect that was being interpreted
        storage_error: Error message from S3 or infrastructure
        is_retryable: Whether retry might succeed (network vs config error)

    Example:
        >>> match result:
        ...     case Err(StorageError(storage_error=msg, is_retryable=True)):
        ...         # Retry with backoff
        ...         await retry_with_backoff(program)
        ...     case Err(StorageError(storage_error=msg, is_retryable=False)):
        ...         # Permanent failure - log and alert
        ...         logger.error(f"Non-retryable error: {msg}")
    """

    effect: Effect
    storage_error: str
    is_retryable: bool


@dataclass(frozen=True)
class AuthError:
    """Auth operation failed.

    This error type represents infrastructure-level failures when executing
    auth effects (Redis connection errors, JWT encoding failures, etc.).

    Domain-level failures (token expired, token invalid) are handled via
    TokenValidationResult ADT, not this error type.

    Attributes:
        effect: The auth effect that was being interpreted
        auth_error: Error message from auth service or infrastructure
        is_retryable: Whether retry might succeed (connection vs invalid token)

    Example:
        >>> match result:
        ...     case Err(AuthError(auth_error=msg, is_retryable=True)):
        ...         # Retry with backoff
        ...         await retry_with_backoff(program)
        ...     case Err(AuthError(auth_error=msg, is_retryable=False)):
        ...         # Permanent failure - log and alert
        ...         logger.error(f"Non-retryable error: {msg}")
    """

    effect: Effect
    auth_error: str
    is_retryable: bool


# ADT: Union of all interpreter errors using PEP 695 type statement
type InterpreterError = (
    UnhandledEffectError
    | WebSocketClosedError
    | DatabaseError
    | CacheError
    | MessagingError
    | StorageError
    | AuthError
)
