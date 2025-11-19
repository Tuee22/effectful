# Claude Code Patterns for functional_effects

## Project Overview

**functional_effects** is a pure functional effect system for Python that brings algebraic data types, explicit error handling, and composable programs to async Python applications.

**Core Philosophy**: Make invalid states unrepresentable through the type system.

## Type Safety Doctrines

### 1. NO Escape Hatches

```python
# ❌ FORBIDDEN - These constructs are NEVER allowed
from typing import Any, cast

def process(data: Any) -> Any:  # NO!
    return cast(int, data)      # NO!

def transform(x):  # type: ignore  # NO!
    return x

# ✅ CORRECT - Explicit types always
from uuid import UUID
from functional_effects.algebraic.result import Result, Ok, Err
from functional_effects.domain.user import User

def process(user_id: UUID) -> Result[User, str]:
    if not isinstance(user_id, UUID):
        return Err("Invalid UUID")
    return Ok(User(id=user_id, email="test@example.com", name="Test"))
```

**Enforcement**: `mypy --strict` with `disallow_any_explicit = true` in pyproject.toml

### 2. ADTs Over Optional Types

```python
# ❌ WRONG - Optional hides the reason for None
from typing import Optional

async def get_user(user_id: UUID) -> Optional[User]:
    user = await db.query(...)
    return user  # Why is it None? Not found? Error? Timeout?

# ✅ CORRECT - ADT makes all cases explicit
from dataclasses import dataclass
from functional_effects.domain.user import User

@dataclass(frozen=True)
class UserFound:
    user: User
    source: str  # "database" | "cache"

@dataclass(frozen=True)
class UserNotFound:
    user_id: UUID
    reason: str  # "does_not_exist" | "deleted" | "access_denied"

type UserLookupResult = UserFound | UserNotFound

async def get_user(user_id: UUID) -> UserLookupResult:
    user = await db.query(...)
    if user is not None:
        return UserFound(user=user, source="database")
    return UserNotFound(user_id=user_id, reason="does_not_exist")

# Usage with exhaustive pattern matching
match result:
    case UserFound(user=user, source=source):
        print(f"Found {user.name} from {source}")
    case UserNotFound(user_id=uid, reason=reason):
        print(f"User {uid} not found: {reason}")
```

**Why**: ADTs force callers to handle all cases explicitly. The type system prevents forgetting edge cases.

### 3. Result Type for Error Handling

```python
# ❌ WRONG - Exceptions are invisible in type signatures
async def save_message(user_id: UUID, text: str) -> ChatMessage:
    # Raises ValueError? DatabaseError? Who knows!
    return await db.save(...)

# ✅ CORRECT - Errors are part of the type signature
from functional_effects.algebraic.result import Result, Ok, Err
from functional_effects.interpreters.errors import DatabaseError

async def save_message(
    user_id: UUID, text: str
) -> Result[ChatMessage, DatabaseError]:
    try:
        msg = await db.save(...)
        return Ok(msg)
    except Exception as e:
        return Err(DatabaseError(
            effect=SaveChatMessage(user_id=user_id, text=text),
            db_error=str(e),
            is_retryable=True
        ))

# Caller MUST handle errors
match result:
    case Ok(message):
        print(f"Saved: {message.id}")
    case Err(error):
        print(f"Failed: {error.db_error}")
        if error.is_retryable:
            await retry_logic()
```

**Why**: Errors become type-checked documentation. Impossible to forget error handling.

### 4. Immutability by Default

```python
# ❌ WRONG - Mutable state allows invalid mutations
from dataclasses import dataclass

@dataclass
class User:
    id: UUID
    email: str
    name: str

user = User(id=uuid4(), email="test@example.com", name="Alice")
user.email = None  # Oops! Type checker doesn't prevent this at runtime

# ✅ CORRECT - Frozen dataclasses prevent mutation
@dataclass(frozen=True)
class User:
    id: UUID
    email: str
    name: str

user = User(id=uuid4(), email="test@example.com", name="Alice")
# user.email = None  # Error: cannot assign to field 'email'

# To "update", create new instance
updated_user = User(id=user.id, email="new@example.com", name=user.name)
```

**Why**: Immutability eliminates entire classes of bugs (race conditions, unexpected mutations, temporal coupling).

### 5. Exhaustive Pattern Matching

```python
# ❌ WRONG - Non-exhaustive matching
from functional_effects.algebraic.result import Result, Ok, Err

def process(result: Result[int, str]) -> int:
    match result:
        case Ok(value):
            return value
    # Missing Err case - mypy error!

# ✅ CORRECT - Exhaustive matching
def process(result: Result[int, str]) -> int:
    match result:
        case Ok(value):
            return value
        case Err(error):
            print(f"Error: {error}")
            return 0
```

**Why**: Type checker enforces handling all cases. No forgotten branches.

### 6. Type Narrowing for Union Types

