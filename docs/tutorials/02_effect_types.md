# Effect Types

This tutorial covers all available effect types in **functional_effects** and how to use them.

## Effect Categories

functional_effects provides three categories of effects:

1. **WebSocket Effects** - Real-time communication
2. **Database Effects** - Data persistence
3. **Cache Effects** - Performance optimization

## WebSocket Effects

### SendText

Send a text message over WebSocket.

```python
from functional_effects import SendText

def send_greeting() -> Generator[AllEffects, EffectResult, None]:
    yield SendText(text="Hello from the server!")
    return None
```

**Effect Signature:**
```python
@dataclass(frozen=True)
class SendText:
    text: str
```

**Returns:** `None` (no value returned)

**Errors:** `WebSocketClosedError` if connection is closed

### ReceiveText

Receive a text message from WebSocket.

```python
from functional_effects import ReceiveText

def receive_and_echo() -> Generator[AllEffects, EffectResult, str]:
    # Receive message
    message = yield ReceiveText()

    # Type narrowing
    assert isinstance(message, str)

    # Echo back
    yield SendText(text=f"You said: {message}")
    return message
```

**Effect Signature:**
```python
@dataclass(frozen=True)
class ReceiveText:
    pass
```

**Returns:** `str` (the received message)

**Errors:** `WebSocketClosedError` if connection is closed

### Close

Close the WebSocket connection with a reason.

```python
from functional_effects import Close, CloseNormal

def goodbye() -> Generator[AllEffects, EffectResult, None]:
    yield SendText(text="Goodbye!")
    yield Close(reason=CloseNormal())
    return None
```

**Effect Signature:**
```python
@dataclass(frozen=True)
class Close:
    reason: CloseReason

# CloseReason variants:
@dataclass(frozen=True)
class CloseNormal:
    pass

@dataclass(frozen=True)
class CloseGoingAway:
    pass

@dataclass(frozen=True)
class CloseProtocolError:
    pass

@dataclass(frozen=True)
class ClosePolicyViolation:
    pass
```

**Returns:** `None`

**Errors:** None (always succeeds)

## Database Effects

### GetUserById

Look up a user by UUID.

```python
from uuid import UUID
from functional_effects import GetUserById, User

def lookup_user(user_id: UUID) -> Generator[AllEffects, EffectResult, str]:
    # Yield effect
    user_result = yield GetUserById(user_id=user_id)

    # Handle result (can be User or None)
    match user_result:
        case None:
            return "User not found"
        case User(name=name, email=email):
            return f"{name} ({email})"
```

**Effect Signature:**
```python
@dataclass(frozen=True)
class GetUserById:
    user_id: UUID
```

**Returns:** `User | None`

**Errors:** `DatabaseError` if query fails

**User Model:**
```python
@dataclass(frozen=True)
class User:
    id: UUID
    email: str
    name: str
```

### SaveChatMessage

Save a chat message to the database.

```python
from functional_effects import SaveChatMessage, ChatMessage

def save_user_message(user_id: UUID, text: str) -> Generator[AllEffects, EffectResult, UUID]:
    # Yield effect
    message = yield SaveChatMessage(user_id=user_id, text=text)

    # Type narrowing
    assert isinstance(message, ChatMessage)

    # Return message ID
    return message.id
```

**Effect Signature:**
```python
@dataclass(frozen=True)
class SaveChatMessage:
    user_id: UUID
    text: str
```

**Returns:** `ChatMessage`

**Errors:** `DatabaseError` if save fails

**ChatMessage Model:**
```python
@dataclass(frozen=True)
class ChatMessage:
    id: UUID
    user_id: UUID
    text: str
    created_at: datetime
```

## Cache Effects

### GetCachedProfile

Look up a cached user profile.

```python
from functional_effects import GetCachedProfile, ProfileData

def get_profile(user_id: UUID) -> Generator[AllEffects, EffectResult, ProfileData | None]:
    # Yield effect
    cached = yield GetCachedProfile(user_id=user_id)

    # Handle cache hit/miss
    match cached:
        case ProfileData(name=name):
            yield SendText(text=f"Found cached profile for {name}")
            return cached
        case _:
            yield SendText(text="Cache miss")
            return None
```

**Effect Signature:**
```python
@dataclass(frozen=True)
class GetCachedProfile:
    user_id: UUID
```

**Returns:** `ProfileData | None`

**Errors:** `CacheError` if cache access fails

**ProfileData Model:**
```python
@dataclass(frozen=True)
class ProfileData:
    id: str
    name: str
    email: str | None = None
```

### PutCachedProfile

Store a user profile in cache with TTL.

```python
from functional_effects import PutCachedProfile

def cache_profile(user_id: UUID, profile: ProfileData) -> Generator[AllEffects, EffectResult, None]:
    # Store in cache for 5 minutes
    yield PutCachedProfile(
        user_id=user_id,
        profile_data=profile,
        ttl_seconds=300
    )
    yield SendText(text="Profile cached")
    return None
```

**Effect Signature:**
```python
@dataclass(frozen=True)
class PutCachedProfile:
    user_id: UUID
    profile_data: ProfileData
    ttl_seconds: int
```

**Returns:** `None`

**Errors:** `CacheError` if cache write fails

## Composing Effects

### Sequential Effects

