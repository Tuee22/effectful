# Patient Onboarding Workflow

**Status**: Authoritative source\
**Supersedes**: none\
**Referenced by**: demo/healthhub/documents/tutorials/README.md

> **Purpose**: Single Source of Truth for onboarding a new HealthHub patient from registration through first appointment and billing.

## Prerequisites

- Docker workflow running; commands executed via `docker compose -f docker/docker-compose.yml`.
- Completed [Intermediate Journey](../../tutorials/01_journeys/intermediate_journey.md).
- Access to HealthHub at `http://localhost:8851`.

## Learning Objectives

- Execute complete patient journey from registration to billing
- Understand data flow across authentication → appointments → prescriptions → invoices
- Observe feature integration points and notification triggers
- Experience patient perspective throughout entire process
- Verify e2e test coverage for complete care episode

## Overview

**Workflow**: Registration → First Appointment → Prescription → Invoice

**Duration**: ~1.5 hours (following the complete workflow)

**Features Involved**:

1. **Authentication**: User registration and login
1. **Appointments**: Request → Confirm → Start → Complete
1. **Prescriptions**: Doctor creates after appointment
1. **Invoices**: Generated from completed appointment

**Demo User**: emily.patient@example.com (new patient)

**Learning Outcome**: Complete understanding of patient journey from first contact to billing.

## Workflow Diagram

```text
# patient onboarding steps
Step 1: Patient Registration
   ↓ (creates User + Patient records)
Step 2: Patient Login
   ↓ (AuthorizationState: PatientAuthorized)
Step 3: Patient Requests Appointment
   ↓ (Appointment status: Requested)
Step 4: Doctor Confirms Appointment
   ↓ (Appointment status: Confirmed, patient notified)
Step 5: Doctor Starts Appointment
   ↓ (Appointment status: InProgress)
Step 6: Doctor Completes Appointment with Notes
   ↓ (Appointment status: Completed, patient notified)
Step 7: Doctor Creates Prescription
   ↓ (Prescription created, patient notified)
Step 8: Admin Generates Invoice
   ↓ (Invoice status: Sent, patient notified)
Step 9: Patient Views Invoice
   ↓ (Patient sees itemized charges)
```

## Step 1: Patient Registration

**Goal**: Create new patient account.

**Actor**: Emily (prospective patient)

**Actions**:

1. **Navigate to Registration**: `http://localhost:8851/register`

1. **Fill out Registration Form**:

   - **Email**: `emily.patient@example.com`
   - **Password**: `password123`
   - **Confirm Password**: `password123`
   - **First Name**: Emily
   - **Last Name**: Evans
   - **Date of Birth**: 1992-08-20
   - **Blood Type**: O-
   - **Allergies**: Peanuts
   - **Phone**: (555) 123-4567
   - **Address**: 123 Main St, Anytown, ST 12345

1. **Submit Registration**: Click "Register"

1. **Backend Processing**:

   ```python
   # Effect program: register_patient
   def register_patient(registration_data):
       # Hash password
       password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12))

       # Create user record
       user_result = yield DatabaseEffect.Execute(
           query="INSERT INTO users (email, password_hash, role, is_active) VALUES ($1, $2, 'patient', true) RETURNING user_id",
           params=(email, password_hash.decode('utf-8'))
       )

       # Create patient record
       patient_result = yield DatabaseEffect.Execute(
           query="INSERT INTO patients (user_id, first_name, last_name, date_of_birth, blood_type, allergies) VALUES (...)",
           params=(user_id, first_name, last_name, dob, blood_type, allergies)
       )

       return Ok({"user_id": user_id, "patient_id": patient_id})
   ```

1. **Expected Result**:

   - User account created with role "patient"
   - Patient record created with demographics
   - Redirect to login page
   - Success message: "Registration successful. Please log in."

**Data Created**:

- `users` table: user_id, email, password_hash (bcrypt), role="patient", is_active=true
- `patients` table: patient_id, user_id, first_name, last_name, dob, blood_type, allergies

**Test Coverage**: `test_complete_care_episode.py::test_patient_registration`

## Step 2: Patient Login

**Goal**: Authenticate and obtain JWT token.

**Actor**: Emily

**Actions**:

1. **Navigate to Login**: `http://localhost:8851/login`

1. **Enter Credentials**:

   - **Email**: `emily.patient@example.com`
   - **Password**: `password123`

1. **Click "Login"**

