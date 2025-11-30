# Purity Patterns

This document provides implementation patterns for writing pure functional code in Python. Since Python lacks tail-call optimization (TCO), we use the **trampoline pattern** to avoid stack overflows in recursive algorithms.

---

## Core Philosophy

**Pure functions use expressions, not control-flow statements. No `for`, `if`, or `while`.**

Pure functional code in effectful:
- **Forbids control-flow statements**: No `for`, `if`, or `while` loops
- **Uses expressions**: Comprehensions, conditional expressions (`x if cond else y`), `match`/`case`
- **Trampolines for recursion**: Python lacks tail-call optimization
- Returns values (expressions) rather than performing actions (statements)
- Transforms data immutably rather than mutating in place
- Uses pattern matching exhaustively

---

## Forbidden Patterns

These constructs are **strictly forbidden** in pure code. They represent imperative control flow that breaks functional purity.

### 1. `for` Loops

**Anti-pattern**:
```python
def process_items(items: list[int]) -> list[int]:
    result = []
    for item in items:
        result.append(item * 2)
    return result
```

**Why forbidden**:
- Requires mutable accumulator (`result = []`)
- Iterative mutation (`result.append()`)
- Not expression-oriented

**Correct pattern** (comprehension):
```python
def process_items(items: list[int]) -> list[int]:
    return [item * 2 for item in items]
```

### 2. `if` Statements

**Anti-pattern**:
```python
def process(value: int | str) -> int:
    if isinstance(value, str):
        return int(value)
    return value
```

**Why forbidden**:
- Control flow via statements
- Multiple return points
- Not expression-oriented

**Correct pattern** (conditional expression):
```python
def process(value: int | str) -> int:
    return int(value) if isinstance(value, str) else value
```

**Correct pattern** (match/case for complex branching):
```python
from effectful.algebraic import Result, Success, Failure

def handle_result(result: Result[str, str]) -> str:
    match result:
        case Success(value=v):
            return f"Success: {v}"
        case Failure(error=e):
            return f"Error: {e}"
```

### 3. `while` Loops

**Anti-pattern**:
```python
def find_first(items: list[int], predicate: Callable[[int], bool]) -> int | None:
    i = 0
    while i < len(items):
        if predicate(items[i]):
            return items[i]
        i += 1
    return None
```

**Why forbidden**:
- Mutable loop counter
- Control flow statements
- Imperative style

**Correct pattern** (generator expression with next):
```python
from collections.abc import Callable

def find_first(items: list[int], predicate: Callable[[int], bool]) -> int | None:
    return next((item for item in items if predicate(item)), None)
```

### 4. `raise` for Expected Errors

**Anti-pattern**:
```python
from dataclasses import dataclass
from uuid import UUID

@dataclass(frozen=True)
class User:
    id: UUID
    email: str

    def __post_init__(self) -> None:
        if not self.email:
            raise ValueError("Email cannot be empty")
```

**Why forbidden**:
- Exceptions break control flow
- Caller cannot statically know failure modes
- Error handling via try/except is impure

**Correct pattern** (factory returning Result):
```python
from dataclasses import dataclass
from uuid import UUID
from effectful.algebraic import Result, Success, Failure

@dataclass(frozen=True)
class User:
    """Validated user - only constructible via factory."""
    id: UUID
    email: str

@dataclass(frozen=True)
class InvalidEmailError:
    """Error when email is empty."""
    pass

def user(id: UUID, email: str) -> Result[User, InvalidEmailError]:
    """Create User, returning Failure if email is empty."""
    return (
        Failure(InvalidEmailError())
        if not email
        else Success(User(id=id, email=email))
    )
```

### 5. Side Effects in Pure Functions

**Anti-pattern**:
```python
def compute_total(items: list[int]) -> int:
    print(f"Computing total for {len(items)} items")  # Side effect!
    return sum(items)
```

**Why forbidden**:
- I/O operations are not reproducible
- Logging changes global state
- Function behavior depends on external state

