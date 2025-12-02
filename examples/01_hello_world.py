"""Example 01: Hello World

Minimal effect program demonstrating basic WebSocket communication.

Run:
    python -m examples.01_hello_world
"""

import asyncio
from collections.abc import Generator

from unittest.mock import AsyncMock

from effectful import AllEffects, EffectResult, SendText, run_ws_program
from effectful.algebraic.result import Err, Ok
from effectful.infrastructure.websocket import WebSocketConnection
from effectful.interpreters.websocket import WebSocketInterpreter


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
    # Create a typed AsyncMock for the WebSocket connection (matches doctrine: spec'ed mocks)
    ws = AsyncMock(spec=WebSocketConnection)
    ws.is_open.return_value = True
    interpreter = WebSocketInterpreter(connection=ws)

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
