# Effect Program Patterns

> **SSoT** for effect program composition, error handling, and real-world code examples in effectful.

## Overview

This document provides **real-world patterns** for writing effect programs using effectful's generator-based DSL.

**Core Principle**: Programs are pure generators that yield effects and receive typed results.

For complete purity rules and functional programming patterns, see [Purity](purity.md) and [Purity Patterns](purity_patterns.md).

## Pattern 1: Generator-Based DSL

**Use Case**: All effect programs use this pattern as the foundation.

```python
from collections.abc import Generator
from effectful import (
    AllEffects,
    EffectResult,
    GetUserById,
    SendText,
    SaveChatMessage,
)
from effectful.domain import User, ChatMessage

def greet_user(user_id: UUID) -> Generator[AllEffects, EffectResult, bool]:
    """Effect program that looks up user and sends personalized greeting."""

    # Yield effect, receive result
    user = yield GetUserById(user_id=user_id)

    # Type narrowing
    if not isinstance(user, User):
        yield SendText(text="Error: User not found")
        return False

    # Use narrowed type
    greeting = f"Hello {user.name}!"
    yield SendText(text=greeting)

    # Type narrowing for next effect
    message = yield SaveChatMessage(user_id=user_id, text=greeting)
    assert isinstance(message, ChatMessage)

    yield SendText(text=f"Message saved with ID: {message.id}")
    return True
```

**Key Points**:
- **Type signature**: `Generator[AllEffects, EffectResult, ReturnType]`
- **Yield pattern**: `result = yield Effect(...)`
- **Type narrowing**: Use `isinstance()` checks before using result
- **Return value**: Any type (bool, str, ADT, etc.)

**See**: [Type Safety](type-safety-enforcement.md) - Doctrine 6: Type Narrowing for Union Types.

---

## Pattern 2: Fail-Fast Error Propagation

**Use Case**: Handle errors from effect execution at the program boundary.

```python
from effectful import run_ws_program
from effectful.algebraic.result import Ok, Err

async def execute() -> None:
    result = await run_ws_program(greet_user(user_id), interpreter)

    # run_ws_program returns Err immediately on first effect failure
    match result:
        case Ok(success):
            print(f"Program completed: {success}")
        case Err(error):
            print(f"Program failed: {error}")
            # error is one of: DatabaseError | WebSocketClosedError | CacheError | etc.
```

**Key Points**:
- **First effect failure stops program**: No partial execution
- **Error type is union**: `DatabaseError | WebSocketClosedError | ...`
- **Pattern match required**: Caller must handle Ok and Err cases
- **No exceptions**: All errors returned as Result types

**Rationale**: Fail-fast prevents cascading failures and inconsistent state.

**See**: [Type Safety](type-safety-enforcement.md) - Doctrine 3: Result Type for Error Handling.

---

## Pattern 3: Composing Programs

**Use Case**: Build complex workflows from smaller, reusable programs.

```python
def lookup_and_cache_profile(
    user_id: UUID
) -> Generator[AllEffects, EffectResult, ProfileData | None]:
    """Reusable program: lookup user, create profile, cache it."""
    user = yield GetUserById(user_id=user_id)

    if not isinstance(user, User):
        return None

    profile = ProfileData(id=str(user.id), name=user.name, email=user.email)
    yield PutCachedProfile(user_id=user.id, profile_data=profile, ttl_seconds=300)
    return profile

def greet_with_caching(user_id: UUID) -> Generator[AllEffects, EffectResult, str]:
    """Compose smaller programs into larger workflows."""

    # Check cache first
    cached = yield GetCachedProfile(user_id=user_id)
    if isinstance(cached, ProfileData):
        greeting = f"Hello {cached.name} (from cache)!"
    else:
        # Cache miss - lookup and cache
        profile = yield from lookup_and_cache_profile(user_id)
        if profile is None:
            return "User not found"
        greeting = f"Hello {profile.name}!"

    yield SendText(text=greeting)
    return greeting
```

**Key Points**:
- **yield from**: Delegates to sub-program
- **Reusable sub-programs**: `lookup_and_cache_profile` can be used anywhere
- **Type safety**: Sub-program return type flows through
- **Composition pattern**: Build complex from simple

**Rationale**: Encourages modularity and code reuse.

**See**: [Purity Patterns](purity_patterns.md) for functional composition patterns.

---

## Pattern 4: Recording Metrics (Don't Fail on Metric Errors)

**Use Case**: Record metrics without causing business logic to fail.