**Correct pattern** (pure computation):
```python
def compute_total(items: list[int]) -> int:
    """Pure computation - no logging, no I/O."""
    return sum(items)
```

Side effects belong in the Effect Interpreter. See `documents/engineering/purity.md`.

---

## Allowed Constructs

These constructs are **pure** when used correctly:

### 1. `match`/`case` on Pure Types

Pattern matching on ADTs (Result, custom sum types) is **pure**:

```python
from typing import assert_never
from effectful.algebraic import Result, Success, Failure

def describe_result(result: Result[int, str]) -> str:
    """Pure function using match/case on Result ADT."""
    match result:
        case Success(value=v):
            return f"Got value: {v}"
        case Failure(error=e):
            return f"Got error: {e}"
        case _ as unreachable:
            assert_never(unreachable)
```

**Why allowed**:
- Exhaustive handling enforced by `assert_never()`
- No mutation, no side effects
- Expression-oriented (each case returns a value)
- Closest to functional pattern matching in Python

### 2. Comprehensions (Without Side Effects)

List, dict, set, and generator comprehensions are **pure** when they:
- Do not call functions with side effects
- Do not mutate external state
- Do not perform I/O

```python
# Pure comprehensions
squares: list[int] = [x * x for x in range(10)]
evens: list[int] = [x for x in items if x % 2 == 0]
lookup: dict[str, int] = {name: idx for idx, name in enumerate(names)}
unique: set[int] = {abs(x) for x in values}

# Impure comprehension (FORBIDDEN)
logged: list[int] = [log_and_return(x) for x in items]  # Side effect!
```

### 3. Conditional Expressions

The ternary operator is **pure**:

```python
def clamp(value: float, min_val: float, max_val: float) -> float:
    """Pure clamping using conditional expressions."""
    return min_val if value < min_val else (max_val if value > max_val else value)
```

### 4. Definitions

`def`, `class`, `return`, `import` are **allowed** - they define structure, not control flow:

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Config:
    learning_rate: float
    batch_size: int

def create_config(lr: float, bs: int) -> Config:
    return Config(learning_rate=lr, batch_size=bs)
```

### 5. `assert_never()` for Exhaustiveness

The `assert_never()` function is allowed to `raise` because:
- It's a compile-time exhaustiveness check
- It should **never** execute at runtime
- If it executes, it indicates a programming error (missing case)

```python
from typing import assert_never
from effectful.algebraic import Result, Success, Failure

def handle_result(result: Result[int, str]) -> str:
    match result:
        case Success(value=v):
            return f"Value: {v}"
        case Failure(error=e):
            return f"Error: {e}"
        case _ as unreachable:
            assert_never(unreachable)  # Allowed - compile-time check
```

---

## Constructor Validation Pattern

When dataclass construction requires validation, use **factory functions** instead of `__post_init__` that raises:

### Before (Impure - raises)

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class BoundSpec:
    lower: float
    upper: float

    def __post_init__(self) -> None:
        if self.lower >= self.upper:
            raise ValueError(f"lower ({self.lower}) must be < upper ({self.upper})")
```

### After (Pure - factory returns Result)

```python
from dataclasses import dataclass
from effectful.algebraic import Result, Success, Failure

@dataclass(frozen=True)
class BoundSpec:
    """Validated bound specification - only constructible via factory."""
    lower: float
    upper: float

@dataclass(frozen=True)
class InvalidBoundsError:
    """Error when lower >= upper."""
    lower: float
    upper: float

def bound_spec(lower: float, upper: float) -> Result[BoundSpec, InvalidBoundsError]:
    """Create BoundSpec, returning Failure if bounds are invalid."""
    return (
        Failure(InvalidBoundsError(lower=lower, upper=upper))
        if lower >= upper
        else Success(BoundSpec(lower=lower, upper=upper))
    )
```

### Usage Pattern

