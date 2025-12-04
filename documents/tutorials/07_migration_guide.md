# Tutorial 07: Migration Guide

This tutorial guides you through migrating from imperative WebSocket code to effectful programs.

> **Core Doctrine**: For architecture patterns and type safety requirements, see:
> - [architecture.md](../engineering/architecture.md) - 5-layer architecture
> - [Code Quality](../engineering/code_quality.md) - Result types and ADTs

## Prerequisites

- Completed previous tutorials (01-06)
- Understanding of effectful architecture
- Familiarity with async/await patterns
- Experience with imperative WebSocket code

## Learning Objectives

By the end of this tutorial, you will:
- Identify imperative patterns to replace with effect programs
- Transform imperative code to functional programs
- Migrate error handling to Result types
- Replace mutable state with immutable data flow
- Incrementally adopt effectful in existing codebases
- Test both imperative and functional code during migration

---

## Part 1: Identifying Migration Opportunities

### Imperative WebSocket Handler (Before)

**Anti-Pattern**: Direct WebSocket manipulation, exception-based errors, mutable state.

```python
# ❌ BEFORE: Imperative WebSocket handler
from fastapi import WebSocket, WebSocketDisconnect
import asyncpg
import logging

logger = logging.getLogger(__name__)


async def handle_chat_connection(websocket: WebSocket, user_id: str) -> None:
    """Imperative WebSocket handler with direct I/O."""
    await websocket.accept()

    db_conn = None

    try:
        # Mutable state
        db_conn = await asyncpg.connect(DATABASE_URL)

        # Direct database access
        user_record = await db_conn.fetchrow(
            "SELECT id, name, email FROM users WHERE id = $1", user_id
        )

        if user_record is None:
            # Direct WebSocket manipulation
            await websocket.send_text("Error: User not found")
            await websocket.close(code=1008)
            return

        # Direct WebSocket manipulation
        await websocket.send_text(f"Hello {user_record['name']}!")

        # Receive message
        message_text = await websocket.receive_text()

        # Direct database access
        await db_conn.execute(
            "INSERT INTO chat_messages (user_id, text) VALUES ($1, $2)",
            user_id,
            message_text,
        )

        # Direct WebSocket manipulation
        await websocket.send_text("Message saved")

    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except asyncpg.PostgresError as e:
        logger.error(f"Database error: {e}")
        if websocket.client_state.value == 1:  # CONNECTED
            await websocket.send_text("Error: Database failure")
            await websocket.close(code=1011)
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        if websocket.client_state.value == 1:  # CONNECTED
            await websocket.close(code=1011)
    finally:
        if db_conn is not None:
            await db_conn.close()
```

**Problems**:
- ❌ Direct I/O operations (WebSocket, database) - hard to test
- ❌ Exception-based error handling - unclear control flow
- ❌ Mutable state (`db_conn`) - resource leaks possible
- ❌ Mixed concerns (I/O, business logic, error handling)
- ❌ No type safety for WebSocket state
- ❌ Difficult to compose or reuse

### Functional Program (After)

**Pattern**: Declarative effects, explicit error handling, immutable data flow.

```python
# ✅ AFTER: Functional program with effects
from collections.abc import Generator
from effectful import (
    AllEffects,
    EffectResult,
    GetUserById,
    SendText,
    ReceiveText,
    SaveChatMessage,
    Close,
)
from effectful.domain import User, ChatMessage
from effectful.domain.user import UserNotFound
from uuid import UUID


def chat_program(user_id: UUID) -> Generator[AllEffects, EffectResult, str]:
    """Functional chat program with declarative effects."""
    # Effect: Lookup user
    user = yield GetUserById(user_id=user_id)

    match user:
        case UserNotFound():
            # Effect: Send error message
            yield SendText(text="Error: User not found")
            # Effect: Close connection
            yield Close(code=1008, reason="User not found")
            return "user_not_found"

        case User(name=name):
            # Effect: Send greeting
            yield SendText(text=f"Hello {name}!")

            # Effect: Receive message
            message_text = yield ReceiveText()
            assert isinstance(message_text, str)

            # Effect: Save message
            message = yield SaveChatMessage(user_id=user_id, text=message_text)
            assert isinstance(message, ChatMessage)

            # Effect: Send confirmation
            yield SendText(text="Message saved")

            return "message_saved"
```

