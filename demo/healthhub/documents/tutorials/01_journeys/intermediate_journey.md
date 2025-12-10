# Intermediate Journey

**Status**: Authoritative source (HealthHub tutorial patterns)
**Supersedes**: none
**Referenced by**: demo/healthhub/documents/tutorials/README.md

> **Purpose**: Tutorial on HealthHub state machines, effect programs, and multi-step workflows including appointments, prescriptions, and lab results.

> **Core Doctrines**: For comprehensive patterns, see:
> - [Effect Types](../../../../../documents/tutorials/effect_types.md)
> - [Effect Patterns](../../../../../documents/engineering/effect_patterns.md)
> - [Code Quality](../../../../../documents/engineering/code_quality.md)

## Prerequisites

- Completed [Beginner Journey](beginner_journey.md)
- Docker workflow running
- Familiarity with Python generators and `yield` syntax
- Understanding of [Effect Types tutorial](../../../../../documents/tutorials/effect_types.md)

## Learning Objectives

- Schedule and manage appointments using state machine
- Understand state transition validation (prevent invalid state changes)
- Create prescriptions with medication interaction checking
- Process lab results with critical value alerts
- Write and test effect programs using generator pattern
- Trace data flow through effect programs

## Step 1: Understand Appointment State Machine

**State machine diagram**:

```
Requested → Confirmed → InProgress → Completed
    ↓           ↓           ↓
Cancelled   Cancelled   Cancelled
```

**Valid transitions**:
- `Requested` → `Confirmed` (doctor confirms appointment)
- `Requested` → `Cancelled` (patient or doctor cancels)
- `Confirmed` → `InProgress` (doctor starts appointment)
- `Confirmed` → `Cancelled` (patient or doctor cancels before start)
- `InProgress` → `Completed` (doctor completes with notes)
- `InProgress` → `Cancelled` (emergency cancellation during appointment)

**Terminal states** (no further transitions allowed):
- `Completed`: Appointment successfully finished
- `Cancelled`: Appointment terminated

**Invalid transitions** (prevented by code):
- `Completed` → any state (terminal state)
- `Cancelled` → any state (terminal state)
- `Requested` → `InProgress` (must confirm first)
- `Requested` → `Completed` (must go through workflow)

**Open file**: `demo/healthhub/backend/app/domain/appointment.py`

**AppointmentStatus ADT**:
```python
# file: demo/healthhub/backend/app/domain/appointment.py
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

@dataclass(frozen=True)
class Requested:
    """Appointment requested, awaiting confirmation."""
    requested_at: datetime

@dataclass(frozen=True)
class Confirmed:
    """Appointment confirmed and scheduled."""
    confirmed_at: datetime
    scheduled_time: datetime

@dataclass(frozen=True)
class InProgress:
    """Appointment currently in progress."""
    started_at: datetime

@dataclass(frozen=True)
class Completed:
    """Appointment successfully completed."""
    completed_at: datetime
    notes: str

@dataclass(frozen=True)
class Cancelled:
    """Appointment cancelled."""
    cancelled_at: datetime
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
- Each variant carries state-specific metadata
- `Requested`: timestamp when patient requested
- `Confirmed`: confirmation timestamp + scheduled time
- `InProgress`: start timestamp
- `Completed`: completion timestamp + doctor notes
- `Cancelled`: cancellation timestamp + reason

**Transition validation function**:
```python
# file: demo/healthhub/backend/app/domain/appointment.py
def validate_transition(
    current: AppointmentStatus,
    target: type[AppointmentStatus],
) -> bool:
    """Validate if state transition is allowed."""
    match current:
        case Requested():
            return target in (Confirmed, Cancelled)
        case Confirmed():
            return target in (InProgress, Cancelled)
        case InProgress():
            return target in (Completed, Cancelled)
        case Completed() | Cancelled():
            return False  # Terminal states
    return False
