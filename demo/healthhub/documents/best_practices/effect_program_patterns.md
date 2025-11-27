# Effect Program Patterns

> Pure functional effect program patterns and anti-patterns.

---

## Principle

Programs should be pure generators that yield effect descriptions without executing them.

---

## Patterns

### Pattern 1: Generator-Based Programs

```python
def greet_patient(
    patient_id: UUID
) -> Generator[AllEffects, object, str]:
    # Yield effect, receive result
    patient = yield GetPatientById(patient_id=patient_id)

    # Type narrowing
    if not isinstance(patient, Patient):
        return "Patient not found"

    return f"Hello {patient.first_name}!"
```

---

### Pattern 2: Type Narrowing After Effects

Always narrow union types after receiving effect results:

```python
# GOOD - Explicit type narrowing
patient = yield GetPatientById(patient_id=patient_id)
if not isinstance(patient, Patient):
    return None

# Now `patient` is known to be Patient type
name = patient.first_name  # Safe to access
```

---

### Pattern 3: Fire-and-Forget Notifications

Notifications should not block workflow completion:

```python
def schedule_appointment_program(...) -> Generator[AllEffects, object, Appointment]:
    # Core workflow
    appointment = yield CreateAppointment(...)

    # Fire-and-forget (don't check result)
    yield PublishWebSocketNotification(...)

    # Continue regardless of notification success
    return appointment
```

---

### Pattern 4: Program Composition with yield from

Delegate to sub-programs:

```python
def complete_visit_program(
    appointment_id: UUID,
    notes: str,
    actor_id: UUID,
) -> Generator[AllEffects, object, Invoice | None]:
    # Delegate to transition program
    result = yield from transition_appointment_program(
        appointment_id,
        Completed(completed_at=datetime.now(UTC), notes=notes),
        actor_id,
    )

    if isinstance(result, TransitionInvalid):
        return None

    # Create invoice after successful completion
    invoice = yield CreateInvoice(...)
    return invoice
```

---

### Pattern 5: Early Return on Failure

```python
def create_prescription_program(
    patient_id: UUID,
    doctor_auth: DoctorAuthorized,
    medication: str,
    ...
) -> Generator[AllEffects, object, Prescription | None]:
    # Early return if no prescribing authority
    if not doctor_auth.can_prescribe:
        return None

    # Early return if patient not found
    patient = yield GetPatientById(patient_id=patient_id)
    if not isinstance(patient, Patient):
        return None

    # Early return on severe interaction
    check = yield CheckMedicationInteractions(medications=[medication])
    if isinstance(check, MedicationInteractionWarning) and check.severity == "severe":
        return None

    # All checks passed - create prescription
    prescription = yield CreatePrescription(...)
    return prescription
```

---

### Pattern 6: Audit Logging Pattern

Log all PHI access for HIPAA compliance.

**Healthcare Context**: See [HIPAA Compliance](../domain/hipaa_compliance.md) for complete audit logging requirements.

```python
def view_patient_program(
    patient_id: UUID,
    actor_id: UUID,
    ip_address: str | None,
) -> Generator[AllEffects, object, Patient | None]:
    patient = yield GetPatientById(patient_id=patient_id)

    # Log regardless of success (HIPAA requirement)
    yield LogAuditEvent(
        user_id=actor_id,
        action="view_patient",
        resource_type="patient",
        resource_id=patient_id,
        ip_address=ip_address,
        metadata={"status": "found" if patient else "not_found"},
        ...
    )

    return patient if isinstance(patient, Patient) else None
```

**HIPAA Requirement**: All Protected Health Information (PHI) access must be logged with who, what, when, why, and from where.

---

## Anti-Patterns

### Anti-Pattern 1: Direct Infrastructure Calls

```python
# BAD - Calls infrastructure directly
async def greet_patient(db, patient_id):
    row = await db.fetchrow("SELECT * FROM patients WHERE id = $1", patient_id)
    return f"Hello {row['first_name']}"

# GOOD - Yields effect
def greet_patient(patient_id) -> Generator[AllEffects, object, str]:
    patient = yield GetPatientById(patient_id=patient_id)
    if not isinstance(patient, Patient):
        return "Not found"
    return f"Hello {patient.first_name}"
```

