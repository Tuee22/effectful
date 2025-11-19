# functional_effects Documentation

Welcome to the **functional_effects** documentation!

## Getting Started

New to functional_effects? Start here:

1. [Quickstart Guide](tutorials/01_quickstart.md) - Get running in 10 minutes
2. [Effect Types](tutorials/02_effect_types.md) - Learn about all available effects
3. [ADTs and Result Types](tutorials/03_adts_and_results.md) - Master type safety

## Documentation Structure

### Tutorials

Step-by-step guides for learning functional_effects:

**Getting Started**:
- **[01_quickstart.md](tutorials/01_quickstart.md)** - Your first effect program
- **[02_effect_types.md](tutorials/02_effect_types.md)** - WebSocket, Database, Cache effects
- **[03_adts_and_results.md](tutorials/03_adts_and_results.md)** - Type-safe error handling

**Advanced Topics**:
- **[04_testing_guide.md](tutorials/04_testing_guide.md)** - Comprehensive testing strategies
- **[05_production_deployment.md](tutorials/05_production_deployment.md)** - Deploy with Docker, PostgreSQL, Redis
- **[06_advanced_composition.md](tutorials/06_advanced_composition.md)** - Build complex workflows
- **[07_migration_guide.md](tutorials/07_migration_guide.md)** - Migrate from imperative code

### API Reference

Complete API documentation:

- **[API Overview](api/README.md)** - Quick reference and navigation
- **[effects.md](api/effects.md)** - All effect definitions
- **[result.md](api/result.md)** - Result type and utilities
- **[interpreters.md](api/interpreters.md)** - Interpreter interfaces and error types
- **[programs.md](api/programs.md)** - Program execution and composition
- **[testing.md](api/testing.md)** - Testing utilities and patterns

## Core Concepts

### Effects

Effects are **pure data** describing what should happen:

```python
from functional_effects import SendText, GetUserById

# Effects are frozen dataclasses
effect1 = SendText(text="Hello!")
effect2 = GetUserById(user_id=user_id)
```

### Programs

Programs are **generators** that yield effects:

```python
from collections.abc import Generator
from functional_effects import AllEffects, EffectResult

def my_program() -> Generator[AllEffects, EffectResult, str]:
    user_result = yield GetUserById(user_id=user_id)
    match user_result:
        case User(name=name):
            yield SendText(text=f"Hello {name}!")
            return "success"
        case _:
            return "not_found"
```

### Interpreters

Interpreters **execute** effects against infrastructure:

```python
from functional_effects import run_ws_program, create_composite_interpreter

# Production interpreter (real infrastructure)
interpreter = create_composite_interpreter(
    websocket_connection=real_websocket,
    user_repo=real_db_repo,
    message_repo=real_db_repo,
    cache=real_redis_cache,
)

# Test interpreter (fakes)
from functional_effects.testing import create_test_interpreter
test_interpreter = create_test_interpreter()

# Run program
result = await run_ws_program(my_program(), interpreter)
```

### Result Type

Explicit error handling instead of exceptions:

```python
from functional_effects.algebraic.result import Result, Ok, Err

# Functions return Result
def divide(a: int, b: int) -> Result[float, str]:
    if b == 0:
        return Err("Division by zero")
    return Ok(a / b)

# Callers handle both cases
match divide(10, 2):
    case Ok(value):
        print(f"Result: {value}")
    case Err(error):
        print(f"Error: {error}")
```

## Quick Links

- [GitHub Repository](https://github.com/your-org/functional_effects)
- [Issue Tracker](https://github.com/your-org/functional_effects/issues)
- [Contributing Guide](../CONTRIBUTING.md)
- [Architecture](../ARCHITECTURE.md)
- [Code Style](../functional_effects/CLAUDE.md)

## Examples

See the `examples/` directory for complete working programs:

- **hello_world.py** - Minimal effect program
- **user_greeting.py** - Database + WebSocket workflow
- **caching_workflow.py** - Cache + Database integration
- **error_handling.py** - Comprehensive error handling patterns

## Type Safety

functional_effects enforces **strict type safety**:

- Zero `Any` types
- Zero `cast()` calls
- Zero `# type: ignore` comments
- 100% `mypy --strict` compliance

See [CLAUDE.md](../functional_effects/CLAUDE.md) for type safety guidelines.

## Testing

All programs can be tested without real infrastructure:

```python
from functional_effects.testing import (
    create_test_interpreter,
    FakeUserRepository,
    assert_ok,
    unwrap_ok,
)

@pytest.mark.asyncio
async def test_my_program():
    # Setup fakes
    fake_repo = FakeUserRepository()
    fake_repo._users[user_id] = User(...)

    # Create test interpreter
    interpreter = create_test_interpreter(user_repo=fake_repo)

    # Run program
    result = await run_ws_program(my_program(), interpreter)

    # Assert
    value = unwrap_ok(result)
    assert value == "expected"
```

## Philosophy

> Make invalid states unrepresentable through the type system.

- **ADTs** over Optional types
- **Result** type over exceptions
- **Immutability** by default (frozen dataclasses)
- **Exhaustive matching** enforced by type checker
- **Explicit effects** instead of hidden side effects

## Support

- **Questions?** Open a [discussion](https://github.com/your-org/functional_effects/discussions)
- **Bug reports?** File an [issue](https://github.com/your-org/functional_effects/issues)
- **Contributing?** See [CONTRIBUTING.md](../CONTRIBUTING.md)

---

**Happy effect programming!**