1. **Backend Processing**:

   ```python
   # Effect program: login
   def login(email, password):
       # Fetch user
       user_result = yield DatabaseEffect.Query(
           query="SELECT * FROM users WHERE email = $1 AND is_active = true",
           params=(email,)
       )

       # Verify password
       if not bcrypt.checkpw(password.encode('utf-8'), user["password_hash"].encode('utf-8')):
           return Err("Invalid credentials")

       # Fetch patient_id
       patient_result = yield DatabaseEffect.Query(
           query="SELECT patient_id FROM patients WHERE user_id = $1",
           params=(user["user_id"],)
       )

       # Generate JWT
       auth_state = PatientAuthorized(
           user_id=user["user_id"],
           patient_id=patient["patient_id"],
           email=user["email"]
       )

       token = jwt.encode(
           {
               "user_id": str(auth_state.user_id),
               "email": auth_state.email,
               "role": "patient",
               "patient_id": str(auth_state.patient_id),
               "exp": datetime.utcnow() + timedelta(minutes=15)
           },
           "healthhub-secret",
           algorithm="HS256"
       )

       return Ok({"token": token, "user": {...}})
   ```

1. **Expected Result**:

   - JWT token issued
   - Token stored in localStorage as `healthhub-auth`
   - Redirect to patient dashboard
   - Welcome message: "Welcome, Emily Evans"

**AuthorizationState**:

```python
# snippet
PatientAuthorized(
    user_id=UUID("..."),
    patient_id=UUID("..."),
    email="emily.patient@example.com",
    role="patient"
)
```

**Test Coverage**: `test_complete_care_episode.py::test_patient_login`

## Step 3: Patient Requests Appointment

**Goal**: Request first appointment with doctor.

**Actor**: Emily (logged in as patient)

**Actions**:

1. **Navigate to Appointments**: Click "Appointments" in sidebar

1. **Click "Request Appointment"**

1. **Fill out Appointment Form**:

   - **Doctor**: Select "Dr. Sarah Smith (Cardiology)"
   - **Scheduled Time**: Select date/time (e.g., 2025-12-10 14:00)
   - **Reason**: "Initial consultation for cardiac health assessment"

1. **Submit Request**: Click "Submit Request"

1. **Backend Processing**:

   ```python
   # Effect program: request_appointment
   def request_appointment(patient_id, doctor_id, scheduled_time, reason):
       # Validate patient exists
       patient_result = yield DatabaseEffect.Query(
           query="SELECT * FROM patients WHERE patient_id = $1",
           params=(patient_id,)
       )

       # Validate doctor exists
       doctor_result = yield DatabaseEffect.Query(
           query="SELECT * FROM doctors WHERE doctor_id = $1",
           params=(doctor_id,)
       )

       # Create appointment with Requested status
       appointment_id = uuid4()
       initial_status = Requested(requested_at=datetime.now(timezone.utc))

       insert_result = yield DatabaseEffect.Execute(
           query="INSERT INTO appointments (appointment_id, patient_id, doctor_id, scheduled_time, reason, status, ...) VALUES (...)",
           params=(appointment_id, patient_id, doctor_id, scheduled_time, reason, serialize_status(initial_status), ...)
       )

       # Notify doctor
       _ = yield SendDoctorAlert(
           doctor_id=doctor_id,
           alert_type="appointment_requested",
           message=f"New appointment request from Emily Evans for {scheduled_time}",
           urgency="medium"
       )

       return Ok({"appointment_id": appointment_id, "status": initial_status})
   ```

1. **Expected Result**:

   - Appointment created with status "Requested"
   - Doctor notified via alert
   - Appointment appears in patient dashboard under "Upcoming Appointments"
   - Status badge: Yellow "Requested"

**Data Created**:

- `appointments` table: appointment_id, patient_id, doctor_id, scheduled_time, reason, status (Requested), created_at

**Test Coverage**: `test_complete_care_episode.py::test_patient_request_appointment`

## Step 4: Doctor Confirms Appointment

**Goal**: Doctor confirms patient's appointment request.

**Actor**: Dr. Sarah Smith (logged in as doctor)

**Actions**:

1. **Navigate to Dashboard**: View "Pending Appointment Confirmations"

1. **Click Emily's Appointment**: View details

1. **Review Patient History**:

   - New patient (no previous appointments)
   - Allergies: Peanuts
   - Blood type: O-

1. **Click "Confirm Appointment"**

1. **Backend Processing**:

   ```python
   # Effect program: confirm_appointment
   def confirm_appointment(appointment_id, doctor_id):
       # Fetch appointment
       appointment_result = yield DatabaseEffect.Query(
           query="SELECT * FROM appointments WHERE appointment_id = $1",
           params=(appointment_id,)
       )

       # Validate transition (Requested → Confirmed)
       current_status = deserialize_status(appointment["status"])
       if not validate_transition(current_status, Confirmed):
           return Err("Invalid transition")

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
           message=f"Your appointment with Dr. Sarah Smith has been confirmed for {appointment['scheduled_time']}",
       )

       return Ok({"appointment_id": appointment_id, "status": new_status})
   ```