```

## Step 2: Schedule Appointment as Patient

**Login as patient**:
- Email: `bob.patient@example.com`
- Password: `password123`

**Patient Bob's profile** (from seed_data.sql):
- Name: Bob Baker
- DOB: 1978-07-22
- Blood Type: A+
- Allergies: Latex
- Insurance: INS-002-2024
- **Existing appointment**: Requested appointment with Dr. Johnson (Orthopedics) for "Knee pain evaluation"

**Navigate to Appointments**: Click "Appointments" in sidebar

**Expected**: See existing appointment with status badge "Requested" (yellow/orange)

**Click "Request New Appointment"**: Opens appointment request form

**Fill form**:
- Doctor: Select "Dr. Johnson (Orthopedics)"
- Reason: "Follow-up on knee pain"
- Preferred Date: Select future date
- Click "Submit"

**Expected**: New appointment created with status `Requested`

**What's happening** (effect program trace):

```python
# file: demo/healthhub/backend/app/programs/appointment_programs.py
def schedule_appointment_program(
    patient_id: UUID,
    doctor_id: UUID,
    reason: str,
    requested_time: datetime | None,
) -> Generator[AllEffects, EffectResult, Result[UUID, AppointmentError]]:
    """Schedule new appointment."""

    # Step 1: Verify patient exists
    patient_result = yield GetPatientById(patient_id=patient_id)

    match patient_result:
        case Patient() as patient:
            pass  # Continue
        case PatientNotFound():
            return Err(AppointmentError(reason="patient_not_found"))

    # Step 2: Verify doctor exists
    doctor_result = yield GetDoctorById(doctor_id=doctor_id)

    match doctor_result:
        case Doctor() as doctor:
            pass  # Continue
        case DoctorNotFound():
            return Err(AppointmentError(reason="doctor_not_found"))

    # Step 3: Create appointment with Requested status
    appointment = Appointment(
        id=uuid4(),
        patient_id=patient_id,
        doctor_id=doctor_id,
        status=Requested(requested_at=datetime.now(UTC)),
        reason=reason,
        requested_time=requested_time,
    )

    # Step 4: Save to database
    save_result = yield SaveAppointment(appointment=appointment)

    match save_result:
        case AppointmentSaved():
            # Step 5: Send notification to doctor
            yield SendNotification(
                user_id=doctor.user_id,
                message=f"New appointment request from {patient.first_name} {patient.last_name}",
                type="appointment_requested",
            )

            return Ok(appointment.id)

        case AppointmentSaveError(error=error):
            return Err(AppointmentError(reason=error))
