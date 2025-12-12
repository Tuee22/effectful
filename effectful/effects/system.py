"""System effect DSL.

This module defines effects for system operations that provide pure
access to otherwise impure system resources:
- GetCurrentTime: Get current UTC timestamp
- GenerateUUID: Generate a new UUID v4

All effects are immutable (frozen dataclasses).

These effects enable full purity in effect programs by making
time and UUID generation explicit and testable.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class GetCurrentTime:
    """Effect: Get current UTC timestamp.

    Returns:
        datetime: Current UTC timestamp

    Example:
        >>> current_time = yield GetCurrentTime()
        >>> assert isinstance(current_time, datetime)
    """

    pass


@dataclass(frozen=True)
class GenerateUUID:
    """Effect: Generate a new UUID v4.

    Returns:
        UUID: Newly generated UUID v4

    Example:
        >>> new_id = yield GenerateUUID()
        >>> assert isinstance(new_id, UUID)
    """

    pass


# ADT: Union of all system effects using PEP 695 type statement
type SystemEffect = GetCurrentTime | GenerateUUID