1. **Expected Result**:

   - Appointment status transitions: Requested → Confirmed
   - Emily notified via notification
   - Appointment status badge: Green "Confirmed"
   - Appointment appears in doctor's "Today's Appointments" (if today)

**State Transition**:

- **Before**: Requested(requested_at=2025-12-09T10:00:00Z)
- **After**: Confirmed(confirmed_at=2025-12-09T10:15:00Z, confirmed_by_doctor_id=UUID("..."))

**Test Coverage**: `test_complete_care_episode.py::test_doctor_confirm_appointment`

## Step 5: Doctor Starts Appointment

**Goal**: Doctor starts appointment when Emily arrives.

**Actor**: Dr. Sarah Smith

**Actions**:

1. **Navigate to Appointments**: Click "Appointments" in sidebar

1. **Click Emily's Appointment**: View details

1. **Click "Start Appointment"**

1. **Backend Processing**:

   ```python
   # Effect program: start_appointment
   def start_appointment(appointment_id):
       # Fetch appointment
       # Validate transition (Confirmed → InProgress)
       # Perform transition

       new_status = InProgress(started_at=datetime.now(timezone.utc))

       # Update appointment status
       update_result = yield DatabaseEffect.Execute(...)

       return Ok({"appointment_id": appointment_id, "status": new_status})
   ```

1. **Expected Result**:

   - Appointment status transitions: Confirmed → InProgress
   - Status badge: Blue "In Progress"
   - Timer starts (for appointment duration tracking)

**State Transition**:

- **Before**: Confirmed(confirmed_at=2025-12-09T10:15:00Z, confirmed_by_doctor_id=UUID("..."))
- **After**: InProgress(started_at=2025-12-10T14:00:00Z)

**Test Coverage**: `test_complete_care_episode.py::test_doctor_start_appointment`

## Step 6: Doctor Completes Appointment with Notes

**Goal**: Doctor completes appointment and documents clinical findings.

**Actor**: Dr. Sarah Smith

**Actions**:

1. **Click "Complete Appointment"**

1. **Add Clinical Notes**:

   ```
   Chief Complaint: Patient seeking initial cardiac health assessment.

   Physical Examination:
   - Blood pressure: 125/80 (normal)
   - Heart rate: 68 bpm (normal)
   - Lungs: Clear, no abnormalities
   - Heart: Regular rhythm, no murmurs

   Diagnosis: No cardiac concerns at this time. Patient in good cardiovascular health.

   Treatment Plan:
   - Prescribed Lisinopril 10mg once daily for blood pressure management
   - Recommended annual cardiac checkup
   - Advised regular exercise (30 min daily)

   Follow-up: 1 year for routine cardiac checkup
   ```

1. **Submit Notes**: Click "Complete Appointment"

1. **Backend Processing**:

   ```python
   # Effect program: complete_appointment
   def complete_appointment(appointment_id, notes):
       # Fetch appointment
       # Validate transition (InProgress → Completed)

       new_status = Completed(
           completed_at=datetime.now(timezone.utc),
           notes=notes
       )

       # Update appointment status (terminal state)
       update_result = yield DatabaseEffect.Execute(...)

       # Notify patient
       _ = yield SendPatientNotification(
           patient_id=appointment["patient_id"],
           notification_type="appointment_completed",
           message="Your appointment has been completed. Notes are available in your portal.",
       )

       return Ok({"appointment_id": appointment_id, "status": new_status})
   ```

1. **Expected Result**:

   - Appointment status transitions: InProgress → Completed (terminal state)
   - Notes saved and visible to Emily
   - Emily notified via notification
   - Status badge: Gray "Completed"
   - Appointment ready for invoice generation

**State Transition**:

- **Before**: InProgress(started_at=2025-12-10T14:00:00Z)
- **After**: Completed(completed_at=2025-12-10T14:45:00Z, notes="...")

**Test Coverage**: `test_complete_care_episode.py::test_doctor_complete_appointment`

## Step 7: Doctor Creates Prescription

**Goal**: Prescribe medication recommended during appointment.

**Actor**: Dr. Sarah Smith (can_prescribe=true)

**Actions**:

1. **Navigate to Patients**: Click "Patients" in sidebar

1. **Select Emily Evans**: Click name

