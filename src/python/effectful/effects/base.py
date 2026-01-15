"""Base effect protocol.

This module defines the base Effect protocol that all effects must conform to.
Using Protocol (structural typing) allows effects to be defined without inheritance.
"""

from typing import Protocol


class Effect(Protocol):
    """Base protocol for all effects.

    All effect types should be frozen dataclasses that implement this protocol.
    This enables structural typing rather than nominal typing.
    """
