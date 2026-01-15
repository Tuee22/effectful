"""Base interpreter protocol.

This module defines the Protocol for effect interpreters.
All interpreters must implement this interface.
"""

from typing import Protocol

from effectful.algebraic.effect_return import EffectReturn
from effectful.algebraic.result import Result
from effectful.effects.base import Effect
from effectful.interpreters.errors import InterpreterError
from effectful.programs.program_types import EffectResult


class EffectInterpreter(Protocol):
    """Protocol for effect interpreters.

    Each interpreter handles a specific subset of effects.
    """

    async def interpret(
        self, effect: Effect
    ) -> Result[EffectReturn[EffectResult], InterpreterError]:
        """Interpret an effect and return a result.

        Args:
            effect: The effect to interpret

        Returns:
            Ok(EffectReturn(value)) if successful
            Err(InterpreterError) if failed or effect not handled by this interpreter
        """
        ...
