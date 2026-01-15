# Effects API Reference

**Status**: Authoritative source
**Supersedes**: none
**Referenced by**: documents/api/README.md

> **Purpose**: Comprehensive reference for all effect types in the effectful package.

> **Note**: This API reference covers the legacy Python effectful library. For the Effectful Language, see [DSL Documentation](../dsl/intro.md).

> **Core Doctrine**: For the effect type hierarchy diagram and architecture patterns, see [architecture.md](../engineering/architecture.md#effect-type-hierarchy).

## SSoT Link Map

| Need                      | Link                                                                 |
| ------------------------- | -------------------------------------------------------------------- |
| Effect type hierarchy     | [Architecture](../engineering/architecture.md#effect-type-hierarchy) |
| Auth effects              | [Auth API](auth.md)                                                  |
| Messaging effects         | [Messaging API](messaging.md)                                        |
| Storage effects           | [Storage API](storage.md)                                            |
| Metrics effects           | [Metrics API](metrics.md)                                            |
| Interpreter configuration | [Interpreters API](interpreters.md)                                  |
| Program execution         | [Programs API](programs.md)                                          |
| Testing effects           | [Testing](../engineering/testing.md)                                 |

## Overview

Effects are declarative descriptions of side effects. They are pure data structures that describe **what** should happen, without implementing **how** it happens. Interpreters handle the actual execution.

## Effect Categories

- **WebSocket Effects**: Communication over WebSocket connections
- **Database Effects**: Data persistence and retrieval
- **Cache Effects**: High-performance data caching
- **Auth Effects**: JWT authentication and password operations - see [Auth API](auth.md)
- **Messaging Effects**: Pub/sub with Apache Pulsar - see [Messaging API](messaging.md)
- **Storage Effects**: S3-compatible object storage - see [Storage API](storage.md)
- **System Effects**: Pure time and UUID generation

## WebSocket Effects

### SendText

Send a text message over the WebSocket connection.

**Type Signature**:

```python
# file: examples/effects.py
@dataclass(frozen=True)
class SendText:
    text: str
```

**Parameters**:

- `text: str` - The message to send

**Returns**: `None` (wrapped in `EffectReturn[None]`)

**Usage**:

```python
# file: examples/effects.py
from effectful import SendText

def greeting_program() -> Generator[AllEffects, EffectResult, None]:
    yield SendText(text="Hello, client!")
    return None
```

**Error Cases**:

- `WebSocketClosedError` - Connection is closed

______________________________________________________________________

### ReceiveText

Receive a text message from the WebSocket connection.

**Type Signature**:

```python
# file: examples/effects.py
@dataclass(frozen=True)
class ReceiveText:
    """Effect: Receive a text message."""
    # No fields; interpreter yields the inbound text as the generator result
```

**Parameters**: None

**Returns**: `str` - The received message text

**Usage**:

```python
# file: examples/effects.py
from effectful import ReceiveText, SendText

def echo_program() -> Generator[AllEffects, EffectResult, None]:
    message = yield ReceiveText()
    assert isinstance(message, str)
    yield SendText(text=f"Echo: {message}")
    return None
```

**Error Cases**:

- `WebSocketClosedError` - Connection closed before receiving

______________________________________________________________________

### Close

Close the WebSocket connection with a specific reason.

**Type Signature**:

```python
# file: examples/effects.py
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
# file: examples/effects.py
from effectful import Close, CloseNormal, SendText

def goodbye_program() -> Generator[AllEffects, EffectResult, None]:
    yield SendText(text="Goodbye!")
    yield Close(reason=CloseNormal())
    return None
```

**Notes**:

- Close always succeeds, even if connection is already closed
- After close, further send/receive operations will fail

______________________________________________________________________

## Database Effects

### GetUserById

Lookup a user by their unique identifier.

**Type Signature**:

```python
# file: examples/effects.py
@dataclass(frozen=True)
class GetUserById:
    user_id: UUID
```

**Parameters**:

- `user_id: UUID` - The user's unique identifier

**Returns**: `User | UserNotFound`

- `User` - If user found in database
- `UserNotFound` - ADT if user not found (with `user_id` and `reason` fields)

**Usage**:

```python
# file: examples/effects.py
from uuid import UUID
from effectful import GetUserById, SendText
from effectful.domain.user import User, UserNotFound

def greet_user(user_id: UUID) -> Generator[AllEffects, EffectResult, bool]:
    user_result = yield GetUserById(user_id=user_id)

    match user_result:
        case UserNotFound():
            yield SendText(text="User not found")
            return False
        case User(name=name):
            yield SendText(text=f"Hello, {name}!")
            return True
```

**Error Cases**:

- `DatabaseError` - Database connection failure or query error

**Domain Model**:

````python
# file: examples/effects.py
@dataclass(frozen=True)
class User:
    id: UUID
    email: str
    name: str
```text

______________________________________________________________________

### SaveChatMessage

Persist a chat message to the database.

**Type Signature**:

```python
# file: examples/effects.py
@dataclass(frozen=True)
class SaveChatMessage:
    user_id: UUID
    text: str
````

**Parameters**:

- `user_id: UUID` - The user who sent the message
- `text: str` - The message content

**Returns**: `ChatMessage` - The saved message with generated ID and timestamp

**Usage**:

```python
# file: examples/effects.py
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

````python
# file: examples/effects.py
@dataclass(frozen=True)
class ChatMessage:
    id: UUID
    user_id: UUID
    text: str
    created_at: datetime
```text

______________________________________________________________________

### ListUsers

List users with pagination support.

**Type Signature**:

```python
# file: examples/effects.py
@dataclass(frozen=True)
class ListUsers:
    limit: int | None = None
    offset: int | None = None
````

**Parameters**:

- `limit: int | None` - Maximum number of users to return (default: None for all)
- `offset: int | None` - Number of users to skip (default: None for 0)

**Returns**: `list[User]` - List of users (may be empty)

**Usage**:

```python
# file: examples/effects.py
from effectful import ListUsers, SendText

def list_all_users() -> Generator[AllEffects, EffectResult, int]:
    users = yield ListUsers(limit=50, offset=0)
    assert isinstance(users, list)

    yield SendText(text=f"Found {len(users)} users")
    return len(users)
```

**Error Cases**:

- `DatabaseError` - Database connection failure or query error

______________________________________________________________________

### CreateUser

Create a new user in the database.

**Type Signature**:

```python
# file: examples/effects.py
@dataclass(frozen=True)
class CreateUser:
    email: str
    name: str
    password_hash: str
```

**Parameters**:

- `email: str` - User's email address
- `name: str` - User's display name
- `password_hash: str` - Bcrypt password hash

**Returns**: `User` - The created user with generated ID

**Usage**:

```python
# file: examples/effects.py
from effectful import CreateUser, HashPassword, SendText

def register_user(
    email: str, name: str, password: str
) -> Generator[AllEffects, EffectResult, UUID]:
    # Hash password first
    password_hash = yield HashPassword(password=password)
    assert isinstance(password_hash, str)

    user = yield CreateUser(email=email, name=name, password_hash=password_hash)
    assert isinstance(user, User)

    yield SendText(text=f"Created user: {user.name}")
    return user.id
```

**Error Cases**:

- `DatabaseError` - Database connection failure or constraint violation (e.g., duplicate email)

______________________________________________________________________

### UpdateUser

Update an existing user's information.

**Type Signature**:

```python
# file: examples/effects.py
@dataclass(frozen=True)
class UpdateUser:
    user_id: UUID
    email: str | None = None
    name: str | None = None
```

**Parameters**:

- `user_id: UUID` - The user's unique identifier
- `email: str | None` - New email address (optional)
- `name: str | None` - New display name (optional)

**Returns**: `User | UserNotFound`

- `User` - The updated user if found
- `UserNotFound` - ADT if user doesn't exist

**Usage**:

```python
# file: examples/effects.py
from uuid import UUID
from effectful import UpdateUser, SendText
from effectful.domain.user import UserNotFound

def update_user_name(user_id: UUID, new_name: str) -> Generator[AllEffects, EffectResult, bool]:
    result = yield UpdateUser(user_id=user_id, name=new_name)

    match result:
        case User(name=name):
            yield SendText(text=f"Updated user to: {name}")
            return True
        case UserNotFound():
            yield SendText(text="User not found")
            return False
```

**Error Cases**:

- `DatabaseError` - Database connection failure or constraint violation

______________________________________________________________________

### DeleteUser

Delete a user from the database.

**Type Signature**:

```python
# file: examples/effects.py
@dataclass(frozen=True)
class DeleteUser:
    user_id: UUID
```

**Parameters**:

- `user_id: UUID` - The user's unique identifier

**Returns**: `bool` - True if deleted, False if user not found

**Usage**:

```python
# file: examples/effects.py
from uuid import UUID
from effectful import DeleteUser, SendText

def remove_user(user_id: UUID) -> Generator[AllEffects, EffectResult, bool]:
    deleted = yield DeleteUser(user_id=user_id)
    assert isinstance(deleted, bool)

    if deleted:
        yield SendText(text="User deleted successfully")
    else:
        yield SendText(text="User not found")

    return deleted
```

**Error Cases**:

- `DatabaseError` - Database connection failure

______________________________________________________________________

### ListMessagesForUser

Retrieve all messages for a specific user.

**Type Signature**:

```python
# file: examples/effects.py
@dataclass(frozen=True)
class ListMessagesForUser:
    user_id: UUID
```

**Parameters**:

- `user_id: UUID` - The user's unique identifier

**Returns**: `list[ChatMessage]` - List of messages (may be empty)

**Usage**:

```python
# file: examples/effects.py
from uuid import UUID
from effectful import ListMessagesForUser, SendText

def get_user_history(user_id: UUID) -> Generator[AllEffects, EffectResult, int]:
    messages = yield ListMessagesForUser(user_id=user_id)
    assert isinstance(messages, list)

    yield SendText(text=f"Found {len(messages)} messages")
    return len(messages)
```

**Error Cases**:

- `DatabaseError` - Database connection failure or query error

______________________________________________________________________

## Cache Effects

### GetCachedProfile

Retrieve a user's profile from the cache.

**Type Signature**:

```python
# file: examples/effects.py
@dataclass(frozen=True)
class GetCachedProfile:
    user_id: UUID
```

**Parameters**:

- `user_id: UUID` - The user's unique identifier

**Returns**: `ProfileData | CacheMiss`

- `ProfileData` - If profile found in cache
- `CacheMiss` - ADT if profile not found (cache miss)

**Usage**:

```python
# file: examples/effects.py
from uuid import UUID
from effectful import GetCachedProfile, GetUserById, SendText
from effectful.domain.cache_result import CacheMiss
from effectful.domain.user import User, UserNotFound

def get_profile_cached(user_id: UUID) -> Generator[AllEffects, EffectResult, str]:
    # Try cache first
    cached = yield GetCachedProfile(user_id=user_id)

    match cached:
        case ProfileData(name=name):
            yield SendText(text=f"Hello {name} (from cache)!")
            return "cache_hit"
        case CacheMiss():
            # Cache miss - fallback to database
            user = yield GetUserById(user_id=user_id)
            match user:
                case UserNotFound():
                    return "not_found"
                case User(name=name):
                    yield SendText(text=f"Hello {name} (from DB)!")
                    return "db_hit"
```

**Error Cases**:

- `CacheError` - Cache connection failure or timeout

**Domain Model**:

````python
# file: examples/effects.py
@dataclass(frozen=True)
class ProfileData:
    id: str  # UUID as string
    name: str
```text

______________________________________________________________________

### PutCachedProfile

Store a user's profile in the cache.

**Type Signature**:

```python
# file: examples/effects.py
@dataclass(frozen=True)
class PutCachedProfile:
    user_id: UUID
    profile_data: ProfileData
    ttl_seconds: int = 300  # 5 minutes default
````

**Parameters**:

- `user_id: UUID` - The user's unique identifier
- `profile_data: ProfileData` - The profile data to cache
- `ttl_seconds: int` - Time-to-live in seconds (default: 300)

**Returns**: `None` (wrapped in `EffectReturn[None]`)

**Usage**:

```python
# file: examples/effects.py
from uuid import UUID
from effectful import (
    GetUserById,
    PutCachedProfile,
    ProfileData,
)

def cache_user_profile(user_id: UUID) -> Generator[AllEffects, EffectResult, bool]:
    user = yield GetUserById(user_id=user_id)

    match user:
        case UserNotFound():
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

______________________________________________________________________

### GetCachedValue

Retrieve a value from the cache by key (generic key-value storage).

**Type Signature**:

```python
# file: examples/effects.py
@dataclass(frozen=True)
class GetCachedValue:
    key: str
```

**Parameters**:

- `key: str` - The cache key to retrieve

**Returns**: `bytes | CacheMiss`

- `bytes` - The cached value if found
- `CacheMiss` - ADT if key not found

**Usage**:

```python
# file: examples/effects.py
from effectful import GetCachedValue, SendText
from effectful.domain.cache_result import CacheMiss

def get_session_data(session_id: str) -> Generator[AllEffects, EffectResult, bytes | None]:
    result = yield GetCachedValue(key=f"session:{session_id}")

    match result:
        case bytes() as data:
            yield SendText(text="Session found")
            return data
        case CacheMiss():
            yield SendText(text="Session not found")
            return None
```

**Error Cases**:

- `CacheError` - Cache connection failure or timeout

______________________________________________________________________

### PutCachedValue

Store a value in the cache with TTL (generic key-value storage).

**Type Signature**:

```python
# file: examples/effects.py
@dataclass(frozen=True)
class PutCachedValue:
    key: str
    value: bytes
    ttl_seconds: int
```

**Parameters**:

- `key: str` - The cache key
- `value: bytes` - The value to cache
- `ttl_seconds: int` - Time-to-live in seconds

**Returns**: `bool` - True if stored successfully

**Usage**:

```python
# file: examples/effects.py
import json
from effectful import PutCachedValue

def cache_session(session_id: str, data: dict[str, str]) -> Generator[AllEffects, EffectResult, bool]:
    value = json.dumps(data).encode()
    result = yield PutCachedValue(
        key=f"session:{session_id}",
        value=value,
        ttl_seconds=3600  # 1 hour
    )
    assert isinstance(result, bool)
    return result
```

**Error Cases**:

- `CacheError` - Cache connection failure or out of memory

______________________________________________________________________

### InvalidateCache

Remove a value from the cache by key.

**Type Signature**:

```python
# file: examples/effects.py
@dataclass(frozen=True)
class InvalidateCache:
    key: str
```

**Parameters**:

- `key: str` - The cache key to invalidate

**Returns**: `bool` - True if deleted, False if key not found

**Usage**:

```python
# file: examples/effects.py
from effectful import InvalidateCache, SendText

def logout_session(session_id: str) -> Generator[AllEffects, EffectResult, bool]:
    deleted = yield InvalidateCache(key=f"session:{session_id}")
    assert isinstance(deleted, bool)

    if deleted:
        yield SendText(text="Session invalidated")
    else:
        yield SendText(text="Session already expired")

    return deleted
```

**Error Cases**:

- `CacheError` - Cache connection failure

______________________________________________________________________

## Effect Composition Patterns

### Sequential Composition

Chain effects in sequence using normal generator syntax:

```python
# file: examples/effects.py
def multi_step_workflow(user_id: UUID) -> Generator[AllEffects, EffectResult, None]:
    # Effects execute in order
    user = yield GetUserById(user_id=user_id)

    match user:
        case User(name=name):
            yield SendText(text=f"Hello {name}!")
            message = yield SaveChatMessage(user_id=user_id, text=f"Hello {name}!")
            assert isinstance(message, ChatMessage)
            yield SendText(text="Message saved!")
        case UserNotFound():
            yield SendText(text="User not found")

    return None
```

### Delegating Composition

Delegate to sub-programs using `yield from`:

```python
# file: examples/effects.py
def lookup_and_greet(user_id: UUID) -> Generator[AllEffects, EffectResult, str]:
    user = yield GetUserById(user_id=user_id)

    match user:
        case UserNotFound():
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
# file: examples/effects.py
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
        case UserNotFound():
            yield SendText(text="User not found")

    return None
```

### Error-Aware Composition

Programs automatically stop on first error (fail-fast):

````python
# file: examples/effects.py
def error_aware_program(user_id: UUID) -> Generator[AllEffects, EffectResult, str]:
    # If GetUserById returns Err(DatabaseError), program stops here
    user = yield GetUserById(user_id=user_id)

    # This only executes if GetUserById succeeded
    match user:
        case User(name=name):
            # If SendText returns Err(WebSocketClosedError), program stops here
            yield SendText(text=f"Hello {name}!")
            return "success"
        case UserNotFound():
            return "not_found"
```text

______________________________________________________________________

## System Effects

System effects provide pure access to otherwise impure system resources, enabling full purity in effect programs by making time and UUID generation explicit and testable.

### GetCurrentTime

Get the current UTC timestamp.

**Type Signature**:

```python
# file: examples/effects.py
@dataclass(frozen=True)
class GetCurrentTime:
    pass
````

**Parameters**: None

**Returns**: `datetime` - Current UTC timestamp

**Usage**:

```python
# file: examples/effects.py
from effectful import GetCurrentTime, SendText
from datetime import datetime

def log_with_timestamp() -> Generator[AllEffects, EffectResult, None]:
    current_time = yield GetCurrentTime()
    assert isinstance(current_time, datetime)

    yield SendText(text=f"Current time: {current_time.isoformat()}")
    return None
```

**Why Use This Effect?**:

- Makes time-dependent code testable (inject fixed times in tests)
- Explicit dependency on current time
- Pure functions remain pure

______________________________________________________________________

### GenerateUUID

Generate a new UUID v4.

**Type Signature**:

```python
# file: examples/effects.py
@dataclass(frozen=True)
class GenerateUUID:
    pass
```

**Parameters**: None

**Returns**: `UUID` - Newly generated UUID v4

**Usage**:

```python
# file: examples/effects.py
from uuid import UUID
from effectful import GenerateUUID, SaveChatMessage, SendText

def create_message_with_id(user_id: UUID, text: str) -> Generator[AllEffects, EffectResult, UUID]:
    new_id = yield GenerateUUID()
    assert isinstance(new_id, UUID)

    # Use the generated ID
    yield SendText(text=f"Generated message ID: {new_id}")
    return new_id
```

**Why Use This Effect?**:

- Makes UUID-dependent code testable (inject fixed UUIDs in tests)
- Explicit dependency on randomness
- Enables deterministic testing of ID generation

______________________________________________________________________

## See Also

- [Auth Effects API](./auth.md) - JWT tokens and passwords
- [Messaging Effects API](./messaging.md) - Pub/sub messaging
- [Storage Effects API](./storage.md) - S3 object storage
- [Result Type API](./result.md) - Error handling with Result types
- [Interpreters API](./interpreters.md) - How effects are executed
- [Programs API](./programs.md) - Program execution and types
- [Testing Standards](../engineering/testing.md) - Testing programs with effects

______________________________________________________________________

## Cross-References

- [Documentation Standards](../documentation_standards.md)
- [Engineering Architecture](../engineering/architecture.md)
