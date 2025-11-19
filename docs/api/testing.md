# Testing API Reference

This document provides a comprehensive reference for testing effect programs.

## Overview

The functional-effects package provides utilities for testing effect programs without requiring real infrastructure. Tests use pytest-mock to create controlled test doubles.

## Test Matchers

Import matchers from the testing module:

```python
from functional_effects.testing import (
    assert_ok,
    assert_err,
    unwrap_ok,
    unwrap_err,
    assert_ok_value,
    assert_err_message,
)
```

### assert_ok

Assert that a Result is Ok (success).

**Type Signature**:
```python
def assert_ok[T, E](result: Result[T, E]) -> None
```

**Usage**:
```python
from functional_effects import run_ws_program, Ok
from functional_effects.testing import assert_ok

result = await run_ws_program(my_program(), interpreter)
assert_ok(result)  # Passes if result is Ok, fails if Err
```

**Failure Message**:
```
AssertionError: Expected Ok, got Err(DatabaseError(...))
```

---

### assert_err

Assert that a Result is Err (failure).

**Type Signature**:
```python
def assert_err[T, E](result: Result[T, E], expected_error_type: type[E] | None = None) -> None
```

**Parameters**:
- `result` - The Result to check
- `expected_error_type` - Optional specific error type to expect

**Usage**:
```python
from functional_effects import run_ws_program, Err
from functional_effects.testing import assert_err
from functional_effects.interpreters.errors import DatabaseError

result = await run_ws_program(failing_program(), interpreter)

# Assert any error
assert_err(result)

# Assert specific error type
assert_err(result, DatabaseError)
```

**Failure Messages**:
```
AssertionError: Expected Err, got Ok(42)
AssertionError: Expected Err(DatabaseError), got Err(WebSocketClosedError(...))
```

---

### unwrap_ok

Extract the success value from an Ok result.

**Type Signature**:
```python
def unwrap_ok[T, E](result: Result[T, E]) -> T
```

**Usage**:
```python
from functional_effects import run_ws_program
from functional_effects.testing import unwrap_ok

result = await run_ws_program(my_program(), interpreter)
value = unwrap_ok(result)  # Returns T, or raises if Err

assert value == "expected_value"
```

**Failure**:
```python
# Raises AssertionError if result is Err
value = unwrap_ok(Err("failed"))  # AssertionError: Expected Ok, got Err("failed")
```

---

### unwrap_err

Extract the error value from an Err result.

**Type Signature**:
```python
def unwrap_err[T, E](result: Result[T, E]) -> E
```

**Usage**:
```python
from functional_effects import run_ws_program
from functional_effects.testing import unwrap_err
from functional_effects.interpreters.errors import DatabaseError

result = await run_ws_program(failing_program(), interpreter)
error = unwrap_err(result)  # Returns E, or raises if Ok

assert isinstance(error, DatabaseError)
assert "Connection timeout" in error.db_error
```

**Failure**:
```python
# Raises AssertionError if result is Ok
error = unwrap_err(Ok(42))  # AssertionError: Expected Err, got Ok(42)
```

---

### assert_ok_value

Assert Ok result with specific value.

**Type Signature**:
```python
def assert_ok_value[T, E](result: Result[T, E], expected_value: T) -> None
```

**Usage**:
```python
from functional_effects import run_ws_program
from functional_effects.testing import assert_ok_value

result = await run_ws_program(my_program(), interpreter)
assert_ok_value(result, "success")  # Passes if Ok("success")
```

**Failure Messages**:
```
AssertionError: Expected Ok, got Err(...)
AssertionError: Expected Ok("success"), got Ok("failed")
```

---

### assert_err_message

Assert Err result contains specific message substring.

**Type Signature**:
```python
def assert_err_message[T, E](result: Result[T, E], expected_substring: str) -> None
```

**Usage**:
```python
from functional_effects import run_ws_program
from functional_effects.testing import assert_err_message

result = await run_ws_program(failing_program(), interpreter)
assert_err_message(result, "Connection timeout")  # Passes if error contains substring
```

**Failure Messages**:
```
AssertionError: Expected Err, got Ok(...)
AssertionError: Expected error containing "timeout", got "Connection refused"
```

---

## Testing with pytest-mock