```

**Generator pattern**:
- `yield` effect → Interpreter handles → Send result back
- `match` on result → Handle Ok/Err cases
- Return final `Result[UUID, AppointmentError]`

## Step 3: Confirm Appointment as Doctor

**Logout and login as doctor**:
- Email: `dr.johnson@healthhub.com`
- Password: `password123`

**Doctor Johnson's profile**:
- Name: Dr. Michael Johnson
- Specialization: Orthopedics
- License: MD-CA-23456
- Can Prescribe: Yes

**Navigate to Dashboard**: Should see "Pending Confirmations" section

**Expected**: Bob's appointment request listed

**Click on appointment**: Opens appointment detail view

**Status**: "Requested" badge

**Click "Confirm Appointment"**: Opens confirmation dialog

**Select scheduled time**: Choose date/time for appointment

**Click "Confirm"**: State transition `Requested` → `Confirmed`

**Expected**: Status badge changes to "Confirmed" (green)

**What's happening** (state transition program):

```python
# file: demo/healthhub/backend/app/programs/appointment_programs.py
def transition_appointment_program(
    appointment_id: UUID,
    new_status: AppointmentStatus,
    auth_state: AuthorizationState,
) -> Generator[AllEffects, EffectResult, Result[None, TransitionError]]:
    """Transition appointment to new status."""

    # Step 1: Get appointment
    appt_result = yield GetAppointmentById(appointment_id=appointment_id)

    match appt_result:
        case Appointment() as appt:
            pass
        case AppointmentNotFound():
            return Err(TransitionError(reason="not_found"))

    # Step 2: Validate authorization
    match auth_state:
        case DoctorAuthorized() | AdminAuthorized():
            pass  # Authorized
        case PatientAuthorized():
            # Patients can only cancel own appointments
            if not isinstance(new_status, Cancelled):
                return Err(TransitionError(reason="unauthorized"))
        case Unauthorized():
            return Err(TransitionError(reason="unauthorized"))

    # Step 3: Validate transition
    if not validate_transition(appt.status, type(new_status)):
        return Err(TransitionError(
            reason="invalid_transition",
            detail=f"Cannot transition from {type(appt.status).__name__} to {type(new_status).__name__}"
        ))

    # Step 4: Update appointment
    updated_appt = dataclasses.replace(appt, status=new_status)

    save_result = yield SaveAppointment(appointment=updated_appt)

    match save_result:
        case AppointmentSaved():
            # Step 5: Send notification
            yield SendNotification(
                user_id=appt.patient_id,
                message=f"Appointment {type(new_status).__name__.lower()}",
                type=f"appointment_{type(new_status).__name__.lower()}",
            )

            return Ok(None)

        case AppointmentSaveError(error=error):
            return Err(TransitionError(reason=error))
```

**Notice**:
- `validate_transition()` prevents invalid state changes
- Authorization check enforced before transition
- Notification sent after successful transition
- Uses `dataclasses.replace()` to create new immutable instance

## Step 4: Complete Appointment Workflow

**Still logged in as Dr. Johnson**

**Click "Start Appointment"**: Transition `Confirmed` → `InProgress`

**Expected**: Status badge changes to "In Progress" (blue)

**Timer appears**: Shows appointment duration

**Conduct mock appointment** (in real app, doctor would interact with patient)

**Click "Complete Appointment"**: Opens completion form

**Fill form**:
- Notes: "Patient reports knee pain has improved with physical therapy. Recommend continuing exercises for 3 more weeks. No need for imaging at this time."
- Click "Complete"

**Transition**: `InProgress` → `Completed`

**Expected**: Status badge changes to "Completed" (gray), notes displayed

**What happens next**:
- Invoice automatically generated (admin creates later)
- Patient receives notification
- Appointment now in terminal state (no further transitions)

## Step 5: Create Prescription with Interaction Check

**Still on appointment detail page**

**Click "Create Prescription"**: Opens prescription form

**Fill form**:
- Patient: Bob Baker (pre-selected from appointment)
- Medication: "Ibuprofen"
- Dosage: "400mg"
- Frequency: "Take as needed for pain, max 3 times daily"
- Duration (days): 30
- Refills: 1
- Notes: "Take with food. Do not exceed 1200mg per day."

**Click "Check Interactions"**: System checks against:
1. Patient allergies (Bob: Latex - not a medication, OK)
2. Existing prescriptions (Bob: none in seed data)
3. Known drug interactions (Ibuprofen: minimal interactions)

**Expected**: "No interactions found" message

**Click "Submit"**: Prescription created

**What's happening** (prescription program):

```python
# file: demo/healthhub/backend/app/programs/prescription_programs.py
def create_prescription_program(
    patient_id: UUID,
    doctor_id: UUID,
    medication: str,
    dosage: str,
    frequency: str,
    duration_days: int,
    refills_remaining: int,
    notes: str,
    auth_state: AuthorizationState,
) -> Generator[AllEffects, EffectResult, Result[UUID, PrescriptionError]]:
    """Create new prescription with interaction checking."""

    # Step 1: Verify authorization
    match auth_state:
        case DoctorAuthorized(can_prescribe=True):
            pass  # Authorized
        case DoctorAuthorized(can_prescribe=False):
            return Err(PrescriptionError(reason="cannot_prescribe"))
        case PatientAuthorized() | Unauthorized():
            return Err(PrescriptionError(reason="unauthorized"))
        case AdminAuthorized():
            pass  # Admin can create prescriptions

    # Step 2: Get patient (for allergy check)
    patient_result = yield GetPatientById(patient_id=patient_id)

    match patient_result:
        case Patient() as patient:
            pass
        case PatientNotFound():
            return Err(PrescriptionError(reason="patient_not_found"))

    # Step 3: Check medication allergies
    if medication.lower() in [a.lower() for a in patient.allergies]:
        return Err(PrescriptionError(
            reason="allergy_interaction",
            detail=f"Patient allergic to {medication}"
        ))

    # Step 4: Get existing prescriptions
    existing_result = yield GetPrescriptionsForPatient(patient_id=patient_id)

    match existing_result:
        case list() as existing_prescriptions:
            # Step 5: Check drug-drug interactions
            for existing in existing_prescriptions:
                interaction = check_drug_interaction(medication, existing.medication)
                if interaction.severity == "high":
                    return Err(PrescriptionError(
                        reason="drug_interaction",
                        detail=f"{medication} interacts with {existing.medication}: {interaction.warning}"
                    ))

    # Step 6: Create prescription
    prescription = Prescription(
        id=uuid4(),
        patient_id=patient_id,
        doctor_id=doctor_id,
        medication=medication,
        dosage=dosage,
        frequency=frequency,
        duration_days=duration_days,
        refills_remaining=refills_remaining,
        notes=notes,
        created_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(days=365),
    )

    # Step 7: Save prescription
    save_result = yield SavePrescription(prescription=prescription)

    match save_result:
        case PrescriptionSaved():
            # Step 8: Notify patient
            yield SendNotification(
                user_id=patient.user_id,
                message=f"New prescription: {medication}",
                type="prescription_created",
            )

            return Ok(prescription.id)

        case PrescriptionSaveError(error=error):
            return Err(PrescriptionError(reason=error))
