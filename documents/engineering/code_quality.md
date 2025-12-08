# Code Quality

**Status**: Authoritative source  
**Supersedes**: type_safety_enforcement.md, purity.md  
**Referenced by**: engineering/README.md, documents/readme.md

> **Purpose**: Single Source of Truth for type safety, purity, and code quality enforcement in Effectful.

## SSoT Link Map

```mermaid
flowchart TB
  CodeQuality[Code Quality SSoT]
  Architecture[Architecture SSoT]
  Testing[Testing SSoT]
  Docs[Documentation Standards]
  Observability[Observability]
  EffectPatterns[Effect Patterns]
  Docker[Docker Workflow]

  CodeQuality --> Architecture
  CodeQuality --> Testing
  CodeQuality --> Docs
  CodeQuality --> Observability
  CodeQuality --> EffectPatterns
  CodeQuality --> Docker
  Testing --> Docs
  Architecture --> Testing
```

| Need | Link |
|------|------|
| Layer boundaries and imports | [Architecture](architecture.md#core-abstractions) |
| Generator + interpreter testing | [Testing](testing.md#part-4-four-layer-testing-architecture) |
| Documentation + link hygiene | [Documentation Standards](../documentation_standards.md) |
| Metrics/alert hooks | [Observability](observability.md) |
| Canonical effect patterns | [Effect Patterns](effect_patterns.md) |
| Docker-only contract | [Docker Workflow](docker_workflow.md#development-contract) |

---

## Overview

Code quality = **type safety + purity**. Programs remain pure descriptions, interpreters isolate impurity, and the type system makes invalid states unrepresentable. All standards, anti-pattern routing, and remediation workflows now live here to enforce a single, heavily cross-linked source of truth.

**Core principles**
- Zero escape hatches: no `Any`, `cast()`, or `# type: ignore` anywhere.
- Effects as data: programs `yield` effect descriptions; interpreters execute I/O.
- Immutability by default: frozen dataclasses, Result/ADT returns, exhaustive matches.
- Link, don’t duplicate: every rule below links to the SSoT section that owns the fix.

---

## Type Safety Doctrines

### 1. NO Escape Hatches (ZERO Exceptions)
- ❌ Forbidden: `Any`, `cast()`, `# type: ignore` in all code (prod, tests, docs, scripts).
- ✅ Required: explicit types + `mypy --strict` (`disallow_any_explicit = true`).
- Testing frozen dataclasses: use `setattr` + `pytest.raises` instead of `type: ignore`.

### 2. ADTs Over Optional Types
- Replace `Optional[T]` with explicit ADT unions that encode why a value may be absent.
- Example: `UserFound | UserNotFound | UserDeleted` instead of `Optional[User]`.

### 3. Result Type for Error Handling
- Never throw for expected errors; return `Result[T, E]` and pattern match on outcomes.
- Errors must be part of the type to keep flows explicit and testable.

### 4. Immutability by Default
- Domain models and effects use `@dataclass(frozen=True)`.
- Update via `replace()` or immutable copies, never in-place mutation.

### 5. Exhaustive Pattern Matching
- Use `match` with `assert_never()` to cover every union variant at compile time.
- No wildcard fallbacks that swallow new cases.

### 6. Type Narrowing for Union Types
- Narrow with structural checks (`match`, `isinstance`, tagged unions) instead of casts.
- Prefer `match` or guards over Boolean flag fields.

### 7. Generic Type Parameters
- Keep generics concrete and bounded; avoid unconstrained `TypeVar` usage.
- Use variance annotations only when necessary; document constraints.

### 8. PEP 695 Type Aliases
- Use inline `type` aliases for readability and reuse.
- Aliases must remain immutable and specific (no aliasing to `Any`).

---

## Purity Doctrines

### Doctrine 1: No Loops
- No `for`/`while` loops in pure code; use comprehensions or trampolines.
- Controlled exceptions: trampoline driver and program runner loops only.

### Doctrine 2: Effects as Data
- Effects describe intent; they never perform I/O. Interpreters do the work.

### Doctrine 3: Yield Don't Call
- Programs `yield` effect descriptions rather than calling infrastructure.
- Composition via `yield from` keeps flows testable without mocks.

### Doctrine 4: Interpreters Isolate Impurity
- All I/O, logging, and randomness live in interpreters/adapters at the boundary.
- Mutable state is acceptable only inside adapters that wrap infrastructure handles.

### Doctrine 5: Immutability by Default
- Pure layers construct new values instead of mutating; adapters may manage mutable handles.

### Doctrine 6: Exhaustive Pattern Matching
- Pure code matches on ADTs exhaustively with `assert_never()` safeguards.

---

## Generator Program Rules

- Programs are synchronous generators; never `async def` or `await` inside programs.
- No direct I/O in generators (no `print`, file, network, time, random); always yield effects.
- Compose with `yield from` and return immutable results (tuples/records).
- Use comprehensions inside generators only when the body is pure; prefer explicit `for` + `yield` when building effect sequences.

---

## Anti-Pattern Index (Routing to Canonical Fixes)

| Anti-Pattern | Impact | Fix |
|--------------|--------|-----|
| Using `Any` / `cast()` / `# type: ignore` | Breaks type safety gates | See [Doctrine 1](#1-no-escape-hatches-zero-exceptions) |
| Mutable domain/effects | Hidden state, races | See [Doctrine 4](#4-immutability-by-default) |
| Optional for domain logic | Ambiguous absence | See [Doctrine 2](#2-adts-over-optional-types) |
| Exceptions for expected errors | Hidden control flow | See [Doctrine 3](#3-result-type-for-error-handling) |
| Imperative effect execution | Untestable programs | See [Doctrine 3: Yield Don't Call](#doctrine-3-yield-dont-call) |
| Impure comprehensions | Side effects in pure layer | See [Doctrine 1: No Loops](#doctrine-1-no-loops) |
| Global mutable state | Non-determinism | See [Doctrine 5: Immutability by Default](#doctrine-5-immutability-by-default) |
| Inline interpreter construction | Boilerplate, resource leaks | Use `Depends(get_audited_composite_interpreter)` for API endpoints |
| Skipped tests (`pytest.skip`) | Masks regressions | See [Testing Anti-Patterns](testing.md#anti-pattern-2-skipped-tests) |
| Running pytest/poetry on host | Bypasses infra contract | See [Docker Workflow](docker_workflow.md#development-contract) |

**How to remediate**
1. Stop and map the violation to the doctrine above.
2. Apply the canonical pattern from this file (or linked SSoT).
3. Add/adjust tests (unit/integration as appropriate).
4. Run `docker compose -f docker/docker-compose.yml exec effectful poetry run check-code`.

---

## Detection and Enforcement

- **Primary gate:** `docker compose -f docker/docker-compose.yml exec effectful poetry run check-code` (Black → MyPy strict → doc link verification). See [Command Reference](command_reference.md).
- **Static queries:** search for `Any`, `cast`, `# type: ignore`, `for ` / `while ` in pure modules, and direct `raise` in business logic.
- **Code review checklist:** exhaustive matches present, no direct I/O in programs, frozen dataclasses, Result-based errors, adapters own impurity, and links target SSoT sections instead of duplicating guidance.

---

## Cross-References

- **Testing:** effect generators, integration policies, and anti-pattern catalog live in [testing.md](testing.md).
- **Observability:** metrics/alert hooks and registries live in [observability.md](observability.md) and [monitoring_and_alerting.md](monitoring_and_alerting.md).
- **Documentation:** SSoT/DRY rules and mermaid safety in [documentation_standards.md](../documentation_standards.md).
- **Architecture:** import boundaries and layer rules in [architecture.md](architecture.md).
- **Effect Patterns:** canonical program and interpreter shapes in [effect_patterns.md](effect_patterns.md).
