"""WebSocket interpreter implementation.

This module implements the interpreter for WebSocket effects.
"""

from dataclasses import dataclass

from functional_effects.algebraic.effect_return import EffectReturn
from functional_effects.algebraic.result import Err, Ok, Result
from functional_effects.effects.base import Effect
from functional_effects.effects.websocket import Close, CloseReason, ReceiveText, SendText
from functional_effects.infrastructure.websocket import WebSocketConnection
from functional_effects.interpreters.errors import (
    InterpreterError,
    UnhandledEffectError,
    WebSocketClosedError,
)
from functional_effects.programs.program_types import EffectResult


@dataclass(frozen=True)
class WebSocketInterpreter:
    """Interpreter for WebSocket effects.

    Attributes:
        connection: WebSocket connection protocol implementation
    """

    connection: WebSocketConnection

    async def interpret(
        self, effect: Effect
    ) -> Result[EffectReturn[EffectResult], InterpreterError]:
        """Interpret a WebSocket effect.

        Args:
            effect: The effect to interpret

        Returns:
            Ok(EffectReturn(value)) if successful
            Err(InterpreterError) if failed or not a WebSocket effect
        """
        match effect:
            case SendText(text=text):
                return await self._handle_send_text(text, effect)
            case ReceiveText():
                return await self._handle_receive_text(effect)
            case Close(reason=reason):
                return await self._handle_close(reason, effect)
            case _:
                return Err(
                    UnhandledEffectError(
                        effect=effect,
                        available_interpreters=["WebSocketInterpreter"],
                    )
                )

    async def _handle_send_text(
        self, text: str, effect: Effect
    ) -> Result[EffectReturn[EffectResult], InterpreterError]:
        """Handle SendText effect."""
        is_open = await self.connection.is_open()
        match is_open:
            case True:
                await self.connection.send_text(text)
                return Ok(EffectReturn(value=None, effect_name="SendText"))
            case False:
                return Err(
                    WebSocketClosedError(
                        effect=effect,
                        close_code=1006,
                        reason="Connection closed before send",
                    )
                )

    async def _handle_receive_text(
        self, effect: Effect
    ) -> Result[EffectReturn[EffectResult], InterpreterError]:
        """Handle ReceiveText effect."""
        is_open = await self.connection.is_open()
        match is_open:
            case True:
                text = await self.connection.receive_text()
                return Ok(EffectReturn(value=text, effect_name="ReceiveText"))
            case False:
                return Err(
                    WebSocketClosedError(
                        effect=effect,
                        close_code=1006,
                        reason="Connection closed before receive",
                    )
                )

    async def _handle_close(
        self, _reason: CloseReason, _effect: Effect
    ) -> Result[EffectReturn[EffectResult], InterpreterError]:
        """Handle Close effect."""
        # Close always succeeds, even if already closed
        await self.connection.close()
        return Ok(EffectReturn(value=None, effect_name="Close"))
