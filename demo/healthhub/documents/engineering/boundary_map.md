# HealthHub Boundary Model Reference Implementation

**Status**: Authoritative source
**Supersedes**: none
**Referenced by**: CLAUDE.md, README.md, documents/readme.md

> **Purpose**: Map HealthHub components to the Effectful boundary model. HealthHub serves as the canonical reference implementation showing how legacy Python applications align with the three-boundary architecture.
> **📖 Base Standard**: [boundary_map.md](../../../../documents/engineering/boundary_map.md)

______________________________________________________________________

## SSoT Link Map

| Need                      | Link                                                                                |
| ------------------------- | ----------------------------------------------------------------------------------- |
| Base boundary model       | [Boundary Model](../../../../documents/engineering/boundary_model.md)               |
| Proof boundary philosophy | [Proof Boundary Essay](../../../../documents/dsl/proof_boundary.md)                 |
| Language architecture     | [Language Architecture](../../../../documents/engineering/language_architecture.md) |
| Runner pattern            | [Runner Pattern](../../../../documents/engineering/runner_pattern.md)               |
| External assumptions      | [External Assumptions](external_assumptions.md)                                     |
| Migration guide           | [Migration Guide](haskell_rust_migration.md)                                        |
| Verification strategy     | [Verification Strategy](verification_strategy.md)                                   |

______________________________________________________________________

## Deltas

This document extends the base boundary_map.md with HealthHub-specific component mappings and annotation examples.

______________________________________________________________________

## 1. HealthHub in the Boundary Model

### 1.1 Visual Boundary Map

