# Tutorial 02: Scheduling Appointments

> Extends base [Tutorial 02: Effect Types](../../../../documents/tutorials/02_effect_types.md); base steps apply. This tutorial documents HealthHub-specific deltas only.

---

## Overview

Appointments follow a state machine:

```
Requested → Confirmed → InProgress → Completed
    ↓           ↓           ↓
 Cancelled  Cancelled   Cancelled
```

---

## Step 1: Request an Appointment (as Patient)

```bash
# Login as patient
TOKEN=$(curl -s -X POST http://localhost:8850/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "alice@example.com", "password": "patient123"}' | jq -r '.access_token')

# Request appointment
curl -X POST http://localhost:8850/api/v1/appointments \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": "<your_patient_id>",
    "doctor_id": "<doctor_id>",
    "requested_time": "2025-02-01T10:00:00Z",
    "reason": "Annual checkup"
  }'
```

**Response**: Appointment in `Requested` status

---

## Step 2: Confirm Appointment (as Doctor)

```bash
# Login as doctor
TOKEN=$(curl -s -X POST http://localhost:8850/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "dr.smith@example.com", "password": "doctor123"}' | jq -r '.access_token')

# Confirm the appointment
curl -X POST http://localhost:8850/api/v1/appointments/<appointment_id>/transition \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "new_status": "confirmed",
    "scheduled_time": "2025-02-01T10:00:00Z"
  }'
```

**Response**: Appointment in `Confirmed` status with scheduled time

---

## Step 3: Start the Visit (as Doctor)

```bash
curl -X POST http://localhost:8850/api/v1/appointments/<appointment_id>/transition \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"new_status": "in_progress"}'
```

---

## Step 4: Complete the Visit (as Doctor)

```bash
curl -X POST http://localhost:8850/api/v1/appointments/<appointment_id>/transition \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "new_status": "completed",
    "notes": "Patient in good health. Recommended annual follow-up."
  }'
```

---

## Understanding the Effect Program

The appointment workflow is implemented as an effect program:

```python
def schedule_appointment_program(
    patient_id: UUID,
    doctor_id: UUID,
    requested_time: datetime | None,
    reason: str,
    actor_id: UUID,
) -> Generator[AllEffects, object, Appointment | None]:
    # Step 1: Verify patient exists
    patient = yield GetPatientById(patient_id=patient_id)
    if not isinstance(patient, Patient):
        return None

    # Step 2: Verify doctor exists
    doctor = yield GetDoctorById(doctor_id=doctor_id)
    if not isinstance(doctor, Doctor):
        return None

    # Step 3: Create appointment
    appointment = yield CreateAppointment(
        patient_id=patient_id,
        doctor_id=doctor_id,
        requested_time=requested_time,
        reason=reason,
    )

    # Step 4: Notify doctor
    yield PublishWebSocketNotification(
        channel=f"doctor:{doctor_id}:notifications",
        message={"type": "appointment_requested", ...},
        recipient_id=doctor_id,
    )

    # Step 5: Log audit event
    yield LogAuditEvent(
        user_id=actor_id,
        action="create_appointment",
        resource_type="appointment",
        resource_id=appointment.id,
        ...
    )

    return appointment
```

---

## Transition Validation

The state machine validates all transitions:

```python
# Valid: Requested → Confirmed
result = validate_transition(
    Requested(requested_at=now),
    Confirmed(confirmed_at=now, scheduled_time=scheduled)
)
assert isinstance(result, TransitionSuccess)

# Invalid: Requested → Completed (must go through Confirmed first)
result = validate_transition(
    Requested(requested_at=now),
    Completed(completed_at=now, notes="Notes")
)
assert isinstance(result, TransitionInvalid)
```

---

## Cancellation

Any non-terminal status can be cancelled:

```bash
curl -X POST http://localhost:8850/api/v1/appointments/<appointment_id>/transition \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "new_status": "cancelled",
    "reason": "Patient requested cancellation"
  }'
```

---

## Real-Time Notifications

When appointments are created or transitioned, notifications are sent via WebSocket:

```javascript
// Connect to WebSocket
const ws = new WebSocket('wss://localhost:8850/ws/<user_id>');

ws.onmessage = (event) => {
    const notification = JSON.parse(event.data);
    if (notification.type === 'appointment_status_changed') {
        console.log(`Appointment ${notification.appointment_id} is now ${notification.new_status}`);
    }
};
```

---

## Next Steps

- [Tutorial 03: Creating Prescriptions](03_prescriptions.md)
- [Appointment State Machine](../product/appointment_state_machine.md)
- [Effects Reference](../product/effects_reference.md)

---

**Last Updated**: 2025-11-25  
**Supersedes**: none  
**Referenced by**: ../README.md
