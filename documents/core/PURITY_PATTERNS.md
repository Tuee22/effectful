# Purity Patterns

This document provides implementation patterns for writing pure functional code in Python. Since Python lacks tail-call optimization (TCO), we use the **trampoline pattern** to avoid stack overflows in recursive algorithms.

---

## Core Philosophy

**Expressions over statements. Comprehensions over loops. Trampolines over recursion.**

Pure functional code:
- Returns values (expressions) rather than performing actions (statements)
- Transforms data immutably rather than mutating in place
- Uses pattern matching exhaustively
- Avoids all forms of loops (`for`, `while`)

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
# WRONG - Building full list when only iterating
emails = []
for user in users:
    emails.append(user.email)
for email in emails:
    process(email)

# CORRECT - Generator expression (lazy)
emails = (user.email for user in users)
for email in emails:
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

The single `while True` in the trampoline driver is acceptable - it's the controlled iteration point:

```python
def trampoline(step: TrampolineStep[T]) -> T:
    current = step
    while True:  # Acceptable - controlled iteration point
        match current:
            case Done(value):
                return value
            case Continue(thunk):
                current = thunk()
```

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
- [ ] Replace `while` loops with recursion + trampoline
- [ ] Replace `+=` accumulation with `reduce`
- [ ] Replace `.append()` with tuple spread or comprehension
- [ ] Replace `del` with dict comprehension filter
- [ ] Replace if-else assignment with ternary
- [ ] Replace mutable defaults with `None` + expression
- [ ] Use `replace()` for dataclass updates
- [ ] Use dict spread for dict updates

---

## Related Documentation

- **Purity Doctrine**: `documents/core/PURITY.md` - Core purity rules
- **Type Safety Doctrine**: `documents/core/TYPE_SAFETY_DOCTRINE.md`
- **Trampoline Module**: `effectful/algebraic/trampoline.py`

---

**Last Updated**: 2025-11-22
