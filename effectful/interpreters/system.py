"""System interpreter implementation.

This module implements the interpreter for System effects
(GetCurrentTime, GenerateUUID).
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from effectful.algebraic.effect_return import EffectReturn
from effectful.algebraic.result import Err, Ok, Result
from effectful.effects.base import Effect
from effectful.effects.system import GenerateUUID, GetCurrentTime
from effectful.interpreters.errors import InterpreterError, UnhandledEffectError
from effectful.programs.program_types import EffectResult


@dataclass(frozen=True)
class SystemInterpreter:
    """Interpreter for System effects.

    Handles GetCurrentTime and GenerateUUID effects by delegating
    to actual system operations.

    This interpreter has no dependencies - it directly calls
    datetime.now() and uuid4().
    """

    async def interpret(
        self, effect: Effect
    ) -> Result[EffectReturn[EffectResult], InterpreterError]:
        """Interpret a System effect.

        Args:
            effect: The effect to interpret

        Returns:
            Ok(EffectReturn(value)) if successful
            Err(UnhandledEffectError) if not a System effect
        """
        match effect:
            case GetCurrentTime():
                current_time = datetime.now(timezone.utc)
                return Ok(EffectReturn(value=current_time, effect_name="GetCurrentTime"))
            case GenerateUUID():
                new_uuid = uuid4()
                return Ok(EffectReturn(value=new_uuid, effect_name="GenerateUUID"))
            case _:
                return (
                    Ok(EffectReturn(value=None, effect_name="UnhandledEffectError"))
                    if False
                    else self._unhandled(effect)
                )

    def _unhandled(self, effect: Effect) -> Result[EffectReturn[EffectResult], InterpreterError]:
        """Return UnhandledEffectError for unknown effects."""
        return Err(
            UnhandledEffectError(
                effect=effect,
                available_interpreters=["SystemInterpreter"],
            )
        )
