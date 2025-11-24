# Programs API Reference

This document provides a comprehensive reference for program execution and program types.

> **Core Doctrine**: For program composition diagrams and execution flow, see [architecture.md](../core/architecture.md#program-composition).

## Overview

Programs are Python generators that yield effects and return values. They describe workflows using imperative-style code while maintaining functional purity through the effect system.

## Program Execution

### run_ws_program

Execute an effect program to completion with fail-fast error handling.

**Type Signature**:
```python
async def run_ws_program[T](
    program: Generator[AllEffects, EffectResult, T],
    interpreter: EffectInterpreter,
) -> Result[T, InterpreterError]
```

**Type Parameters**:
- `T` - The program's return type

**Parameters**:
- `program: Generator[AllEffects, EffectResult, T]` - The program to execute
- `interpreter: EffectInterpreter` - The interpreter that executes effects

**Returns**: `Result[T, InterpreterError]`
- `Ok(value: T)` - Program completed successfully with return value
- `Err(error: InterpreterError)` - First effect failure

**Usage**:
```python
from effectful import run_ws_program, SendText, GetUserById, Ok, Err

def greeting_program(user_id: UUID) -> Generator[AllEffects, EffectResult, str]:
    user = yield GetUserById(user_id=user_id)

    match user:
        case User(name=name):
            greeting = f"Hello {name}!"
            yield SendText(text=greeting)
            return greeting
        case UserNotFound():
            yield SendText(text="User not found")
            return "not_found"

# Execute program
result = await run_ws_program(greeting_program(user_id), interpreter)

# Handle result
match result:
    case Ok(greeting):
        print(f"Program succeeded: {greeting}")
    case Err(error):
        print(f"Program failed: {error}")
```

---

## Execution Behavior

### Sequential Effect Execution

Effects execute in the order they are yielded:

```python
def sequential_program() -> Generator[AllEffects, EffectResult, None]:
    yield SendText(text="Step 1")  # Executes first
    yield SendText(text="Step 2")  # Executes second
    yield SendText(text="Step 3")  # Executes third
    return None
```

### Fail-Fast Error Propagation

Program stops on first effect failure:

```python
def failing_program() -> Generator[AllEffects, EffectResult, str]:
    yield SendText(text="Before error")  # Succeeds

    # GetUserById fails with DatabaseError
    user = yield GetUserById(user_id=invalid_id)  # STOPS HERE

    # Never executed:
    yield SendText(text="After error")
    return "never"

# Program returns Err(DatabaseError) immediately
result = await run_ws_program(failing_program(), interpreter)
assert result.is_err()
```

### Type-Safe Return Values

Generic return types are preserved:

```python
def bool_program() -> Generator[AllEffects, EffectResult, bool]:
    user = yield GetUserById(user_id=user_id)
    return user is not None

# Result type: Result[bool, InterpreterError]
result = await run_ws_program(bool_program(), interpreter)

match result:
    case Ok(found):
        # 'found' has type bool
        assert isinstance(found, bool)
    case Err(error):
        ...
```

---

## Program Types

### AllEffects

Union of all effect types.

```python
type AllEffects = (
    WebSocketEffect      # SendText, ReceiveText, Close
    | DatabaseEffect     # GetUserById, SaveChatMessage, ListMessagesForUser, ListUsers, CreateUser, UpdateUser, DeleteUser
    | CacheEffect        # GetCachedProfile, PutCachedProfile, GetCachedValue, PutCachedValue, InvalidateCache
    | MessagingEffect    # PublishMessage, ConsumeMessage, AcknowledgeMessage, NegativeAcknowledge
    | StorageEffect      # PutObject, GetObject, DeleteObject, ListObjects
    | AuthEffect         # GenerateToken, ValidateToken, RefreshToken, RevokeToken, HashPassword, ValidatePassword
    | SystemEffect       # GetCurrentTime, GenerateUUID
)
```

**Usage**:
```python
from collections.abc import Generator
from effectful import AllEffects, EffectResult

def my_program() -> Generator[AllEffects, EffectResult, str]:
    # Can yield any effect in AllEffects union
    yield SendText(text="Hello")
    yield GetUserById(user_id=user_id)
    return "done"
```

---

### EffectResult

Union of all possible effect return values.

```python
type EffectResult = (
    None                      # SendText, Close, PutCachedProfile, AcknowledgeMessage, etc.
    | str                     # ReceiveText, PublishMessage, GenerateToken, RefreshToken, HashPassword
    | bool                    # ValidatePassword, InvalidateCache, PutCachedValue, DeleteUser
    | bytes                   # GetCachedValue (cache hit)
    | UUID                    # CreateUser, GenerateUUID
    | datetime                # GetCurrentTime
    # User ADTs
    | User                    # GetUserById, GetUserByEmail (success)
    | UserNotFound            # GetUserById, GetUserByEmail (not found)
    # Message types
    | ChatMessage             # SaveChatMessage
    # Cache ADTs
    | ProfileData             # GetCachedProfile (cache hit)
    | CacheMiss               # GetCachedProfile, GetCachedValue (cache miss)
    # Messaging ADTs
    | MessageEnvelope         # ConsumeMessage (success)
    | ConsumeTimeout          # ConsumeMessage (timeout)
    | PublishResult           # PublishMessage result
    # Storage types
    | S3Object                # GetObject (success)
    | PutSuccess              # PutObject (success)
    # Token ADTs
    | TokenValidationResult   # ValidateToken (TokenValid | TokenExpired | TokenInvalid)
    # List types
    | list[ChatMessage]       # ListMessagesForUser
    | list[str]               # ListObjects
    | list[User]              # ListUsers
)
```

**Components**:
- `str` - From `ReceiveText`, `HashPassword`, `GenerateToken`
- `User | UserNotFound` - From `GetUserById` (ADT for explicit semantics)
- `ChatMessage` - From `SaveChatMessage`
- `ProfileData | CacheMiss` - From `GetCachedProfile` (ADT for explicit semantics)
- `None` - From `SendText`, `Close`, `PutCachedProfile`
- `UUID` - From `GenerateUUID`
- `datetime` - From `GetCurrentTime`

**Type Narrowing**:

Programs must narrow types after yielding effects:

```python
def program() -> Generator[AllEffects, EffectResult, str]:
    # EffectResult is a wide union type
    message = yield SaveChatMessage(user_id=user_id, text="Hello")

    # Narrow to ChatMessage using assertion
    assert isinstance(message, ChatMessage)

    # Now type checker knows message is ChatMessage
    return f"Saved: {message.id}"
```

**Pattern Matching**:

```python
def program() -> Generator[AllEffects, EffectResult, str]:
    user_result = yield GetUserById(user_id=user_id)

    # Pattern match narrows type
    match user_result:
        case User(name=name):
            # Type checker knows this is User
            return f"Hello {name}"
        case UserNotFound():
            # Type checker knows this is UserNotFound
            return "Not found"
```

---

### WSProgram

Type alias for WebSocket programs that return None.

```python
type WSProgram = Generator[AllEffects, EffectResult, None]
```

**Usage**:
```python
def simple_greeting() -> WSProgram:
    yield SendText(text="Hello, client!")
    return None
```

Equivalent to:

```python
def simple_greeting() -> Generator[AllEffects, EffectResult, None]:
    yield SendText(text="Hello, client!")
    return None
```

---

## Program Patterns

### Basic Program Structure

```python
from collections.abc import Generator
from effectful import AllEffects, EffectResult, SendText

def my_program() -> Generator[AllEffects, EffectResult, str]:
    """
    Program docstring explaining what it does.

    Returns:
        Success message or error indicator
    """
    # 1. Yield effects
    yield SendText(text="Hello")

    # 2. Return final value
    return "success"
```

### Program with Parameters

```python
def parameterized_program(
    user_id: UUID,
    greeting: str,
) -> Generator[AllEffects, EffectResult, bool]:
    """Greet a specific user with custom message."""
    user = yield GetUserById(user_id=user_id)

    match user:
        case User(name=name):
            yield SendText(text=f"{greeting}, {name}!")
            return True
        case UserNotFound():
            yield SendText(text="User not found")
            return False
```

### Conditional Logic

```python
def conditional_program(
    user_id: UUID,
    should_cache: bool,
) -> Generator[AllEffects, EffectResult, None]:
    """Execute effects conditionally."""
    user = yield GetUserById(user_id=user_id)

    match user:
        case User(id=uid, name=name):
            yield SendText(text=f"Hello {name}!")

            # Conditional effect execution
            if should_cache:
                profile = ProfileData(id=str(uid), name=name)
                yield PutCachedProfile(user_id=user_id, profile_data=profile)
        case UserNotFound():
            yield SendText(text="User not found")

    return None
```

### Loops and Iteration

```python
def batch_program(
    user_ids: list[UUID],
) -> Generator[AllEffects, EffectResult, dict[str, int]]:
    """Process multiple users."""
    stats = {"found": 0, "not_found": 0}

    for uid in user_ids:
        user = yield GetUserById(user_id=uid)

        match user:
            case User(name=name):
                yield SendText(text=f"Found: {name}")
                stats["found"] += 1
            case UserNotFound():
                stats["not_found"] += 1

    return stats
```

### Error Handling

```python
def error_aware_program(
    user_id: UUID,
) -> Generator[AllEffects, EffectResult, str]:
    """Program that handles domain-level failures."""
    # Effect failures (DatabaseError, etc.) automatically stop program
    user = yield GetUserById(user_id=user_id)

    # Domain-level failures handled with pattern matching
    match user:
        case User(name=name):
            yield SendText(text=f"Hello {name}!")
            return "success"
        case UserNotFound():
            # User not found is not an error - it's a valid outcome
            yield SendText(text="User not found")
            return "not_found"
```

---

## Program Composition

### Delegating with yield from

Compose programs by delegating to sub-programs:

```python
def lookup_and_greet(user_id: UUID) -> Generator[AllEffects, EffectResult, str]:
    """Sub-program: lookup user and greet."""
    user = yield GetUserById(user_id=user_id)

    match user:
        case User(name=name):
            greeting = f"Hello {name}!"
            yield SendText(text=greeting)
            return greeting
        case UserNotFound():
            yield SendText(text="User not found")
            return "not_found"

def main_program(user_id: UUID) -> Generator[AllEffects, EffectResult, None]:
    """Main program: delegates to sub-program."""
    # Delegate to sub-program using yield from
    result = yield from lookup_and_greet(user_id)

    # Continue with sub-program's result
    yield SendText(text=f"Greeting result: {result}")
    return None
```

### Building Reusable Components

```python
def cache_user_profile(
    user_id: UUID,
    ttl_seconds: int = 300,
) -> Generator[AllEffects, EffectResult, ProfileData | None]:
    """Reusable: fetch user and cache profile."""
    user = yield GetUserById(user_id=user_id)

    match user:
        case User(id=uid, name=name):
            profile = ProfileData(id=str(uid), name=name)
            yield PutCachedProfile(
                user_id=user_id,
                profile_data=profile,
                ttl_seconds=ttl_seconds,
            )
            return profile
        case UserNotFound():
            return None

def workflow_with_caching(
    user_id: UUID,
) -> Generator[AllEffects, EffectResult, bool]:
    """Workflow using reusable component."""
    # Use reusable sub-program
    profile = yield from cache_user_profile(user_id, ttl_seconds=600)

    match profile:
        case ProfileData(name=name):
            yield SendText(text=f"Cached profile for {name}")
            return True
        case None:
            yield SendText(text="User not found")
            return False
```

### Recursive Programs

```python
def retry_with_backoff[T](
    program_factory: Callable[[], Generator[AllEffects, EffectResult, T]],
    max_retries: int = 3,
    delay_seconds: float = 1.0,
) -> Generator[AllEffects, EffectResult, T]:
    """Retry a program with exponential backoff."""
    for attempt in range(max_retries):
        # Execute program
        result = yield from program_factory()

        # Check if succeeded
        if result is not None:
            return result

        # Wait before retry (would need a Sleep effect for real implementation)
        if attempt < max_retries - 1:
            yield SendText(text=f"Retry {attempt + 1}/{max_retries}...")

    # All retries failed
    raise RuntimeError("Max retries exceeded")
```

---

## Advanced Patterns

### Cache-Aside Pattern

```python
def get_with_cache_aside(
    user_id: UUID,
) -> Generator[AllEffects, EffectResult, ProfileData | None]:
    """Get profile with cache-aside strategy."""
    # 1. Try cache first
    cached = yield GetCachedProfile(user_id=user_id)

    match cached:
        case ProfileData():
            # Cache hit
            return cached
        case CacheMiss():
            # Cache miss - fallback to database
            user = yield GetUserById(user_id=user_id)

            match user:
                case User(id=uid, name=name):
                    # Populate cache for next time
                    profile = ProfileData(id=str(uid), name=name)
                    yield PutCachedProfile(user_id=user_id, profile_data=profile)
                    return profile
                case UserNotFound():
                    return None
```

### Request-Response Pattern

```python
def request_response_program() -> Generator[AllEffects, EffectResult, None]:
    """Handle WebSocket request-response."""
    # 1. Receive request
    request = yield ReceiveText()
    assert isinstance(request, str)

    # 2. Parse and validate
    if not request.startswith("GET_USER:"):
        yield SendText(text="ERROR: Invalid request")
        return None

    user_id_str = request.removeprefix("GET_USER:")

    try:
        user_id = UUID(user_id_str)
    except ValueError:
        yield SendText(text="ERROR: Invalid UUID")
        return None

    # 3. Process request
    user = yield GetUserById(user_id=user_id)

    # 4. Send response
    match user:
        case User(name=name, email=email):
            yield SendText(text=f"USER:{name}:{email}")
        case UserNotFound():
            yield SendText(text="ERROR: User not found")

    return None
```

### Multi-Step Workflow

```python
def complete_workflow(
    user_id: UUID,
    message_text: str,
) -> Generator[AllEffects, EffectResult, dict[str, str]]:
    """Complete workflow with multiple steps."""
    # Step 1: Validate user exists
    user = yield GetUserById(user_id=user_id)

    match user:
        case UserNotFound():
            yield SendText(text="Error: User not found")
            return {"status": "error", "reason": "user_not_found"}
        case User(name=name):
            # Step 2: Send personalized greeting
            yield SendText(text=f"Hello {name}!")

            # Step 3: Save message
            message = yield SaveChatMessage(user_id=user_id, text=message_text)
            assert isinstance(message, ChatMessage)

            # Step 4: Confirm to user
            yield SendText(text=f"Message saved: {message.id}")

            # Step 5: Cache profile
            profile = ProfileData(id=str(user_id), name=name)
            yield PutCachedProfile(user_id=user_id, profile_data=profile)

            return {
                "status": "success",
                "message_id": str(message.id),
            }
```

---

## Performance Considerations

### Effect Batching

Programs execute effects sequentially. Batch independent effects when possible:

```python
# ❌ Inefficient - sequential lookups
def slow_program(user_ids: list[UUID]) -> Generator[AllEffects, EffectResult, list[User]]:
    users = []
    for uid in user_ids:
        user = yield GetUserById(user_id=uid)  # One query at a time
        if user is not None:
            users.append(user)
    return users

# ✅ Better - would need batch effect (future enhancement)
# def fast_program(user_ids: list[UUID]) -> Generator[AllEffects, EffectResult, list[User]]:
#     users = yield GetUsersByIds(user_ids=user_ids)  # Single batch query
#     return users
```

### Caching Strategy

Use cache to reduce database load:

```python
def optimized_program(
    user_id: UUID,
) -> Generator[AllEffects, EffectResult, str]:
    """Check cache before database."""
    # Fast path: cache
    cached = yield GetCachedProfile(user_id=user_id)

    match cached:
        case ProfileData(name=name):
            return f"Hello {name} (cached)"
        case CacheMiss():
            # Slow path: database
            user = yield GetUserById(user_id=user_id)

            match user:
                case User(name=name):
                    # Populate cache for next request
                    profile = ProfileData(id=str(user_id), name=name)
                    yield PutCachedProfile(user_id=user_id, profile_data=profile)
                    return f"Hello {name}"
                case UserNotFound():
                    return "User not found"
```

---

## Debugging Programs

### Logging Effect Execution

```python
import logging

logger = logging.getLogger(__name__)

def instrumented_program(
    user_id: UUID,
) -> Generator[AllEffects, EffectResult, str]:
    """Program with logging for debugging."""
    logger.info(f"Starting program for user {user_id}")

    logger.debug("Fetching user from database")
    user = yield GetUserById(user_id=user_id)

    match user:
        case User(name=name):
            logger.info(f"User found: {name}")
            yield SendText(text=f"Hello {name}!")
            return "success"
        case UserNotFound():
            logger.warning(f"User not found: {user_id}")
            return "not_found"
```

### Tracing with EffectReturn

Access effect names for tracing:

```python
# Interpreters return EffectReturn with effect_name
# Can be used for distributed tracing, metrics, etc.
```

---

## See Also

- [Effects API](./effects.md) - Effect types used in programs
- [Result Type API](./result.md) - Return types from run_ws_program
- [Interpreters API](./interpreters.md) - Executing programs
- [Testing API](./testing.md) - Testing programs
