# Tutorial 04: Testing Effect Programs

This tutorial teaches you how to test effect programs using pytest-mock without requiring real infrastructure.

## Prerequisites

- Completed [Tutorial 01: Quick Start](./01_quickstart.md)
- Completed [Tutorial 02: Effect Types](./02_effect_types.md)
- Completed [Tutorial 03: ADTs and Results](./03_adts_and_results.md)
- Familiarity with pytest

## Learning Objectives

By the end of this tutorial, you will:
- Write unit tests for effect programs using pytest-mock
- Test success paths and error paths
- Verify mock interactions
- Test program composition
- Understand test organization strategies

## Setup

### Installation

```bash
poetry add --group dev pytest pytest-asyncio pytest-mock pytest-cov
```

### Project Structure

```
your_project/
├── src/
│   └── programs/
│       ├── greet_user.py
│       └── workflows.py
└── tests/
    ├── test_programs/
    │   ├── test_greet_user.py
    │   └── test_workflows.py
    └── conftest.py
```

---

## Part 1: Basic Program Testing

### Writing a Testable Program

Let's start with a simple program to test:

```python
# src/programs/greet_user.py
from collections.abc import Generator
from uuid import UUID

from functional_effects import (
    AllEffects,
    EffectResult,
    GetUserById,
    SendText,
)
from functional_effects.domain.user import User

def greet_user(user_id: UUID) -> Generator[AllEffects, EffectResult, str]:
    """Greet a user by looking them up and sending a personalized message.

    Returns:
        "greeted" if user found, "not_found" if user doesn't exist
    """
    user = yield GetUserById(user_id=user_id)

    match user:
        case User(name=name):
            yield SendText(text=f"Hello {name}!")
            return "greeted"
        case None:
            yield SendText(text="User not found")
            return "not_found"
```

### Writing the Test

```python
# tests/test_programs/test_greet_user.py
import pytest
from pytest_mock import MockerFixture
from uuid import uuid4

from functional_effects import (
    run_ws_program,
    create_composite_interpreter,
)
from functional_effects.domain.user import User, UserFound, UserNotFound
from functional_effects.infrastructure.websocket import WebSocketConnection
from functional_effects.infrastructure.repositories import (
    UserRepository,
    ChatMessageRepository,
)
from functional_effects.infrastructure.cache import ProfileCache
from functional_effects.testing import unwrap_ok

from src.programs.greet_user import greet_user


@pytest.mark.asyncio()
async def test_greet_user_when_user_exists(mocker: MockerFixture) -> None:
    """Test greeting succeeds when user exists."""
    # 1. Create mocks with spec for type safety
    mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
    mock_ws.is_open.return_value = True

    mock_user_repo = mocker.AsyncMock(spec=UserRepository)
    mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
    mock_cache = mocker.AsyncMock(spec=ProfileCache)

    # 2. Configure mock behavior
    user_id = uuid4()
    user = User(id=user_id, email="alice@example.com", name="Alice")
    mock_user_repo.get_by_id.return_value = UserFound(user=user, source="database")

    # 3. Create interpreter with mocks
    interpreter = create_composite_interpreter(
        websocket_connection=mock_ws,
        user_repo=mock_user_repo,
        message_repo=mock_msg_repo,
        cache=mock_cache,
    )

    # 4. Execute program
    result = await run_ws_program(greet_user(user_id), interpreter)

    # 5. Verify result
    value = unwrap_ok(result)
    assert value == "greeted"

    # 6. Verify mock interactions
    mock_user_repo.get_by_id.assert_called_once_with(user_id)
    mock_ws.send_text.assert_called_once_with("Hello Alice!")


@pytest.mark.asyncio()
async def test_greet_user_when_user_not_found(mocker: MockerFixture) -> None:
    """Test greeting handles user not found."""
    # Setup mocks
    mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
    mock_ws.is_open.return_value = True

    mock_user_repo = mocker.AsyncMock(spec=UserRepository)
    mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
    mock_cache = mocker.AsyncMock(spec=ProfileCache)

    # Configure: user not found
    user_id = uuid4()
    mock_user_repo.get_by_id.return_value = UserNotFound(
        user_id=user_id,
        reason="does_not_exist"
    )

    interpreter = create_composite_interpreter(
        websocket_connection=mock_ws,
        user_repo=mock_user_repo,
        message_repo=mock_msg_repo,
        cache=mock_cache,
    )

    # Execute
    result = await run_ws_program(greet_user(user_id), interpreter)

    # Verify
    value = unwrap_ok(result)
    assert value == "not_found"

    mock_ws.send_text.assert_called_once_with("User not found")
```