```python
# ❌ WRONG - Accessing union type attributes without narrowing
from functional_effects.effects.database import SaveChatMessage

def program() -> Generator[AllEffects, EffectResult, str]:
    message = yield SaveChatMessage(user_id=user_id, text="Hello")
    # Error: EffectResult is str | User | ChatMessage | None
    return f"Saved: {message.text}"  # mypy error!

# ✅ CORRECT - Type narrowing with isinstance
def program() -> Generator[AllEffects, EffectResult, str]:
    message = yield SaveChatMessage(user_id=user_id, text="Hello")
    assert isinstance(message, ChatMessage)  # Type narrowing
    return f"Saved: {message.text}"  # OK - mypy knows it's ChatMessage

# ✅ ALTERNATIVE - Pattern matching
def program() -> Generator[AllEffects, EffectResult, str]:
    message = yield SaveChatMessage(user_id=user_id, text="Hello")
    match message:
        case ChatMessage(id=msg_id, text=text):
            return f"Saved: {text}"
        case _:
            return "Unexpected type"
```

**Why**: Union types require explicit narrowing. Type checker ensures runtime type safety.

### 7. Generic Type Parameters

```python
# ❌ WRONG - Bare generic types lose information
def process(items: list) -> dict:  # What kind of list? What dict structure?
    return {str(i): item for i, item in enumerate(items)}

# ✅ CORRECT - Fully parameterized generics
def process(items: list[str]) -> dict[str, str]:
    return {str(i): item for i, item in enumerate(items)}

# ✅ CORRECT - Generic functions with TypeVar
from typing import TypeVar

T = TypeVar("T")

def first_or_none(items: list[T]) -> T | None:
    return items[0] if items else None

# Type checker infers: first_or_none([1, 2, 3]) -> int | None
```

**Why**: Generic parameters preserve type information through transformations.

### 8. PEP 695 Type Aliases

```python
# ❌ WRONG - String-based type aliases (deprecated)
from typing import Generator

EffectResult = "str | User | ChatMessage | None"  # NO!

# ✅ CORRECT - PEP 695 type aliases (Python 3.12+)
from collections.abc import Generator

type EffectResult = str | User | ChatMessage | ProfileData | CacheLookupResult | None

type WSProgram = Generator[AllEffects, EffectResult, None]

# Usage
def my_program() -> WSProgram:
    yield SendText(text="Hello")
    return None
```

**Why**: Type aliases are first-class citizens with proper IDE support and type checking.

## Testing Antipatterns

### 1. Testing with Real Infrastructure

```python
# ❌ WRONG - Tests depend on PostgreSQL, Redis, etc.
@pytest.mark.asyncio
async def test_user_lookup():
    async with asyncpg.connect(DATABASE_URL) as conn:  # Real DB!
        user = await UserRepository(conn).get_by_id(user_id)
        assert user is not None

# ✅ CORRECT - Use fakes from functional_effects.testing
from functional_effects.testing import (
    FakeUserRepository,
    create_test_interpreter,
    unwrap_ok,
)

@pytest.mark.asyncio
async def test_user_lookup():
    # Setup
    fake_repo = FakeUserRepository()
    fake_repo._users[user_id] = User(id=user_id, email="test@example.com", name="Alice")
    interpreter = create_test_interpreter(user_repo=fake_repo)

    # Test
    def program() -> Generator[AllEffects, EffectResult, bool]:
        user_result = yield GetUserById(user_id=user_id)
        match user_result:
            case User(name=name):
                yield SendText(text=f"Hello {name}")
                return True
            case _:
                return False

    result = await run_ws_program(program(), interpreter)
    value = unwrap_ok(result)
    assert value is True
```

**Why**: Tests must be fast, deterministic, and isolated. Real infrastructure introduces flakiness.

### 2. Not Testing Error Paths

```python
# ❌ WRONG - Only testing happy path
@pytest.mark.asyncio
async def test_user_lookup():
    result = await run_ws_program(program(), interpreter)
    value = unwrap_ok(result)  # Assumes Ok
    assert value == "success"

# ✅ CORRECT - Test error cases explicitly
from functional_effects.testing import (
    FailingUserRepository,
    assert_err,
)

@pytest.mark.asyncio
async def test_user_lookup_database_failure():
    # Setup failing infrastructure
    failing_repo = FailingUserRepository(error_message="Connection timeout")
    interpreter = create_test_interpreter(user_repo=failing_repo)

    # Test
    def program() -> Generator[AllEffects, EffectResult, bool]:
        user_result = yield GetUserById(user_id=user_id)
        return True

    result = await run_ws_program(program(), interpreter)

    # Assert error
    assert_err(result, DatabaseError)
    error = unwrap_err(result)
    assert "Connection timeout" in error.db_error
```

**Why**: Error handling is half your code. Test it.

### 3. Incomplete Assertions

```python
# ❌ WRONG - Only checking result succeeded
result = await run_ws_program(program(), interpreter)
assert_ok(result)  # Did the program do the right thing?

# ✅ CORRECT - Verify side effects and state changes
result = await run_ws_program(program(), interpreter)
value = unwrap_ok(result)

# Check return value
assert value == "success"

# Check side effects
assert len(fake_websocket._sent_messages) == 2
assert fake_websocket._sent_messages[0] == "Hello Alice"
assert fake_websocket._sent_messages[1] == "Message saved"

# Check state changes
assert len(fake_message_repo._messages) == 1
assert fake_message_repo._messages[0].text == "Hello Alice"
```

