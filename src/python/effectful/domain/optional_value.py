"""Optional value algebraic data type to avoid bare Optional usage.

This module provides a small ADT that encodes whether a value is present or
absent with an explicit reason. It replaces `Optional[T]` sentinels while still
allowing concise construction via helper functions.
"""

from dataclasses import dataclass
from typing import Generic, TypeVar

T_co = TypeVar("T_co", covariant=True)


@dataclass(frozen=True)
class Provided(Generic[T_co]):
    """Represents a present value."""

    value: T_co


@dataclass(frozen=True)
class Absent(Generic[T_co]):
    """Represents an intentionally missing value with a reason."""

    reason: str = "not_provided"


type OptionalValue[T_co] = Provided[T_co] | Absent[T_co]


def to_optional_value(value: T_co | None, *, reason: str = "not_provided") -> OptionalValue[T_co]:
    """Convert an optional input into the OptionalValue ADT."""
    if value is None:
        return Absent(reason=reason)
    return Provided(value=value)


def from_optional_value(optional_value: OptionalValue[T_co]) -> T_co | None:
    """Convert OptionalValue back to an optional sentinel for boundary calls."""
    if isinstance(optional_value, Provided):
        return optional_value.value
    return None