**Key Testing Patterns**:
1. ✅ Use `mocker.AsyncMock(spec=Protocol)` for type safety
2. ✅ Configure mock return values before execution
3. ✅ Use `unwrap_ok` to assert success and extract value
4. ✅ Verify mock calls with `assert_called_once_with`

---

## Part 2: Testing Error Paths

### Testing Database Errors

```python
from functional_effects.interpreters.errors import DatabaseError
from functional_effects.testing import assert_err, unwrap_err


@pytest.mark.asyncio()
async def test_greet_user_database_failure(mocker: MockerFixture) -> None:
    """Test program handles database errors correctly."""
    # Setup mocks
    mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
    mock_ws.is_open.return_value = True

    mock_user_repo = mocker.AsyncMock(spec=UserRepository)
    mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
    mock_cache = mocker.AsyncMock(spec=ProfileCache)

    # Configure repository to raise exception
    mock_user_repo.get_by_id.side_effect = Exception("Connection timeout")

    interpreter = create_composite_interpreter(
        websocket_connection=mock_ws,
        user_repo=mock_user_repo,
        message_repo=mock_msg_repo,
        cache=mock_cache,
    )

    # Execute
    result = await run_ws_program(greet_user(uuid4()), interpreter)

    # Verify error
    assert_err(result, DatabaseError)
    error = unwrap_err(result)
    assert "Connection timeout" in error.db_error
    assert error.is_retryable is True

    # Verify program stopped before sending message
    mock_ws.send_text.assert_not_called()
```

### Testing WebSocket Errors

```python
from functional_effects.interpreters.errors import WebSocketClosedError


@pytest.mark.asyncio()
async def test_greet_user_websocket_closed(mocker: MockerFixture) -> None:
    """Test program handles closed WebSocket connections."""
    # Setup mocks
    mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
    mock_ws.is_open.return_value = False  # Connection closed!

    mock_user_repo = mocker.AsyncMock(spec=UserRepository)
    mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
    mock_cache = mocker.AsyncMock(spec=ProfileCache)

    # User lookup succeeds, but WebSocket is closed
    user_id = uuid4()
    user = User(id=user_id, email="alice@example.com", name="Alice")
    mock_user_repo.get_by_id.return_value = UserFound(user=user, source="database")

    interpreter = create_composite_interpreter(
        websocket_connection=mock_ws,
        user_repo=mock_user_repo,
        message_repo=mock_msg_repo,
        cache=mock_cache,
    )

    # Execute
    result = await run_ws_program(greet_user(user_id), interpreter)

    # Verify error
    assert_err(result, WebSocketClosedError)
    error = unwrap_err(result)
    assert error.close_code == 1006  # Abnormal closure
```

---

## Part 3: Testing with Sequential Returns

Use `side_effect` for mocks that return different values on subsequent calls:

```python
from functional_effects import GetCachedProfile, PutCachedProfile
from functional_effects.domain.cache_result import CacheHit, CacheMiss
from functional_effects.domain.profile import ProfileData


def cache_aware_program(user_id: UUID) -> Generator[AllEffects, EffectResult, str]:
    """Check cache first, fallback to database."""
    # Try cache
    cached = yield GetCachedProfile(user_id=user_id)

    match cached:
        case ProfileData(name=name):
            yield SendText(text=f"Hello {name} (cached)")
            return "cache_hit"
        case None:
            # Cache miss - fetch from database
            user = yield GetUserById(user_id=user_id)

            match user:
                case User(id=uid, name=name):
                    # Populate cache
                    profile = ProfileData(id=str(uid), name=name)
                    yield PutCachedProfile(user_id=user_id, profile_data=profile)
                    yield SendText(text=f"Hello {name}")
                    return "db_hit"
                case None:
                    return "not_found"


@pytest.mark.asyncio()
async def test_cache_aware_program_cache_miss_then_hit(mocker: MockerFixture) -> None:
    """Test cache miss followed by cache hit on second call."""
    # Setup mocks
    mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
    mock_ws.is_open.return_value = True

    mock_user_repo = mocker.AsyncMock(spec=UserRepository)
    mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
    mock_cache = mocker.AsyncMock(spec=ProfileCache)

    # Configure cache: first call miss, second call hit
    user_id = uuid4()
    profile = ProfileData(id=str(user_id), name="Bob")

    mock_cache.get_profile.side_effect = [
        CacheMiss(key=str(user_id), reason="not_found"),  # First call
        CacheHit(value=profile, ttl_remaining=300),       # Second call
    ]

    # Configure user repo for cache miss path
    user = User(id=user_id, email="bob@example.com", name="Bob")
    mock_user_repo.get_by_id.return_value = UserFound(user=user, source="database")

    interpreter = create_composite_interpreter(
        websocket_connection=mock_ws,
        user_repo=mock_user_repo,
        message_repo=mock_msg_repo,
        cache=mock_cache,
    )

    # First execution - cache miss
    result1 = await run_ws_program(cache_aware_program(user_id), interpreter)
    value1 = unwrap_ok(result1)
    assert value1 == "db_hit"
    mock_cache.put_profile.assert_called_once_with(user_id, profile, 300)

    # Reset WebSocket mock for second execution
    mock_ws.reset_mock()

    # Second execution - cache hit
    result2 = await run_ws_program(cache_aware_program(user_id), interpreter)
    value2 = unwrap_ok(result2)
    assert value2 == "cache_hit"

    # Verify database not called on cache hit
    assert mock_user_repo.get_by_id.call_count == 1  # Only from first execution
```

---

## Part 4: Testing with Stateful Behavior

Use closures for stateful mock behavior:

```python
@pytest.mark.asyncio()
async def test_program_connection_closes_midway(mocker: MockerFixture) -> None:
    """Test program stops when connection closes during execution."""
    # Setup mocks
    mock_ws = mocker.AsyncMock(spec=WebSocketConnection)

    # Stateful behavior: first call returns True, subsequent calls return False
    call_count = {"count": 0}

    def is_open_side_effect() -> bool:
        call_count["count"] += 1
        return call_count["count"] == 1

    mock_ws.is_open.side_effect = is_open_side_effect

    interpreter = create_composite_interpreter(
        websocket_connection=mock_ws,
        user_repo=mocker.AsyncMock(spec=UserRepository),
        message_repo=mocker.AsyncMock(spec=ChatMessageRepository),
        cache=mocker.AsyncMock(spec=ProfileCache),
    )

    # Program that sends multiple messages
    def multi_message_program() -> Generator[AllEffects, EffectResult, str]:
        yield SendText(text="First")   # Succeeds
        yield SendText(text="Second")  # Fails - connection closed
        yield SendText(text="Third")   # Never reached
        return "never"

    # Execute
    result = await run_ws_program(multi_message_program(), interpreter)

    # Verify error
    assert_err(result, WebSocketClosedError)

    # Verify only first message sent (program stopped after connection closed)
    mock_ws.send_text.assert_called_once_with("First")
```

---

## Part 5: Testing Program Composition

Test programs that use `yield from`:

```python
def lookup_user_sub_program(user_id: UUID) -> Generator[AllEffects, EffectResult, User | None]:
    """Reusable sub-program: lookup user."""
    user = yield GetUserById(user_id=user_id)
    return user


def greet_user_composite(user_id: UUID) -> Generator[AllEffects, EffectResult, str]:
    """Main program using sub-program."""
    # Delegate to sub-program
    user = yield from lookup_user_sub_program(user_id)

    match user:
        case User(name=name):
            yield SendText(text=f"Hello {name}!")
            return "greeted"
        case None:
            yield SendText(text="User not found")
            return "not_found"


@pytest.mark.asyncio()
async def test_composite_program_success(mocker: MockerFixture) -> None:
    """Test program composition with yield from."""
    # Setup mocks
    mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
    mock_ws.is_open.return_value = True

    mock_user_repo = mocker.AsyncMock(spec=UserRepository)

    user_id = uuid4()
    user = User(id=user_id, email="alice@example.com", name="Alice")
    mock_user_repo.get_by_id.return_value = UserFound(user=user, source="database")

    interpreter = create_composite_interpreter(
        websocket_connection=mock_ws,
        user_repo=mock_user_repo,
        message_repo=mocker.AsyncMock(spec=ChatMessageRepository),
        cache=mocker.AsyncMock(spec=ProfileCache),
    )

    # Execute
    result = await run_ws_program(greet_user_composite(user_id), interpreter)

    # Verify
    value = unwrap_ok(result)
    assert value == "greeted"

    # Verify both sub-program and main program effects executed
    mock_user_repo.get_by_id.assert_called_once_with(user_id)
    mock_ws.send_text.assert_called_once_with("Hello Alice!")
```

