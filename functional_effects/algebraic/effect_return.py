"""EffectReturn[T] wrapper for type-safe effect results.

This module provides a wrapper that encodes which effect returned which type,
enabling better type safety and debugging in the effect interpreter.
"""

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class EffectReturn[T]:
    """Wrapper encoding which effect returned which type.

    This wrapper provides:
    - Type safety: Tracks that a specific effect produced a specific type
    - Debugging: Includes effect name for tracing
    - Telemetry: Can be used to track which effects are being executed

    Attributes:
        value: The actual return value from the effect
        effect_name: Name of the effect that produced this value (for debugging/telemetry)
    """

    value: T
    effect_name: str

    def map[U](self, f: Callable[[T], U]) -> EffectReturn[U]:
        """Map the wrapped value with function f.

        Args:
            f: Function to apply to the wrapped value

        Returns:
            New EffectReturn with mapped value and same effect_name

        Example:
            >>> result = EffectReturn(42, "GetCount")
            >>> result.map(lambda x: x * 2)
            EffectReturn(value=84, effect_name='GetCount')
        """
        return EffectReturn(f(self.value), self.effect_name)