HealthHub's Python codebase maps to the three-boundary model:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                       OUTSIDE PROOF BOUNDARY                                 │
│  PostgreSQL | Redis | Pulsar | MinIO | FastAPI (api/*.py) | frontend/*      │
│  interpreters/*_interpreter.py | repositories/ | auth/ | infrastructure/    │
│  config.py | main.py                                                         │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  │ Assumptions documented in external_assumptions.md
                                  │
┌─────────────────────────────────┴───────────────────────────────────────────┐
│                       PROOF BOUNDARY                                         │
│  programs/runner.py | composite_interpreter.py | auditing_interpreter.py    │
│  adapters/*.py | container.py                                                │
│                                                                              │
│  In target architecture: Rust (imperative, memory-safe, verified)            │
│  Current implementation: Python with typed Result, exhaustive matching       │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  │ Effects as pure data descriptions
                                  │
┌─────────────────────────────────┴───────────────────────────────────────────┐
│                       PURITY BOUNDARY                                        │
│  domain/*.py | effects/*.py | programs/*_programs.py | protocols/*.py       │
│  (Patient, Appointment, HealthcareEffect, schedule_appointment_program)     │
│                                                                              │
│  In target architecture: Haskell DSL (pure, deterministic, total)            │
│  Current implementation: Python with frozen dataclasses, ADTs, generators    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Boundary Semantics

| Boundary    | Meaning                               | HealthHub Implementation               |
| ----------- | ------------------------------------- | -------------------------------------- |
| **Purity**  | Pure, deterministic, side-effect-free | Frozen dataclasses, generator programs |
| **Proof**   | Verifiable against TLA+ specs         | Effect runner, orchestration logic     |
| **Outside** | Assumed correct, documented           | External services, framework glue      |

______________________________________________________________________

## 2. Component-to-Boundary Mapping

### 2.1 Complete Directory Mapping

| Directory                                               | Boundary    | Target Language | Rationale                            |
| ------------------------------------------------------- | ----------- | --------------- | ------------------------------------ |
| `backend/app/domain/*.py`                               | **PURITY**  | Haskell         | Frozen dataclasses, pure validation  |
| `backend/app/effects/*.py`                              | **PURITY**  | Haskell         | Pure effect descriptions (data only) |
| `backend/app/programs/*_programs.py`                    | **PURITY**  | Haskell         | Generator-based pure programs        |
| `backend/app/protocols/*.py`                            | **PURITY**  | Haskell         | Protocol definitions (interfaces)    |
| `backend/app/programs/runner.py`                        | **PROOF**   | Rust            | Effect execution loop                |
| `backend/app/interpreters/composite_interpreter.py`     | **PROOF**   | Rust            | Effect routing                       |
| `backend/app/interpreters/auditing_interpreter.py`      | **PROOF**   | Rust            | Pure transformation wrapper          |
| `backend/app/adapters/*.py`                             | **PROOF**   | Rust            | Protocol implementations             |
| `backend/app/container.py`                              | **PROOF**   | Rust            | Pure DI wiring                       |
| `backend/app/interpreters/healthcare_interpreter.py`    | **OUTSIDE** | N/A             | Real database operations             |
| `backend/app/interpreters/notification_interpreter.py`  | **OUTSIDE** | N/A             | Redis/Pulsar operations              |
| `backend/app/interpreters/observability_interpreter.py` | **OUTSIDE** | N/A             | Metrics operations                   |
| `backend/app/repositories/*.py`                         | **OUTSIDE** | N/A             | Database access                      |
| `backend/app/api/*.py`                                  | **OUTSIDE** | N/A             | HTTP boundary                        |
| `backend/app/auth/*.py`                                 | **OUTSIDE** | N/A             | Crypto libraries                     |
| `backend/app/infrastructure/*.py`                       | **OUTSIDE** | N/A             | Rate limiting, etc.                  |
| `backend/app/config.py`                                 | **OUTSIDE** | N/A             | Environment config                   |
| `backend/app/main.py`                                   | **OUTSIDE** | N/A             | Entry point                          |
| `frontend/src/*`                                        | **OUTSIDE** | N/A             | Browser runtime                      |

### 2.2 Key Files by Boundary

**Purity Boundary Exemplars**:

- `domain/patient.py` - Frozen dataclass with immutable fields
- `effects/healthcare.py` - Effect descriptions as pure data
- `programs/appointment_programs.py` - Generator-based pure programs

**Proof Boundary Exemplars**:

- `programs/runner.py` - Effect execution loop with typed Result
- `interpreters/composite_interpreter.py` - Effect routing logic
- `adapters/patient_adapter.py` - Protocol implementations

**Outside Boundary Exemplars**:

- `interpreters/healthcare_interpreter.py` - PostgreSQL operations
- `api/appointments.py` - FastAPI endpoint handlers
- `repositories/patient_repository.py` - asyncpg queries

______________________________________________________________________

## 3. Annotation Standards

### 3.1 Python Module Annotation Format

All HealthHub source files should include boundary metadata in module docstrings:

**Purity Boundary**:

```python
# example
"""Patient domain model.

Boundary: PURITY
Target-Language: Haskell

Pure immutable data model representing a patient entity.
Contains no side effects, I/O operations, or mutable state.
"""
```

**Proof Boundary (with invariants)**:

```python
# example
"""Program runner for effect execution.

Boundary: PROOF
Target-Language: Rust

Layer 2 in 5-layer architecture: The verified execution loop.

Invariants:
- Never swallows exceptions (wraps in Err)
- Always returns typed Result
- Effect execution order matches program yield order
"""
```

**Outside Boundary (with assumptions)**:

```python
# example
"""Healthcare effect interpreter.

Boundary: OUTSIDE_PROOF
Target-Language: N/A (assumed correct)

Assumptions:
- [Library] asyncpg correctly implements PostgreSQL wire protocol
- [Service] PostgreSQL server enforces ACID guarantees
- [Network] Connection pool handles transient failures
- [Security] SQL parameterization prevents injection
"""
```

### 3.2 TypeScript Annotation Format

```typescript
// TypeScript annotation example
/**
 * Patient detail component.
 *
 * @boundary OUTSIDE_PROOF
 * @target N/A (browser runtime assumed correct)
 *
 * Assumptions:
 * - React reconciliation is correct
 * - Browser DOM APIs behave as documented
 */
```

______________________________________________________________________

## 4. Why This Mapping Matters

### 4.1 Current State (Python)

HealthHub demonstrates that Python can approximate the boundary model:

- **Purity boundary**: `frozen=True` dataclasses, generators that yield effects
- **Proof boundary**: Typed `Result[T, E]`, exhaustive pattern matching
- **Outside boundary**: Explicit assumptions about PostgreSQL, Redis, etc.

### 4.2 Target State (Haskell + Rust)

In the fully realized Effectful architecture:

- **Purity boundary (Haskell)**: Compute graph optimization, pure effect descriptions
- **Proof boundary (Rust)**: Memory-safe effect execution, TLA+ verified
- **Outside boundary**: Same external services, same documented assumptions

### 4.3 Migration Path

HealthHub's Python code can be mechanically translated:

1. Domain models → Haskell ADTs
1. Effect descriptions → Haskell data types
1. Generator programs → Haskell do-notation
1. Runner → Rust effect executor
1. Interpreters (pure) → Rust protocol handlers
1. Interpreters (I/O) → Rust with documented assumptions

See [Migration Guide](haskell_rust_migration.md) for code translation examples.

______________________________________________________________________

## 5. Validation Rules

### 5.1 Purity Boundary Requirements

Code in the purity boundary MUST:

- [ ] Use `@dataclass(frozen=True)` for all domain models
- [ ] Never import from `api/`, `repositories/`, or `infrastructure/`
- [ ] Never use `async/await` (effects are synchronous descriptions)
- [ ] Never raise exceptions (use typed Result variants)
- [ ] Have no mutable state

### 5.2 Proof Boundary Requirements

Code in the proof boundary MUST:

- [ ] Return `Result[T, E]` for fallible operations
- [ ] Use exhaustive pattern matching (all cases handled)
- [ ] Document invariants in module docstring
- [ ] Never call external services directly (delegate to outside boundary)

### 5.3 Outside Boundary Requirements

Code in the outside boundary MUST:

- [ ] Document all assumptions about external services
- [ ] Convert external errors to typed variants
- [ ] Never expose raw exceptions to proof boundary
- [ ] Log all assumption-dependent operations

______________________________________________________________________

## Cross-References

- [Boundary Model](../../../../documents/engineering/boundary_model.md) - Base concepts
- [External Assumptions](external_assumptions.md) - Service assumption inventory
- [Migration Guide](haskell_rust_migration.md) - Code translation examples
- [Verification Strategy](verification_strategy.md) - Testing-to-boundary mapping
- [Proof Boundary Essay](../../../../documents/dsl/proof_boundary.md) - Philosophical foundation