**Benefits**:
- ✅ Pure business logic - effects are declarative
- ✅ Easy to test - no real I/O in program
- ✅ Immutable data flow - no mutable state
- ✅ Explicit error handling with pattern matching
- ✅ Type-safe - all values have known types
- ✅ Composable - can be used in larger workflows

### Visual Comparison: Imperative vs Functional

The following diagrams show the key architectural differences:

```mermaid
flowchart TB
    ImperativeStart[Imperative - WebSocket Handler]
    ImperativeDB[Imperative - Direct DB Connection]
    ImperativeErrors[Imperative - Try/Except]
    ImperativeState[Imperative - Mutable State]
    ImperativeIO[Imperative - Direct WebSocket I/O]
    ImperativeCleanup[Imperative - Finally Cleanup]

    FunctionalStart[Functional - Effect Program Generator]
    FunctionalYield[Functional - Yield Effects (Pure Data)]
    FunctionalMatch[Functional - Pattern Match Results]
    FunctionalImmutable[Functional - Immutable Values]
    FunctionalInterpreter[Functional - Interpreter Owns I/O]
    FunctionalManage[Functional - Managed Resources]

    ImperativeStart --> ImperativeDB --> ImperativeErrors --> ImperativeState --> ImperativeIO --> ImperativeCleanup
    FunctionalStart --> FunctionalYield --> FunctionalMatch --> FunctionalImmutable --> FunctionalInterpreter --> FunctionalManage
```

**Key Differences:**

| Aspect | Imperative | Functional |
|--------|-----------|-----------|
| **I/O** | Direct (websocket.send, db.query) | Declarative (yield SendText, yield GetUserById) |
| **Errors** | Exceptions (try/except) | Result types (Ok/Err with pattern matching) |
| **State** | Mutable (db_conn variable) | Immutable (all values frozen dataclasses) |
| **Testing** | Requires mocks for WebSocket/DB | Generator-based testing (no mocks needed) |
| **Composition** | Difficult (async callbacks) | Easy (yield from) |
| **Type Safety** | Partial (exceptions not in types) | Full (Result types, exhaustive matching) |

---

## Part 2: Step-by-Step Migration

### Step 1: Identify Effects

**Task**: Extract all I/O operations into effect descriptions.

**Imperative Code**:
```python
# ❌ Direct I/O
user_record = await db_conn.fetchrow("SELECT ...", user_id)
await websocket.send_text("Hello")
```

**Functional Code**:
```python
# ✅ Declarative effects
user = yield GetUserById(user_id=user_id)
yield SendText(text="Hello")
```

### Step 2: Replace Exceptions with Result Types

**Imperative Code**:
```python
# ❌ Exception-based error handling
try:
    user_record = await db_conn.fetchrow("SELECT ...", user_id)
    if user_record is None:
        raise ValueError("User not found")
except asyncpg.PostgresError as e:
    logger.error(f"Database error: {e}")
    # Handle error...
```

**Functional Code**:
```python
# ✅ Result-based error handling
result = await run_ws_program(chat_program(user_id), interpreter)

match result:
    case Ok(value):
        logger.info(f"Program succeeded: {value}")
    case Err(DatabaseError(db_error=msg, is_retryable=True)):
        logger.error(f"Retryable database error: {msg}")
        # Retry logic...
    case Err(DatabaseError(db_error=msg, is_retryable=False)):
        logger.error(f"Permanent database error: {msg}")
    case Err(WebSocketClosedError(close_code=code, reason=reason)):
        logger.info(f"WebSocket closed: {code} - {reason}")
```