**Why**: Programs have effects beyond return values. Verify the entire behavior.

### 4. Using pytest.skip()

```python
# ❌ FORBIDDEN - Never skip tests
@pytest.mark.skip(reason="TODO: Implement later")
def test_complex_workflow():
    pass

# ✅ CORRECT - Either implement or delete
def test_complex_workflow():
    # Full implementation
    ...

# Or delete the test entirely if not needed
```

**Why**: Skipped tests hide gaps in coverage. They rot and are never implemented.

## Effect Program Patterns

### 1. Generator-Based DSL

```python
from collections.abc import Generator
from functional_effects import (
    AllEffects,
    EffectResult,
    GetUserById,
    SendText,
    SaveChatMessage,
)

def greet_user(user_id: UUID) -> Generator[AllEffects, EffectResult, bool]:
    """Effect program that looks up user and sends personalized greeting."""

    # Yield effect, receive result
    user_result = yield GetUserById(user_id=user_id)

    # Pattern match on result
    match user_result:
        case None:
            yield SendText(text="Error: User not found")
            return False
        case User(name=name):
            greeting = f"Hello {name}!"
            yield SendText(text=greeting)

            # Type narrowing for next effect
            message = yield SaveChatMessage(user_id=user_id, text=greeting)
            assert isinstance(message, ChatMessage)

            yield SendText(text=f"Message saved with ID: {message.id}")
            return True
```

**Pattern**: `result = yield Effect(...)` - Yield effect, receive typed result.

### 2. Fail-Fast Error Propagation

```python
from functional_effects import run_ws_program

async def execute() -> None:
    result = await run_ws_program(greet_user(user_id), interpreter)

    # run_ws_program returns Err immediately on first effect failure
    match result:
        case Ok(success):
            print(f"Program completed: {success}")
        case Err(error):
            print(f"Program failed: {error}")
            # error is one of: DatabaseError | WebSocketClosedError | CacheError
```

**Pattern**: First effect that returns Err short-circuits the entire program.

### 3. Composing Programs

```python
def lookup_and_cache_profile(user_id: UUID) -> Generator[AllEffects, EffectResult, ProfileData | None]:
    """Reusable program: lookup user, create profile, cache it."""
    user_result = yield GetUserById(user_id=user_id)

    match user_result:
        case None:
            return None
        case User(id=uid, name=name, email=email):
            profile = ProfileData(id=str(uid), name=name, email=email)
            yield PutCachedProfile(user_id=uid, profile_data=profile, ttl_seconds=300)
            return profile

def greet_with_caching(user_id: UUID) -> Generator[AllEffects, EffectResult, str]:
    """Compose smaller programs into larger workflows."""

    # Check cache first
    cached = yield GetCachedProfile(user_id=user_id)
    match cached:
        case ProfileData(name=name):
            greeting = f"Hello {name} (from cache)!"
        case _:
            # Cache miss - lookup and cache
            profile = yield from lookup_and_cache_profile(user_id)
            if profile is None:
                return "User not found"
            greeting = f"Hello {profile.name}!"

    yield SendText(text=greeting)
    return greeting
```

**Pattern**: Use `yield from` to delegate to sub-programs.

## Code Review Checklist

Before committing code, verify:

- [ ] Zero `Any` types (check with `mypy --strict`)
- [ ] Zero `cast()` calls
- [ ] Zero `# type: ignore` comments
- [ ] All dataclasses are `frozen=True`
- [ ] All functions have inline type hints
- [ ] All generics have type parameters (e.g., `list[str]` not `list`)
- [ ] ADTs used instead of Optional for domain logic
- [ ] Result type used for all fallible operations
- [ ] Pattern matching is exhaustive (all cases handled)
- [ ] Tests use fakes from functional_effects.testing
- [ ] Both success and error paths tested
- [ ] Side effects verified in tests (not just return values)
- [ ] No skipped tests (`pytest.skip()` forbidden)

## Configuration

**pyproject.toml** must include:

```toml
[tool.mypy]
strict = true
disallow_any_explicit = true
disallow_any_generics = true
disallow_subclassing_any = true
disallow_untyped_calls = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
disallow_untyped_decorators = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_return_any = true
warn_unreachable = true
strict_equality = true
python_version = "3.12"
```

## References

- **Result Type**: `functional_effects/algebraic/result.py`
- **ADT Examples**: `functional_effects/domain/user.py`, `functional_effects/domain/cache_result.py`
- **Testing Utilities**: `functional_effects/testing/__init__.py`
- **Effect Programs**: `tests/test_integration/test_chat_workflow.py`
- **Type Aliases**: `functional_effects/programs/types.py`

---

**Philosophy**: If the type checker passes, the program is correct. Make the type system work for you, not against you.
