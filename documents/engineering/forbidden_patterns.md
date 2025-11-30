# Forbidden Patterns

> **SSoT** for all anti-patterns and prohibited constructs in effectful.

## Overview

This document catalogs **forbidden implementation patterns** that violate effectful's core principles. These patterns are automatically detected by:
- MyPy strict mode (type safety violations)
- Code review (architectural violations)
- Testing doctrine (test anti-patterns)

**Core Philosophy**: Make invalid states unrepresentable through the type system.

## Implementation Anti-Patterns

### 1. Using `Any` Types

**Impact**: Destroys type safety, allows runtime errors to slip through

**❌ WRONG** - Function parameters or return types with `Any`:
```python
from typing import Any

def process_data(data: Any) -> Any:  # Forbidden!
    return data
```

**✅ CORRECT** - Explicit types always:
```python
from effectful.domain import UserData, ProcessedData
from effectful.algebraic.result import Result

def process_data(data: UserData) -> Result[ProcessedData, ProcessingError]:
    return Ok(ProcessedData(...))
```

**Detection**: `mypy --strict` with `disallow_any_explicit = true` catches all `Any` usage.

**See**: [Type Safety](type-safety-enforcement.md) for complete doctrine.

---

### 2. Mutable Domain Models

**Impact**: Breaks immutability guarantee, enables race conditions and unexpected mutations

**❌ WRONG** - Dataclasses without `frozen=True`:
```python
from dataclasses import dataclass

@dataclass
class User:
    name: str
    email: str

# Mutation possible!
user.name = "Changed"  # No error
```

**✅ CORRECT** - All domain models immutable:
```python
from dataclasses import dataclass

@dataclass(frozen=True)
class User:
    name: str
    email: str

# Mutation prevented!
# user.name = "Changed"  # FrozenInstanceError
```

**Detection**: Code review, manual inspection.

**See**: [Type Safety](type-safety-enforcement.md) - Doctrine 4: Immutability by Default.

---

### 3. Optional for Domain Logic

**Impact**: Loses type information, forces None checks everywhere, unclear semantics

**❌ WRONG** - Returning `Optional[User]` from domain methods:
```python
from typing import Optional

def get_user(user_id: UUID) -> Optional[User]:
    # Why is it None? Not found? Deleted? Access denied?
    return None
```

**✅ CORRECT** - ADT types with explicit variants:
```python
from dataclasses import dataclass

@dataclass(frozen=True)
class UserFound:
    user: User

@dataclass(frozen=True)
class UserNotFound:
    user_id: UUID
    reason: str  # "does_not_exist" | "deleted" | "access_denied"

type UserLookupResult = UserFound | UserNotFound

def get_user(user_id: UUID) -> UserLookupResult:
    # Explicit failure reasons
    return UserNotFound(user_id=user_id, reason="does_not_exist")
```

**Detection**: Code review, pattern matching.

**See**: [Type Safety](type-safety-enforcement.md) - Doctrine 2: ADTs Over Optional Types.

---

### 4. Exceptions for Expected Errors

**Impact**: Hidden error paths, no type checking, forces try/except everywhere

**❌ WRONG** - Raising exceptions for expected failure cases:
```python
def divide(a: int, b: int) -> float:
    if b == 0:
        raise ValueError("Division by zero")  # Forbidden!
    return a / b

# Caller doesn't know this can fail from signature
result = divide(10, 0)  # Uncaught exception
```

**✅ CORRECT** - Result type for all fallible operations:
```python
from effectful.algebraic.result import Result, Ok, Err

def divide(a: int, b: int) -> Result[float, str]:
    if b == 0:
        return Err("Division by zero")
    return Ok(a / b)

# Caller must handle both cases
match divide(10, 0):
    case Ok(value):
        print(f"Result: {value}")
    case Err(error):
        print(f"Error: {error}")
```

**Detection**: MyPy catches unhandled Result types, code review.

**See**: [Type Safety](type-safety-enforcement.md) - Doctrine 3: Result Type for Error Handling.

---

### 5. Imperative Effect Execution

**Impact**: Breaks separation of concerns, makes testing difficult, couples business logic to infrastructure

**❌ WRONG** - Directly calling infrastructure in programs:
```python
async def greet_user(user_id: UUID, db: UserRepository) -> str:
    user = await db.get_by_id(user_id)  # Forbidden!
    return f"Hello {user.name}!"
```

**✅ CORRECT** - Yield effects, let interpreters execute:
```python
from collections.abc import Generator
from effectful import AllEffects, EffectResult, GetUserById

def greet_user(user_id: UUID) -> Generator[AllEffects, EffectResult, str]:
    user = yield GetUserById(user_id=user_id)

    if not isinstance(user, User):
        return "User not found"

    return f"Hello {user.name}!"
```

**Detection**: Code review, architectural review.

**See**: [Purity](purity.md) - Doctrine 3: Yield Don't Call.

---

### 6. Using Immutability Libraries in Adapters

**Impact**: Over-engineering, unnecessary dependencies, fights Python's design, degrades performance