---

## Part 6: Test Organization

### Fixture Reuse

Create reusable fixtures in `conftest.py`:

```python
# tests/conftest.py
import pytest
from pytest_mock import MockerFixture

from functional_effects import create_composite_interpreter
from functional_effects.infrastructure.websocket import WebSocketConnection
from functional_effects.infrastructure.repositories import UserRepository, ChatMessageRepository
from functional_effects.infrastructure.cache import ProfileCache


@pytest.fixture
def mock_interpreter(mocker: MockerFixture):
    """Create interpreter with all mocks."""
    mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
    mock_ws.is_open.return_value = True

    mock_user_repo = mocker.AsyncMock(spec=UserRepository)
    mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
    mock_cache = mocker.AsyncMock(spec=ProfileCache)

    interpreter = create_composite_interpreter(
        websocket_connection=mock_ws,
        user_repo=mock_user_repo,
        message_repo=mock_msg_repo,
        cache=mock_cache,
    )

    return {
        "interpreter": interpreter,
        "ws": mock_ws,
        "user_repo": mock_user_repo,
        "msg_repo": mock_msg_repo,
        "cache": mock_cache,
    }
```

Use in tests:

```python
@pytest.mark.asyncio()
async def test_with_fixture(mock_interpreter) -> None:
    """Test using reusable fixture."""
    interpreter = mock_interpreter["interpreter"]
    mock_user_repo = mock_interpreter["user_repo"]

    # Configure mock
    user_id = uuid4()
    user = User(id=user_id, email="alice@example.com", name="Alice")
    mock_user_repo.get_by_id.return_value = UserFound(user=user, source="database")

    # Execute
    result = await run_ws_program(greet_user(user_id), interpreter)

    # Verify
    value = unwrap_ok(result)
    assert value == "greeted"
```

---

## Best Practices

### ✅ DO

1. **Use `spec=` for Type Safety**
   ```python
   mock_repo = mocker.AsyncMock(spec=UserRepository)  # Type-safe
   ```

2. **Verify Mock Calls**
   ```python
   mock_ws.send_text.assert_called_once_with("Hello")
   mock_repo.get_by_id.assert_called_once_with(user_id)
   ```

3. **Test One Behavior Per Test**
   ```python
   def test_user_found_sends_greeting() -> None: ...
   def test_user_not_found_sends_error() -> None: ...
   ```

4. **Use Descriptive Test Names**
   ```python
   def test_greet_user_when_database_fails_returns_error() -> None: ...
   ```

5. **Reset Mocks Between Calls**
   ```python
   mock_ws.reset_mock()
   ```

### ❌ DON'T

1. **Don't Create Mocks Without spec**
   ```python
   mock_repo = mocker.AsyncMock()  # No type safety
   ```

2. **Don't Skip Mock Verification**
   ```python
   result = await run_ws_program(program(), interpreter)
   assert_ok(result)
   # Missing: verify mocks were called correctly
   ```

3. **Don't Test Multiple Behaviors**
   ```python
   def test_greet_user() -> None:
       # Tests both found AND not found - too much!
       ...
   ```

4. **Don't Use Real Infrastructure**
   ```python
   # ❌ Don't do this in unit tests
   db_conn = await asyncpg.connect(DATABASE_URL)
   ```

---

## Next Steps

- Read [API Reference: Testing](../api/testing.md) for complete testing utilities
- Read [Tutorial 05: Production Deployment](./05_production_deployment.md) for deploying tested programs
- Explore test examples in `tests/test_programs/` and `tests/test_integration/`

## Summary

You learned how to:
- ✅ Write unit tests using pytest-mock
- ✅ Test success and error paths
- ✅ Use `side_effect` for sequential returns
- ✅ Test stateful mock behavior
- ✅ Test program composition
- ✅ Organize tests with fixtures

Happy testing! 🧪