```python
from effectful.effects.metrics import IncrementCounter, ObserveHistogram
from effectful.domain.metrics_result import MetricRecorded, MetricRecordingFailed
import time

def process_task_with_metrics(
    task_type: str,
    task_id: str,
) -> Generator[AllEffects, EffectResult, bool]:
    """Process task and record metrics."""

    # Start timer
    start = time.perf_counter()

    # Execute business logic
    result = yield ProcessTask(task_id=task_id)

    # Calculate duration
    duration = time.perf_counter() - start
    status = "success" if isinstance(result, TaskCompleted) else "failed"

    # Record counter metric
    counter_result = yield IncrementCounter(
        metric_name="tasks_processed_total",
        labels={"task_type": task_type, "status": status},
        value=1.0,
    )

    # Record histogram metric
    histogram_result = yield ObserveHistogram(
        metric_name="task_duration_seconds",
        labels={"task_type": task_type},
        value=duration,
    )

    # Pattern match on results
    match (counter_result, histogram_result):
        case (MetricRecorded(), MetricRecorded()):
            return True
        case (MetricRecordingFailed(reason=r), _):
            # Log error but don't fail the task
            print(f"⚠️  Counter metric failed: {r}")
            return isinstance(result, TaskCompleted)
        case (_, MetricRecordingFailed(reason=r)):
            print(f"⚠️  Histogram metric failed: {r}")
            return isinstance(result, TaskCompleted)
```

**Key Points**:
- **Metrics effects return ADT**: `MetricRecorded | MetricRecordingFailed`
- **Don't fail on metric errors**: Business logic proceeds even if metrics fail
- **Pattern match results**: Exhaustive handling of metric outcomes
- **Log failures**: Record metric errors for debugging

**Rationale**: Metrics are observability, not critical path. Metric failures shouldn't break features.

**See**: [Observability](observability.md) for complete metrics philosophy.

---

## Pattern 5: Exhaustive Pattern Matching

**Use Case**: Handle all possible result variants from effects.

```python
from effectful.domain import UserFound, UserNotFound

def handle_user_lookup(user_id: UUID) -> Generator[AllEffects, EffectResult, str]:
    """Demonstrate exhaustive pattern matching."""

    lookup_result = yield LookupUser(user_id=user_id)

    # Exhaustive match - all cases handled
    match lookup_result:
        case UserFound(user=user, source="database"):
            yield SendText(text=f"Found {user.name} in database")
            return "database_hit"

        case UserFound(user=user, source="cache"):
            yield SendText(text=f"Found {user.name} in cache")
            return "cache_hit"

        case UserNotFound(user_id=uid, reason="does_not_exist"):
            yield SendText(text=f"User {uid} does not exist")
            return "not_found"

        case UserNotFound(user_id=uid, reason="deleted"):
            yield SendText(text=f"User {uid} was deleted")
            return "deleted"

        case UserNotFound(user_id=uid, reason="access_denied"):
            yield SendText(text=f"Access denied for user {uid}")
            return "access_denied"
```

**Key Points**:
- **All cases handled**: MyPy enforces exhaustiveness
- **Nested pattern matching**: Extract fields from ADT variants
- **Type narrowing**: After match, type is narrowed to specific variant
- **Unreachable code detected**: MyPy warns if case is impossible

**Rationale**: Prevents forgotten error cases, ensures all paths handled.

**See**: [Type Safety](type-safety-enforcement.md) - Doctrine 5: Exhaustive Pattern Matching.

---

## Common Mistakes

### Mistake 1: Forgetting Type Narrowing

**❌ WRONG**:
```python
def greet_user(user_id: UUID) -> Generator[AllEffects, EffectResult, str]:
    user = yield GetUserById(user_id=user_id)
    # MyPy error: user might not be User, could be None or error type
    return f"Hello {user.name}!"
```

**✅ CORRECT**:
```python
def greet_user(user_id: UUID) -> Generator[AllEffects, EffectResult, str]:
    user = yield GetUserById(user_id=user_id)

    if not isinstance(user, User):
        return "User not found"

    # Type narrowed - user is definitely User
    return f"Hello {user.name}!"
```

### Mistake 2: Calling Infrastructure Directly

**❌ WRONG**:
```python
async def greet_user(user_id: UUID, db: UserRepository) -> str:
    user = await db.get_by_id(user_id)  # Forbidden!
    return f"Hello {user.name}!"
```

**✅ CORRECT**:
```python
def greet_user(user_id: UUID) -> Generator[AllEffects, EffectResult, str]:
    user = yield GetUserById(user_id=user_id)
    # ...
```

**See**: [Forbidden Patterns](forbidden_patterns.md) - Anti-Pattern 5.

### Mistake 3: Ignoring Effect Results

**❌ WRONG**:
```python
def save_message(user_id: UUID, text: str) -> Generator[AllEffects, EffectResult, None]:
    yield SaveChatMessage(user_id=user_id, text=text)
    # Ignored result! Don't know if save succeeded
```

**✅ CORRECT**:
```python
def save_message(user_id: UUID, text: str) -> Generator[AllEffects, EffectResult, bool]:
    result = yield SaveChatMessage(user_id=user_id, text=text)

    if not isinstance(result, ChatMessage):
        return False

    return True
```

## See Also

- [Purity](purity.md) - Six purity doctrines
- [Purity Patterns](purity_patterns.md) - Functional programming patterns
- [Type Safety](type-safety-enforcement.md) - Eight type safety doctrines
- [Forbidden Patterns](forbidden_patterns.md) - Anti-patterns to avoid
- [Observability](observability.md) - Metrics and monitoring

---

**Last Updated**: 2025-11-29
**Referenced by**: CLAUDE.md, purity.md, type-safety-enforcement.md