The recommended approach is using `pytest-mock` to create test doubles for infrastructure protocols.

### Basic Test Pattern

```python
import pytest
from pytest_mock import MockerFixture
from uuid import uuid4

from functional_effects import (
    run_ws_program,
    GetUserById,
    SendText,
    create_composite_interpreter,
)
from functional_effects.domain.user import User, UserFound
from functional_effects.infrastructure.websocket import WebSocketConnection
from functional_effects.infrastructure.repositories import UserRepository, ChatMessageRepository
from functional_effects.infrastructure.cache import ProfileCache
from functional_effects.testing import unwrap_ok

@pytest.mark.asyncio()
async def test_user_greeting(mocker: MockerFixture) -> None:
    # Create mocks with spec for type safety
    mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
    mock_ws.is_open.return_value = True

    mock_user_repo = mocker.AsyncMock(spec=UserRepository)
    mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
    mock_cache = mocker.AsyncMock(spec=ProfileCache)

    # Configure mock behavior
    user_id = uuid4()
    user = User(id=user_id, email="alice@example.com", name="Alice")
    mock_user_repo.get_by_id.return_value = UserFound(user=user, source="database")

    # Create interpreter with mocks
    interpreter = create_composite_interpreter(
        websocket_connection=mock_ws,
        user_repo=mock_user_repo,
        message_repo=mock_msg_repo,
        cache=mock_cache,
    )

    # Define program to test
    def greet_user_program():
        user_result = yield GetUserById(user_id=user_id)
        match user_result:
            case User(name=name):
                yield SendText(text=f"Hello {name}!")
                return "greeted"
            case None:
                return "not_found"

    # Execute and verify
    result = await run_ws_program(greet_user_program(), interpreter)
    value = unwrap_ok(result)

    assert value == "greeted"
    mock_ws.send_text.assert_called_once_with("Hello Alice!")
    mock_user_repo.get_by_id.assert_called_once_with(user_id)
```

---

## Testing Patterns

### Testing Success Paths

Verify programs execute correctly with valid data:

```python
@pytest.mark.asyncio()
async def test_save_message_success(mocker: MockerFixture) -> None:
    # Setup mocks
    mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
    mock_ws.is_open.return_value = True

    mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
    saved_message = ChatMessage(
        id=uuid4(),
        user_id=user_id,
        text="Hello",
        created_at=datetime.now()
    )
    mock_msg_repo.save_message.return_value = saved_message

    # Create interpreter
    interpreter = create_composite_interpreter(
        websocket_connection=mock_ws,
        user_repo=mocker.AsyncMock(spec=UserRepository),
        message_repo=mock_msg_repo,
        cache=mocker.AsyncMock(spec=ProfileCache),
    )

    # Test program
    def program():
        message = yield SaveChatMessage(user_id=user_id, text="Hello")
        assert isinstance(message, ChatMessage)
        yield SendText(text=f"Saved: {message.id}")
        return "success"

    result = await run_ws_program(program(), interpreter)
    assert_ok_value(result, "success")

    # Verify mock calls
    mock_msg_repo.save_message.assert_called_once_with(user_id, "Hello")
    mock_ws.send_text.assert_called_once()
```

---

### Testing Error Paths

Verify programs handle errors correctly:

```python
@pytest.mark.asyncio()
async def test_database_error_propagates(mocker: MockerFixture) -> None:
    # Setup mocks
    mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
    mock_ws.is_open.return_value = True

    mock_user_repo = mocker.AsyncMock(spec=UserRepository)
    # Configure repository to raise exception
    mock_user_repo.get_by_id.side_effect = Exception("Connection timeout")

    interpreter = create_composite_interpreter(
        websocket_connection=mock_ws,
        user_repo=mock_user_repo,
        message_repo=mocker.AsyncMock(spec=ChatMessageRepository),
        cache=mocker.AsyncMock(spec=ProfileCache),
    )

    # Test program
    def program():
        user = yield GetUserById(user_id=uuid4())
        yield SendText(text=f"User: {user}")  # Never reached
        return "never"

    result = await run_ws_program(program(), interpreter)

    # Verify error
    assert_err(result, DatabaseError)
    error = unwrap_err(result)
    assert "Connection timeout" in error.db_error
    assert error.is_retryable is True
```

