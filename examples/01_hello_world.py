"""Example 01: Hello World

Minimal effect program demonstrating basic WebSocket communication.

Run:
    python -m examples.01_hello_world
"""

import asyncio
from collections.abc import Generator

from functional_effects import (
    AllEffects,
    EffectResult,
    SendText,
    run_ws_program,
)
from functional_effects.algebraic.result import Err, Ok
from functional_effects.testing import create_test_interpreter


def hello_world() -> Generator[AllEffects, EffectResult, str]:
    """Simplest possible effect program.

    Yields:
        SendText effect

    Returns:
        Success message
    """
    yield SendText(text="Hello, World!")
    return "Message sent successfully"


async def main() -> None:
    """Run the hello world program."""
    # Create test interpreter (uses fake WebSocket)
    interpreter = create_test_interpreter()

    print("Running hello_world program...")

    # Run program
    result = await run_ws_program(hello_world(), interpreter)

    # Handle result
    match result:
        case Ok(value):
            print(f"✓ Success: {value}")
        case Err(error):
            print(f"✗ Error: {error}")


if __name__ == "__main__":
    asyncio.run(main())
