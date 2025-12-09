# Appointments Feature

**Status**: Authoritative source
**Supersedes**: none
**Referenced by**: demo/healthhub/documents/tutorials/README.md

> **Purpose**: Complete reference for HealthHub appointment system: AppointmentStatus state machine, valid transitions, scheduling workflows, and execution workflows.

> **Core Doctrines**: For comprehensive patterns, see:
> - [ADTs and Result Types](../../../../../documents/tutorials/adts_and_results.md)
> - [Effect Patterns - State Machines](../../../../../documents/engineering/effect_patterns.md#state-machines)
> - [Code Quality](../../../../../documents/engineering/code_quality.md)

## Prerequisites

- Docker workflow running; commands executed via `docker compose -f docker/docker-compose.yml`.
- Completed [Intermediate Journey](../01_journeys/intermediate_journey.md).
- Familiarity with state machines, ADTs, Python type hints, pattern matching.

## Learning Objectives

- Define AppointmentStatus ADT with 5 variants (Requested, Confirmed, InProgress, Completed, Cancelled)
- Implement valid state transitions and terminal states
- Write transition validation function (prevent invalid state changes)
- Execute scheduling workflows (patient requests, doctor confirms)
- Execute appointment workflows (start, complete with notes)
- Handle cancellation from non-terminal states
- Write e2e tests for all state transitions

## Overview

**Appointment Lifecycle**:
1. **Requested**: Patient requests appointment (initial state)
2. **Confirmed**: Doctor confirms appointment time
3. **InProgress**: Doctor starts appointment (patient present)
4. **Completed**: Doctor completes appointment with notes (terminal state)
5. **Cancelled**: Appointment cancelled by patient or doctor (terminal state)

**State Machine Diagram**:
```
Requested → Confirmed → InProgress → Completed (terminal)
    ↓           ↓           ↓
Cancelled   Cancelled   Cancelled (terminal)
```

**Terminal States**: Once an appointment reaches `Completed` or `Cancelled`, no further transitions are allowed.

## Domain Models

### Appointment Model

**File**: `demo/healthhub/backend/app/domain/appointments.py`

```python
# file: demo/healthhub/backend/app/domain/appointments.py
from dataclasses import dataclass
from uuid import UUID
from datetime import datetime

@dataclass(frozen=True)
class Appointment:
    """
    Appointment between patient and doctor.

    Fields:
    - appointment_id: Unique identifier
    - patient_id: Links to patients table
    - doctor_id: Links to doctors table
    - scheduled_time: When appointment is scheduled
    - reason: Patient's reason for visit
    - status: Current state (AppointmentStatus ADT)
    - created_at: When appointment was requested
    - updated_at: Last status change timestamp
    """
    appointment_id: UUID
    patient_id: UUID
    doctor_id: UUID
    scheduled_time: datetime
    reason: str
    status: "AppointmentStatus"
    created_at: datetime
    updated_at: datetime
```

### AppointmentStatus ADT

**File**: `demo/healthhub/backend/app/domain/appointments.py`

```python
# file: demo/healthhub/backend/app/domain/appointments.py
from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True)
class Requested:
    """
    Appointment requested by patient.

    Context:
    - requested_at: Timestamp when patient requested appointment
    """
    requested_at: datetime

@dataclass(frozen=True)
class Confirmed:
    """
    Appointment confirmed by doctor.

    Context:
    - confirmed_at: Timestamp when doctor confirmed appointment
    - confirmed_by_doctor_id: Which doctor confirmed (for audit trail)
    """
    confirmed_at: datetime
    confirmed_by_doctor_id: UUID

@dataclass(frozen=True)
class InProgress:
    """
    Appointment in progress (patient present, doctor started).

    Context:
    - started_at: Timestamp when appointment started
    """
    started_at: datetime

@dataclass(frozen=True)
class Completed:
    """
    Appointment completed by doctor (terminal state).

    Context:
    - completed_at: Timestamp when appointment completed
    - notes: Doctor's notes (diagnosis, recommendations, prescriptions)

    Terminal: No further transitions allowed.
    """
    completed_at: datetime
    notes: str

@dataclass(frozen=True)
class Cancelled:
    """
    Appointment cancelled by patient or doctor (terminal state).

    Context:
    - cancelled_at: Timestamp when appointment cancelled
    - cancelled_by: Who cancelled ("patient" | "doctor")
    - reason: Cancellation reason

    Terminal: No further transitions allowed.
    """
    cancelled_at: datetime
    cancelled_by: str  # "patient" | "doctor"
    reason: str

type AppointmentStatus = (
    Requested
    | Confirmed
    | InProgress
    | Completed
    | Cancelled
)
```

**Why 5 variants?**
1. **Requested**: Initial state, carries `requested_at` timestamp
2. **Confirmed**: Doctor approved, carries `confirmed_at` and `confirmed_by_doctor_id`
3. **InProgress**: Appointment started, carries `started_at`
4. **Completed**: Terminal state, carries `completed_at` and doctor's notes
5. **Cancelled**: Terminal state, carries `cancelled_at`, `cancelled_by`, and cancellation reason

**Benefits over string status**:
- **Type-safe**: MyPy enforces exhaustive pattern matching
- **Context-rich**: Each variant carries state-specific data
- **Terminal states explicit**: Type system prevents transitions from terminal states
- **Self-documenting**: All valid states visible in type definition

## State Transition Validation

**File**: `demo/healthhub/backend/app/domain/appointments.py`

```python
# file: demo/healthhub/backend/app/domain/appointments.py
from typing import Type

def validate_transition(
    current: AppointmentStatus,
    target: Type[AppointmentStatus]
) -> bool:
    """
    Validate appointment state transition.

    Rules:
    - Requested → Confirmed, Cancelled
    - Confirmed → InProgress, Cancelled
    - InProgress → Completed, Cancelled
    - Completed → (terminal, no transitions)
    - Cancelled → (terminal, no transitions)

    Returns True if transition is valid, False otherwise.
    """

    match current:
        case Requested():
            # From Requested: Can confirm or cancel
            return target in (Confirmed, Cancelled)

        case Confirmed():
            # From Confirmed: Can start or cancel
            return target in (InProgress, Cancelled)

        case InProgress():
            # From InProgress: Can complete or cancel
            return target in (Completed, Cancelled)

        case Completed() | Cancelled():
            # Terminal states: No transitions allowed
            return False

def is_terminal_state(status: AppointmentStatus) -> bool:
    """
    Check if appointment status is terminal (no further transitions).
    """
    match status:
        case Completed() | Cancelled():
            return True
        case _:
            return False
```

**Usage in programs**:
```python
# file: demo/healthhub/backend/app/programs/appointment_programs.py
def confirm_appointment_program(appointment_id: UUID) -> Generator[Effect, Result, Result[dict]]:
    """
    Confirm appointment (transition Requested → Confirmed).
    """

    # Fetch current appointment
    appointment_result = yield DatabaseEffect.Query(
        query="SELECT * FROM appointments WHERE appointment_id = $1",
        params=(appointment_id,)
    )

    match appointment_result:
        case Ok(rows) if len(rows) > 0:
            appointment = rows[0]
        case _:
            return Err("Appointment not found")

    # Validate transition
    current_status = appointment["status"]  # Deserialized to AppointmentStatus ADT

    if not validate_transition(current_status, Confirmed):
        return Err(f"Invalid transition from {type(current_status).__name__} to Confirmed")

    # Perform transition
    new_status = Confirmed(
        confirmed_at=datetime.now(timezone.utc),
        confirmed_by_doctor_id=doctor_id
    )

    update_result = yield DatabaseEffect.Execute(
        query="""
            UPDATE appointments
            SET status = $1, updated_at = $2
            WHERE appointment_id = $3
        """,
        params=(serialize_status(new_status), datetime.now(timezone.utc), appointment_id)
    )

    match update_result:
        case Ok(_):
            return Ok({"appointment_id": appointment_id, "status": new_status})
        case Err(error):
            return Err(f"Failed to update appointment: {error}")
```

## Scheduling Workflows

### Workflow 1: Patient Requests Appointment

**Endpoint**: `POST /api/appointments`

**Request**:
```json
{
  "patient_id": "30000000-0000-0000-0000-000000000001",
  "doctor_id": "40000000-0000-0000-0000-000000000001",
  "scheduled_time": "2025-12-15T10:00:00Z",
  "reason": "Annual physical examination"
}
```

**Program**: `demo/healthhub/backend/app/programs/appointment_programs.py`

```python
# file: demo/healthhub/backend/app/programs/appointment_programs.py
def request_appointment_program(
    patient_id: UUID,
    doctor_id: UUID,
    scheduled_time: datetime,
    reason: str
) -> Generator[Effect, Result, Result[dict]]:
    """
    Patient requests new appointment (initial state: Requested).
    """

    # Validate patient exists
    patient_result = yield DatabaseEffect.Query(
        query="SELECT patient_id FROM patients WHERE patient_id = $1",
        params=(patient_id,)
    )

    match patient_result:
        case Ok(rows) if len(rows) > 0:
            pass  # Patient exists
        case _:
            return Err("Patient not found")

    # Validate doctor exists
    doctor_result = yield DatabaseEffect.Query(
        query="SELECT doctor_id FROM doctors WHERE doctor_id = $1",
        params=(doctor_id,)
    )

    match doctor_result:
        case Ok(rows) if len(rows) > 0:
            pass  # Doctor exists
        case _:
            return Err("Doctor not found")

    # Create appointment with Requested status
    appointment_id = uuid4()
    initial_status = Requested(requested_at=datetime.now(timezone.utc))

    insert_result = yield DatabaseEffect.Execute(
        query="""
            INSERT INTO appointments (appointment_id, patient_id, doctor_id, scheduled_time, reason, status, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """,
        params=(
            appointment_id,
            patient_id,
            doctor_id,
            scheduled_time,
            reason,
            serialize_status(initial_status),
            datetime.now(timezone.utc),
            datetime.now(timezone.utc),
        )
    )

    match insert_result:
        case Ok(_):
            return Ok({
                "appointment_id": appointment_id,
                "status": initial_status,
            })
        case Err(error):
            return Err(f"Failed to create appointment: {error}")
```

**RBAC**: Patients can only request appointments for themselves, doctors/admins can request on behalf of patients.

### Workflow 2: Doctor Confirms Appointment

**Endpoint**: `POST /api/appointments/{appointment_id}/confirm`

**Program**:
```python
# file: demo/healthhub/backend/app/programs/appointment_programs.py
def confirm_appointment_program(
    appointment_id: UUID,
    doctor_id: UUID
) -> Generator[Effect, Result, Result[dict]]:
    """
    Doctor confirms appointment (transition Requested → Confirmed).
    """

    # Fetch appointment
    appointment_result = yield DatabaseEffect.Query(
        query="SELECT * FROM appointments WHERE appointment_id = $1",
        params=(appointment_id,)
    )

    match appointment_result:
        case Ok(rows) if len(rows) > 0:
            appointment = rows[0]
        case _:
            return Err("Appointment not found")

    # Validate transition
    current_status = deserialize_status(appointment["status"])

    if not validate_transition(current_status, Confirmed):
        return Err(f"Cannot confirm appointment in {type(current_status).__name__} state")

    # Perform transition
    new_status = Confirmed(
        confirmed_at=datetime.now(timezone.utc),
        confirmed_by_doctor_id=doctor_id
    )

    update_result = yield DatabaseEffect.Execute(
        query="""
            UPDATE appointments
            SET status = $1, updated_at = $2
            WHERE appointment_id = $3
        """,
        params=(serialize_status(new_status), datetime.now(timezone.utc), appointment_id)
    )

    match update_result:
        case Ok(_):
            # Trigger notification (fire-and-forget)
            _ = yield NotificationEffect.SendPatientNotification(
                patient_id=appointment["patient_id"],
                notification_type="appointment_confirmed",
                message=f"Your appointment has been confirmed for {appointment['scheduled_time']}",
            )

            return Ok({
                "appointment_id": appointment_id,
                "status": new_status,
            })
        case Err(error):
            return Err(f"Failed to confirm appointment: {error}")
```

**RBAC**: Only doctors can confirm appointments (enforced by AuthorizationState ADT).

## Execution Workflows

### Workflow 3: Doctor Starts Appointment

**Endpoint**: `POST /api/appointments/{appointment_id}/start`

**Program**:
```python
# file: demo/healthhub/backend/app/programs/appointment_programs.py
def start_appointment_program(appointment_id: UUID) -> Generator[Effect, Result, Result[dict]]:
    """
    Doctor starts appointment (transition Confirmed → InProgress).
    """

    # Fetch appointment
    appointment_result = yield DatabaseEffect.Query(
        query="SELECT * FROM appointments WHERE appointment_id = $1",
        params=(appointment_id,)
    )

    match appointment_result:
        case Ok(rows) if len(rows) > 0:
            appointment = rows[0]
        case _:
            return Err("Appointment not found")

    # Validate transition
    current_status = deserialize_status(appointment["status"])

    if not validate_transition(current_status, InProgress):
        return Err(f"Cannot start appointment in {type(current_status).__name__} state")

    # Perform transition
    new_status = InProgress(started_at=datetime.now(timezone.utc))

    update_result = yield DatabaseEffect.Execute(
        query="""
            UPDATE appointments
            SET status = $1, updated_at = $2
            WHERE appointment_id = $3
        """,
        params=(serialize_status(new_status), datetime.now(timezone.utc), appointment_id)
    )

    match update_result:
        case Ok(_):
            return Ok({
                "appointment_id": appointment_id,
                "status": new_status,
            })
        case Err(error):
            return Err(f"Failed to start appointment: {error}")
```

**RBAC**: Only doctors can start appointments.

### Workflow 4: Doctor Completes Appointment

**Endpoint**: `POST /api/appointments/{appointment_id}/complete`

**Request**:
```json
{
  "notes": "Patient presented with stable blood pressure (120/80). Lungs clear, heart rate normal. Recommended annual follow-up. Prescribed Lisinopril 10mg daily."
}
```

**Program**:
```python
# file: demo/healthhub/backend/app/programs/appointment_programs.py
def complete_appointment_program(
    appointment_id: UUID,
    notes: str
) -> Generator[Effect, Result, Result[dict]]:
    """
    Doctor completes appointment with notes (transition InProgress → Completed).

    Terminal state: No further transitions allowed.
    """

    # Fetch appointment
    appointment_result = yield DatabaseEffect.Query(
        query="SELECT * FROM appointments WHERE appointment_id = $1",
        params=(appointment_id,)
    )

    match appointment_result:
        case Ok(rows) if len(rows) > 0:
            appointment = rows[0]
        case _:
            return Err("Appointment not found")

    # Validate transition
    current_status = deserialize_status(appointment["status"])

    if not validate_transition(current_status, Completed):
        return Err(f"Cannot complete appointment in {type(current_status).__name__} state")

    # Perform transition to terminal state
    new_status = Completed(
        completed_at=datetime.now(timezone.utc),
        notes=notes
    )

    update_result = yield DatabaseEffect.Execute(
        query="""
            UPDATE appointments
            SET status = $1, updated_at = $2
            WHERE appointment_id = $3
        """,
        params=(serialize_status(new_status), datetime.now(timezone.utc), appointment_id)
    )

    match update_result:
        case Ok(_):
            # Trigger notification (fire-and-forget)
            _ = yield NotificationEffect.SendPatientNotification(
                patient_id=appointment["patient_id"],
                notification_type="appointment_completed",
                message="Your appointment has been completed. Notes are available in your portal.",
            )

            return Ok({
                "appointment_id": appointment_id,
                "status": new_status,
            })
        case Err(error):
            return Err(f"Failed to complete appointment: {error}")
```

**Terminal State**: Once completed, appointment cannot transition to any other state.

## Cancellation Workflow

### Workflow 5: Cancel Appointment

**Endpoint**: `POST /api/appointments/{appointment_id}/cancel`

**Request**:
```json
{
  "reason": "Patient requested reschedule due to conflict"
}
```

**Program**:
```python
# file: demo/healthhub/backend/app/programs/appointment_programs.py
def cancel_appointment_program(
    appointment_id: UUID,
    cancelled_by: str,  # "patient" | "doctor"
    reason: str
) -> Generator[Effect, Result, Result[dict]]:
    """
    Cancel appointment (transition from any non-terminal state → Cancelled).

    Terminal state: No further transitions allowed.
    """

    # Fetch appointment
    appointment_result = yield DatabaseEffect.Query(
        query="SELECT * FROM appointments WHERE appointment_id = $1",
        params=(appointment_id,)
    )

    match appointment_result:
        case Ok(rows) if len(rows) > 0:
            appointment = rows[0]
        case _:
            return Err("Appointment not found")

    # Validate transition
    current_status = deserialize_status(appointment["status"])

    if not validate_transition(current_status, Cancelled):
        return Err(f"Cannot cancel appointment in {type(current_status).__name__} state")

    # Perform transition to terminal state
    new_status = Cancelled(
        cancelled_at=datetime.now(timezone.utc),
        cancelled_by=cancelled_by,
        reason=reason
    )

    update_result = yield DatabaseEffect.Execute(
        query="""
            UPDATE appointments
            SET status = $1, updated_at = $2
            WHERE appointment_id = $3
        """,
        params=(serialize_status(new_status), datetime.now(timezone.utc), appointment_id)
    )

    match update_result:
        case Ok(_):
            # Trigger notification
            if cancelled_by == "doctor":
                _ = yield NotificationEffect.SendPatientNotification(
                    patient_id=appointment["patient_id"],
                    notification_type="appointment_cancelled",
                    message=f"Your appointment has been cancelled. Reason: {reason}",
                )

            return Ok({
                "appointment_id": appointment_id,
                "status": new_status,
            })
        case Err(error):
            return Err(f"Failed to cancel appointment: {error}")
```

**RBAC**:
- Patients can cancel own appointments (any non-terminal state)
- Doctors can cancel any appointment (any non-terminal state)

## Status Serialization

**File**: `demo/healthhub/backend/app/domain/appointments.py`

```python
# file: demo/healthhub/backend/app/domain/appointments.py
import json

def serialize_status(status: AppointmentStatus) -> str:
    """
    Serialize AppointmentStatus ADT to JSON string for database storage.
    """
    match status:
        case Requested(requested_at=requested_at):
            return json.dumps({
                "type": "Requested",
                "requested_at": requested_at.isoformat()
            })
        case Confirmed(confirmed_at=confirmed_at, confirmed_by_doctor_id=doctor_id):
            return json.dumps({
                "type": "Confirmed",
                "confirmed_at": confirmed_at.isoformat(),
                "confirmed_by_doctor_id": str(doctor_id)
            })
        case InProgress(started_at=started_at):
            return json.dumps({
                "type": "InProgress",
                "started_at": started_at.isoformat()
            })
        case Completed(completed_at=completed_at, notes=notes):
            return json.dumps({
                "type": "Completed",
                "completed_at": completed_at.isoformat(),
                "notes": notes
            })
        case Cancelled(cancelled_at=cancelled_at, cancelled_by=cancelled_by, reason=reason):
            return json.dumps({
                "type": "Cancelled",
                "cancelled_at": cancelled_at.isoformat(),
                "cancelled_by": cancelled_by,
                "reason": reason
            })

def deserialize_status(status_json: str) -> AppointmentStatus:
    """
    Deserialize JSON string to AppointmentStatus ADT.
    """
    data = json.loads(status_json)

    match data["type"]:
        case "Requested":
            return Requested(requested_at=datetime.fromisoformat(data["requested_at"]))
        case "Confirmed":
            return Confirmed(
                confirmed_at=datetime.fromisoformat(data["confirmed_at"]),
                confirmed_by_doctor_id=UUID(data["confirmed_by_doctor_id"])
            )
        case "InProgress":
            return InProgress(started_at=datetime.fromisoformat(data["started_at"]))
        case "Completed":
            return Completed(
                completed_at=datetime.fromisoformat(data["completed_at"]),
                notes=data["notes"]
            )
        case "Cancelled":
            return Cancelled(
                cancelled_at=datetime.fromisoformat(data["cancelled_at"]),
                cancelled_by=data["cancelled_by"],
                reason=data["reason"]
            )
        case _:
            raise ValueError(f"Unknown status type: {data['type']}")
```

## E2E Tests

**File**: `demo/healthhub/tests/pytest/e2e/test_appointments.py`

```python
# file: demo/healthhub/tests/pytest/e2e/test_appointments.py
import pytest
from demo.healthhub.backend.app.programs.appointment_programs import (
    request_appointment_program,
    confirm_appointment_program,
    start_appointment_program,
    complete_appointment_program,
    cancel_appointment_program,
)
from demo.healthhub.backend.app.domain.appointments import Requested, Confirmed, InProgress, Completed, Cancelled
from effectful import Ok, Err

@pytest.mark.asyncio
async def test_complete_appointment_lifecycle(clean_healthhub_state, postgres_interpreter):
    """E2E: Complete appointment lifecycle (Requested → Confirmed → InProgress → Completed)."""

    # Step 1: Patient requests appointment
    request_program = request_appointment_program(
        patient_id=UUID("30000000-0000-0000-0000-000000000001"),
        doctor_id=UUID("40000000-0000-0000-0000-000000000001"),
        scheduled_time=datetime(2025, 12, 15, 10, 0, 0, tzinfo=timezone.utc),
        reason="Annual physical"
    )
    request_result = await postgres_interpreter.run(request_program)

    match request_result:
        case Ok(appointment):
            appointment_id = appointment["appointment_id"]
            assert isinstance(appointment["status"], Requested)
        case Err(error):
            pytest.fail(f"Failed to request appointment: {error}")

    # Step 2: Doctor confirms appointment
    confirm_program = confirm_appointment_program(appointment_id, doctor_id=UUID("40000000-0000-0000-0000-000000000001"))
    confirm_result = await postgres_interpreter.run(confirm_program)

    match confirm_result:
        case Ok(appointment):
            assert isinstance(appointment["status"], Confirmed)
        case Err(error):
            pytest.fail(f"Failed to confirm appointment: {error}")

    # Step 3: Doctor starts appointment
    start_program = start_appointment_program(appointment_id)
    start_result = await postgres_interpreter.run(start_program)

    match start_result:
        case Ok(appointment):
            assert isinstance(appointment["status"], InProgress)
        case Err(error):
            pytest.fail(f"Failed to start appointment: {error}")

    # Step 4: Doctor completes appointment
    complete_program = complete_appointment_program(appointment_id, notes="Patient in good health.")
    complete_result = await postgres_interpreter.run(complete_program)

    match complete_result:
        case Ok(appointment):
            assert isinstance(appointment["status"], Completed)
            assert "good health" in appointment["status"].notes
        case Err(error):
            pytest.fail(f"Failed to complete appointment: {error}")

@pytest.mark.asyncio
async def test_invalid_transition_prevented(clean_healthhub_state, postgres_interpreter):
    """E2E: Invalid transition (Requested → InProgress) is prevented."""

    # Create appointment in Requested state
    request_program = request_appointment_program(
        patient_id=UUID("30000000-0000-0000-0000-000000000001"),
        doctor_id=UUID("40000000-0000-0000-0000-000000000001"),
        scheduled_time=datetime(2025, 12, 15, 10, 0, 0, tzinfo=timezone.utc),
        reason="Test appointment"
    )
    request_result = await postgres_interpreter.run(request_program)

    match request_result:
        case Ok(appointment):
            appointment_id = appointment["appointment_id"]
        case Err(error):
            pytest.fail(f"Failed to request appointment: {error}")

    # Attempt invalid transition: Requested → InProgress (should fail)
    start_program = start_appointment_program(appointment_id)
    start_result = await postgres_interpreter.run(start_program)

    match start_result:
        case Err(error):
            assert "cannot start" in error.lower()
        case Ok(_):
            pytest.fail("Expected Err for invalid transition, got Ok")

@pytest.mark.asyncio
async def test_terminal_state_prevents_transitions(clean_healthhub_state, postgres_interpreter):
    """E2E: Terminal state (Completed) prevents further transitions."""

    # Create and complete appointment
    # ... (request → confirm → start → complete) ...

    # Attempt transition from terminal state: Completed → Cancelled (should fail)
    cancel_program = cancel_appointment_program(appointment_id, cancelled_by="patient", reason="Changed mind")
    cancel_result = await postgres_interpreter.run(cancel_program)

    match cancel_result:
        case Err(error):
            assert "cannot cancel" in error.lower()
        case Ok(_):
            pytest.fail("Expected Err for transition from terminal state, got Ok")
```

## Summary

**You have learned**:
- ✅ AppointmentStatus ADT with 5 variants (Requested, Confirmed, InProgress, Completed, Cancelled)
- ✅ State machine with valid transitions and terminal states
- ✅ Transition validation function (prevent invalid state changes)
- ✅ Scheduling workflows (request, confirm)
- ✅ Execution workflows (start, complete with notes)
- ✅ Cancellation from non-terminal states
- ✅ Status serialization/deserialization for database storage
- ✅ E2E testing for all transitions

**Key Takeaways**:
1. **ADT State Machines**: Each state variant carries state-specific context
2. **Transition Validation**: Centralized validation prevents invalid state changes
3. **Terminal States**: Type system enforces no transitions from terminal states
4. **Pattern Matching**: Exhaustive coverage ensures all states handled
5. **Context-Rich**: Status variants carry timestamps, notes, reasons
6. **Immutable**: Frozen dataclasses prevent accidental mutations

## Cross-References

- [Intermediate Journey - Appointment State Machine](../01_journeys/intermediate_journey.md#step-2-create-appointment-with-state-machine)
- [Effect Patterns - State Machines](../../../../../documents/engineering/effect_patterns.md#state-machines)
- [ADTs and Result Types](../../../../../documents/tutorials/adts_and_results.md)
- [Code Quality](../../../../../documents/engineering/code_quality.md)
- [Doctor Guide](../02_roles/doctor_guide.md)
- [Appointment Lifecycle Workflow](../04_workflows/appointment_lifecycle.md)