### Step 3: Eliminate Mutable State

**Imperative Code**:
```python
# ❌ Mutable connection state
db_conn = None
try:
    db_conn = await asyncpg.connect(DATABASE_URL)
    # ... use db_conn
finally:
    if db_conn is not None:
        await db_conn.close()
```

**Functional Code**:
```python
# ✅ Immutable data flow - interpreter manages connections
async with get_db_connection() as db_conn:
    user_repo = PostgresUserRepository(connection=db_conn)
    message_repo = PostgresChatMessageRepository(connection=db_conn)

    interpreter = create_composite_interpreter(
        websocket_connection=ws_conn,
        user_repo=user_repo,
        message_repo=message_repo,
        cache=cache,
    )

    result = await run_ws_program(chat_program(user_id), interpreter)
```

### Step 4: Extract Business Logic into Programs

**Imperative Code**:
```python
# ❌ Business logic mixed with I/O
async def handle_user_message(websocket: WebSocket, db_conn, user_id: str) -> None:
    user_record = await db_conn.fetchrow("SELECT ...", user_id)

    if user_record is None:
        await websocket.send_text("User not found")
        return

    await websocket.send_text(f"Hello {user_record['name']}")

    message_text = await websocket.receive_text()

    await db_conn.execute("INSERT INTO chat_messages ...", user_id, message_text)

    await websocket.send_text("Saved")
```

**Functional Code**:
```python
# ✅ Pure business logic - testable without I/O
def handle_user_message(
    user_id: UUID,
) -> Generator[AllEffects, EffectResult, str]:
    """Pure business logic."""
    user = yield GetUserById(user_id=user_id)

    match user:
        case None:
            yield SendText(text="User not found")
            return "not_found"
        case User(name=name):
            yield SendText(text=f"Hello {name}")

            message_text = yield ReceiveText()
            assert isinstance(message_text, str)

            yield SaveChatMessage(user_id=user_id, text=message_text)

            yield SendText(text="Saved")

            return "saved"
```

---

## Part 3: Incremental Adoption

### Strategy 1: Parallel Implementation

**Pattern**: Run old and new implementations side-by-side during migration.

```python
from fastapi import WebSocket
from effectful import run_ws_program, create_composite_interpreter


async def websocket_endpoint(websocket: WebSocket, use_functional: bool = False) -> None:
    """Endpoint supporting both implementations."""
    await websocket.accept()

    if use_functional:
        # New functional implementation
        async with get_db_connection() as db_conn:
            interpreter = create_composite_interpreter(
                websocket_connection=FastAPIWebSocketConnection(websocket),
                user_repo=PostgresUserRepository(connection=db_conn),
                message_repo=PostgresChatMessageRepository(connection=db_conn),
                cache=RedisProfileCache(redis=get_redis()),
            )

            result = await run_ws_program(chat_program(user_id), interpreter)

            match result:
                case Ok(_):
                    logger.info("Functional implementation succeeded")
                case Err(error):
                    logger.error(f"Functional implementation failed: {error}")
    else:
        # Old imperative implementation
        await handle_chat_connection(websocket, user_id)
```

### Strategy 2: Feature Flags

**Pattern**: Use feature flags to gradually roll out functional implementation.

```python
from backend.core.settings import settings


@app.websocket("/ws/chat")
async def websocket_chat_endpoint(websocket: WebSocket, user_id: str) -> None:
    """WebSocket endpoint with feature flag."""
    await websocket.accept()

    # Feature flag determines implementation
    if settings.use_effectful:
        # Functional implementation
        result = await run_functional_chat(websocket, UUID(user_id))
    else:
        # Imperative implementation
        await handle_chat_connection(websocket, user_id)
```

### Strategy 3: Strangler Fig Pattern

**Pattern**: Incrementally replace imperative code by wrapping it in functional abstractions.

