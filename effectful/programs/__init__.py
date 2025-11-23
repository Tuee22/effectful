"""Program execution and type definitions.

This module provides the core program runner and type definitions:

- **run_ws_program()** - Execute effect programs to completion
- **WSProgram** - Type alias for programs returning None
- **AllEffects** - Union of all effect types
- **EffectResult** - Union of all effect result types

Example:
    >>> from effectful.programs import run_ws_program
    >>> from effectful import AllEffects, EffectResult
    >>> from collections.abc import Generator
    >>>
    >>> def my_program() -> Generator[AllEffects, EffectResult, str]:
    ...     user_result = yield GetUserById(user_id=user_id)
    ...     match user_result:
    ...         case User(name=name):
    ...             yield SendText(text=f"Hello {name}!")
    ...             return "success"
    ...         case _:
    ...             return "not_found"
    >>>
    >>> result = await run_ws_program(my_program(), interpreter)
    >>> match result:
    ...     case Ok(value):
    ...         print(f"Program returned: {value}")
    ...     case Err(error):
    ...         print(f"Program failed: {error}")

Program Execution:
    run_ws_program uses the generator protocol:

    1. Call next(program) to get first effect
    2. Call interpreter.interpret(effect) to execute
    3. Call program.send(result) to resume with result
    4. Repeat until StopIteration (program completes)
    5. Return Ok(final_value) or Err(first_error)

    Programs are **fail-fast**: First Err stops execution immediately.

See Also:
    - effectful.programs.program_types - Type definitions
    - effectful.programs.runners - run_ws_program implementation
    - effectful.interpreters - Effect interpreters
"""

from effectful.programs.program_types import AllEffects, EffectResult, WSProgram
from effectful.programs.runners import run_ws_program

__all__ = [
    "run_ws_program",
    "AllEffects",
    "EffectResult",
    "WSProgram",
]
