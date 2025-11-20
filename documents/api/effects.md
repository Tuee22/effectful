# Effects API Reference

This document provides a comprehensive reference for all effect types in the effectful package.

## Overview

Effects are declarative descriptions of side effects. They are pure data structures that describe **what** should happen, without implementing **how** it happens. Interpreters handle the actual execution.

## Effect Categories

- **WebSocket Effects**: Communication over WebSocket connections
- **Database Effects**: Data persistence and retrieval
- **Cache Effects**: High-performance data caching

## WebSocket Effects

### SendText

Send a text message over the WebSocket connection.

**Type Signature**:
```python
@dataclass(frozen=True)
class SendText:
    text: str
```

**Parameters**:
- `text: str` - The message to send

**Returns**: `None` (wrapped in `EffectReturn[None]`)

**Usage**:
```python
from effectful import SendText

def greeting_program() -> Generator[AllEffects, EffectResult, None]:
    yield SendText(text="Hello, client!")
    return None
```

**Error Cases**:
- `WebSocketClosedError` - Connection is closed

---

### ReceiveText

Receive a text message from the WebSocket connection.

**Type Signature**:
```python
@dataclass(frozen=True)
class ReceiveText:
    pass
```

**Parameters**: None

**Returns**: `str` - The received message text

**Usage**:
```python
from effectful import ReceiveText, SendText

def echo_program() -> Generator[AllEffects, EffectResult, None]:
    message = yield ReceiveText()
    assert isinstance(message, str)
    yield SendText(text=f"Echo: {message}")
    return None
```

**Error Cases**:
- `WebSocketClosedError` - Connection closed before receiving

---

### Close

Close the WebSocket connection with a specific reason.

**Type Signature**:
```python
@dataclass(frozen=True)
class Close:
    reason: CloseReason

type CloseReason = CloseNormal | CloseGoingAway | CloseProtocolError | ClosePolicyViolation
```

**Parameters**:
- `reason: CloseReason` - The close reason (ADT with 4 variants)

**Close Reasons**:
- `CloseNormal()` - Normal closure (1000)
- `CloseGoingAway()` - Endpoint going away (1001)
- `CloseProtocolError()` - Protocol error (1002)
- `ClosePolicyViolation()` - Policy violation (1008)

**Returns**: `None` (wrapped in `EffectReturn[None]`)

**Usage**:
```python
from effectful import Close, CloseNormal, SendText

def goodbye_program() -> Generator[AllEffects, EffectResult, None]:
    yield SendText(text="Goodbye!")
    yield Close(reason=CloseNormal())
    return None
```

**Notes**:
- Close always succeeds, even if connection is already closed
- After close, further send/receive operations will fail

---

## Database Effects

### GetUserById

Lookup a user by their unique identifier.

**Type Signature**:
```python
@dataclass(frozen=True)
class GetUserById:
    user_id: UUID
```

**Parameters**:
- `user_id: UUID` - The user's unique identifier

**Returns**: `User | None`
- `User` - If user found in database
- `None` - If user not found

**Usage**:
```python
from uuid import UUID
from effectful import GetUserById, SendText

def greet_user(user_id: UUID) -> Generator[AllEffects, EffectResult, bool]:
    user_result = yield GetUserById(user_id=user_id)

    match user_result:
        case None:
            yield SendText(text="User not found")
            return False
        case User(name=name):
            yield SendText(text=f"Hello, {name}!")
            return True
```

**Error Cases**:
- `DatabaseError` - Database connection failure or query error

**Domain Model**:
```python
@dataclass(frozen=True)
class User:
    id: UUID
    email: str
    name: str
```

---

### SaveChatMessage

Persist a chat message to the database.

**Type Signature**:
```python
@dataclass(frozen=True)
class SaveChatMessage:
    user_id: UUID
    text: str
```

**Parameters**:
- `user_id: UUID` - The user who sent the message
- `text: str` - The message content

**Returns**: `ChatMessage` - The saved message with generated ID and timestamp

**Usage**:
```python
from uuid import UUID
from effectful import SaveChatMessage, SendText

def save_and_confirm(user_id: UUID, text: str) -> Generator[AllEffects, EffectResult, None]:
    message = yield SaveChatMessage(user_id=user_id, text=text)
    assert isinstance(message, ChatMessage)

    yield SendText(text=f"Message saved with ID: {message.id}")
    return None
```

**Error Cases**:
- `DatabaseError` - Database connection failure or constraint violation

**Domain Model**:
```python
@dataclass(frozen=True)
class ChatMessage:
    id: UUID
    user_id: UUID
    text: str
    created_at: datetime
```

---

## Cache Effects

### GetCachedProfile

Retrieve a user's profile from the cache.

**Type Signature**:
```python
@dataclass(frozen=True)
class GetCachedProfile:
    user_id: UUID
```

**Parameters**:
- `user_id: UUID` - The user's unique identifier

