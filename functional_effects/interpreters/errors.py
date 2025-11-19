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


# ADT: Union of all interpreter errors using PEP 695 type statement
type InterpreterError = (UnhandledEffectError | WebSocketClosedError | DatabaseError | CacheError)
