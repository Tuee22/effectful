# Tutorial 08: Testing HealthHub

> Extends base [Tutorial 08: Messaging Effects](../../../../documents/tutorials/08_messaging_effects.md); base steps apply. This tutorial documents HealthHub-specific testing flows only.

---

## Overview

Delta-only. Full testing SSoT lives in base + engineering overlays; this tutorial just lists HealthHub-specific commands and layout.

**Read first**:
- Base: [Testing](../../../../documents/testing/README.md)
- Engineering: [Testing](../engineering/testing.md), [Audit Logging](../engineering/monitoring_and_alerting.md#audit-logging-observability) for PHI audit assertions

---

## Running Tests

```bash
# All tests
docker compose -f demo/healthhub/docker/docker-compose.yml exec healthhub poetry run test-all

# Unit tests only
docker compose -f demo/healthhub/docker/docker-compose.yml exec healthhub poetry run test-backend

# Integration tests only
docker compose -f demo/healthhub/docker/docker-compose.yml exec healthhub poetry run test-integration

# Specific test file
docker compose -f demo/healthhub/docker/docker-compose.yml exec healthhub poetry run pytest tests/pytest/backend/test_effects.py -v
```

---

## Testing Effect Programs

Effect programs are pure generators, making them easy to test by stepping through:

### Basic Pattern

```python
def test_schedule_appointment_success() -> None:
    # Create the generator
    gen = schedule_appointment_program(
        patient_id=PATIENT_ID,
        doctor_id=DOCTOR_ID,
        requested_time=datetime.now(UTC) + timedelta(days=7),
        reason="Annual checkup",
        actor_id=PATIENT_ID,
    )

    # Step 1: Expect GetPatientById
    effect = next(gen)
    assert isinstance(effect, GetPatientById)
    assert effect.patient_id == PATIENT_ID

    # Send mock patient, expect GetDoctorById
    effect = gen.send(mock_patient)
    assert isinstance(effect, GetDoctorById)
    assert effect.doctor_id == DOCTOR_ID

    # Send mock doctor, expect CreateAppointment
    effect = gen.send(mock_doctor)
    assert isinstance(effect, CreateAppointment)
    assert effect.patient_id == PATIENT_ID

    # Send mock appointment, expect notification
    effect = gen.send(mock_appointment)
    assert isinstance(effect, PublishWebSocketNotification)

    # Send notification result, expect audit log
    effect = gen.send(NotificationPublished(...))
    assert isinstance(effect, LogAuditEvent)

    # Send audit result, program completes
    try:
        gen.send(AuditEventLogged(...))
        pytest.fail("Should have completed")
    except StopIteration as e:
        assert e.value == mock_appointment
```

---

## Testing Error Paths

### Patient Not Found

```python
def test_schedule_appointment_patient_not_found() -> None:
    gen = schedule_appointment_program(
        patient_id=INVALID_PATIENT_ID,
        doctor_id=DOCTOR_ID,
        ...
    )

    # First effect: GetPatientById
    effect = next(gen)
    assert isinstance(effect, GetPatientById)

    # Send None (patient not found)
    try:
        gen.send(None)
        pytest.fail("Should have completed")
    except StopIteration as e:
        assert e.value is None  # Program returned None
```

### Invalid State Transition

```python
def test_transition_invalid() -> None:
    gen = transition_appointment_program(
        appointment_id=APPOINTMENT_ID,
        new_status=Completed(...),  # Invalid from Requested
        actor_id=DOCTOR_ID,
    )

    # Get appointment
    effect = next(gen)
    gen.send(Appointment(status=Requested(...), ...))

    # Attempt transition
    effect = gen.send(TransitionInvalid(
        current_status="Requested",
        attempted_status="Completed",
        reason="Cannot skip Confirmed state",
    ))

    # Verify program returns invalid result
    try:
        gen.send(...)
    except StopIteration as e:
        assert isinstance(e.value, TransitionInvalid)
```

---

## Testing Domain Models

### Appointment State Machine

```python
def test_valid_transition_requested_to_confirmed() -> None:
    current = Requested(requested_at=datetime.now(UTC))
    new = Confirmed(
        confirmed_at=datetime.now(UTC),
        scheduled_time=datetime.now(UTC) + timedelta(days=1),
    )

    result = validate_transition(current, new)
    assert isinstance(result, TransitionSuccess)

def test_invalid_transition_requested_to_completed() -> None:
    current = Requested(requested_at=datetime.now(UTC))
    new = Completed(completed_at=datetime.now(UTC), notes="Notes")

    result = validate_transition(current, new)
    assert isinstance(result, TransitionInvalid)
    assert "Cannot transition" in result.reason
```

### Authorization ADT

```python
def test_patient_authorized_has_patient_id() -> None:
    auth = PatientAuthorized(
        user_id=uuid4(),
        patient_id=PATIENT_ID,
        email="patient@example.com",
    )

    assert auth.patient_id == PATIENT_ID
    assert auth.role == "patient"

def test_doctor_authorized_prescribing_flag() -> None:
    auth = DoctorAuthorized(
        user_id=uuid4(),
        doctor_id=uuid4(),
        email="dr@example.com",
        specialization="Cardiology",
        can_prescribe=True,
    )

    assert auth.can_prescribe is True
```

---

## Integration Tests

Integration tests use real infrastructure:

```python
@pytest.fixture
async def pool() -> AsyncIterator[asyncpg.Pool]:
    pool = await asyncpg.create_pool(
        host="postgres",
        port=5432,
        database="healthhub_test",
        user="healthhub",
        password="healthhub_pass",
    )
    yield pool
    await pool.close()

@pytest.fixture
async def redis_client() -> AsyncIterator[redis.Redis]:
    client = redis.Redis(host="redis", port=6379, db=0)
    yield client
    await client.close()

async def test_create_appointment_integration(
    pool: asyncpg.Pool,
    redis_client: redis.Redis,
) -> None:
    interpreter = CompositeInterpreter(pool, redis_client)

    result = await run_program(
        schedule_appointment_program(
            patient_id=SEEDED_PATIENT_ID,
            doctor_id=SEEDED_DOCTOR_ID,
            requested_time=datetime.now(UTC) + timedelta(days=7),
            reason="Integration test",
            actor_id=SEEDED_PATIENT_ID,
        ),
        interpreter,
    )

    assert isinstance(result, Appointment)
    assert result.status == Requested(...)
```

---

## Test Fixtures

### Mock Entities

```python
PATIENT_ID = uuid4()
DOCTOR_ID = uuid4()

mock_patient = Patient(
    id=PATIENT_ID,
    user_id=uuid4(),
    first_name="Alice",
    last_name="Johnson",
    date_of_birth=date(1985, 6, 15),
    blood_type="A+",
    allergies=["Penicillin"],
    ...
)

mock_doctor = Doctor(
    id=DOCTOR_ID,
    user_id=uuid4(),
    first_name="John",
    last_name="Smith",
    specialization="Internal Medicine",
    license_number="MD12345",
    can_prescribe=True,
    ...
)
```

---

## Test Anti-Patterns to Avoid

| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| Using `pytest.skip()` | Tests exist for a reason | Fix or delete |
| Real DB in unit tests | Slow, flaky | Use pytest-mock |
| Missing error paths | Incomplete coverage | Test all branches |
| Partial assertions | May miss bugs | Assert all fields |
| Truncated output | Miss failures | Redirect to file |

---

## Code Quality Checks

Run before committing:

```bash
docker compose -f demo/healthhub/docker/docker-compose.yml exec healthhub poetry run check-code
```

This runs:
1. **Black**: Code formatting
2. **MyPy**: Strict type checking

Must pass with zero errors.

---

## Related Documentation

- [Testing Patterns](../engineering/testing_patterns.md)
- [Effect Patterns](../engineering/effect_patterns.md)
- [Architecture Overview](../product/architecture_overview.md)

---

**Last Updated**: 2025-11-25  
**Supersedes**: none  
**Referenced by**: ../README.md, ../engineering/testing.md
