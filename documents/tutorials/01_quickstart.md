# Quickstart Guide

Welcome to **effectful**! This guide will get you writing effect programs in 10 minutes.

## Installation

```bash
pip install effectful
```

Or with Poetry:

```bash
poetry add effectful
```

## Your First Program

Let's write a simple program that sends a WebSocket message:

```python
from collections.abc import Generator
from effectful import (
    AllEffects,
    EffectResult,
    SendText,
    run_ws_program,
    create_composite_interpreter,
)

def hello_program() -> Generator[AllEffects, EffectResult, str]:
    """Send a greeting message over WebSocket."""
    yield SendText(text="Hello, World!")
    return "Message sent"
```

**What's happening:**
- `Generator[AllEffects, EffectResult, str]` means:
  - Yields `AllEffects` (any effect type)
  - Receives `EffectResult` (result from effect)
  - Returns `str` (final program result)
- `yield SendText(...)` requests an effect execution
- `return "Message sent"` is the program's final value

## Running the Program

Programs need an **interpreter** to execute effects:

```python
import asyncio
from effectful.testing import create_test_interpreter

async def main():
    # Create interpreter with test fakes
    interpreter = create_test_interpreter()

    # Run program
    result = await run_ws_program(hello_program(), interpreter)

    # Handle result
    match result:
        case Ok(value):
            print(f"Success: {value}")
        case Err(error):
            print(f"Error: {error}")

asyncio.run(main())
```

Output:
```
Success: Message sent
```

## Receiving Effect Results

Effects return values. Use them to build workflows:

```python
from uuid import uuid4
from effectful import GetUserById, User

def greet_user(user_id: UUID) -> Generator[AllEffects, EffectResult, str]:
    # Yield effect, receive result
    user_result = yield GetUserById(user_id=user_id)

    # Pattern match on result
    match user_result:
        case None:
            yield SendText(text="User not found")
            return "error"
        case User(name=name):
            yield SendText(text=f"Hello {name}!")
            return "success"
```

**What's happening:**
- `user_result` receives the effect result
- Pattern matching handles both success and failure cases
- Type checker ensures all cases are handled

## Testing Your Programs

Use test fakes to run programs without real infrastructure:

```python
import pytest
from effectful.testing import (
    FakeUserRepository,
    create_test_interpreter,
    unwrap_ok,
)

@pytest.mark.asyncio
async def test_greet_user():
    # Setup test data
    fake_repo = FakeUserRepository()
    user_id = uuid4()
    fake_repo._users[user_id] = User(
        id=user_id,
        email="alice@example.com",
        name="Alice"
    )

    # Create interpreter with fake
    interpreter = create_test_interpreter(user_repo=fake_repo)

    # Run program
    result = await run_ws_program(greet_user(user_id), interpreter)

    # Assert
    value = unwrap_ok(result)
    assert value == "success"
```

**Benefits:**
- Fast (no real database/WebSocket)
- Deterministic (no network flakiness)
- Isolated (tests don't interfere)

## Error Handling

All effects can fail. Handle errors explicitly:

```python
from effectful import SaveChatMessage, ChatMessage

def save_greeting(user_id: UUID, text: str) -> Generator[AllEffects, EffectResult, bool]:
    # Yield effect
    message = yield SaveChatMessage(user_id=user_id, text=text)

    # Type narrowing (effect results are unions)
    if not isinstance(message, ChatMessage):
        yield SendText(text="Failed to save message")
        return False

    yield SendText(text=f"Saved message: {message.id}")
    return True
```

**What's happening:**
- `isinstance()` checks narrow the type
- Type checker enforces handling unexpected types
- Programs fail-fast on first error

## Production Setup

For production, use real infrastructure:

```python
from fastapi import WebSocket
from effectful import create_composite_interpreter
from your_app.database import get_user_repo, get_message_repo
from your_app.cache import get_cache

async def handle_websocket(websocket: WebSocket):
    # Create interpreter with real infrastructure
    interpreter = create_composite_interpreter(
        websocket_connection=websocket,
        user_repo=get_user_repo(),
        message_repo=get_message_repo(),
        cache=get_cache(),
    )

    # Run program
    result = await run_ws_program(your_program(), interpreter)

    # Handle result
    match result:
        case Ok(value):
            await websocket.send_json({"status": "success", "data": value})
        case Err(error):
            await websocket.send_json({"status": "error", "message": str(error)})
```

## Next Steps

- [Tutorial 02: Effect Types](02_effect_types.md) - Learn about all available effects
- [Tutorial 03: ADTs and Result Types](03_adts_and_results.md) - Master algebraic data types
- [Tutorial 04: Testing Patterns](04_testing_patterns.md) - Write comprehensive tests
- [Tutorial 05: Production Deployment](05_production_deployment.md) - Deploy to production

## Quick Reference

### Available Effects

- **WebSocket**: `SendText`, `ReceiveText`, `Close`
- **Database**: `GetUserById`, `SaveChatMessage`
- **Cache**: `GetCachedProfile`, `PutCachedProfile`

### Testing Utilities

```python
from effectful.testing import (
    # Fakes
    FakeWebSocketConnection,
    FakeUserRepository,
    FakeChatMessageRepository,
    FakeProfileCache,
    create_test_interpreter,

    # Matchers
    assert_ok,
    assert_err,
    unwrap_ok,
    unwrap_err,
)
```

### Type Safety

```python
# ✅ Always use explicit types
def program() -> Generator[AllEffects, EffectResult, str]:
    ...

# ✅ Use frozen dataclasses
@dataclass(frozen=True)
class MyData:
    value: str

# ✅ Use Result for errors
from effectful.algebraic.result import Result, Ok, Err

def fallible() -> Result[int, str]:
    if condition:
        return Ok(42)
    return Err("failed")
```

---

**Next**: [Tutorial 02: Effect Types](02_effect_types.md)
