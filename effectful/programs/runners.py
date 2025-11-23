"""Program runners for executing effect programs.

This module provides functions to run effect programs to completion using
interpreters. The main entry point is run_ws_program which drives a generator-based
program forward, interpreting each effect and propagating results.

Key Concepts:
- Programs are generators that yield effects and receive results
- Runners drive the program forward using .send() and next()
- Results are propagated via Result[T, E] for explicit error handling
- StopIteration captures the program's final return value

Note on Purity:
    The while loop in run_ws_program is an acceptable exception to the no-loops
    doctrine because it serves as the core program execution driver (similar to
    the trampoline driver). It cannot be replaced with a trampoline without adding
    complexity, as each iteration requires async I/O.

Example:
    >>> def chat_program(user_id: UUID) -> WSProgram:
    ...     user = yield GetUserById(user_id)
    ...     yield SendText(f"Hello {user.name}")
    ...
    >>> result = await run_ws_program(chat_program(user_id), interpreter)
    >>> match result:
    ...     case Ok(value): print(f"Success: {value}")
    ...     case Err(error): print(f"Failed: {error}")
"""

from collections.abc import Generator
from typing import TypeVar

from effectful.algebraic.effect_return import EffectReturn
from effectful.algebraic.result import Err, Ok, Result
from effectful.interpreters.base import EffectInterpreter
from effectful.interpreters.errors import InterpreterError
from effectful.programs.program_types import AllEffects, EffectResult

T = TypeVar("T")


async def run_ws_program(
    program: Generator[AllEffects, EffectResult, T],
    interpreter: EffectInterpreter,
) -> Result[T, InterpreterError]:
    """Run an effect program to completion using the provided interpreter.

    This is the main entry point for executing effect programs. It handles:
    - Driving the generator forward with .send()
    - Interpreting each yielded effect
    - Error propagation via Result type (fail-fast)
    - Type-safe return values via generics

    The execution model:
    1. Get first effect from program using next()
    2. Interpret effect using provided interpreter
    3. If Ok: unwrap EffectReturn.value and send to program
    4. If Err: immediately return error (fail-fast)
    5. Repeat until StopIteration (program completes)
    6. Return final value from StopIteration.value

    Args:
        program: Generator yielding effects and receiving results.
                 Type: Generator[AllEffects, EffectResult, T]
                 - Yields: AllEffects (WebSocket | Database | Cache effects)
                 - Receives: EffectResult (None | str | User | ChatMessage | ...)
                 - Returns: T (final program value)
        interpreter: EffectInterpreter implementation (usually CompositeInterpreter).
                    Must handle all effect types yielded by the program.

    Returns:
        Ok(final_value) if program completes successfully.
        Err(InterpreterError) if any effect fails (UnhandledEffectError,
        DatabaseError, WebSocketClosedError, CacheError).

    Example:
        >>> from effectful.effects.database import GetUserById
        >>> from effectful.effects.websocket import SendText
        >>> from effectful.interpreters.composite import create_composite_interpreter
        >>>
        >>> def greet_user(user_id: UUID) -> WSProgram:
        ...     user = yield GetUserById(user_id)
        ...     if user is None:
        ...         yield SendText("User not found")
        ...         return False
        ...     yield SendText(f"Hello {user.name}!")
        ...     return True
        >>>
        >>> interpreter = create_composite_interpreter(...)
        >>> result = await run_ws_program(greet_user(user_id), interpreter)
        >>> match result:
        ...     case Ok(success): print(f"Greeting sent: {success}")
        ...     case Err(error): print(f"Failed: {error}")

    Note:
        - Programs must yield AllEffects types only
        - Interpreter must handle all yielded effect types
        - Return values must be type-compatible with declared T
        - Errors are propagated immediately (fail-fast, no retry)
    """
    try:
        # Start the program - get first effect
        effect = next(program)

        # Program execution loop - acceptable while loop (core driver, see docstring)
        while True:
            # Interpret the current effect
            result: Result[
                EffectReturn[EffectResult], InterpreterError
            ] = await interpreter.interpret(effect)

            # Handle interpretation result
            match result:
                case Ok(EffectReturn(value=effect_value, effect_name=_)):
                    # Effect succeeded - send result to program, get next effect
                    # The program receives effect_value (EffectResult type)
                    effect = program.send(effect_value)

                case Err(interpreter_error):
                    # Effect failed - propagate error immediately (fail-fast)
                    # No cleanup, no retry - explicit error handling
                    return Err(interpreter_error)

    except StopIteration as stop:
        # Program completed successfully
        # StopIteration.value contains the program's return value
        final_value: T = stop.value
        return Ok(final_value)