1. **Click "Prescribe Medication"**

1. **Fill out Prescription Form**:

   - **Medication**: Lisinopril
   - **Dosage**: 10mg
   - **Frequency**: Once daily
   - **Duration**: 90 days
   - **Refills**: 2
   - **Instructions**: "Take in the morning with water. Monitor blood pressure."

1. **System Checks Interactions**:

   - **Allergy Check**: Lisinopril vs Peanuts → No interaction
   - **Drug Interaction Check**: No current prescriptions → No interactions
   - **Result**: Safe to prescribe

1. **Submit Prescription**: Click "Create Prescription"

1. **Backend Processing**:

   ```python
   # Effect program: create_prescription_with_interaction_check
   def create_prescription_with_interaction_check(patient_id, doctor_id, medication, ...):
       # Check allergies
       allergy_warnings = yield from check_allergy_interactions(patient_id, medication)
       if any(w.severity == "critical" for w in allergy_warnings):
           return Err("Critical allergy interaction")

       # Check drug interactions
       drug_warnings = yield from check_drug_interactions(patient_id, medication)
       if any(w.severity == "critical" for w in drug_warnings):
           return Err("Critical drug interaction")

       # Create prescription
       prescription_id = uuid4()
       expires_at = created_at + timedelta(days=duration_days)

       insert_result = yield DatabaseEffect.Execute(
           query="INSERT INTO prescriptions (...) VALUES (...)",
           params=(prescription_id, patient_id, doctor_id, medication, dosage, frequency, duration_days, refills, notes, created_at, expires_at)
       )

       # Notify patient
       _ = yield SendPatientNotification(
           patient_id=patient_id,
           notification_type="prescription_ready",
           message=f"New prescription for {medication} is ready",
       )

       return Ok({"prescription_id": prescription_id, "warnings": []})
   ```

1. **Expected Result**:

   - Prescription created successfully
   - Emily notified via notification
   - Prescription visible to Emily in "Prescriptions" section

**Data Created**:

- `prescriptions` table: prescription_id, patient_id, doctor_id, medication (Lisinopril), dosage (10mg), frequency (Once daily), duration_days (90), refills (2), notes, created_at, expires_at

**Test Coverage**: `test_complete_care_episode.py::test_doctor_create_prescription`

## Step 8: Admin Generates Invoice

**Goal**: Generate invoice for Emily's completed appointment.

**Actor**: Admin (logged in as admin)

**Actions**:

1. **Navigate to Appointments**: Click "Appointments" in sidebar

1. **Filter to Completed**: Select "Completed" status filter

1. **Select Emily's Appointment**: Click appointment

1. **Click "Generate Invoice"**

1. **Backend Processing**:

   ```python
   # Effect program: generate_invoice_from_appointment
   def generate_invoice_from_appointment(appointment_id):
       # Fetch appointment (verify Completed status)
       # Determine pricing based on specialization (Cardiology: $250)
       # Create line items

       line_items = [
           {"description": "Office Visit - Cardiology", "quantity": 1, "unit_price": Decimal("250.00"), "amount": Decimal("250.00")},
           {"description": "Initial Cardiac Assessment", "quantity": 1, "unit_price": Decimal("50.00"), "amount": Decimal("50.00")},
       ]

       subtotal = Decimal("300.00")
       tax = subtotal * Decimal("0.07")  # 7% tax
       total = subtotal + tax  # $321.00

       # Create invoice
       invoice_id = uuid4()
       issued_date = datetime.now(timezone.utc)
       due_date = issued_date + timedelta(days=30)

       insert_invoice_result = yield DatabaseEffect.Execute(
           query="INSERT INTO invoices (...) VALUES (...)",
           params=(invoice_id, patient_id, appointment_id, "Sent", subtotal, tax, total, due_date, issued_date, None, issued_date, issued_date)
       )

       # Create line items
       for item in line_items:
           line_item_id = uuid4()
           insert_item_result = yield DatabaseEffect.Execute(...)

       # Notify patient
       _ = yield SendPatientNotification(
           patient_id=patient_id,
           notification_type="invoice_ready",
           message=f"Your invoice for appointment on {issued_date.strftime('%Y-%m-%d')} is ready. Amount due: ${total}. Due date: {due_date.strftime('%Y-%m-%d')}.",
       )

       return Ok({"invoice_id": invoice_id, "total": total, "due_date": due_date})
   ```

1. **Expected Result**:

   - Invoice created with status "Sent"
   - Emily notified via notification
   - Invoice visible to Emily in "Invoices" section

**Data Created**:

- `invoices` table: invoice_id, patient_id, appointment_id, status ("Sent"), subtotal ($300.00), tax ($21.00), total ($321.00), due_date (2026-01-09), issued_date (2025-12-10)
- `invoice_line_items` table: 2 line items (Office Visit, Initial Assessment)

**Test Coverage**: `test_complete_care_episode.py::test_admin_generate_invoice`

## Step 9: Patient Views Invoice

**Goal**: Emily reviews invoice for completed appointment.

**Actor**: Emily (logged in as patient)

**Actions**:

1. **Navigate to Invoices**: Click "Invoices" in sidebar

1. **View Invoice List**: See newly generated invoice

1. **Click Invoice**: View details

   ```
   Invoice #50000000-0000-0000-0000-000000000001
   Issued: 2025-12-10
   Due: 2026-01-09
   Status: Sent

   Line Items:
   1. Office Visit - Cardiology (1 × $250.00) = $250.00
   2. Initial Cardiac Assessment (1 × $50.00) = $50.00

   Subtotal: $300.00
   Tax (7%): $21.00
   Total: $321.00
   ```

1. **Expected Result**:

   - Emily sees itemized charges
   - Due date displayed (30 days from issue)
   - Payment instructions displayed
   - Status: "Sent"

**Test Coverage**: `test_complete_care_episode.py::test_patient_view_invoice`

## Integration Points

**Feature-to-Feature Data Flow**:

1. **Authentication → Appointments**:

   - JWT contains `patient_id` from authentication
   - Appointment creation uses `patient_id` from AuthorizationState
   - RBAC enforced via pattern matching on AuthorizationState

1. **Appointments → Prescriptions**:

   - Prescription references completed appointment in doctor notes
   - Doctor creates prescription during/after appointment
   - Prescription notification sent after creation

1. **Appointments → Invoices**:

   - Invoice references completed appointment (appointment_id foreign key)
   - Line items populated from appointment details (specialization, reason)
   - Invoice cannot be generated until appointment status is Completed

1. **Notifications Throughout**:

   - Appointment confirmed → Patient notified
   - Appointment completed → Patient notified
   - Prescription created → Patient notified
   - Invoice generated → Patient notified

## E2E Test Coverage

**File**: `demo/healthhub/tests/pytest/e2e/test_complete_care_episode.py`

**Test Function**: `test_complete_patient_journey`

**Test Steps**:

1. Register new patient (Emily)
1. Login as Emily
1. Request appointment with Dr. Smith
1. Login as Dr. Smith
1. Confirm Emily's appointment
1. Start appointment
1. Complete appointment with notes
1. Create prescription for Emily
1. Login as admin
1. Generate invoice from completed appointment
1. Verify invoice created and visible to Emily

**Assertions**:

- Patient record created
- Appointment status transitions: Requested → Confirmed → InProgress → Completed
- Prescription created with no interactions
- Invoice generated with correct line items
- All notifications triggered

**Run Test**:

```bash
# snippet
docker compose -f docker/docker-compose.yml exec healthhub poetry run pytest tests/pytest/e2e/test_complete_care_episode.py::test_complete_patient_journey -v
```

## Summary

**You have successfully**:

- ✅ Registered new patient account
- ✅ Authenticated and obtained JWT token
- ✅ Requested first appointment
- ✅ Confirmed appointment (doctor workflow)
- ✅ Started and completed appointment with clinical notes
- ✅ Created prescription with medication interaction checking
- ✅ Generated invoice from completed appointment
- ✅ Viewed invoice as patient

**Key Takeaways**:

1. **Multi-Feature Integration**: Complete workflow spans authentication, appointments, prescriptions, invoices
1. **State Machine Enforcement**: Appointment status transitions enforced by ADT validation
1. **Notification Cascade**: Patient notified at each major workflow step
1. **RBAC Throughout**: AuthorizationState ADT enforces role-based access at every API call
1. **Data Flow**: patient_id flows from authentication through all features
1. **E2E Test Coverage**: Complete workflow verified programmatically

**Workflow Duration**: ~1.5 hours from registration to invoice viewing

## Cross-References

- [Intermediate Journey](../../tutorials/01_journeys/intermediate_journey.md)
- [Authentication Feature](../../engineering/features/authentication.md)
- [Appointments Feature](../../engineering/features/appointments.md)
- [Prescriptions Feature](../../engineering/features/prescriptions.md)
- [Invoices Feature](../../engineering/features/invoices.md)
- [Patient Guide](../../product/roles/patient_guide.md)
- [Doctor Guide](../../product/roles/doctor_guide.md)
- [Admin Guide](../../product/roles/admin_guide.md)
