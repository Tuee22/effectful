# Forbidden Patterns

> **Navigation Hub** for all anti-patterns and prohibited constructs in effectful.

## Overview

This document serves as a **quick reference guide** to forbidden implementation patterns. All detailed documentation lives in the appropriate Single Source of Truth (SSoT) documents linked below.

**Core Philosophy**: Make invalid states unrepresentable through the type system.

---

## Anti-Pattern Quick Reference

| Anti-Pattern | Impact | SSoT Document |
|--------------|--------|---------------|
| **Using `Any` Types** | Destroys type safety | [Type Safety](type_safety_enforcement.md) - Doctrine 1 |
| **Using `cast()`** | Bypasses type checker | [Type Safety](type_safety_enforcement.md) - Doctrine 1 |
| **Using `# type: ignore`** | Silences type errors | [Type Safety](type_safety_enforcement.md) - Doctrine 1 |
| **Mutable Domain Models** | Breaks immutability | [Type Safety](type_safety_enforcement.md) - Doctrine 4 |
| **Optional for Domain Logic** | Loses type information | [Type Safety](type_safety_enforcement.md) - Doctrine 2 |
| **Exceptions for Expected Errors** | Hidden error paths | [Type Safety](type_safety_enforcement.md) - Doctrine 3 |
| **Imperative Effect Execution** | Couples logic to infrastructure | [Purity](purity.md) - Doctrine 3 |
| **Immutability Libraries in Adapters** | Over-engineering, unnecessary dependencies | [Purity](purity.md) - Doctrine 4 |
| **While Loops in Programs** | Breaks purity (exception: trampoline) | [Purity](purity.md) - Doctrine 1 |
| **Direct Infrastructure Calls** | Violates separation of concerns | [Purity](purity.md) - Doctrine 3 |
| **Skipped Tests (`pytest.skip()`)** | Masks broken features | [Testing](testing.md) - Anti-Pattern 2 |
| **Tests Without Assertions** | Provides false confidence | [Testing](testing.md) - Anti-Pattern 5 |
| **Running pytest Locally** | No infrastructure access | [Docker Workflow](docker_workflow.md) |
| **Running poetry Locally** | Bypasses Docker environment | [Docker Workflow](docker_workflow.md) |

---

## Detection Strategies

### Automated Detection

**Tools:**
- **MyPy** (`mypy --strict`): Catches Any, cast, type:ignore, missing annotations, unhandled unions
- **pytest**: Catches skipped tests, missing coverage (< 45%), test failures
- **Black**: Catches formatting violations

**See**: [Type Safety](type_safety_enforcement.md#anti-pattern-detection) for complete detection workflow.

### Manual Detection

**Code review catches:**
- Mutable domain models (missing `frozen=True`)
- Optional instead of ADTs (semantic issue)
- Exceptions instead of Result (control flow anti-pattern)
- Imperative effect execution (architectural violation)
- Immutability library usage in adapters

**Grep patterns:**
```bash
# Find mutable dataclasses
grep -r "@dataclass" effectful/ | grep -v "frozen=True"

# Find Optional in domain
grep -r "Optional\[" effectful/domain/

# Find exceptions in business logic
grep -r "raise " effectful/programs/ effectful/domain/

# Find Any types
grep -r "Any" effectful/ tests/
```

---

## Remediation Workflow

**When anti-pattern detected:**

1. **Stop immediately** - Do not proceed with broken code
2. **Identify doctrine** - Which principle is violated?
3. **Consult SSoT** - Navigate to the authoritative document:
   - Type safety violations → [Type Safety](type_safety_enforcement.md)
   - Purity violations → [Purity](purity.md)
   - Test violations → [Testing](testing.md)
   - Docker violations → [Docker Workflow](docker_workflow.md)
4. **Refactor** - Apply the correct pattern from SSoT examples
5. **Add test** - Prevent regression
6. **Verify** - Run `poetry run check-code` to confirm fix

---

## SSoT Documents

**Core Engineering Standards:**
- [Type Safety Enforcement](type_safety_enforcement.md) - Eight type safety doctrines, zero-tolerance policy
- [Purity](purity.md) - Six purity doctrines, functional programming patterns
- [Testing](testing.md) - 22 test anti-patterns, testing doctrine
- [Docker Workflow](docker_workflow.md) - All development in Docker, infrastructure management
- [Architecture](architecture.md) - 5-layer architecture design, layer boundaries

**Supporting Documentation:**
- [Command Reference](command_reference.md) - Docker commands, test execution
- [Development Workflow](development_workflow.md) - Daily development loop
- [Effect Patterns](effect_patterns.md) - Real-world effect program patterns
- [Documentation Standards](documentation_standards.md) - SSoT, DRY, cross-references

---

**Last Updated**: 2025-11-30
**Referenced by**: CLAUDE.md, type_safety_enforcement.md, purity.md, testing.md, docker_workflow.md
