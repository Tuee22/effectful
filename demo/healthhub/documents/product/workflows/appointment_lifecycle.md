# Appointment Lifecycle Workflow

**Status**: Authoritative source
**Supersedes**: none
**Referenced by**: demo/healthhub/documents/tutorials/README.md

> **Purpose**: Complete appointment lifecycle workflow demonstrating state machine progression from request through completion and billing.

> **Core Doctrines**: For comprehensive patterns, see:
> - [Intermediate Journey](../01_journeys/intermediate_journey.md)
> - [Appointments Feature](../03_features/appointments.md)
> - [Effect Patterns - State Machines](../../../../../documents/engineering/effect_patterns.md#state-machines)

## Prerequisites

- Docker workflow running; commands executed via `docker compose -f docker/docker-compose.yml`.
- Completed [Intermediate Journey](../01_journeys/intermediate_journey.md).
- Access to HealthHub at `http://localhost:8851`.
- Understanding of state machines and ADTs.

## Learning Objectives

- Execute complete appointment lifecycle from request to invoice
- Understand state machine progression (Requested → Confirmed → InProgress → Completed)
- Observe notification triggers at each state transition
- Experience both patient and doctor perspectives
- Verify invoice generation workflow from completed appointment
- Understand terminal states and transition validation

## Overview

**Workflow**: Request → Confirm → Start → Complete → Invoice → Patient Views

**Duration**: ~1 hour

**Features Involved**:
1. **Appointments**: Complete state machine (5 states, 4 transitions)
2. **Notifications**: Triggered at each state transition
3. **Invoices**: Generated from completed appointment

**Demo Users**:
- Patient: david.patient@example.com
- Doctor: dr.williams@healthhub.com
- Admin: admin@healthhub.com

**Learning Outcome**: Deep understanding of appointment state machine and notification cascade.

## Workflow Diagram

```
Step 1: Patient Requests Appointment
   ↓ (State: Requested, notification to doctor)
Step 2: Doctor Confirms Appointment
   ↓ (State: Confirmed, notification to patient)
Step 3: Patient Arrives, Doctor Starts Appointment
   ↓ (State: InProgress)
Step 4: Doctor Completes Appointment with Notes
   ↓ (State: Completed - TERMINAL, notification to patient)
Step 5: Admin Generates Invoice
   ↓ (Invoice status: Sent, notification to patient)
Step 6: Patient Views Invoice and Appointment Notes
   ↓ (Complete transparency)
```

## Appointment State Machine

**States**: Requested, Confirmed, InProgress, Completed, Cancelled

**Valid Transitions**:
```
Requested → Confirmed, Cancelled
Confirmed → InProgress, Cancelled
InProgress → Completed, Cancelled
Completed → (terminal, no transitions)
Cancelled → (terminal, no transitions)
```

**State Variants**:
```python
@dataclass(frozen=True)
class Requested:
    requested_at: datetime

@dataclass(frozen=True)
class Confirmed:
    confirmed_at: datetime
    confirmed_by_doctor_id: UUID

@dataclass(frozen=True)
class InProgress:
    started_at: datetime

@dataclass(frozen=True)
class Completed:
    completed_at: datetime
    notes: str  # Doctor's clinical notes

@dataclass(frozen=True)
class Cancelled:
    cancelled_at: datetime
    cancelled_by: str  # "patient" | "doctor"
    reason: str

type AppointmentStatus = Requested | Confirmed | InProgress | Completed | Cancelled
```

## Step 1: Patient Requests Appointment

**Goal**: David requests appointment with Dr. Williams (Pediatrics).

**Actor**: David Davis (patient)

**Login**:
- Email: `david.patient@example.com`
- Password: `password123`

**Actions**:

1. **Navigate to Appointments**: Click "Appointments" in sidebar

2. **Click "Request Appointment"**

3. **Fill out Form**:
   - **Doctor**: Dr. John Williams (Pediatrics)
   - **Scheduled Time**: 2025-12-15 10:00 AM
   - **Reason**: "Annual wellness checkup for adolescent"

4. **Submit Request**: Click "Submit Request"

5. **Backend Processing**:
   ```python
   def request_appointment_program(patient_id, doctor_id, scheduled_time, reason):
       # Validate patient and doctor exist
       # ...

       # Create appointment with initial state
       appointment_id = uuid4()
       initial_status = Requested(requested_at=datetime.now(timezone.utc))

       insert_result = yield DatabaseEffect.Execute(
           query="INSERT INTO appointments (...) VALUES (...)",
           params=(appointment_id, patient_id, doctor_id, scheduled_time, reason, serialize_status(initial_status), ...)
       )

       # Notify doctor
       _ = yield SendDoctorAlert(
           doctor_id=doctor_id,
           alert_type="appointment_requested",
           message=f"New appointment request from David Davis for {scheduled_time}",
           urgency="medium",
           metadata={"appointment_id": str(appointment_id)}
       )

       return Ok({"appointment_id": appointment_id, "status": initial_status})
   ```

6. **Expected Result**:
   - **Appointment Created**: appointment_id generated
   - **Status**: Requested(requested_at=2025-12-09T15:00:00Z)
   - **Notification**: Dr. Williams receives alert
   - **Patient Dashboard**: Appointment appears with yellow "Requested" badge
   - **Doctor Dashboard**: Appointment appears in "Pending Confirmations" section

**State**:
```python
Requested(requested_at=datetime(2025, 12, 9, 15, 0, 0, tzinfo=timezone.utc))
```

**Notification Sent**:
- **Recipient**: Dr. Williams
- **Type**: "appointment_requested"
- **Urgency**: Medium
- **Message**: "New appointment request from David Davis for 2025-12-15 10:00"

**Test Coverage**: `test_complete_care_episode.py::test_appointment_request`

## Step 2: Doctor Confirms Appointment

**Goal**: Dr. Williams confirms David's appointment request.

**Actor**: Dr. John Williams (doctor)

**Login**:
- Email: `dr.williams@healthhub.com`
- Password: `password123`

**Actions**:

1. **Navigate to Dashboard**: View "Pending Appointment Confirmations"

2. **Click David's Appointment**: View request details
   - **Patient**: David Davis (AB+, allergies: Aspirin, Bee stings)
   - **Scheduled Time**: 2025-12-15 10:00 AM
   - **Reason**: "Annual wellness checkup for adolescent"
   - **Current Status**: Requested

3. **Review Patient History** (optional):
   - Click "View Patient" to see medical history
   - Previous appointments, prescriptions, lab results

4. **Click "Confirm Appointment"**

5. **Backend Processing**:
   ```python
   def confirm_appointment_program(appointment_id, doctor_id):
       # Fetch appointment
       appointment_result = yield DatabaseEffect.Query(
           query="SELECT * FROM appointments WHERE appointment_id = $1",
           params=(appointment_id,)
       )

       # Deserialize current status
       current_status = deserialize_status(appointment["status"])

       # Validate transition (Requested → Confirmed)
       if not validate_transition(current_status, Confirmed):
           return Err(f"Cannot confirm appointment in {type(current_status).__name__} state")

       # Perform transition
       new_status = Confirmed(
           confirmed_at=datetime.now(timezone.utc),
           confirmed_by_doctor_id=doctor_id
       )

       update_result = yield DatabaseEffect.Execute(
           query="UPDATE appointments SET status = $1, updated_at = $2 WHERE appointment_id = $3",
           params=(serialize_status(new_status), datetime.now(timezone.utc), appointment_id)
       )

       # Notify patient
       _ = yield SendPatientNotification(
           patient_id=appointment["patient_id"],
           notification_type="appointment_confirmed",
           message=f"Your appointment with Dr. John Williams has been confirmed for {appointment['scheduled_time']}",
           metadata={"appointment_id": str(appointment_id)}
       )

       return Ok({"appointment_id": appointment_id, "status": new_status})
   ```

6. **Expected Result**:
   - **Status Transition**: Requested → Confirmed
   - **Notification**: David receives confirmation notification
   - **Patient Dashboard**: Appointment badge changes to green "Confirmed"
   - **Doctor Dashboard**: Appointment moves to "Today's Appointments" (if today)

**State Transition**:
- **Before**: Requested(requested_at=2025-12-09T15:00:00Z)
- **After**: Confirmed(confirmed_at=2025-12-09T15:10:00Z, confirmed_by_doctor_id=UUID("..."))

**Notification Sent**:
- **Recipient**: David Davis
- **Type**: "appointment_confirmed"
- **Message**: "Your appointment with Dr. John Williams has been confirmed for 2025-12-15 10:00"

**Test Coverage**: `test_complete_care_episode.py::test_appointment_confirm`

## Step 3: Doctor Starts Appointment

**Goal**: Dr. Williams starts appointment when David arrives.

**Actor**: Dr. John Williams (doctor)

**Actions**:

1. **Navigate to Appointments**: Click "Appointments" in sidebar

2. **Filter to Confirmed**: Select "Confirmed" status filter

3. **Click David's Appointment**: View details

4. **Click "Start Appointment"**

5. **Backend Processing**:
   ```python
   def start_appointment_program(appointment_id):
       # Fetch appointment
       appointment_result = yield DatabaseEffect.Query(
           query="SELECT * FROM appointments WHERE appointment_id = $1",
           params=(appointment_id,)
       )

       # Validate transition (Confirmed → InProgress)
       current_status = deserialize_status(appointment["status"])
       if not validate_transition(current_status, InProgress):
           return Err(f"Cannot start appointment in {type(current_status).__name__} state")

       # Perform transition
       new_status = InProgress(started_at=datetime.now(timezone.utc))

       update_result = yield DatabaseEffect.Execute(
           query="UPDATE appointments SET status = $1, updated_at = $2 WHERE appointment_id = $3",
           params=(serialize_status(new_status), datetime.now(timezone.utc), appointment_id)
       )

       return Ok({"appointment_id": appointment_id, "status": new_status})
   ```

6. **Expected Result**:
   - **Status Transition**: Confirmed → InProgress
   - **Patient Dashboard**: Appointment badge changes to blue "In Progress"
   - **Doctor Dashboard**: Timer starts (appointment duration tracking)
   - **No Notification**: Patient not notified when appointment starts (in-person event)

**State Transition**:
- **Before**: Confirmed(confirmed_at=2025-12-09T15:10:00Z, confirmed_by_doctor_id=UUID("..."))
- **After**: InProgress(started_at=2025-12-15T10:00:00Z)

**No Notification Sent**: Appointment start is an in-person event, patient already present.

**Test Coverage**: `test_complete_care_episode.py::test_appointment_start`

## Step 4: Doctor Completes Appointment with Notes

**Goal**: Dr. Williams completes appointment and documents findings.

**Actor**: Dr. John Williams (doctor)

**Actions**:

1. **Click "Complete Appointment"**

2. **Add Clinical Notes**:
   ```
   Chief Complaint: Annual wellness checkup for adolescent patient (age 14).

   Physical Examination:
   - Height: 165 cm (65 inches)
   - Weight: 55 kg (121 lbs)
   - BMI: 20.2 (healthy weight)
   - Blood pressure: 110/70 (normal)
   - Heart rate: 72 bpm (normal)
   - Respiratory rate: 16 breaths/min (normal)
   - Vision: 20/20 (both eyes)
   - Hearing: Normal

   Immunizations: Up to date

   Development: Age-appropriate physical and cognitive development

   Diagnosis: Patient in excellent health for age. No concerns.

   Treatment Plan:
   - No medications needed at this time
   - Continue regular exercise and healthy diet
   - Recommended annual follow-up

   Follow-up: 1 year for next annual wellness checkup
   ```

3. **Submit Notes**: Click "Complete Appointment"

4. **Backend Processing**:
   ```python
   def complete_appointment_program(appointment_id, notes):
       # Fetch appointment
       # Validate transition (InProgress → Completed)

       # Perform transition to terminal state
       new_status = Completed(
           completed_at=datetime.now(timezone.utc),
           notes=notes
       )

       update_result = yield DatabaseEffect.Execute(
           query="UPDATE appointments SET status = $1, updated_at = $2 WHERE appointment_id = $3",
           params=(serialize_status(new_status), datetime.now(timezone.utc), appointment_id)
       )

       # Notify patient
       _ = yield SendPatientNotification(
           patient_id=appointment["patient_id"],
           notification_type="appointment_completed",
           message="Your appointment has been completed. Notes are available in your portal.",
           metadata={"appointment_id": str(appointment_id)}
       )

       return Ok({"appointment_id": appointment_id, "status": new_status})
   ```

5. **Expected Result**:
   - **Status Transition**: InProgress → Completed (TERMINAL)
   - **Notification**: David receives completion notification
   - **Patient Dashboard**: Appointment badge changes to gray "Completed"
   - **Patient Dashboard**: Notes visible to David
   - **Invoice Eligibility**: Appointment ready for invoice generation

**State Transition**:
- **Before**: InProgress(started_at=2025-12-15T10:00:00Z)
- **After**: Completed(completed_at=2025-12-15T10:30:00Z, notes="...")

**Terminal State**: No further transitions allowed from Completed state.

**Notification Sent**:
- **Recipient**: David Davis
- **Type**: "appointment_completed"
- **Message**: "Your appointment has been completed. Notes are available in your portal."

**Test Coverage**: `test_complete_care_episode.py::test_appointment_complete`

## Step 5: Admin Generates Invoice

**Goal**: Admin generates invoice from completed appointment.

**Actor**: Admin

**Login**:
- Email: `admin@healthhub.com`
- Password: `password123`

**Actions**:

1. **Navigate to Appointments**: Click "Appointments" in sidebar

2. **Filter to Completed**: Select "Completed" status filter

3. **Identify Unbilled Appointments**: Look for "Invoice Needed" badge

4. **Click David's Appointment**: View details

5. **Click "Generate Invoice"**

6. **Backend Processing**:
   ```python
   def generate_invoice_from_appointment(appointment_id):
       # Fetch appointment (verify Completed status)
       # Fetch doctor specialization (Pediatrics: $150)

       line_items = [
           {"description": "Office Visit - Pediatrics", "quantity": 1, "unit_price": Decimal("150.00"), "amount": Decimal("150.00")},
           {"description": "Annual Wellness Checkup", "quantity": 1, "unit_price": Decimal("50.00"), "amount": Decimal("50.00")},
       ]

       subtotal = Decimal("200.00")
       tax = subtotal * Decimal("0.07")  # $14.00
       total = subtotal + tax  # $214.00

       # Create invoice
       invoice_id = uuid4()
       issued_date = datetime.now(timezone.utc)
       due_date = issued_date + timedelta(days=30)

       insert_invoice_result = yield DatabaseEffect.Execute(
           query="INSERT INTO invoices (...) VALUES (...)",
           params=(invoice_id, patient_id, appointment_id, "Sent", subtotal, tax, total, due_date, issued_date, None, ...)
       )

       # Create line items
       # ...

       # Notify patient
       _ = yield SendPatientNotification(
           patient_id=patient_id,
           notification_type="invoice_ready",
           message=f"Your invoice for appointment on {issued_date.strftime('%Y-%m-%d')} is ready. Amount due: ${total}. Due date: {due_date.strftime('%Y-%m-%d')}.",
           metadata={"invoice_id": str(invoice_id), "total": str(total)}
       )

       return Ok({"invoice_id": invoice_id, "total": total, "due_date": due_date})
   ```

7. **Expected Result**:
   - **Invoice Created**: invoice_id generated
   - **Status**: "Sent"
   - **Notification**: David receives invoice ready notification
   - **Patient Dashboard**: Invoice appears in "Invoices" section

**Invoice Details**:
```
Invoice #...
Issued: 2025-12-15
Due: 2026-01-14
Status: Sent

Line Items:
1. Office Visit - Pediatrics (1 × $150.00) = $150.00
2. Annual Wellness Checkup (1 × $50.00) = $50.00

Subtotal: $200.00
Tax (7%): $14.00
Total: $214.00
```

**Notification Sent**:
- **Recipient**: David Davis
- **Type**: "invoice_ready"
- **Message**: "Your invoice for appointment on 2025-12-15 is ready. Amount due: $214.00. Due date: 2026-01-14."

**Test Coverage**: `test_complete_care_episode.py::test_invoice_generation`

## Step 6: Patient Views Invoice and Appointment Notes

**Goal**: David reviews appointment notes and invoice.

**Actor**: David Davis (patient)

**Actions**:

### View Appointment Notes

1. **Navigate to Appointments**: Click "Appointments" in sidebar

2. **Click Completed Appointment**: View details

3. **Review Doctor's Notes**:
   - Physical examination findings
   - Diagnosis
   - Treatment plan
   - Follow-up recommendations

4. **Expected Result**:
   - **Full Transparency**: David sees complete clinical notes
   - **Status**: Completed (terminal, cannot be modified)
   - **Doctor**: Dr. John Williams (Pediatrics)

### View Invoice

1. **Navigate to Invoices**: Click "Invoices" in sidebar

2. **Click Invoice**: View itemized charges

3. **Review Invoice Details**:
   - Line items (Office Visit, Annual Wellness Checkup)
   - Subtotal, tax, total
   - Due date (30 days from issue)
   - Payment instructions

4. **Expected Result**:
   - **Full Transparency**: David sees itemized charges
   - **Status**: "Sent"
   - **Payment Options**: Credit card, check, online portal

**Test Coverage**: `test_complete_care_episode.py::test_patient_view_completed_appointment_and_invoice`

## Notification Cascade Summary

**Total Notifications in Workflow**:

1. **Appointment Requested** → Doctor notified (alert)
2. **Appointment Confirmed** → Patient notified
3. **Appointment Completed** → Patient notified
4. **Invoice Generated** → Patient notified

**Notification Timing**:
- **Immediate**: All notifications sent synchronously during API call
- **Reliable**: Notifications stored in database before API returns (transactional)

**Notification Channels**:
- **In-App**: Notifications visible in HealthHub UI
- **Future**: Email, SMS, push notifications (not yet implemented)

## Invalid Transitions (Demonstrating Validation)

**Example 1: Skip Confirmation**

**Attempt**: Patient tries to start appointment directly from Requested state

**Backend Validation**:
```python
# Transition: Requested → InProgress (INVALID)
current_status = Requested(requested_at=...)

if not validate_transition(current_status, InProgress):
    return Err("Cannot start appointment in Requested state")
```

**Result**: Error returned, transition blocked

**Expected**: Appointment must be confirmed before starting

---

**Example 2: Modify Terminal State**

**Attempt**: Admin tries to cancel completed appointment

**Backend Validation**:
```python
# Transition: Completed → Cancelled (INVALID)
current_status = Completed(completed_at=..., notes="...")

if not validate_transition(current_status, Cancelled):
    return Err("Cannot cancel appointment in Completed state")
```

**Result**: Error returned, transition blocked

**Expected**: Terminal states (Completed, Cancelled) cannot transition to any other state

## E2E Test Coverage

**File**: `demo/healthhub/tests/pytest/e2e/test_complete_care_episode.py`

**Test Function**: `test_complete_appointment_lifecycle`

**Test Steps**:
1. Patient requests appointment
2. Doctor confirms appointment
3. Doctor starts appointment
4. Doctor completes appointment with notes
5. Admin generates invoice
6. Patient views appointment notes and invoice
7. Verify state transitions
8. Verify notifications triggered
9. Attempt invalid transitions (verify blocked)

**Run Test**:
```bash
docker compose -f docker/docker-compose.yml exec healthhub poetry run pytest tests/pytest/e2e/test_complete_care_episode.py::test_complete_appointment_lifecycle -v
```

## Summary

**You have successfully**:
- ✅ Requested appointment (Requested state)
- ✅ Confirmed appointment (Confirmed state, patient notified)
- ✅ Started appointment (InProgress state)
- ✅ Completed appointment with notes (Completed state, terminal)
- ✅ Generated invoice from completed appointment
- ✅ Viewed appointment notes and invoice as patient
- ✅ Observed notification cascade at each transition
- ✅ Understood terminal state enforcement

**Key Takeaways**:
1. **State Machine Enforcement**: ADT with validate_transition prevents invalid state changes
2. **Terminal States**: Completed and Cancelled states cannot transition further
3. **Notification Cascade**: Patient notified at confirmation, completion, and invoice generation
4. **Context-Rich States**: Each state carries state-specific data (timestamps, notes, doctor_id)
5. **Invoice Generation**: Only possible from Completed state (terminal)
6. **Full Transparency**: Patient sees complete appointment notes and itemized invoice

**Workflow Duration**: ~1 hour from request to invoice viewing

## Cross-References

- [Intermediate Journey - Appointment State Machine](../01_journeys/intermediate_journey.md#step-2-create-appointment-with-state-machine)
- [Appointments Feature](../03_features/appointments.md)
- [Invoices Feature](../03_features/invoices.md)
- [Patient Guide](../02_roles/patient_guide.md)
- [Doctor Guide](../02_roles/doctor_guide.md)
- [Admin Guide](../02_roles/admin_guide.md)
- [Effect Patterns - State Machines](../../../../../documents/engineering/effect_patterns.md#state-machines)
