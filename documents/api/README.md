# API Reference

Complete API documentation for the effectful package.

## Overview

The effectful package provides a type-safe, testable effect system for Python using algebraic data types (ADTs) and the Result type pattern.

**Core Concepts**:
- **Effects**: Declarative descriptions of side effects (I/O operations)
- **Programs**: Python generators that yield effects and return values
- **Interpreters**: Execute effects by implementing actual side effects
- **Result Type**: Explicit error handling with `Result[T, E]`

---

## API Documentation

### [Effects API](./effects.md)

Effect types for WebSocket, database, and cache operations.

**Topics Covered**:
- WebSocket Effects (`SendText`, `ReceiveText`, `Close`)
- Database Effects (`GetUserById`, `SaveChatMessage`)
- Cache Effects (`GetCachedProfile`, `PutCachedProfile`)
- Effect composition patterns
- Type signatures and usage examples

**Start Here If**: You need to understand what effects are available and how to use them in programs.

---

### [Result Type API](./result.md)

The `Result[T, E]` type for explicit error handling.

**Topics Covered**:
- `Ok[T]` and `Err[E]` variants
- Pattern matching with `match` statements
- Methods (`map`, `flat_map`, `unwrap`, `unwrap_or`, etc.)
- `EffectReturn[T]` wrapper for interpreter results
- Common patterns (railway-oriented programming, chaining, error recovery)

**Start Here If**: You need to handle errors explicitly or chain operations that can fail.

---

### [Interpreters API](./interpreters.md)

Interpreter types, error types, and production configuration.

**Topics Covered**:
- `create_composite_interpreter` factory function
- Individual interpreters (`WebSocketInterpreter`, `DatabaseInterpreter`, `CacheInterpreter`)
- Error types (`DatabaseError`, `WebSocketClosedError`, `CacheError`, `UnhandledEffectError`)
- Infrastructure protocols (`WebSocketConnection`, `UserRepository`, `ChatMessageRepository`, `ProfileCache`)
- Custom interpreter patterns
- Production configuration (connection pooling, error monitoring, timeouts)

**Start Here If**: You need to execute programs, configure interpreters, or handle interpreter errors.

---

### [Programs API](./programs.md)

Program execution, types, and composition patterns.

**Topics Covered**:
- `run_ws_program` function for executing programs
- Program types (`AllEffects`, `EffectResult`, `WSProgram`)
- Execution behavior (sequential effects, fail-fast error propagation)
- Type narrowing with pattern matching and assertions
- Composition patterns (`yield from`, reusable components, recursive programs)
- Advanced patterns (cache-aside, request-response, multi-step workflows)
- Performance considerations

**Start Here If**: You need to write programs, compose programs, or understand program execution.

---

### [Testing Standards](../engineering/testing.md)

Testing utilities, matchers, and strategies.

**Topics Covered**:
- Test matchers (`assert_ok`, `assert_err`, `unwrap_ok`, `unwrap_err`)
- pytest-mock patterns with `spec=` for type safety
- Testing strategies (success paths, error paths, sequential returns, stateful behavior, composition)
- Test organization with fixtures
- Best practices for testing programs and interpreters

**Start Here If**: You need to write tests for programs or understand testing patterns.

---

## Quick Reference

### Importing Core Types

```python
from effectful import (
    # Result type
    Result,
    Ok,
    Err,

    # Program execution
    run_ws_program,
    create_composite_interpreter,

    # Effect types
    AllEffects,
    EffectResult,
    SendText,
    ReceiveText,
    Close,
    GetUserById,
    SaveChatMessage,
    GetCachedProfile,
    PutCachedProfile,

    # Domain models
    User,
    ChatMessage,
    ProfileData,

    # Error types
    InterpreterError,
    DatabaseError,
    WebSocketClosedError,
    CacheError,
)
```

### Basic Program Pattern

```python
from collections.abc import Generator
from effectful import AllEffects, EffectResult, SendText
from uuid import UUID


def my_program(user_id: UUID) -> Generator[AllEffects, EffectResult, str]:
    """Basic program structure."""
    # Yield effects
    yield SendText(text="Hello")

    # Return final value
    return "success"
```

### Running Programs

```python
from effectful import run_ws_program, create_composite_interpreter

# Create interpreter
interpreter = create_composite_interpreter(
    websocket_connection=ws_conn,
    user_repo=user_repo,
    message_repo=message_repo,
    cache=cache,
)

# Run program
result = await run_ws_program(my_program(user_id), interpreter)

# Handle result
match result:
    case Ok(value):
        print(f"Success: {value}")
    case Err(error):
        print(f"Failed: {error}")
```

---

## Type Safety

All API documentation follows strict type safety guidelines:

- ❌ **NO** `Any`, `cast()`, or `# type: ignore`
- ✅ Inline type hints on all functions
- ✅ Generics with parameters: `dict[str, str]` not `dict`
- ✅ MyPy strict mode compatible

**Example**:

```python
# ✅ CORRECT: Type-safe program
def process(user_id: UUID) -> Generator[AllEffects, EffectResult, str]:
    user = yield GetUserById(user_id=user_id)

    match user:
        case User(name=name):
            # Type checker knows this is User
            return f"Hello {name}"
        case None:
            # Type checker knows this is None
            return "not_found"

# ❌ WRONG: Untyped program
def process(user_id):  # Missing type hints
    user = yield GetUserById(user_id=user_id)
    return user.name  # Unsafe - could be None!
```

---

## See Also

- [Tutorials](../tutorials/) - Step-by-step guides for learning effectful
- [Examples](/examples/) - Real-world example programs
- [Architecture](../engineering/architecture.md) - Design principles and architecture overview
- [Docker Workflow](../engineering/docker_workflow.md) - Development workflow (SSoT)
- [CLAUDE.md](/CLAUDE.md) - Complete development reference

---

**Last Updated**: 2025-12-01  
**Supersedes**: none  
**Referenced by**: documents/README.md