**Step 1**: Wrap existing imperative function in effect interpreter.

```python
# Existing imperative function
async def legacy_send_message(websocket: WebSocket, text: str) -> None:
    """Legacy imperative function."""
    await websocket.send_text(text)


# Wrap in functional interpreter
class LegacyWebSocketInterpreter:
    """Interpreter wrapping legacy WebSocket code."""

    def __init__(self, websocket: WebSocket) -> None:
        self.websocket = websocket

    async def interpret(
        self, effect: WebSocketEffect
    ) -> Result[EffectReturn[EffectResult], InterpreterError]:
        match effect:
            case SendText(text=text):
                # Delegate to legacy function
                try:
                    await legacy_send_message(self.websocket, text)
                    return Ok(EffectReturn(value=None, effect_name="SendText"))
                except Exception as e:
                    return Err(
                        WebSocketClosedError(
                            effect=effect, close_code=1006, reason=str(e)
                        )
                    )
            case _:
                return Err(
                    UnhandledEffectError(
                        effect=effect, interpreter_name="LegacyWebSocketInterpreter"
                    )
                )
```

**Step 2**: Use functional program with legacy interpreter.

```python
# Functional program using legacy interpreter
interpreter = create_composite_interpreter(
    websocket_connection=LegacyWebSocketInterpreter(websocket),  # Legacy!
    user_repo=PostgresUserRepository(connection=db_conn),
    message_repo=PostgresChatMessageRepository(connection=db_conn),
    cache=cache,
)

result = await run_ws_program(chat_program(user_id), interpreter)
```

**Step 3**: Replace legacy interpreter with functional implementation incrementally.

---

## Part 4: Testing During Migration

### Test Both Implementations

**Pattern**: Parameterized tests for imperative and functional implementations.

```python
import pytest
from pytest_mock import MockerFixture


@pytest.mark.parametrize("implementation", ["imperative", "functional"])
@pytest.mark.asyncio()
async def test_chat_handler(implementation: str, mocker: MockerFixture) -> None:
    """Test both imperative and functional implementations."""
    user_id = uuid4()

    if implementation == "imperative":
        # Test imperative implementation
        mock_websocket = mocker.AsyncMock(spec=WebSocket)
        mock_db_conn = mocker.AsyncMock(spec=asyncpg.Connection)

        # Mock database response
        mock_db_conn.fetchrow.return_value = {
            "id": str(user_id),
            "name": "Alice",
            "email": "alice@example.com",
        }

        await handle_chat_connection(mock_websocket, str(user_id))

        # Verify WebSocket calls
        mock_websocket.send_text.assert_any_call("Hello Alice!")

    elif implementation == "functional":
        # Test functional implementation
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)

        user = User(id=user_id, name="Alice", email="alice@example.com")
        mock_user_repo.get_by_id.return_value = UserFound(user=user, source="database")

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mocker.AsyncMock(spec=ChatMessageRepository),
            cache=mocker.AsyncMock(spec=ProfileCache),
        )

        result = await run_ws_program(chat_program(user_id), interpreter)

        # Verify result
        assert result.is_ok()
        mock_ws.send_text.assert_any_call("Hello Alice!")
```

### Test Migration Adapter

**Pattern**: Test that legacy wrapper behaves like functional implementation.

```python
@pytest.mark.asyncio()
async def test_legacy_wrapper_compatibility(mocker: MockerFixture) -> None:
    """Test that legacy wrapper is compatible with functional programs."""
    mock_websocket = mocker.AsyncMock(spec=WebSocket)

    # Legacy interpreter wrapping imperative code
    legacy_interpreter = LegacyWebSocketInterpreter(mock_websocket)

    # Test with functional program
    def simple_program() -> Generator[AllEffects, EffectResult, None]:
        yield SendText(text="Hello")
        return None

    # Should work with legacy interpreter
    result = await run_ws_program(simple_program(), legacy_interpreter)

    assert result.is_ok()
    mock_websocket.send_text.assert_called_once_with("Hello")
```