---

### Testing with Multiple Return Values

Use `side_effect` for sequential returns:

```python
@pytest.mark.asyncio()
async def test_cache_miss_then_hit(mocker: MockerFixture) -> None:
    mock_cache = mocker.AsyncMock(spec=ProfileCache)

    # First call: cache miss, second call: cache hit
    profile = ProfileData(id=str(user_id), name="Bob")
    mock_cache.get_profile.side_effect = [
        CacheMiss(key=str(user_id), reason="not_found"),  # First call
        CacheHit(value=profile, ttl_remaining=300),       # Second call
    ]

    interpreter = create_composite_interpreter(
        websocket_connection=mocker.AsyncMock(spec=WebSocketConnection),
        user_repo=mocker.AsyncMock(spec=UserRepository),
        message_repo=mocker.AsyncMock(spec=ChatMessageRepository),
        cache=mock_cache,
    )

    # Test program (calls get_profile twice)
    def program():
        first = yield GetCachedProfile(user_id=user_id)
        assert first is None  # Cache miss

        # ... populate cache ...

        second = yield GetCachedProfile(user_id=user_id)
        assert isinstance(second, ProfileData)  # Cache hit
        return "success"

    result = await run_ws_program(program(), interpreter)
    assert_ok_value(result, "success")

    # Verify cache was called twice
    assert mock_cache.get_profile.call_count == 2
```

---

### Testing with Stateful Behavior

Use closures for stateful mock behavior:

```python
@pytest.mark.asyncio()
async def test_connection_closes_midway(mocker: MockerFixture) -> None:
    mock_ws = mocker.AsyncMock(spec=WebSocketConnection)

    # First call: open, subsequent calls: closed
    call_count = {"count": 0}

    def is_open_side_effect() -> bool:
        call_count["count"] += 1
        return call_count["count"] == 1  # True first call, False after

    mock_ws.is_open.side_effect = is_open_side_effect

    interpreter = create_composite_interpreter(
        websocket_connection=mock_ws,
        user_repo=mocker.AsyncMock(spec=UserRepository),
        message_repo=mocker.AsyncMock(spec=ChatMessageRepository),
        cache=mocker.AsyncMock(spec=ProfileCache),
    )

    # Test program
    def program():
        yield SendText(text="First")   # Succeeds
        yield SendText(text="Second")  # Fails - connection closed
        yield SendText(text="Never reached")
        return "never"

    result = await run_ws_program(program(), interpreter)

    # Verify error
    assert_err(result, WebSocketClosedError)

    # Verify only first message sent
    mock_ws.send_text.assert_called_once_with("First")
```

---

### Testing Program Composition

Test programs that use `yield from`:

```python
@pytest.mark.asyncio()
async def test_program_composition(mocker: MockerFixture) -> None:
    # Setup mocks...
    interpreter = create_composite_interpreter(...)

    # Sub-program
    def lookup_user(user_id: UUID):
        user = yield GetUserById(user_id=user_id)
        return user

    # Main program using sub-program
    def main_program(user_id: UUID):
        user = yield from lookup_user(user_id)
        match user:
            case User(name=name):
                yield SendText(text=f"Found: {name}")
                return "found"
            case None:
                return "not_found"

    result = await run_ws_program(main_program(user_id), interpreter)
    assert_ok_value(result, "found")
```

---

### Testing Batch Operations

Test programs that process multiple items:

```python
@pytest.mark.asyncio()
async def test_batch_user_greeting(mocker: MockerFixture) -> None:
    mock_user_repo = mocker.AsyncMock(spec=UserRepository)

    # Configure different responses for different user IDs
    users = {
        user_ids[0]: User(id=user_ids[0], email="u1@example.com", name="User 1"),
        user_ids[2]: User(id=user_ids[2], email="u3@example.com", name="User 3"),
    }

    def get_by_id_side_effect(user_id: UUID):
        if user_id in users:
            return UserFound(user=users[user_id], source="database")
        return UserNotFound(user_id=user_id, reason="does_not_exist")

    mock_user_repo.get_by_id.side_effect = get_by_id_side_effect

    interpreter = create_composite_interpreter(
        websocket_connection=mocker.AsyncMock(spec=WebSocketConnection),
        user_repo=mock_user_repo,
        message_repo=mocker.AsyncMock(spec=ChatMessageRepository),
        cache=mocker.AsyncMock(spec=ProfileCache),
    )

    # Test program
    def batch_program(user_ids: list[UUID]):
        stats = {"found": 0, "not_found": 0}
        for uid in user_ids:
            user = yield GetUserById(user_id=uid)
            if user is not None:
                stats["found"] += 1
            else:
                stats["not_found"] += 1
        return stats

    result = await run_ws_program(batch_program(user_ids), interpreter)
    stats = unwrap_ok(result)

    assert stats == {"found": 2, "not_found": 3}
    assert mock_user_repo.get_by_id.call_count == 5
```