Effects execute in order:

```python
def multi_step() -> Generator[AllEffects, EffectResult, str]:
    # Step 1: Get user
    user_result = yield GetUserById(user_id=user_id)
    assert isinstance(user_result, User)

    # Step 2: Send greeting
    yield SendText(text=f"Hello {user_result.name}!")

    # Step 3: Save message
    message = yield SaveChatMessage(user_id=user_id, text="Greeting sent")
    assert isinstance(message, ChatMessage)

    # Step 4: Cache profile
    profile = ProfileData(id=str(user_id), name=user_result.name)
    yield PutCachedProfile(user_id=user_id, profile_data=profile, ttl_seconds=300)

    return "Workflow complete"
```

### Conditional Effects

Use pattern matching for conditional logic:

```python
def conditional_cache(user_id: UUID) -> Generator[AllEffects, EffectResult, str]:
    # Try cache first
    cached = yield GetCachedProfile(user_id=user_id)

    match cached:
        case ProfileData(name=name):
            # Cache hit - use cached data
            yield SendText(text=f"Hello {name} (from cache)!")
            return "cache_hit"
        case _:
            # Cache miss - lookup user
            user_result = yield GetUserById(user_id=user_id)
            match user_result:
                case None:
                    yield SendText(text="User not found")
                    return "not_found"
                case User(name=name):
                    # Cache the profile
                    profile = ProfileData(id=str(user_id), name=name)
                    yield PutCachedProfile(user_id=user_id, profile_data=profile, ttl_seconds=300)
                    yield SendText(text=f"Hello {name}!")
                    return "cache_miss"
```

### Reusable Sub-Programs

Use `yield from` to call sub-programs:

```python
def lookup_and_cache(user_id: UUID) -> Generator[AllEffects, EffectResult, ProfileData | None]:
    """Reusable: lookup user and cache profile."""
    user_result = yield GetUserById(user_id=user_id)

    match user_result:
        case None:
            return None
        case User(id=uid, name=name, email=email):
            profile = ProfileData(id=str(uid), name=name, email=email)
            yield PutCachedProfile(user_id=uid, profile_data=profile, ttl_seconds=300)
            return profile

def greet_with_caching(user_id: UUID) -> Generator[AllEffects, EffectResult, str]:
    """Use sub-program."""
    # Delegate to sub-program
    profile = yield from lookup_and_cache(user_id)

    if profile is None:
        yield SendText(text="User not found")
        return "error"

    yield SendText(text=f"Hello {profile.name}!")
    return "success"
```

## Error Handling

### Fail-Fast Semantics

Programs stop on first error:

```python
def failing_program() -> Generator[AllEffects, EffectResult, str]:
    # This effect fails
    user_result = yield GetUserById(user_id=invalid_uuid)  # DatabaseError!

    # These effects NEVER execute
    yield SendText(text="This won't run")
    yield SaveChatMessage(user_id=user_id, text="This won't run")

    return "This won't return"
```

When run:
```python
result = await run_ws_program(failing_program(), interpreter)

match result:
    case Err(DatabaseError(db_error=error)):
        print(f"Failed at first effect: {error}")
```

### Testing Error Cases

Use failing fakes to test error handling:

```python
from functional_effects.testing import FailingUserRepository

@pytest.mark.asyncio
async def test_database_failure():
    # Setup failing infrastructure
    failing_repo = FailingUserRepository(error_message="Connection timeout")
    interpreter = create_test_interpreter(user_repo=failing_repo)

    # Run program
    result = await run_ws_program(my_program(), interpreter)

    # Assert error
    assert_err(result, DatabaseError)
    error = unwrap_err(result)
    assert "Connection timeout" in error.db_error
```

## Type Safety

### Effect Result Types

All effects return union types:

```python
# EffectResult = str | User | ChatMessage | ProfileData | None
type EffectResult = str | User | ChatMessage | ProfileData | CacheLookupResult | None
```

**Always use type narrowing:**

```python
# ❌ WRONG - mypy error
def program() -> Generator[AllEffects, EffectResult, str]:
    message = yield SaveChatMessage(user_id=user_id, text="Hello")
    return f"ID: {message.id}"  # Error: EffectResult has no attribute 'id'

# ✅ CORRECT - type narrowing
def program() -> Generator[AllEffects, EffectResult, str]:
    message = yield SaveChatMessage(user_id=user_id, text="Hello")
    assert isinstance(message, ChatMessage)  # Narrow type
    return f"ID: {message.id}"  # OK
```

### Pattern Matching

Exhaustive matching ensures all cases are handled:

```python
def program() -> Generator[AllEffects, EffectResult, str]:
    user_result = yield GetUserById(user_id=user_id)

    match user_result:
        case None:
            return "not_found"
        case User(name=name):
            return f"found: {name}"
        # mypy enforces exhaustive matching
```

## Next Steps

- [Tutorial 03: ADTs and Result Types](03_adts_and_results.md) - Deep dive into type safety
- [Tutorial 04: Testing Patterns](04_testing_patterns.md) - Write comprehensive tests
- [API Reference](../api/effects.md) - Complete effect API documentation

---

**Previous**: [Tutorial 01: Quickstart](01_quickstart.md) | **Next**: [Tutorial 03: ADTs and Result Types](03_adts_and_results.md)