---

## Part 5: Common Migration Challenges

### Challenge 1: Request-Response Cycles

**Problem**: Imperative code often has multiple request-response cycles.

**Imperative Code**:
```python
# ❌ Multiple request-response cycles
async def chat_loop(websocket: WebSocket, db_conn) -> None:
    while True:
        try:
            message = await websocket.receive_text()

            # Process message...
            response = f"Echo: {message}"

            await websocket.send_text(response)

        except WebSocketDisconnect:
            break
```

**Functional Solution**:
```python
# ✅ Recursive program for loop behavior
def chat_loop_program() -> Generator[AllEffects, EffectResult, None]:
    """Recursive program for request-response loop."""
    while True:
        # Receive message (will fail with WebSocketClosedError when disconnected)
        message = yield ReceiveText()
        assert isinstance(message, str)

        # Process and respond
        response = f"Echo: {message}"
        yield SendText(text=response)

    return None


# Run with automatic error handling for disconnect
result = await run_ws_program(chat_loop_program(), interpreter)

match result:
    case Err(WebSocketClosedError(close_code=1000)):
        logger.info("Client disconnected normally")
    case Err(error):
        logger.error(f"Loop failed: {error}")
```

### Challenge 2: Shared Mutable State

**Problem**: Imperative code often uses shared mutable state.

**Imperative Code**:
```python
# ❌ Shared mutable state
active_connections: dict[str, WebSocket] = {}


async def handle_connection(websocket: WebSocket, user_id: str) -> None:
    active_connections[user_id] = websocket  # Mutation!

    try:
        # Handle messages...
        pass
    finally:
        del active_connections[user_id]  # Mutation!
```

**Functional Solution**:
```python
# ✅ Immutable state managed by application layer
from dataclasses import dataclass, replace


@dataclass(frozen=True)
class ConnectionState:
    """Immutable connection state."""
    active_users: frozenset[UUID]


# State transitions return new state (immutable)
def add_user(state: ConnectionState, user_id: UUID) -> ConnectionState:
    """Return new state with user added."""
    return replace(state, active_users=state.active_users | {user_id})


def remove_user(state: ConnectionState, user_id: UUID) -> ConnectionState:
    """Return new state with user removed."""
    return replace(state, active_users=state.active_users - {user_id})


# Application manages state transitions
state = ConnectionState(active_users=frozenset())

# Add user
state = add_user(state, user_id)

# Run program
result = await run_ws_program(chat_program(user_id), interpreter)

# Remove user
state = remove_user(state, user_id)
```

### Challenge 3: Background Tasks

**Problem**: Imperative code often spawns background tasks.

**Imperative Code**:
```python
# ❌ Background task spawned inside handler
async def handle_connection(websocket: WebSocket) -> None:
    # Spawn background task
    asyncio.create_task(send_periodic_updates(websocket))

    # Handle messages...
    pass
```

**Functional Solution**:
```python
# ✅ Explicit effect for background operations
# (Future enhancement - not yet implemented)
# def periodic_updates_program() -> Generator[AllEffects, EffectResult, None]:
#     while True:
#         yield Sleep(seconds=5.0)
#         yield SendText(text="Update")

# Current workaround: Manage background tasks at application layer
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Application layer manages background tasks."""

    # Interpreter setup...
    interpreter = create_composite_interpreter(...)

    # Background task at application layer
    update_task = asyncio.create_task(send_periodic_updates(websocket))

    try:
        # Run main program
        result = await run_ws_program(chat_program(user_id), interpreter)
    finally:
        # Clean up background task
        update_task.cancel()
        try:
            await update_task
        except asyncio.CancelledError:
            pass
```

---

## Part 6: Migration Checklist

### Pre-Migration

