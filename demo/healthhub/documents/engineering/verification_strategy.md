# HealthHub Verification Strategy

**Status**: Authoritative source
**Supersedes**: none
**Referenced by**: boundary_map.md

> **Purpose**: Map HealthHub's current testing strategy to the boundary model verification approach. Each boundary has different verification techniques.
> **📖 Base Standard**: [verification_strategy.md](../../../../documents/engineering/verification_strategy.md)

______________________________________________________________________

## SSoT Link Map

| Need                        | Link                                                                                          |
| --------------------------- | --------------------------------------------------------------------------------------------- |
| Boundary model verification | [Boundary Model](../../../../documents/engineering/boundary_model.md#6-verification-strategy) |
| HealthHub boundary map      | [Boundary Map](boundary_map.md)                                                               |
| External assumptions        | [External Assumptions](external_assumptions.md)                                               |
| Testing standards           | [Testing](../../../../documents/engineering/testing.md)                                       |
| HealthHub testing           | [Testing Architecture](../../../../documents/engineering/testing_architecture.md)             |

______________________________________________________________________

## Deltas

This document extends the base verification_strategy.md with HealthHub's specific testing pyramid and boundary mappings.

______________________________________________________________________

## 1. Verification by Boundary

### 1.1 Overview

| Boundary | Current (Python)       | Target (Haskell/Rust)                      |
| -------- | ---------------------- | ------------------------------------------ |
| Purity   | pytest unit tests      | QuickCheck properties + formal semantics   |
| Proof    | pytest + type checking | TLA+ model checking + Rust conformance     |
| Outside  | Integration tests      | Runtime monitoring + assumption validation |

### 1.2 Verification Goals

**Purity boundary**: Prove pure functions are correct for all inputs.

**Proof boundary**: Verify execution logic satisfies safety and liveness properties.

**Outside boundary**: Validate assumptions hold in real environment.

______________________________________________________________________

## 2. Current HealthHub Testing

### 2.1 Test Organization

```python
# test example
tests/
├── pytest/
│   ├── backend/           # Unit tests (PURITY + PROOF verification)
│   │   ├── domain/        # Domain model tests
│   │   ├── effects/       # Effect description tests
│   │   ├── programs/      # Generator program tests
│   │   └── interpreters/  # Interpreter routing tests
│   └── integration/       # Integration tests (OUTSIDE verification)
│       ├── repositories/  # Database assumption validation
│       ├── api/          # HTTP assumption validation
│       └── messaging/    # Pulsar assumption validation
```

### 2.2 Test Counts by Boundary

| Boundary | Test Type          | Test Count | Purpose                      |
| -------- | ------------------ | ---------- | ---------------------------- |
| Purity   | Unit (pytest-mock) | ~60        | Domain logic correctness     |
| Proof    | Unit (pytest-mock) | ~40        | Effect routing, runner logic |
| Outside  | Integration        | ~24        | Assumption validation        |

______________________________________________________________________

## 3. Purity Boundary Verification

### 3.1 Current Approach: Unit Tests

**What we test:**

- Domain model creation and validation
- ADT pattern matching exhaustiveness
- Effect description construction
- Pure program logic via generator stepping

**Example: Domain model test**

```python
# example code
def test_appointment_status_transitions() -> None:
    """Verify valid state machine transitions."""
    requested = Requested(requested_at=datetime.now(UTC))

    # Valid transition
    confirmed = validate_transition(requested, Confirmed(
        confirmed_at=datetime.now(UTC),
        scheduled_time=datetime.now(UTC) + timedelta(hours=1),
    ))
    assert isinstance(confirmed, Ok)

    # Invalid transition (skip Confirmed)
    in_progress = validate_transition(requested, InProgress(
        started_at=datetime.now(UTC),
    ))
    assert isinstance(in_progress, Err)
```

**Example: Generator program test**

```python
# example code
def test_schedule_appointment_program_patient_not_found() -> None:
    """Test program handles missing patient."""
    gen = schedule_appointment_program(
        patient_id=uuid4(),
        doctor_id=uuid4(),
        requested_time=None,
        reason="Checkup",
    )

    # Step 1: GetPatientById effect
    effect = next(gen)
    assert isinstance(effect, GetPatientById)

    # Send NotFound, get final result
    try:
        gen.send(PatientMissingById(patient_id=effect.patient_id))
    except StopIteration as stop:
        result = stop.value
        assert isinstance(result, Err)
        assert "not found" in result.error
```

### 3.2 Target Approach: QuickCheck Properties

In Haskell, purity boundary verification uses property-based testing:

```haskell
-- Property: All valid transitions produce valid states
prop_validTransitions :: AppointmentStatus -> Gen Bool
prop_validTransitions status = do
  nextStatus <- arbitrary
  let result = validateTransition status nextStatus
  pure $ case result of
    Left _ -> True  -- Invalid transition rejected
    Right newStatus -> isValidState newStatus

-- Property: Schedule program never throws
prop_scheduleProgramTotal :: Patient -> Doctor -> Text -> Property
prop_scheduleProgramTotal patient doctor reason =
  forAll arbitrary $ \requestedTime ->
    let program = scheduleAppointmentProgram
          (patientId patient)
          (doctorId doctor)
          requestedTime
          reason
    in evaluatesWithoutException program
```

### 3.3 Gap Analysis

| Current (Python)      | Target (Haskell)     | Gap                             |
| --------------------- | -------------------- | ------------------------------- |
| Example-based tests   | Property-based tests | Limited input coverage          |
| Type hints            | Static types         | Incomplete type safety          |
| Manual exhaustiveness | Compiler-enforced    | Pattern match warnings possible |

______________________________________________________________________

## 4. Proof Boundary Verification

### 4.1 Current Approach: Unit Tests + Types

**What we test:**

- Effect runner correctly executes programs
- Composite interpreter routes effects correctly
- All errors wrapped in Result types
- Exhaustive pattern matching

**Example: Runner test**

```python
# example code
async def test_run_program_wraps_interpreter_failure() -> None:
    """Verify runner converts exceptions to InterpreterFailure."""
    def failing_program() -> Generator[AllEffects, object, str]:
        yield GetPatientById(patient_id=uuid4())
        return "Should not reach"

    failing_interpreter = AsyncMock()
    failing_interpreter.handle.side_effect = Exception("Database down")

    result = await run_program(failing_program(), failing_interpreter)

    assert isinstance(result, Err)
    assert isinstance(result.error, InterpreterFailure)
    assert "Database down" in result.error.message
```

### 4.2 Target Approach: TLA+ Model Checking

In target architecture, proof boundary has TLA+ specifications:

```tla
--------------------------- MODULE EffectRunner ---------------------------
EXTENDS Naturals, Sequences

VARIABLES
  programState,    \* "running" | "completed" | "failed"
  effectQueue,     \* Sequence of effects to process
  currentEffect,   \* Currently executing effect
  result           \* Final result

Init ==
  /\ programState = "running"
  /\ effectQueue = <<>>
  /\ currentEffect = Nil
  /\ result = Nil

\* Safety: Never lose an effect
EffectsPreserved == \A e \in effectQueue : EventuallyProcessed(e)

\* Safety: Errors always wrapped
ErrorsWrapped == programState = "failed" => result \in InterpreterFailure

\* Liveness: Programs eventually complete
EventualCompletion == <>(programState \in {"completed", "failed"})
============================================================================
```

### 4.3 Gap Analysis

| Current (Python)      | Target (TLA+ + Rust)       | Gap                          |
| --------------------- | -------------------------- | ---------------------------- |
| Unit tests            | Model checking             | Limited state space coverage |
| Runtime type checking | Compile-time + conformance | Errors caught at runtime     |
| Mocked interpreters   | Verified against spec      | Mocks may not match reality  |

______________________________________________________________________

## 5. Outside Boundary Verification

### 5.1 Current Approach: Integration Tests

**What we test:**

- PostgreSQL operations behave as expected
- Redis pub/sub delivers messages
- Pulsar message ordering preserved
- FastAPI routing works correctly

**Example: Repository integration test**

```python
# test example
@pytest.mark.integration
async def test_patient_repository_crud(
    patient_repository: PatientRepository,
    test_patient: Patient,
) -> None:
    """Validate PostgreSQL CRUD assumptions."""
    # ASSUMPTION: PostgreSQL correctly stores and retrieves data
    created = await patient_repository.create(test_patient)
    assert created.id == test_patient.id

    # ASSUMPTION: PostgreSQL returns None for missing records
    retrieved = await patient_repository.get_by_id(test_patient.id)
    assert retrieved is not None
    assert retrieved.first_name == test_patient.first_name

    # ASSUMPTION: PostgreSQL deletes cascade correctly
    deleted = await patient_repository.delete(test_patient.id)
    assert deleted is True

    missing = await patient_repository.get_by_id(test_patient.id)
    assert missing is None
```

### 5.2 Target Approach: Runtime Monitoring

Outside boundary assumptions cannot be formally verified. Target approach:

1. **Integration tests**: Validate assumptions in test environment
1. **Health checks**: Continuously validate connectivity
1. **Metrics**: Track assumption-dependent operations
1. **Alerting**: Detect assumption violations in production

### 5.3 Assumption Coverage Matrix

| Assumption      | Test Coverage           | Health Check     | Monitoring                  |
| --------------- | ----------------------- | ---------------- | --------------------------- |
| PostgreSQL ACID | `test_repositories.py`  | `/health/db`     | Transaction rollback rate   |
| Redis pub/sub   | `test_notifications.py` | `/health/redis`  | Message delivery lag        |
| Pulsar delivery | `test_messaging.py`     | `/health/pulsar` | Consumer lag                |
| JWT signing     | `test_auth.py`          | N/A              | Token verification failures |

______________________________________________________________________

## 6. Verification Workflow

### 6.1 Developer Workflow

```text
# example
1. Write/modify code
2. Run unit tests (purity + proof boundary)
   docker compose exec healthhub poetry run pytest tests/pytest/backend/
3. Run integration tests (outside boundary)
   docker compose exec healthhub poetry run pytest tests/pytest/integration/
4. Run type checker (all boundaries)
   docker compose exec healthhub poetry run check-code
```

### 6.2 CI Pipeline

```yaml
# CI pipeline for verification
jobs:
  verify:
    steps:
      # Purity + Proof boundary
      - name: Unit tests
        run: poetry run pytest tests/pytest/backend/ -v

      - name: Type checking
        run: poetry run mypy .

      # Outside boundary
      - name: Integration tests
        run: poetry run pytest tests/pytest/integration/ -v
        env:
          DATABASE_URL: postgres://...
          REDIS_URL: redis://...
```

### 6.3 Production Verification

| Boundary | Technique                           | Frequency  |
| -------- | ----------------------------------- | ---------- |
| Purity   | N/A (verified at compile/test time) | -          |
| Proof    | Canary deployments                  | Per deploy |
| Outside  | Health checks, metrics              | Continuous |

______________________________________________________________________

## 7. Verification Checklist

### 7.1 Before Merge

- [ ] All unit tests pass (`tests/pytest/backend/`)
- [ ] All integration tests pass (`tests/pytest/integration/`)
- [ ] Type checker passes (`poetry run check-code`)
- [ ] No new `type: ignore` or `cast()`
- [ ] New assumptions documented in `external_assumptions.md`

### 7.2 Before Deploy

- [ ] CI pipeline green
- [ ] Health checks passing in staging
- [ ] Metrics baseline established

### 7.3 After Deploy

- [ ] Health checks passing in production
- [ ] No spike in error rates
- [ ] Assumption-dependent metrics within bounds

______________________________________________________________________

## Cross-References

- [Boundary Model](../../../../documents/engineering/boundary_model.md) - Verification framework
- [Boundary Map](boundary_map.md) - Component classifications
- [External Assumptions](external_assumptions.md) - What we're validating
- [Testing Standards](../../../../documents/engineering/testing.md) - Test patterns
- [Testing Architecture](../../../../documents/engineering/testing_architecture.md) - Test organization
