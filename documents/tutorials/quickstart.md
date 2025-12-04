# Quickstart Guide

**Status**: Authoritative source  
**Supersedes**: none  
**Referenced by**: documents/readme.md

> **Purpose**: Tutorial for getting started with effectful and writing your first effect program.

Welcome to **effectful**! This guide will get you writing effect programs in 10 minutes.

> **Core Doctrines**: For comprehensive patterns, see:
> - [Architecture](../engineering/architecture.md) - 5-layer architecture and design decisions
> - [Code Quality](../engineering/code_quality.md) - Type safety + purity rules
> - [Testing](../engineering/testing.md) - Coverage requirements and test patterns
> - [Docker Workflow](../engineering/docker_workflow.md) - All development happens in Docker

## Prerequisites

- Docker installed and running; containers can start from `docker/docker-compose.yml`.
- No local Poetry or Python usage (virtualenv creation disabled in `poetry.toml`).
- Read the overview in [Engineering README](../engineering/README.md) and the policy in [docker_workflow.md](../engineering/docker_workflow.md).

## Learning Objectives

- Set up the containerized development environment and run the core commands.
- Install effectful and author a minimal program using generators and effects.
- Test the program by stepping the generator without real infrastructure.

## Step 1: Install effectful in your app

Install effectful in your application:

```bash
# file: scripts/01_quickstart.sh
pip install effectful
# or
poetry add effectful
```

## Step 2: Prepare the contributor environment

> **CRITICAL**: All development happens inside Docker containers. Poetry is configured to NOT create virtual environments (`poetry.toml`).

> See [Docker Workflow](../engineering/docker_workflow.md) for complete setup.

```bash
# file: scripts/01_quickstart.sh
# Start development environment
docker compose -f docker/docker-compose.yml up -d

# Run tests
docker compose -f docker/docker-compose.yml exec effectful poetry run pytest

# Type check
docker compose -f docker/docker-compose.yml exec effectful poetry run check-code
```

**Do NOT run `poetry install` locally** - it will fail due to no-virtualenv policy enforced by `poetry.toml`.

## Step 3: Write your first program

Let's write a simple program that sends a WebSocket message:

```python
# file: examples/01_quickstart.py
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

## Step 4: Test the program

Test programs by manually stepping through the generator:

```python
# file: examples/01_quickstart.py
def test_hello_program() -> None:
    # Create generator
    gen = hello_program()

    # Get first effect
    effect = next(gen)
    assert effect.__class__.__name__ == "SendText"
    assert effect.text == "Hello, World!"

    # Send response and get final result
    try:
        gen.send(None)
    except StopIteration as e:
        result = e.value

    assert result == "Message sent"
```

**Benefits:**
- No infrastructure needed
- Fast and deterministic
- Tests pure program logic

## Step 5: Receive effect results

Effects return values. Use them to build workflows:

```python
# file: examples/01_quickstart.py
from uuid import uuid4
from effectful import GetUserById, User
from effectful.domain.user import UserNotFound

def greet_user(user_id: UUID) -> Generator[AllEffects, EffectResult, str]:
    # Yield effect, receive result
    user_result = yield GetUserById(user_id=user_id)

    # Pattern match on result
    match user_result:
        case UserNotFound():
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

## Testing Complete Programs

For more complex programs, step through the generator and verify each effect:

```python
# file: examples/01_quickstart.py
from uuid import uuid4
from effectful import GetUserById, SendText, User

def test_greet_user() -> None:
    user_id = uuid4()
    user = User(id=user_id, email="alice@example.com", name="Alice")

    # Create generator
    gen = greet_user(user_id)

    # Step 1: GetUserById effect
    effect1 = next(gen)
    assert effect1.__class__.__name__ == "GetUserById"
    assert effect1.user_id == user_id

    # Step 2: Send user, receive SendText effect
    effect2 = gen.send(user)
    assert effect2.__class__.__name__ == "SendText"
    assert "Hello Alice" in effect2.text

    # Step 3: Send None for SendText, get final result
    try:
        gen.send(None)
    except StopIteration as e:
        result = e.value

    assert result == "success"
```

**Benefits:**
- Fast (no real database/WebSocket)
- Deterministic (no network flakiness)
- Isolated (tests don't interfere)
- Tests pure program logic without interpreters

## Error Handling

All effects can fail. Handle errors explicitly:

```python
# file: examples/01_quickstart.py
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
# file: examples/01_quickstart.py
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

- [Tutorial 02: Effect Types](effect_types.md) - Learn about all available effects
- [Tutorial 03: ADTs and Result Types](adts_and_results.md) - Master algebraic data types
- [Tutorial 04: Testing Patterns](testing_guide.md) - Write comprehensive tests
- [Tutorial 05: Production Deployment](production_deployment.md) - Deploy to production

## Quick Reference

### Available Effects

- **WebSocket**: `SendText`, `ReceiveText`, `Close`
- **Database**: `GetUserById`, `SaveChatMessage`
- **Cache**: `GetCachedProfile`, `PutCachedProfile`

### Testing Utilities

```python
# file: examples/01_quickstart.py
from effectful.testing import (
    # Matchers
    assert_ok,
    assert_err,
    unwrap_ok,
    unwrap_err,
)

# For unit tests with pytest-mock:
# mock_repo = mocker.AsyncMock(spec=UserRepository)
# mock_repo.get_by_id.return_value = User(...)
```

### Type Safety

```python
# file: examples/01_quickstart.py
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

## Summary

- Installed effectful and set up Docker-backed tooling with Poetry inside the container.
- Authored a generator-based program that yields effects and returns values.
- Tested by stepping the generator and pattern-matching results with explicit Result types.

## Next Steps

- Move on to [Tutorial 02: Effect Types](effect_types.md) to explore the full effect catalog.
- Review [Testing](../engineering/testing.md) for exhaustive testing patterns and anti-patterns.
- Study [Effect Patterns](../engineering/effect_patterns.md) to compose larger workflows.

## Cross-References
- [Documentation Standards](../documentation_standards.md)
- [Engineering Standards](../engineering/README.md)
