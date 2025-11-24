# Contributing to effectful

Thank you for considering contributing to **effectful**! This guide will help you understand our development workflow, code standards, and testing practices.

## Table of Contents

- [Development Setup](#development-setup)
- [Code Standards](#code-standards)
- [Testing Requirements](#testing-requirements)
- [Pull Request Process](#pull-request-process)
- [Architecture Guidelines](#architecture-guidelines)
- [Common Tasks](#common-tasks)

## Development Setup

### Prerequisites

- Docker and Docker Compose
- Git

### Initial Setup

```bash
# Clone repository
git clone https://github.com/your-org/effectful.git
cd effectful

# Start Docker services
docker compose -f docker/docker-compose.yml up -d

# Verify setup - run tests
docker compose -f docker/docker-compose.yml exec effectful poetry run pytest

# Verify setup - type check
docker compose -f docker/docker-compose.yml exec effectful poetry run mypy effectful
```

**Note**: All development happens inside Docker containers. Poetry is NOT set up as a local virtual environment.

### Development Environment

All commands run inside Docker:

```bash
# Run tests
docker compose -f docker/docker-compose.yml exec effectful poetry run pytest

# Type check
docker compose -f docker/docker-compose.yml exec effectful poetry run mypy effectful

# Format code
docker compose -f docker/docker-compose.yml exec effectful poetry run black effectful tests

# Lint
docker compose -f docker/docker-compose.yml exec effectful poetry run ruff check effectful tests

# Check code quality (Black + MyPy)
docker compose -f docker/docker-compose.yml exec effectful poetry run check-code

# Run all tests
docker compose -f docker/docker-compose.yml exec effectful poetry run test-all
```

## Core Doctrines

Before contributing, familiarize yourself with the project's core doctrines:

- **Testing Doctrine**: `documents/core/testing_doctrine.md` - Coverage requirements, test anti-patterns
- **Type Safety Doctrine**: `documents/core/type_safety_doctrine.md` - Eight type safety rules
- **Architecture**: `documents/core/architecture.md` - 5-layer architecture, design decisions

## Code Standards

### Type Safety - Zero Tolerance

**CRITICAL**: This project maintains `mypy --strict` with zero errors. All code must pass strict type checking.

For complete type safety patterns and examples, see `documents/core/type_safety_doctrine.md`.

**Key Points:**
- Type checking is mandatory before tests can run
- Zero tolerance for escape hatches (Any, cast, type: ignore)
- All type errors must be fixed, never suppressed
- MyPy acts as a gate, not a suggestion tool

#### Forbidden Constructs

```python
# ❌ NEVER use Any
from typing import Any

def process(data: Any) -> Any:  # FORBIDDEN
    return data

# ❌ NEVER use cast
from typing import cast

result = cast(User, some_value)  # FORBIDDEN

# ❌ NEVER use type: ignore
def broken_function():  # type: ignore  # FORBIDDEN
    ...
```

#### Required Patterns

```python
# ✅ Always use explicit types
from uuid import UUID
from effectful.algebraic.result import Result, Ok, Err

def process(user_id: UUID) -> Result[User, str]:
    if not isinstance(user_id, UUID):
        return Err("Invalid UUID")
    return Ok(User(id=user_id, email="test@example.com", name="Test"))

# ✅ Use generics with parameters
from collections.abc import Generator

def transform(items: list[str]) -> dict[str, int]:  # Not list or dict
    return {item: len(item) for item in items}

# ✅ Use frozen dataclasses
from dataclasses import dataclass

@dataclass(frozen=True)  # Always frozen
class User:
    id: UUID
    email: str
    name: str
```

### ADTs Over Optional

```python
# ❌ WRONG - Optional hides the reason
from typing import Optional

async def get_user(user_id: UUID) -> Optional[User]:
    ...

# ✅ CORRECT - ADT makes all cases explicit
from dataclasses import dataclass

@dataclass(frozen=True)
class UserFound:
    user: User
    source: str

@dataclass(frozen=True)
class UserNotFound:
    user_id: UUID
    reason: str

type UserLookupResult = UserFound | UserNotFound

async def get_user(user_id: UUID) -> UserLookupResult:
    ...
```

### Result Type for Errors

```python
# ❌ WRONG - Exceptions invisible in signature
async def save_data(data: str) -> bool:
    await db.save(data)  # Raises what exceptions?
    return True

# ✅ CORRECT - Errors explicit in signature
from effectful.algebraic.result import Result, Ok, Err

async def save_data(data: str) -> Result[bool, DatabaseError]:
    try:
        await db.save(data)
        return Ok(True)
    except Exception as e:
        return Err(DatabaseError(effect=..., db_error=str(e), is_retryable=True))
```

### Immutability

All dataclasses must be `frozen=True`:

```python
# ❌ WRONG
@dataclass
class User:
    name: str

# ✅ CORRECT
@dataclass(frozen=True)
class User:
    name: str
```

### Code Formatting

```bash
# Format code before committing
docker compose -f docker/docker-compose.yml exec effectful poetry run black effectful tests

# Check formatting
docker compose -f docker/docker-compose.yml exec effectful poetry run black --check effectful tests

# Lint
docker compose -f docker/docker-compose.yml exec effectful poetry run ruff check effectful tests
```

**Configuration**: See `pyproject.toml` for Black/Ruff settings.

## Testing Requirements

For complete testing doctrine including 21 anti-patterns, see `documents/core/testing_doctrine.md`.

### Coverage Doctrine

- **Unit tests**: Minimum 45% overall coverage (adapters/infrastructure excluded)
- **Integration tests**: Conceptual feature coverage (not metric-driven)

```bash
# Run tests with coverage
docker compose -f docker/docker-compose.yml exec effectful poetry run pytest --cov=effectful --cov-report=term-missing

# Coverage will show ~69% overall (adapters excluded from measurement)
```

### Test Strategy Pyramid

The following diagram shows our testing approach organized by type:

```mermaid
flowchart TB
    E2E[E2E Tests<br/>Real Infrastructure<br/>Full Integration<br/>Smoke Tests Only]
    Integration[Integration Tests<br/>Real DB and Redis<br/>Mocked WebSocket<br/>Multi-Effect Workflows]
    Unit[Unit Tests<br/>pytest-mock<br/>No I/O<br/>Fastest - Most Coverage]

    E2E --> Integration
    Integration --> Unit
```

**Test Distribution:**
- **Many** Unit tests (pytest-mock only, no I/O, fastest execution)
- **Some** Integration tests (real DB/Redis, mocked WebSocket)
- **Few** E2E tests (real infrastructure, smoke tests only)

**Philosophy**: Push testing down to the unit level. Most bugs should be caught by fast unit tests with pytest-mock, not slow integration tests with real infrastructure.

### Test Organization

```
tests/
├── test_algebraic/          # Result, EffectReturn
├── test_domain/             # User, ChatMessage, ProfileData
├── test_effects/            # Effect definitions
├── test_interpreters/       # WebSocket, Database, Cache interpreters
├── test_programs/           # run_ws_program
├── test_integration/        # Multi-effect workflows
└── test_testing/            # Testing utilities (matchers)
```

### Testing Antipatterns - Forbidden

#### 1. Using pytest.skip()

```python
# ❌ FORBIDDEN
@pytest.mark.skip(reason="TODO: Implement later")
def test_feature():
    pass

# ✅ CORRECT - Either implement or delete
def test_feature():
    # Full implementation
    ...
```

**Rationale**: Skipped tests hide gaps in coverage and rot.

#### 2. Testing with Real Infrastructure

```python
# ❌ WRONG - Real database in unit tests
@pytest.mark.asyncio
async def test_user_lookup():
    async with asyncpg.connect(DATABASE_URL) as conn:
        ...

# ✅ CORRECT - Use pytest-mock
@pytest.mark.asyncio
async def test_user_lookup(mocker):
    mock_repo = mocker.AsyncMock(spec=UserRepository)
    mock_repo.get_by_id.return_value = User(
        id=user_id, email="test@example.com", name="Alice"
    )
    ...
```

**Rationale**: Tests must be fast, deterministic, isolated.

#### 3. Incomplete Assertions

```python
# ❌ WRONG - Only checking success
result = await run_ws_program(program(), interpreter)
assert_ok(result)

# ✅ CORRECT - Verify side effects and mock calls
result = await run_ws_program(program(), interpreter)
value = unwrap_ok(result)

assert value == "expected"
mock_websocket.send_text.assert_called_with("Hello")
mock_message_repo.save.assert_called_once()
```

**Rationale**: Programs have effects beyond return values.

#### 4. Not Testing Error Paths

```python
# ❌ WRONG - Only happy path
@pytest.mark.asyncio
async def test_user_lookup():
    result = await run_ws_program(program(), interpreter)
    assert_ok(result)

# ✅ CORRECT - Test error cases with pytest-mock
from effectful.interpreters.errors import DatabaseError

@pytest.mark.asyncio
async def test_user_lookup_database_failure(mocker):
    mock_repo = mocker.AsyncMock(spec=UserRepository)
    mock_repo.get_by_id.side_effect = Exception("Connection timeout")

    # ... setup interpreter with mock_repo ...

    result = await run_ws_program(program(), interpreter)

    assert_err(result)
    error = unwrap_err(result)
    assert isinstance(error, DatabaseError)
    assert "Connection timeout" in error.db_error
```

**Rationale**: Error handling is half your code. Test it.

### Testing Utilities

Use the `effectful.testing` module for matchers:

```python
from effectful.testing import (
    # Matchers
    assert_ok,
    assert_err,
    unwrap_ok,
    unwrap_err,
    assert_ok_value,
    assert_err_message,
)

@pytest.mark.asyncio
async def test_my_program(mocker):
    # Setup mocks with pytest-mock
    mock_repo = mocker.AsyncMock(spec=UserRepository)
    mock_repo.get_by_id.return_value = User(...)

    # Create interpreter with mocks
    interpreter = CompositeInterpreter(
        websocket=mocker.AsyncMock(spec=WebSocketConnection),
        user_repo=mock_repo,
        # ... other dependencies
    )

    # Test
    result = await run_ws_program(my_program(), interpreter)

    # Assert
    value = unwrap_ok(result)
    assert value == "expected"
```

## Pull Request Process

### Before Submitting

1. **Run full test suite**:
   ```bash
   docker compose -f docker/docker-compose.yml exec effectful poetry run pytest --cov=effectful --cov-report=term-missing
   ```
   Must show minimum 45% coverage, zero failures.

2. **Type check**:
   ```bash
   docker compose -f docker/docker-compose.yml exec effectful poetry run mypy effectful
   ```
   Must show zero errors.

3. **Format code**:
   ```bash
   docker compose -f docker/docker-compose.yml exec effectful poetry run black effectful tests
   docker compose -f docker/docker-compose.yml exec effectful poetry run ruff check effectful tests
   ```

4. **Update documentation** if adding features:
   - Docstrings on all public functions
   - Examples in docstrings
   - Update README.md if needed

### PR Checklist

- [ ] All tests pass (minimum 45% coverage)
- [ ] Zero mypy errors (`mypy --strict`)
- [ ] Code formatted (Black + Ruff)
- [ ] No forbidden constructs (Any, cast, type: ignore)
- [ ] All dataclasses are frozen
- [ ] ADTs used instead of Optional
- [ ] Result type used for errors
- [ ] Error paths tested
- [ ] Docstrings on public APIs
- [ ] Examples in docstrings
- [ ] CHANGELOG.md updated

### PR Template

```markdown
## Description

Brief description of changes.

## Type of Change

- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing

- [ ] All tests pass (minimum 45% coverage)
- [ ] Zero mypy errors
- [ ] Error paths tested

## Checklist

- [ ] Code formatted (Black + Ruff)
- [ ] No Any/cast/type: ignore
- [ ] All dataclasses frozen
- [ ] Docstrings added
- [ ] CHANGELOG.md updated
```

## Architecture Guidelines

### Adding New Effects

1. **Define effect** (frozen dataclass):
   ```python
   # effectful/effects/new_category.py
   from dataclasses import dataclass

   @dataclass(frozen=True)
   class NewEffect:
       """Description of what this effect does."""
       param: str
   ```

2. **Add to effect union**:
   ```python
   # effectful/programs/types.py
   type NewCategoryEffect = NewEffect | OtherNewEffect
   type AllEffects = WebSocketEffect | DatabaseEffect | CacheEffect | NewCategoryEffect
   ```

3. **Create interpreter**:
   ```python
   # effectful/interpreters/new_category.py
   from effectful.algebraic.result import Result, Ok, Err

   class NewCategoryInterpreter:
       async def interpret(self, effect: NewCategoryEffect) -> Result[EffectReturn, InterpreterError]:
           match effect:
               case NewEffect(param=param):
                   # Execute effect
                   return Ok(EffectReturn(value=result, effect_name="NewEffect"))
   ```

4. **Add to composite interpreter**:
   ```python
   # effectful/interpreters/composite.py
   async def interpret(self, effect: AllEffects) -> Result[EffectReturn, InterpreterError]:
       match effect:
           case NewEffect() | OtherNewEffect():
               return await self._new_category.interpret(effect)
   ```

5. **Create test fake**:
   ```python
   # effectful/testing/fakes.py
   @dataclass
   class FakeNewCategoryService:
       _state: dict[str, str] = field(default_factory=dict)

       async def execute(self, param: str) -> Result[str, str]:
           # Fake implementation
           ...
   ```

6. **Write tests**:
   ```python
   # tests/test_effects/test_new_category.py
   from pytest_mock import MockerFixture

   @pytest.mark.asyncio
   async def test_new_effect(mocker: MockerFixture):
       # Create interpreter with pytest-mock
       mock_infra = mocker.AsyncMock(spec=YourProtocol)
       interpreter = YourInterpreter(infrastructure=mock_infra)
       # Test program using NewEffect
       ...
   ```

### Adding New Domain Models

1. **Define ADT variants**:
   ```python
   # effectful/domain/new_model.py
   from dataclasses import dataclass

   @dataclass(frozen=True)
   class NewModelFound:
       model: NewModel
       source: str

   @dataclass(frozen=True)
   class NewModelNotFound:
       model_id: UUID
       reason: str

   type NewModelLookupResult = NewModelFound | NewModelNotFound
   ```

2. **Export from root**:
   ```python
   # effectful/__init__.py
   from effectful.domain.new_model import (
       NewModel,
       NewModelFound,
       NewModelNotFound,
       NewModelLookupResult,
   )
   ```

3. **Write tests**:
   ```python
   # tests/test_domain/test_new_model.py
   def test_new_model_construction():
       model = NewModel(id=uuid4(), name="Test")
       assert model.name == "Test"
   ```

## Common Tasks

All commands run inside Docker containers.

### Running Tests

```bash
# All tests
docker compose -f docker/docker-compose.yml exec effectful poetry run pytest

# Specific file
docker compose -f docker/docker-compose.yml exec effectful poetry run pytest tests/test_programs/test_runners.py

# Specific test
docker compose -f docker/docker-compose.yml exec effectful poetry run pytest tests/test_programs/test_runners.py::TestRunWSProgram::test_immediate_return

# With coverage
docker compose -f docker/docker-compose.yml exec effectful poetry run pytest --cov=effectful --cov-report=term-missing

# Verbose
docker compose -f docker/docker-compose.yml exec effectful poetry run pytest -v
```

### Type Checking

```bash
# Check entire project
docker compose -f docker/docker-compose.yml exec effectful poetry run mypy effectful

# Check specific file
docker compose -f docker/docker-compose.yml exec effectful poetry run mypy effectful/programs/runners.py

# Strict mode (required)
docker compose -f docker/docker-compose.yml exec effectful poetry run mypy --strict effectful
```

### Code Formatting

```bash
# Format all code
docker compose -f docker/docker-compose.yml exec effectful poetry run black effectful tests

# Check formatting (CI)
docker compose -f docker/docker-compose.yml exec effectful poetry run black --check effectful tests

# Lint
docker compose -f docker/docker-compose.yml exec effectful poetry run ruff check effectful tests

# Auto-fix lint issues
docker compose -f docker/docker-compose.yml exec effectful poetry run ruff check --fix effectful tests
```

### Release Process

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Run full test suite: `docker compose -f docker/docker-compose.yml exec effectful poetry run pytest --cov=effectful`
4. Type check: `docker compose -f docker/docker-compose.yml exec effectful poetry run mypy --strict effectful`
5. Format: `docker compose -f docker/docker-compose.yml exec effectful poetry run black effectful tests`
6. Commit: `git commit -m "Release v0.2.0"`
7. Tag: `git tag v0.2.0`
8. Push: `git push && git push --tags`
9. Build: `docker compose -f docker/docker-compose.yml exec effectful poetry build`
10. Publish: `docker compose -f docker/docker-compose.yml exec effectful poetry publish`

## Git Workflow

### For Claude Code Users

**Critical Rule**: Claude Code is NOT authorized to commit or push changes.

**Forbidden Git Operations:**
- NEVER run `git commit` (including `--amend`, `--no-verify`, etc.)
- NEVER run `git push` (including `--force`, `--force-with-lease`, etc.)
- NEVER run `git add` followed by commit operations
- NEVER create commits under any circumstances

**Required Workflow:**
1. Make all code changes as requested
2. Run tests and validation
3. Leave ALL changes as uncommitted working directory changes
4. User reviews changes using `git status` and `git diff`
5. User manually commits and pushes when satisfied

**Rationale**: All changes must be human-reviewed before entering version control.

## Getting Help

- **Documentation**: See `documents/` directory
- **Examples**: See `examples/` directory
- **Core Doctrines**: See `documents/core/` directory
- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions

## Code of Conduct

### Standards

- Be respectful and inclusive
- Provide constructive feedback
- Focus on what is best for the project
- Show empathy towards others

### Unacceptable Behavior

- Harassment or discrimination
- Trolling or insulting comments
- Publishing others' private information
- Other conduct inappropriate in a professional setting

---

**Remember**: If `mypy --strict` passes with zero errors and pytest shows minimum 45% coverage, your code is ready for review. Type safety is not optional.