```python
def use_bounds(lower: float, upper: float) -> Result[float, InvalidBoundsError]:
    """Example of using factory function."""
    match bound_spec(lower, upper):
        case Success(bounds):
            return Success((bounds.upper - bounds.lower) / 2)
        case Failure(error):
            return Failure(error)
```

---

## The Trampoline Pattern

### Why Trampolines?

Python doesn't optimize tail calls, so naive recursion causes stack overflows:

```python
# WRONG - Stack overflow for large n
def factorial(n: int) -> int:
    if n <= 1:
        return 1
    return n * factorial(n - 1)  # Stack frame per call

factorial(10000)  # RecursionError!
```

The trampoline pattern converts recursion to iteration while preserving functional semantics.

### Trampoline Implementation

```python
from dataclasses import dataclass
from typing import Generic, TypeVar, Callable
from collections.abc import Awaitable

T = TypeVar('T')

@dataclass(frozen=True)
class Continue(Generic[T]):
    """Signal to continue with another step."""
    thunk: Callable[[], 'TrampolineStep[T]']

@dataclass(frozen=True)
class Done(Generic[T]):
    """Signal that computation is complete."""
    value: T

type TrampolineStep[T] = Continue[T] | Done[T]

def trampoline(step: TrampolineStep[T]) -> T:
    """Execute trampoline steps until completion."""
    current = step
    while True:  # Single controlled iteration point
        match current:
            case Done(value=value):
                return value
            case Continue(thunk=thunk):
                current = thunk()

async def async_trampoline(step: TrampolineStep[Awaitable[T]]) -> T:
    """Async version for effect interpretation."""
    current = step
    while True:
        match current:
            case Done(value=awaitable):
                return await awaitable
            case Continue(thunk=thunk):
                current = thunk()
```

### Using Trampolines

Convert recursive functions to return `TrampolineStep`:

```python
# Pure recursive logic expressed with trampolines
def factorial_step(n: int, acc: int = 1) -> TrampolineStep[int]:
    return (
        Done(acc) if n <= 1
        else Continue(lambda n=n, acc=acc: factorial_step(n - 1, n * acc))
    )

# Usage
result = trampoline(factorial_step(10000))  # No stack overflow!
```

---

## Replacing For-Loops

### List Comprehensions

```python
# WRONG - Imperative for-loop with mutation
users: list[User] = []
for row in rows:
    if isinstance(row["id"], UUID):
        users.append(User(id=row["id"], email=row["email"], name=row["name"]))
return users

# CORRECT - List comprehension
return [
    User(id=row["id"], email=row["email"], name=row["name"])
    for row in rows
    if isinstance(row["id"], UUID) and isinstance(row["email"], str) and isinstance(row["name"], str)
]
```

### Dict Comprehensions

```python
# WRONG - For-loop building dict
result: dict[str, int] = {}
for item in items:
    result[item.key] = item.value
return result

# CORRECT - Dict comprehension
return {item.key: item.value for item in items}
```

### Set Comprehensions

```python
# WRONG - For-loop building set
unique: set[str] = set()
for user in users:
    unique.add(user.email)
return unique

# CORRECT - Set comprehension
return {user.email for user in users}
```

### Generator Expressions

For lazy evaluation:

```python
# WRONG - Building full list unnecessarily
emails = []
for user in users:
    emails.append(user.email)

# CORRECT - Generator expression (lazy)
emails = (user.email for user in users)

# Usage in pure code - map/filter style
processed = [process(email) for email in (user.email for user in users)]

# Usage at system boundary (marked with comment)
for email in emails:  # IMPURE OK: system boundary
    process(email)
```

---

## Replacing While-Loops

### With Recursion + Trampoline

```python
# WRONG - While loop with mutation
def find_root(n: int) -> int:
    while n > 1:
        n = n // 2
    return n

# CORRECT - Recursive with trampoline
def find_root_step(n: int) -> TrampolineStep[int]:
    return (
        Done(n) if n <= 1
        else Continue(lambda n=n: find_root_step(n // 2))
    )

result = trampoline(find_root_step(1024))
```