**Returns**: `ProfileData | None`
- `ProfileData` - If profile found in cache
- `None` - If profile not found (cache miss)

**Usage**:
```python
from uuid import UUID
from effectful import GetCachedProfile, GetUserById, SendText

def get_profile_cached(user_id: UUID) -> Generator[AllEffects, EffectResult, str]:
    # Try cache first
    cached = yield GetCachedProfile(user_id=user_id)

    match cached:
        case ProfileData(name=name):
            yield SendText(text=f"Hello {name} (from cache)!")
            return "cache_hit"
        case None:
            # Cache miss - fallback to database
            user = yield GetUserById(user_id=user_id)
            match user:
                case None:
                    return "not_found"
                case User(name=name):
                    yield SendText(text=f"Hello {name} (from DB)!")
                    return "db_hit"
```

**Error Cases**:
- `CacheError` - Cache connection failure or timeout

**Domain Model**:
```python
@dataclass(frozen=True)
class ProfileData:
    id: str  # UUID as string
    name: str
```

---

### PutCachedProfile

Store a user's profile in the cache.

**Type Signature**:
```python
@dataclass(frozen=True)
class PutCachedProfile:
    user_id: UUID
    profile_data: ProfileData
    ttl_seconds: int = 300  # 5 minutes default
```

**Parameters**:
- `user_id: UUID` - The user's unique identifier
- `profile_data: ProfileData` - The profile data to cache
- `ttl_seconds: int` - Time-to-live in seconds (default: 300)

**Returns**: `None` (wrapped in `EffectReturn[None]`)

**Usage**:
```python
from uuid import UUID
from effectful import (
    GetUserById,
    PutCachedProfile,
    ProfileData,
)

def cache_user_profile(user_id: UUID) -> Generator[AllEffects, EffectResult, bool]:
    user = yield GetUserById(user_id=user_id)

    match user:
        case None:
            return False
        case User(id=uid, name=name):
            profile = ProfileData(id=str(uid), name=name)
            yield PutCachedProfile(
                user_id=user_id,
                profile_data=profile,
                ttl_seconds=600  # 10 minutes
            )
            return True
```

**Error Cases**:
- `CacheError` - Cache connection failure or out of memory

---

## Effect Composition Patterns

### Sequential Composition

Chain effects in sequence using normal generator syntax:

```python
def multi_step_workflow(user_id: UUID) -> Generator[AllEffects, EffectResult, None]:
    # Effects execute in order
    user = yield GetUserById(user_id=user_id)

    match user:
        case User(name=name):
            yield SendText(text=f"Hello {name}!")
            message = yield SaveChatMessage(user_id=user_id, text=f"Hello {name}!")
            assert isinstance(message, ChatMessage)
            yield SendText(text="Message saved!")
        case None:
            yield SendText(text="User not found")

    return None
```

### Delegating Composition

Delegate to sub-programs using `yield from`:

```python
def lookup_and_greet(user_id: UUID) -> Generator[AllEffects, EffectResult, str]:
    user = yield GetUserById(user_id=user_id)

    match user:
        case None:
            yield SendText(text="User not found")
            return "not_found"
        case User(name=name):
            greeting = f"Hello {name}!"
            yield SendText(text=greeting)
            return greeting

def main_program(user_id: UUID) -> Generator[AllEffects, EffectResult, None]:
    # Delegate to sub-program
    greeting = yield from lookup_and_greet(user_id)

    # Continue with result
    yield SendText(text=f"Greeting complete: {greeting}")
    return None
```

### Conditional Effects

Execute effects based on runtime conditions:

```python
def conditional_workflow(
    user_id: UUID,
    should_cache: bool
) -> Generator[AllEffects, EffectResult, None]:
    user = yield GetUserById(user_id=user_id)

    match user:
        case User(id=uid, name=name):
            yield SendText(text=f"Hello {name}!")

            # Conditional caching
            if should_cache:
                profile = ProfileData(id=str(uid), name=name)
                yield PutCachedProfile(user_id=user_id, profile_data=profile)
        case None:
            yield SendText(text="User not found")

    return None
```

### Error-Aware Composition

Programs automatically stop on first error (fail-fast):

```python
def error_aware_program(user_id: UUID) -> Generator[AllEffects, EffectResult, str]:
    # If GetUserById returns Err(DatabaseError), program stops here
    user = yield GetUserById(user_id=user_id)

    # This only executes if GetUserById succeeded
    match user:
        case User(name=name):
            # If SendText returns Err(WebSocketClosedError), program stops here
            yield SendText(text=f"Hello {name}!")
            return "success"
        case None:
            return "not_found"
```

---

## See Also

- [Result Type API](./result.md) - Error handling with Result types
- [Interpreters API](./interpreters.md) - How effects are executed
- [Programs API](./programs.md) - Program execution and types
- [Testing API](./testing.md) - Testing programs with effects
