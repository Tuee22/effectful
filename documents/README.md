# effectful Documentation

Welcome to the **effectful** documentation!

## Prerequisites

All development happens inside Docker containers. See [Docker Workflow](engineering/docker_workflow.md).

**Multiple stacks**: The base library runs in the `effectful` service defined in `docker/docker-compose.yml`. Demo apps (e.g., HealthHub) ship their own compose files and service names under `demo/**/docker/`; use the correct compose file and service when running Poetry commands.

**CRITICAL**: Poetry is configured to NOT create virtual environments (`poetry.toml`). Do NOT run `poetry install` locally.

```bash
# Start development environment
docker compose -f docker/docker-compose.yml up -d

# Run tests
docker compose -f docker/docker-compose.yml exec effectful poetry run pytest

# Type check
docker compose -f docker/docker-compose.yml exec effectful poetry run check-code
```

## Getting Started

New to effectful? Start here:

1. [Quickstart Guide](tutorials/01_quickstart.md) - Get running in 10 minutes
2. [Effect Types](tutorials/02_effect_types.md) - Learn about all available effects
3. [ADTs and Result Types](tutorials/03_adts_and_results.md) - Master type safety

## Documentation Structure

### Engineering Standards (SSoT)

Project engineering practices and standards:

- **[Code Quality](engineering/code_quality.md)** - Type safety + purity doctrines, anti-pattern routing (SSoT)
- **[Architecture](engineering/architecture.md)** - 5-layer architecture, design decisions (SSoT)
- **[Docker Workflow](engineering/docker_workflow.md)** - All development in Docker (SSoT)
- **[Testing](engineering/testing.md)** - Coverage requirements, 22 test anti-patterns (SSoT)
- **[Effect Patterns](engineering/effect_patterns.md)** - Functional composition patterns (SSoT)
- **[Command Reference](engineering/command_reference.md)** - All Docker commands and test execution
- **[Development Workflow](engineering/development_workflow.md)** - Daily development loop
- **[Configuration](engineering/configuration.md)** - Environment variables for all services
- **[Documentation Guidelines](documentation_standards.md)** - SSoT/DRY principles, mermaid best practices (SSoT)

**Observability**:
- **[Observability](engineering/observability.md)** - Metrics philosophy and cardinality management (SSoT)
- **[Monitoring & Alerting](engineering/monitoring_and_alerting.md)** - Naming conventions, label standards, severity levels, and runbook requirements (SSoT)

### Tutorials

Step-by-step guides for learning effectful:

**Getting Started**:
- **[01_quickstart.md](tutorials/01_quickstart.md)** - Your first effect program
- **[02_effect_types.md](tutorials/02_effect_types.md)** - WebSocket, Database, Cache effects
- **[03_adts_and_results.md](tutorials/03_adts_and_results.md)** - Type-safe error handling

**Advanced Topics**:
- **[04_testing_guide.md](tutorials/04_testing_guide.md)** - Comprehensive testing strategies
- **[05_production_deployment.md](tutorials/05_production_deployment.md)** - Deploy with Docker, PostgreSQL, Redis
- **[06_advanced_composition.md](tutorials/06_advanced_composition.md)** - Build complex workflows
- **[07_migration_guide.md](tutorials/07_migration_guide.md)** - Migrate from imperative code

**Effect-Specific Guides**:
- **[08_messaging_effects.md](tutorials/08_messaging_effects.md)** - Pub/sub with Apache Pulsar
- **[09_storage_effects.md](tutorials/09_storage_effects.md)** - S3-compatible object storage
- **[10_auth_effects.md](tutorials/10_auth_effects.md)** - JWT authentication and passwords

**Observability**:
- **[11_metrics_quickstart.md](tutorials/11_metrics_quickstart.md)** - Get started with metrics in 15 minutes
- **[12_metric_types_guide.md](tutorials/12_metric_types_guide.md)** - Choose the right metric type
- **[13_prometheus_setup.md](tutorials/13_prometheus_setup.md)** - Docker integration with Prometheus/Grafana
- **[14_alert_rules.md](tutorials/14_alert_rules.md)** - Write actionable Prometheus alerts
- **[15_grafana_dashboards.md](tutorials/15_grafana_dashboards.md)** - Build beautiful dashboards

### API Reference

Complete API documentation:

- **[API Overview](api/README.md)** - Quick reference and navigation
- **[effects.md](api/effects.md)** - WebSocket, Database, Cache effects
- **[auth.md](api/auth.md)** - JWT authentication effects
- **[messaging.md](api/messaging.md)** - Pub/sub messaging effects
- **[storage.md](api/storage.md)** - S3 object storage effects
- **[metrics.md](api/metrics.md)** - Prometheus metrics effects (Counter, Gauge, Histogram, Summary)
- **[result.md](api/result.md)** - Result type and utilities
- **[interpreters.md](api/interpreters.md)** - Interpreter interfaces and error types
- **[programs.md](api/programs.md)** - Program execution and composition

## Core Concepts

### Effects

Effects are **pure data** describing what should happen:

```python
from effectful import SendText, GetUserById

# Effects are frozen dataclasses
effect1 = SendText(text="Hello!")
effect2 = GetUserById(user_id=user_id)
```

### Programs

Programs are **generators** that yield effects:

```python
from collections.abc import Generator
from effectful import AllEffects, EffectResult

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
from effectful import run_ws_program, create_composite_interpreter

# Production interpreter (real infrastructure)
interpreter = create_composite_interpreter(
    websocket_connection=real_websocket,
    user_repo=real_db_repo,
    message_repo=real_db_repo,
    cache=real_redis_cache,
)

# Test interpreter (typed mocks)
from unittest.mock import AsyncMock
from effectful.infrastructure.websocket import WebSocketConnection
from effectful.infrastructure.repositories import UserRepository, ChatMessageRepository
from effectful.infrastructure.cache import ProfileCache

test_interpreter = create_composite_interpreter(
    websocket_connection=AsyncMock(spec=WebSocketConnection),
    user_repo=AsyncMock(spec=UserRepository),
    message_repo=AsyncMock(spec=ChatMessageRepository),
    cache=AsyncMock(spec=ProfileCache),
)

# Run program
result = await run_ws_program(my_program(), interpreter)
```

### Result Type

Explicit error handling instead of exceptions:

```python
from effectful.algebraic.result import Result, Ok, Err

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

- [GitHub Repository](https://github.com/your-org/effectful)
- [Issue Tracker](https://github.com/your-org/effectful/issues)
- [Engineering Standards](engineering/README.md)
- [Docker Workflow](engineering/docker_workflow.md)
- [Architecture](engineering/architecture.md)
- [Testing](engineering/testing.md)
- [Code Quality](engineering/code_quality.md)

## Examples

See the `examples/` directory for complete working programs:

- **01_hello_world.py** - Minimal effect program
- **02_user_greeting.py** - Database + WebSocket workflow
- **03_caching_workflow.py** - Cache + Database integration
- **04_error_handling.py** - Comprehensive error handling patterns
- **05_messaging_workflow.py** - Pub/sub messaging with Apache Pulsar

## Code Quality

effectful enforces **strict type safety and purity**:

- Zero `Any`, `cast()`, or `# type: ignore`
- ADTs over Optional; Result for all fallible operations
- Programs are pure generators (`yield` effects) and return immutable data
- Frozen dataclasses and exhaustive pattern matching

See [Code Quality](engineering/code_quality.md) for detailed doctrines and anti-pattern routing.

## Testing

All programs can be tested without real infrastructure:

```python
from unittest.mock import AsyncMock
from effectful.infrastructure.cache import ProfileCache
from effectful.infrastructure.repositories import UserRepository, ChatMessageRepository
from effectful.infrastructure.websocket import WebSocketConnection
from effectful.interpreters.composite import create_composite_interpreter
from effectful.testing import assert_ok, unwrap_ok

@pytest.mark.asyncio
async def test_my_program() -> None:
    mock_ws = AsyncMock(spec=WebSocketConnection)
    mock_ws.is_open.return_value = True
    mock_user_repo = AsyncMock(spec=UserRepository)
    mock_msg_repo = AsyncMock(spec=ChatMessageRepository)
    mock_cache = AsyncMock(spec=ProfileCache)

    interpreter = create_composite_interpreter(
        websocket_connection=mock_ws,
        user_repo=mock_user_repo,
        message_repo=mock_msg_repo,
        cache=mock_cache,
    )

    result = await run_ws_program(my_program(), interpreter)

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

- **Questions?** Open a [discussion](https://github.com/your-org/effectful/discussions)
- **Bug reports?** File an [issue](https://github.com/your-org/effectful/issues)
- **Contributing?** See [Contributing Guide](CONTRIBUTING.md) and [Engineering Standards](engineering/README.md)

---

**Happy effect programming!**

**Last Updated**: 2025-12-01  
**Supersedes**: none  
**Referenced by**: README.md, CONTRIBUTING.md, demo/healthhub/documents/README.md