```

**Notice**:
- `can_prescribe` flag checked in authorization
- Allergy check against patient allergies list
- Drug-drug interaction check against existing prescriptions
- Multi-step validation before creation

## Step 6: View Prescription as Patient

**Logout and login as Bob**:
- Email: `bob.patient@example.com`
- Password: `password123`

**Navigate to Prescriptions**: Click "Prescriptions" in sidebar

**Expected**: See new Ibuprofen prescription

**Prescription details**:
- Medication: Ibuprofen 400mg
- Frequency: Take as needed, max 3x daily
- Duration: 30 days
- Refills: 1 remaining
- Prescribed by: Dr. Michael Johnson (Orthopedics)
- Notes: "Take with food. Do not exceed 1200mg per day."

**Notification badge**: "1 new prescription"

## Step 7: Process Lab Result with Critical Alert

**Switch scenario**: Login as Dr. Brown (Neurology)
- Email: `dr.brown@healthhub.com`
- Password: `password123`

**Navigate to Lab Results**: Click "Lab Results" in sidebar

**Expected**: See existing lab result for David Davis (Blood Glucose - Critical)

**Existing critical lab** (from seed_data.sql):
- Patient: David Davis
- Test: Blood Glucose
- Results: Fasting glucose 105, HbA1c 6.2
- Critical: **Yes** (prediabetic range)
- Status: Reviewed by Dr. Brown
- Notes: "Prediabetic range. Recommend lifestyle modifications and follow-up in 3 months."

**Critical flag triggers**:
1. Immediate notification to doctor
2. Yellow/red badge on dashboard
3. Priority sorting in lab results list

**Click "Add Results"**: Simulate lab system submitting new result

**Fill form**:
- Patient: Select "David Davis"
- Test Type: "Complete Blood Count (CBC)"
- Results (JSON):
  ```json
  {
    "wbc": "12.5",
    "rbc": "4.8",
    "hemoglobin": "14.2",
    "platelets": "250"
  }
  ```
- Critical: **No** (normal values)

**Click "Submit"**: Lab result created

**Expected**: No critical alert (normal values)

**What's happening** (lab result program):

```python
# file: demo/healthhub/backend/app/programs/lab_result_programs.py
def process_lab_result_program(
    patient_id: UUID,
    doctor_id: UUID,
    test_type: str,
    result_data: dict[str, str],
    critical: bool,
) -> Generator[AllEffects, EffectResult, Result[UUID, LabResultError]]:
    """Process new lab result with critical value checking."""

    # Step 1: Create lab result
    lab_result = LabResult(
        id=uuid4(),
        patient_id=patient_id,
        doctor_id=doctor_id,
        test_type=test_type,
        result_data=result_data,
        critical=critical,
        reviewed_by_doctor=False,
        doctor_notes=None,
    )

    # Step 2: Save lab result
    save_result = yield SaveLabResult(lab_result=lab_result)

    match save_result:
        case LabResultSaved():
            # Step 3: If critical, send immediate alert
            if critical:
                yield SendNotification(
                    user_id=doctor_id,
                    message=f"CRITICAL LAB: {test_type} for patient {patient_id}",
                    type="critical_lab_result",
                    priority="high",
                )

            # Step 4: Notify patient (results available)
            yield SendNotification(
                user_id=patient_id,
                message=f"Lab results available: {test_type}",
                type="lab_result_available",
                priority="normal" if not critical else "high",
            )

            return Ok(lab_result.id)

        case LabResultSaveError(error=error):
            return Err(LabResultError(reason=error))