**❌ WRONG** - Using immutability libraries (pyrsistent, immutables, etc.) in adapters:
```python
from dataclasses import dataclass, field
from pyrsistent import pmap, pvector
from pyrsistent.typing import PMap, PVector

@dataclass(frozen=True)
class InMemoryMetricsCollector:
    """BAD: Using pyrsistent in adapter."""
    counters: PMap[str, PMap[str, float]] = field(default_factory=pmap)
    histograms: PMap[str, PVector[float]] = field(default_factory=pmap)

    async def increment_counter(self, name: str, value: float) -> MetricResult:
        # Fighting frozen dataclass with object.__setattr__()
        new_counters = self.counters.set(name, value)
        object.__setattr__(self, 'counters', new_counters)  # Hack!
        return MetricRecorded(timestamp=time.time())
```

**✅ CORRECT** - Use frozen dataclass with native Python mutable fields:
```python
from dataclasses import dataclass, field

@dataclass(frozen=True)
class InMemoryMetricsCollector:
    """GOOD: frozen=True prevents field reassignment, allows field mutation."""
    _counters: dict[str, dict[str, float]] = field(default_factory=dict, init=False)
    _histograms: dict[str, list[float]] = field(default_factory=dict, init=False)

    async def increment_counter(self, name: str, value: float) -> MetricResult:
        # Direct mutation - no hacks needed
        if name not in self._counters:
            self._counters[name] = {}
        self._counters[name][label] = value
        return MetricRecorded(timestamp=time.time())
```

**Why This Pattern Works:**

1. **`frozen=True` prevents field reassignment**:
   ```python
   collector._counters = {}  # ❌ FrozenInstanceError
   ```

2. **But allows mutation of field contents**:
   ```python
   collector._counters[key] = value  # ✅ OK - mutating dict, not field
   ```

3. **Follows adapter purity doctrine**:
   - Adapters are at the I/O boundary (impure layer)
   - Managing mutable state is their responsibility
   - Using immutability libraries violates separation of concerns

**Benefits of Native Python Pattern:**
- ✅ Zero external dependencies
- ✅ Simpler code (no `object.__setattr__()` hacks)
- ✅ Better performance (no copy-on-write overhead)
- ✅ Lower memory usage
- ✅ Full MyPy type support
- ✅ Idiomatic Python

**When Immutability Is Required:**
- Domain models (always use `frozen=True`)
- Effect definitions (always use `frozen=True`)
- Result types (always use `frozen=True`)
- **NOT in adapters** - they manage state at I/O boundary

**Detection**: Code review, dependency audit, architectural review.

**See**:
- [Purity](purity.md) - Doctrine 4: Interpreters Isolate Impurity
- [Architecture](architecture.md) - Layer boundaries
- `effectful/adapters/prometheus_metrics.py` - Reference implementation

---

## Test Anti-Patterns

**Complete list of 22 test anti-patterns** documented in [Testing](testing.md).

**Key anti-patterns to avoid:**
1. Tests that pass when features are broken
2. Using `pytest.skip()` (NEVER allowed)
3. Testing with real infrastructure in unit tests
4. Not testing error paths
5. Incomplete assertions
6. Docker bind mount permission issues

**Core Principle**: Tests exist to find problems, not provide false confidence.

**See**: [Testing](testing.md) for complete catalog with examples.

---

## Docker Anti-Patterns

**Complete Docker policy** documented in [Docker Workflow](docker_workflow.md).

**Key forbidden patterns:**
- ❌ Running pytest locally (no infrastructure access)
- ❌ Running poetry locally (`poetry.toml` prevents virtualenv creation)
- ❌ Bind mounts for PostgreSQL (permission conflicts on macOS)
- ❌ Manual pip/pipx usage (bypasses dependency management)

**Required pattern**: All commands via Docker prefix.

**See**: [Docker Workflow](docker_workflow.md) for complete policy.

---

## Detection Strategies

### Automated Detection

**MyPy strict mode** catches:
- Any types (`disallow_any_explicit = true`)
- Missing type annotations
- Unhandled union cases
- Type narrowing violations

**pytest** catches:
- Missing tests (coverage < 45%)
- Skipped tests (forbidden)
- Test failures

**Black** catches:
- Formatting inconsistencies

### Manual Detection

**Code review** catches:
- Mutable domain models (missing `frozen=True`)
- Optional instead of ADTs
- Exceptions instead of Result
- Imperative effect execution
- Architectural violations

### Remediation

**When anti-pattern detected**:
1. Stop immediately
2. Identify which doctrine is violated
3. Consult relevant SSoT document (Type Safety, Purity, Testing, Docker Workflow)
4. Refactor to correct pattern
5. Add test to prevent regression

## See Also

- [Type Safety](type-safety-enforcement.md) - Eight type safety doctrines
- [Purity](purity.md) - Six purity doctrines
- [Purity Patterns](purity_patterns.md) - Functional programming patterns
- [Testing](testing.md) - 22 test anti-patterns
- [Docker Workflow](docker_workflow.md) - Docker development policy

---

**Last Updated**: 2025-11-30
**Referenced by**: CLAUDE.md, type-safety-enforcement.md, purity.md, testing.md