- [ ] Identify all I/O operations (WebSocket, database, cache, HTTP)
- [ ] Document current error handling patterns
- [ ] Establish test coverage for existing behavior
- [ ] Identify shared mutable state
- [ ] List external dependencies (third-party services)

### During Migration

- [ ] Create effect types for all I/O operations
- [ ] Write functional programs for business logic
- [ ] Implement interpreters for effects
- [ ] Replace exception handling with Result types
- [ ] Eliminate mutable state
- [ ] Add tests for functional programs
- [ ] Run both implementations in parallel (feature flag)

### Post-Migration

- [ ] Remove imperative implementation
- [ ] Update documentation
- [ ] Monitor error rates and performance
- [ ] Validate type safety (mypy --strict passes)
- [ ] Remove feature flags

---

## Best Practices

### ✅ DO

1. **Migrate Incrementally**
   ```python
   # ✅ Start with one endpoint
   @app.websocket("/ws/chat")  # Migrate first
   async def chat_endpoint(websocket: WebSocket) -> None:
       result = await run_ws_program(chat_program(), interpreter)

   @app.websocket("/ws/notifications")  # Migrate later
   async def notifications_endpoint(websocket: WebSocket) -> None:
       await legacy_notifications_handler(websocket)
   ```

2. **Test Both Implementations During Migration**
   ```python
   # ✅ Parameterized tests
   @pytest.mark.parametrize("implementation", ["imperative", "functional"])
   def test_handler(implementation: str) -> None:
       # Test both...
       pass
   ```

3. **Use Feature Flags**
   ```python
   # ✅ Gradual rollout
   if settings.use_effectful:
       result = await run_functional_implementation()
   else:
       await legacy_implementation()
   ```

4. **Monitor Error Rates**
   ```python
   # ✅ Track errors during migration
   result = await run_ws_program(program(), interpreter)

   match result:
       case Err(error):
           # Track error type and rate
           metrics.increment(f"functional.error.{type(error).__name__}")
   ```

### ❌ DON'T

1. **Don't Migrate Everything at Once**
   ```python
   # ❌ Big bang migration (risky!)
   # Rewriting entire codebase in one PR

   # ✅ Incremental migration
   # One endpoint/feature at a time
   ```

2. **Don't Break Existing Tests**
   ```python
   # ❌ Removing tests during migration
   # Deleting imperative tests before functional tests pass

   # ✅ Keep both test suites until migration complete
   ```

3. **Don't Ignore Type Safety**
   ```python
   # ❌ Using overly generic types during migration (breaks guarantees)
   def migrate_handler(data: object) -> object:  # Lost type safety!
       return data

   # ✅ Maintain type safety
   def migrate_handler(user_id: UUID) -> Generator[AllEffects, EffectResult, str]:
       ...
   ```

4. **Don't Skip Error Handling Migration**
   ```python
   # ❌ Keeping exception-based error handling
   try:
       result = await run_ws_program(program(), interpreter)
   except Exception:
       pass  # Lost error information!

   # ✅ Use Result type for explicit error handling
   result = await run_ws_program(program(), interpreter)
   match result:
       case Err(error):
           logger.error(f"Program failed: {error}")
   ```

---

## Next Steps

- Review [API Reference](../api/) for complete effectful API
- Study [examples/](/examples/) for real-world migration examples
- Read [architecture.md](../engineering/architecture.md) for design principles

## Summary

You learned how to:
- ✅ Identify imperative patterns to replace with effect programs
- ✅ Transform imperative code to functional programs
- ✅ Migrate error handling to Result types
- ✅ Replace mutable state with immutable data flow
- ✅ Incrementally adopt effectful using feature flags and parallel implementations
- ✅ Test both imperative and functional code during migration
- ✅ Handle common migration challenges (request-response cycles, shared state, background tasks)

Your migration strategy is solid and low-risk! 🎉

---

**Last Updated**: 2025-12-01  
**Supersedes**: none  
**Referenced by**: documents/README.md