### With itertools

```python
from itertools import takewhile, dropwhile, accumulate

# WRONG - While loop collecting items
results = []
i = 0
while items[i].valid:
    results.append(items[i])
    i += 1

# CORRECT - takewhile
results = list(takewhile(lambda x: x.valid, items))
```

---

## Replacing Mutations

### Accumulator Pattern with reduce

```python
from functools import reduce

# WRONG - Mutation with +=
total = 0
for value in values:
    total += value
return total

# CORRECT - reduce
return reduce(lambda acc, x: acc + x, values, 0)

# Or simply
return sum(values)
```

### Building Complex Results with reduce

```python
# WRONG - Multiple mutations
stats = {"found": 0, "not_found": 0}
for result in results:
    if result.found:
        stats["found"] += 1
    else:
        stats["not_found"] += 1

# CORRECT - reduce with immutable updates
from functools import reduce

return reduce(
    lambda acc, r: (
        {**acc, "found": acc["found"] + 1} if r.found
        else {**acc, "not_found": acc["not_found"] + 1}
    ),
    results,
    {"found": 0, "not_found": 0}
)
```

### String Building

```python
# WRONG - String concatenation mutation
query = "SELECT * FROM users"
if name:
    query += f" WHERE name = '{name}'"
if limit:
    query += f" LIMIT {limit}"

# CORRECT - Join with comprehension
query_parts = (
    "SELECT * FROM users",
    f" WHERE name = '{name}'" if name else "",
    f" LIMIT {limit}" if limit else "",
)
query = "".join(query_parts)
```

### List Building with Conditionals

```python
# WRONG - Conditional appends
params: list[str] = []
if email:
    params.append(email)
if name:
    params.append(name)

# CORRECT - Filter None from tuple
params = tuple(filter(None, (email, name)))

# Or with explicit comprehension
params = tuple(p for p in (email, name) if p is not None)
```

---

## Expression-Based Conditionals

### Ternary Expressions

```python
# WRONG - If-statement for assignment
if user:
    name = user.name
else:
    name = "Anonymous"

# CORRECT - Ternary expression
name = user.name if user else "Anonymous"
```

### Match Expressions

```python
# WRONG - If-elif chain
if status == "active":
    result = handle_active()
elif status == "pending":
    result = handle_pending()
else:
    result = handle_default()

# CORRECT - Match expression
result = (
    handle_active() if status == "active"
    else handle_pending() if status == "pending"
    else handle_default()
)

# Or with match statement (when all branches return)
match status:
    case "active":
        return handle_active()
    case "pending":
        return handle_pending()
    case _:
        return handle_default()
```

---

## Immutable Data Updates

### Dataclass Updates

```python
from dataclasses import replace

# WRONG - Mutation (requires non-frozen)
user.email = "new@example.com"

# CORRECT - Create new instance with replace
updated = replace(user, email="new@example.com")
```

### Dict Updates

```python
# WRONG - Mutation
config["timeout"] = 30

# CORRECT - Spread operator (creates new dict)
updated_config = {**config, "timeout": 30}
```

### List Updates

```python
# WRONG - Mutation
items.append(new_item)

# CORRECT - Tuple concatenation
updated_items = (*items, new_item)

# Or new list
updated_items = [*items, new_item]
```

### Removing from Dict

```python
# WRONG - Mutation with del
del data[key]

# CORRECT - Dict comprehension excluding key
updated = {k: v for k, v in data.items() if k != key}
```

---

## Functional Builder Pattern

For complex object construction:

```python
from dataclasses import dataclass
from typing import Self

@dataclass(frozen=True)
class QueryBuilder:
    """Immutable query builder using functional pattern."""
    table: str
    columns: tuple[str, ...] = ("*",)
    conditions: tuple[str, ...] = ()
    limit_value: int | None = None
    offset_value: int | None = None

    def select(self, *cols: str) -> Self:
        return replace(self, columns=cols)

    def where(self, condition: str) -> Self:
        return replace(self, conditions=(*self.conditions, condition))

    def limit(self, n: int) -> Self:
        return replace(self, limit_value=n)

    def offset(self, n: int) -> Self:
        return replace(self, offset_value=n)

    def build(self) -> tuple[str, tuple[str, ...]]:
        parts = (
            f"SELECT {', '.join(self.columns)} FROM {self.table}",
            f" WHERE {' AND '.join(self.conditions)}" if self.conditions else "",
            f" LIMIT {self.limit_value}" if self.limit_value else "",
            f" OFFSET {self.offset_value}" if self.offset_value else "",
        )
        return "".join(parts), self.conditions

# Usage - method chaining with immutable updates
query = (
    QueryBuilder("users")
    .select("id", "name", "email")
    .where("active = true")
    .limit(10)
    .build()
)
```

---

## Parameter Building Pattern

For SQL query parameters:

```python
# WRONG - Index mutation
param_idx = 1
updates = []
params = []
if email:
    updates.append(f"email = ${param_idx}")
    params.append(email)
    param_idx += 1
if name:
    updates.append(f"name = ${param_idx}")
    params.append(name)
    param_idx += 1

# CORRECT - Enumerate with filter
fields = tuple(
    (field, value)
    for field, value in [("email", email), ("name", name)]
    if value is not None
)
updates = tuple(f"{field} = ${i+1}" for i, (field, _) in enumerate(fields))
params = tuple(value for _, value in fields)
```

---

## Effect Program Patterns

### Sequential Effects with Comprehension

```python
# WRONG - For-loop accumulating results
results = []
for user_id in user_ids:
    user = yield GetUserById(user_id=user_id)
    if isinstance(user, User):
        results.append(user.name)
return results

# BETTER - Still uses yield in loop (acceptable for generators)
# But collect immutably
names = []
for user_id in user_ids:
    user = yield GetUserById(user_id=user_id)
    names = [*names, user.name] if isinstance(user, User) else names
return names
```

Note: Generator programs may use for-loops with yield since `yield` can't be in comprehensions. The key is avoiding mutable accumulation.

### Parallel Effect Collection

```python
# For bulk operations, create dedicated batch effect
results = yield GetUsersByIds(user_ids=user_ids)
names = [user.name for user in results if isinstance(user, User)]
```

---

## Acceptable Impurities

Some controlled impurity is acceptable:

### 1. Trampoline While-Loop

**The ONLY acceptable while-loop in the entire codebase.** This is the single controlled exception to the no-loops rule.

The `while True` in the trampoline driver is acceptable because:
- Python lacks tail-call optimization
- The trampoline pattern requires a controlled iteration point
- The while-loop is isolated to a single function with well-defined semantics

```python
def trampoline(step: TrampolineStep[T]) -> T:
    current = step
    while True:  # The ONLY acceptable while-loop
        match current:
            case Done(value):
                return value
            case Continue(thunk):
                current = thunk()
```

**Zero tolerance for all other loops**:
- ❌ No for-loops anywhere (use comprehensions)
- ❌ No while-loops anywhere except this trampoline driver
- ✅ List/dict/set comprehensions are acceptable and preferred
- ✅ Trampoline pattern for recursive algorithms

### 2. Adapter Mutable State

Infrastructure adapters may hold mutable connections:

```python
@dataclass
class PostgresAdapter:
    _conn: asyncpg.Connection  # Mutable connection - acceptable for I/O boundary
```

### 3. Test Setup/Teardown

Test code may use imperative patterns for clarity:

```python
def test_feature():
    # Setup (imperative is fine)
    results = []
    for i in range(3):
        results.append(create_fixture(i))

    # Assertions
    assert len(results) == 3
```

---

## Migration Checklist

When refactoring existing code to pure patterns:

- [ ] Replace `for` loops with list/dict/set comprehensions
- [ ] Replace `if` statements with conditional expressions or `match`/`case`
- [ ] Replace `if-else` assignment with ternary
- [ ] Replace `if-elif-else` chains with `match`/`case`
- [ ] Replace `while` loops with recursion + trampoline
- [ ] Replace `+=` accumulation with `reduce`
- [ ] Replace `.append()` with tuple spread or comprehension
- [ ] Replace `del` with dict comprehension filter
- [ ] Replace mutable defaults with `None` + expression
- [ ] Replace `__post_init__` validation with factory functions returning Result
- [ ] Use `replace()` for dataclass updates
- [ ] Use dict spread for dict updates
- [ ] Replace `unreachable()` with `assert_never()` from typing

---

## Purity Summary Table

| Construct | Pure? | Use Instead |
|-----------|-------|-------------|
| `for` loop | No | Comprehension: `[f(x) for x in items]` |
| `if` statement | No | Conditional: `x if cond else y` or `match`/`case` |
| `while` loop | No | Comprehension, recursion, or `next()` with generator |
| `raise` | No | Return `Result[T, E]` type |
| `try`/`except` | No | Pattern match on `Result` |
| `print()` | No | Effect ADT |
| `logger.*()` | No | Effect ADT |
| `match`/`case` | **Yes** | (on pure types) |
| Comprehension | **Yes** | (if no side effects) |
| Conditional expr | **Yes** | |
| `def`/`class` | **Yes** | |
| `return` | **Yes** | |
| `assert_never()` | **Yes** | (compile-time exhaustiveness) |

---

## Enforcement

### Static Analysis

MyPy cannot detect all purity violations. Use code review and grep audits:

```bash
# Check for for-loops in pure code (manual review needed)
grep -rn "^\s*for " effectful/ | grep -v "# IMPURE OK:" | grep -v "tests/"

# Check for if-statements in pure code (manual review needed)
grep -rn "^\s*if " effectful/ | grep -v "# IMPURE OK:" | grep -v "tests/"

# Check for raise statements (should only be assert_never or test code)
grep -rn "^\s*raise " effectful/ | grep -v "assert_never" | grep -v "# IMPURE OK:" | grep -v "tests/"

# Check for print statements
grep -rn "print(" effectful/ | grep -v "tests/" && echo "FOUND print()" || echo "OK"

# Check for logging in pure modules
grep -rn "logger\." effectful/ | grep -v "# EFFECT:" | grep -v "interpreters/" | grep -v "adapters/"
```

### Code Review Checklist

Before approving any PR:

- [ ] No `for` loops (use comprehensions)
- [ ] No `if` statements (use conditional expressions or `match`/`case`)
- [ ] No `while` loops (use comprehensions or trampoline)
- [ ] No `raise` except in `assert_never()` or system boundaries
- [ ] No `print()` or `logger.*()` in pure functions
- [ ] Factory functions return `Result` for validation
- [ ] Comprehensions have no side effects

### Exceptions

**Test Code**: Test code may use impure constructs:
- `assert` statements (pytest requires them)
- `pytest.raises()` context manager
- `for` loops in test setup/teardown

Tests verify behavior; they are not business logic.

**System Boundaries**: At system boundaries (CLI commands, HTTP handlers), impure code is acceptable:
- Logging at entry/exit points
- `raise` after exhaustive Result handling
- I/O operations

Mark system boundary code with `# IMPURE OK: system boundary` comment.

**Effect Interpreter**: The Effect Interpreter itself is impure by design - it executes effects. All impure operations are concentrated in the interpreter. Business logic remains pure.

---

## Related Documentation

- **Purity**: `documents/engineering/purity.md` - Core purity rules
- **Type Safety**: `documents/engineering/type-safety-enforcement.md`
- **Trampoline Module**: `effectful/algebraic/trampoline.py`

---

**Last Updated**: 2025-11-30
