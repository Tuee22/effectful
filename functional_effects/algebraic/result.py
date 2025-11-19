"""Result[T, E] type for explicit error handling.

This module provides a Result type that represents either success (Ok) or failure (Err).
It eliminates the need for exceptions in business logic and makes error handling explicit.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Never


@dataclass(frozen=True)
class Ok[T]:
    """Success variant of Result containing a value."""

    value: T

    def is_ok(self) -> bool:
        """Check if this is an Ok result."""
        return True

    def is_err(self) -> bool:
        """Check if this is an Err result."""
        return False

    def map[U](self, f: Callable[[T], U]) -> Ok[U]:
        """Map the success value with function f."""
        return Ok(f(self.value))

    def flat_map[U, E](self, f: Callable[[T], "Result[U, E]"]) -> "Result[U, E]":
        """Chain another Result-producing computation (monadic bind)."""
        return f(self.value)

    def map_err[E, F](self, _f: Callable[[E], F]) -> Ok[T]:
        """Map the error value (no-op for Ok)."""
        return self

    def unwrap(self) -> T:
        """Extract the value (safe for Ok)."""
        return self.value

    def unwrap_or[U](self, _default: U) -> T:
        """Return the value or default (returns value for Ok)."""
        return self.value

    def unwrap_err(self) -> Never:
        """Extract the error (raises for Ok)."""
        raise ValueError(f"Called unwrap_err on Ok: {self.value}")


@dataclass(frozen=True)
class Err[E]:
    """Failure variant of Result containing an error."""

    error: E

    def is_ok(self) -> bool:
        """Check if this is an Ok result."""
        return False

    def is_err(self) -> bool:
        """Check if this is an Err result."""
        return True

    def map[T, U](self, _f: Callable[[T], U]) -> Err[E]:
        """Map the success value (no-op for Err)."""
        return self

    def flat_map[T, U](self, _f: Callable[[T], "Result[U, E]"]) -> Err[E]:
        """Chain another Result-producing computation (no-op for Err)."""
        return self

    def map_err[F](self, f: Callable[[E], F]) -> Err[F]:
        """Map the error value with function f."""
        return Err(f(self.error))

    def unwrap(self) -> Never:
        """Extract the value (raises for Err)."""
        raise ValueError(f"Called unwrap on Err: {self.error}")

    def unwrap_or[U](self, default: U) -> U:
        """Return the value or default (returns default for Err)."""
        return default

    def unwrap_err(self) -> E:
        """Extract the error (safe for Err)."""
        return self.error


# Type alias for the Result union using PEP 695 syntax
type Result[T, E] = Ok[T] | Err[E]


def fold_result[
    T, E, U
](result: Result[T, E], on_ok: Callable[[T], U], on_err: Callable[[E], U],) -> U:
    """Fold pattern for exhaustive Result handling.

    Args:
        result: The Result to fold over
        on_ok: Function to apply if result is Ok
        on_err: Function to apply if result is Err

    Returns:
        The result of applying the appropriate function

    Example:
        >>> result = Ok(42)
        >>> fold_result(result, lambda x: x * 2, lambda e: 0)
        84
    """
    match result:
        case Ok(value=v):
            return on_ok(v)
        case Err(error=e):
            return on_err(e)
        case _:  # pragma: no cover
            # This should never happen due to Result type constraint
            raise AssertionError(f"Invalid Result variant: {result}")