---

## Test Organization

### Test File Structure

```
tests/
├── test_programs/
│   ├── test_greeting_workflow.py
│   ├── test_caching_workflow.py
│   └── test_error_handling.py
├── test_interpreters/
│   ├── test_websocket.py
│   ├── test_database.py
│   └── test_cache.py
└── test_integration/
    └── test_complete_workflows.py
```

### Test Naming

Use descriptive test names that indicate what is being tested:

```python
def test_user_not_found_sends_error_message() -> None: ...
def test_database_error_stops_program_execution() -> None: ...
def test_cache_miss_fallback_to_database() -> None: ...
```

---

## Coverage Guidelines

### What to Test

✅ **Test Success Paths**:
- Programs execute correctly with valid data
- All effects are called in expected order
- Return values match expectations

✅ **Test Error Paths**:
- Database connection failures
- WebSocket disconnections
- Cache unavailability
- Invalid input data

✅ **Test Edge Cases**:
- Empty results (user not found, cache miss)
- Boundary conditions (first/last item in batch)
- State transitions (connection open → closed)

✅ **Test Program Logic**:
- Conditional branching
- Pattern matching exhaustiveness
- Sub-program composition

### What NOT to Test

❌ **Don't Test Framework Internals**:
- Don't test that `yield` works
- Don't test that pattern matching works
- Don't test mock library behavior

❌ **Don't Test Infrastructure**:
- Don't test PostgreSQL queries in unit tests
- Don't test Redis operations
- Don't test WebSocket protocol

(Use integration tests for infrastructure validation)

---

## Best Practices

### 1. Use `spec=` for Type Safety

Always specify `spec` when creating mocks:

```python
# ✅ Good - type checker validates usage
mock_repo = mocker.AsyncMock(spec=UserRepository)

# ❌ Bad - no type safety
mock_repo = mocker.AsyncMock()
```

### 2. Verify Mock Calls

Always verify mocks were called correctly:

```python
# Verify called exactly once with specific arguments
mock_repo.get_by_id.assert_called_once_with(user_id)

# Verify called with any arguments
mock_ws.send_text.assert_called_once()

# Verify call count
assert mock_repo.save.call_count == 3

# Verify NOT called
mock_cache.put_profile.assert_not_called()
```

### 3. Test One Behavior Per Test

Each test should verify one specific behavior:

```python
# ✅ Good - tests one behavior
def test_user_not_found_returns_none() -> None: ...
def test_user_found_returns_user_object() -> None: ...

# ❌ Bad - tests multiple behaviors
def test_user_lookup() -> None:
    # Tests both found and not found cases
    ...
```

### 4. Use Descriptive Assertions

Make test failures easy to understand:

```python
# ✅ Good - clear assertion messages
result = await run_ws_program(program(), interpreter)
assert_ok_value(result, "success")  # Clear what's expected

# ❌ Bad - unclear failures
assert result == Ok("success")  # What if it's Err? Unclear message
```

### 5. Reset Mocks Between Calls

When testing sequential behavior, reset mocks:

```python
# First call
result1 = await run_ws_program(program(), interpreter)
mock_ws.send_text.assert_called_once()

# Reset before second call
mock_ws.reset_mock()

# Second call
result2 = await run_ws_program(program(), interpreter)
mock_ws.send_text.assert_called_once()
```

---

## See Also

- [Effects API](./effects.md) - Effect types used in programs
- [Result Type API](./result.md) - Result types for test assertions
- [Interpreters API](./interpreters.md) - Creating test interpreters
- [Programs API](./programs.md) - Program execution in tests
