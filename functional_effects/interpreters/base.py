"""Base interpreter protocol.

This module defines the Protocol for effect interpreters.
All interpreters must implement this interface.
"""

from typing import Protocol, TypeVar

from functional_effects.algebraic.effect_return import EffectReturn
from functional_effects.algebraic.result import Result
from functional_effects.effects.base import Effect
from functional_effects.interpreters.errors import InterpreterError

T = TypeVar("T")


class EffectInterpreter(Protocol):
    """Protocol for effect interpreters.

    Each interpreter handles a specific subset of effects.
    """

    async def interpret(self, effect: Effect) -> Result[EffectReturn[T], InterpreterError]:
        """Interpret an effect and return a result.

        Args:
            effect: The effect to interpret

        Returns:
            Ok(EffectReturn(value)) if successful
            Err(InterpreterError) if failed or effect not handled by this interpreter
        """
        ...