---

### Anti-Pattern 2: Missing Type Narrowing

```python
# BAD - No type narrowing
patient = yield GetPatientById(patient_id=patient_id)
name = patient.first_name  # patient could be None!

# GOOD - Explicit narrowing
patient = yield GetPatientById(patient_id=patient_id)
if not isinstance(patient, Patient):
    return None
name = patient.first_name  # Safe
```

---

### Anti-Pattern 3: Silent Effect Failures

```python
# BAD - Ignoring None results
patient = yield GetPatientById(patient_id=patient_id)
# Continues even if patient is None

# GOOD - Handle all cases
patient = yield GetPatientById(patient_id=patient_id)
if not isinstance(patient, Patient):
    return None  # Explicit failure handling
```

---

### Anti-Pattern 4: Blocking on Notification Failure

```python
# BAD - Notification failure blocks workflow
result = yield PublishWebSocketNotification(...)
if isinstance(result, PublishFailed):
    return None  # Workflow fails because notification failed

# GOOD - Fire-and-forget
yield PublishWebSocketNotification(...)
# Continue regardless
```

---

### Anti-Pattern 5: Imperative Loops in Programs

```python
# BAD - for loop in program
def process_all_patients(patient_ids):
    results = []
    for pid in patient_ids:  # Imperative loop
        patient = yield GetPatientById(patient_id=pid)
        results.append(patient)
    return results

# GOOD - Use separate program per item
def process_patient(patient_id) -> Generator[...]:
    return (yield GetPatientById(patient_id=patient_id))

# Call from runner with comprehension
results = [await run_program(process_patient(pid), interp) for pid in patient_ids]
```

---

### Anti-Pattern 6: Skipping Validation

**Healthcare Context**: See [Medical State Machines](../domain/medical_state_machines.md) for transition validation requirements.

```python
# BAD - No transition validation
def complete_appointment(appointment_id):
    appointment = yield GetAppointmentById(appointment_id=appointment_id)
    # Directly transitions without validation
    yield UpdateAppointmentStatus(appointment_id, "completed")

# GOOD - Validate transition
def complete_appointment(appointment_id):
    appointment = yield GetAppointmentById(appointment_id=appointment_id)
    result = yield TransitionAppointmentStatus(
        appointment_id=appointment_id,
        new_status=Completed(...),
        actor_id=...,
    )
    # TransitionAppointmentStatus validates internally
```

**Medical Safety**: State transitions must be validated to prevent dangerous scenarios (e.g., dispensing medication before doctor approval).

---

## Testing Effect Programs

```python
def test_greet_patient_success() -> None:
    gen = greet_patient(PATIENT_ID)

    # Step 1: Effect
    effect = next(gen)
    assert isinstance(effect, GetPatientById)
    assert effect.patient_id == PATIENT_ID

    # Step 2: Send result, get return value
    try:
        gen.send(mock_patient)
    except StopIteration as e:
        assert e.value == f"Hello {mock_patient.first_name}!"

def test_greet_patient_not_found() -> None:
    gen = greet_patient(INVALID_ID)

    effect = next(gen)
    assert isinstance(effect, GetPatientById)

    try:
        gen.send(None)  # Patient not found
    except StopIteration as e:
        assert e.value == "Patient not found"
```

---

## Related Documentation

### Domain Knowledge
- [HIPAA Compliance](../domain/hipaa_compliance.md) - Audit logging requirements for PHI access
- [Medical State Machines](../domain/medical_state_machines.md) - Transition validation requirements

### HealthHub Implementation
- [Architecture Overview](../product/architecture_overview.md) - System architecture and program execution flow
- [Effects Reference](../product/effects_reference.md) - Complete effect catalog

### Best Practices
- [State Machine Patterns](state_machine_patterns.md) - ADT-based state machine implementation
- [Testing Doctrine](testing_doctrine.md) - Comprehensive testing patterns including generator testing

---

**Last Updated**: 2025-11-26
**Maintainer**: HealthHub Team