```

**Critical value workflow**:
1. Lab system submits result with `critical=true`
2. Immediate high-priority notification to doctor
3. Doctor reviews, adds notes, marks as reviewed
4. Patient notified after doctor review

## Step 8: Review Lab Result as Doctor

**Still logged in as Dr. Brown**

**Click on critical lab result**: David Davis Blood Glucose

**Status**: "Reviewed" (Dr. Brown already reviewed in seed data)

**Doctor notes shown**: "Prediabetic range. Recommend lifestyle modifications..."

**For new lab results**:

**Click "Mark as Reviewed"**: Opens review form

**Add notes**:
- "CBC results within normal limits. Continue current treatment plan."

**Click "Submit"**: `reviewed_by_doctor` flag set to `true`

**Expected**: Patient receives notification "Lab results reviewed by Dr. Brown"

## Step 9: Generator-Based Unit Testing

**Open test file**: `demo/healthhub/tests/pytest/backend/test_appointment_programs.py`

**Generator testing pattern**:

```python
# file: demo/healthhub/tests/pytest/backend/test_appointment_programs.py
def test_schedule_appointment_program() -> None:
    """Test appointment scheduling program with generator stepping."""
    patient_id = uuid4()
    doctor_id = uuid4()

    # Create program generator
    gen = schedule_appointment_program(
        patient_id=patient_id,
        doctor_id=doctor_id,
        reason="Test appointment",
        requested_time=None,
    )

    # Step 1: Expect GetPatientById effect
    effect1 = next(gen)
    assert isinstance(effect1, GetPatientById)
    assert effect1.patient_id == patient_id

    # Send mock patient result
    mock_patient = Patient(
        id=patient_id,
        user_id=uuid4(),
        first_name="Test",
        last_name="Patient",
        date_of_birth=date(1990, 1, 1),
        blood_type="O+",
        allergies=[],
        insurance_id="INS-TEST",
        emergency_contact="Test Contact",
        phone="+1-555-0000",
        address="Test Address",
    )

    # Step 2: Expect GetDoctorById effect
    effect2 = gen.send(mock_patient)
    assert isinstance(effect2, GetDoctorById)
    assert effect2.doctor_id == doctor_id

    # Send mock doctor result
    mock_doctor = Doctor(
        id=doctor_id,
        user_id=uuid4(),
        first_name="Test",
        last_name="Doctor",
        specialization="Test",
        license_number="MD-TEST",
        can_prescribe=True,
        phone="+1-555-0001",
    )

    # Step 3: Expect SaveAppointment effect
    effect3 = gen.send(mock_doctor)
    assert isinstance(effect3, SaveAppointment)
    assert isinstance(effect3.appointment.status, Requested)

    # Send save success
    # Step 4: Expect SendNotification effect
    effect4 = gen.send(AppointmentSaved())
    assert isinstance(effect4, SendNotification)
    assert effect4.user_id == mock_doctor.user_id

    # Send notification success, get final result
    try:
        gen.send(NotificationSent())
        pytest.fail("Expected StopIteration")
    except StopIteration as e:
        result = e.value
        assert isinstance(result, Ok)
        assert isinstance(result.value, UUID)
```

**Benefits of generator testing**:
- ✅ Test effect sequence without running interpreter
- ✅ Mock each effect result independently
- ✅ Verify program logic without infrastructure
- ✅ Fast unit tests (<1ms per test)

## Step 10: Verify E2E Test Coverage

**Run appointment tests**:
```bash
docker compose -f docker/docker-compose.yml exec healthhub poetry run pytest tests/pytest/e2e/test_appointments.py -v
```

**Expected tests**:
- `test_request_appointment_as_patient` - Patient requests appointment
- `test_confirm_appointment_as_doctor` - Doctor confirms (Requested → Confirmed)
- `test_start_appointment_as_doctor` - Doctor starts (Confirmed → InProgress)
- `test_complete_appointment_as_doctor` - Doctor completes (InProgress → Completed)
- `test_cancel_appointment` - Cancel from any non-terminal state
- `test_invalid_transition_prevented` - Terminal states reject transitions

**Run prescription tests**:
```bash
docker compose -f docker/docker-compose.yml exec healthhub poetry run pytest tests/pytest/e2e/test_prescriptions.py -v
```

**Run lab result tests**:
```bash
docker compose -f docker/docker-compose.yml exec healthhub poetry run pytest tests/pytest/e2e/test_lab_results.py -v
```

## Summary

**You have successfully**:
- ✅ Understood appointment state machine with 5 states
- ✅ Scheduled appointment as patient (Requested status)
- ✅ Confirmed appointment as doctor (Requested → Confirmed)
- ✅ Completed full appointment workflow (→ InProgress → Completed)
- ✅ Created prescription with allergy and interaction checking
- ✅ Processed lab result with critical value alerts
- ✅ Reviewed lab results and added doctor notes
- ✅ Tested effect programs using generator stepping pattern

**Key Takeaways**:

1. **State Machines**: ADTs + validation functions prevent invalid transitions
2. **Terminal States**: Completed/Cancelled cannot transition further
3. **Effect Programs**: Generator pattern (`yield`) separates logic from execution
4. **Interaction Checking**: Multi-step validation (allergies → drug-drug interactions)
5. **Critical Alerts**: High-priority notifications for urgent results
6. **Generator Testing**: Step through program without interpreter
7. **Immutability**: `dataclasses.replace()` creates new instances

## Next Steps

- [Advanced Journey](advanced_journey.md) - Custom effects, performance, production deployment
- [Appointments Feature](../03_features/appointments.md) - Complete state machine documentation
- [Prescriptions Feature](../03_features/prescriptions.md) - Interaction checking details
- [Lab Results Feature](../03_features/lab_results.md) - Critical alert workflows

## Cross-References

- [Effect Types](../../../../../documents/tutorials/effect_types.md)
- [Effect Patterns](../../../../../documents/engineering/effect_patterns.md#state-machines)
- [Testing Guide](../../../../../documents/tutorials/testing_guide.md)
- [Code Quality](../../../../../documents/engineering/code_quality.md)
