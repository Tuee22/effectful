# Doctor Guide

**Status**: Authoritative source
**Supersedes**: none
**Referenced by**: demo/healthhub/documents/tutorials/README.md

> **Purpose**: Single Source of Truth for doctor capabilities, restrictions, and workflows in HealthHub.

## SSoT Link Map

| Need                   | Link                                                                        |
| ---------------------- | --------------------------------------------------------------------------- |
| Authentication feature | [Authentication Feature](../../engineering/features/authentication.md)      |
| Intermediate journey   | [Intermediate Journey](../../tutorials/01_journeys/intermediate_journey.md) |
| Lab results workflow   | [Lab Result Workflow](../workflows/lab_result_workflow.md)                  |
| Prescription workflow  | [Prescription Workflow](../workflows/prescription_workflow.md)              |
| Appointment workflow   | [Appointment Lifecycle](../workflows/appointment_lifecycle.md)              |

## Prerequisites

- Docker workflow running; commands executed via `docker compose -f docker/docker-compose.yml`.
- Completed [Beginner Journey](../../tutorials/01_journeys/beginner_journey.md) and [Intermediate Journey](../../tutorials/01_journeys/intermediate_journey.md).
- Access to HealthHub at `http://localhost:8851`.

## Learning Objectives

- Understand complete doctor capabilities and restrictions
- Navigate doctor dashboard and features
- Manage appointment lifecycle (confirm, start, complete)
- Create prescriptions with medication interaction checking
- Review lab results and add clinical notes
- Understand `can_prescribe` flag and RBAC enforcement
- Recognize data access scope (all patients, not just own)

## Overview

**Doctor Role**: Doctors are healthcare providers who can view all patient data, manage appointments, prescribe medications, and review lab results. Doctors have elevated access compared to patients.

**Authorization**: DoctorAuthorized ADT variant

```python
# snippet
@dataclass(frozen=True)
class DoctorAuthorized:
    user_id: UUID
    doctor_id: UUID  # Links to doctor-specific data
    email: str
    specialization: str  # Medical specialty (Cardiology, Pediatrics, etc.)
    can_prescribe: bool  # Flag determining prescription creation access
    role: Literal["doctor"] = "doctor"
```

**Key Characteristics**:

- `doctor_id`: Links to doctor-specific data (appointments assigned, prescriptions created)
- `specialization`: Medical specialty (shown in UI, used for appointment filtering)
- `can_prescribe`: Boolean flag controlling prescription creation access

## Doctor Capabilities

### ✅ What Doctors CAN Do

| Capability                 | Description                                           | API Endpoint                           | Tutorial Reference                                                     |
| -------------------------- | ----------------------------------------------------- | -------------------------------------- | ---------------------------------------------------------------------- |
| **View all patients**      | View patient list and individual profiles             | `GET /api/patients`                    | [Beginner Journey](../../tutorials/01_journeys/beginner_journey.md)    |
| **View patient details**   | View patient demographics, allergies, medical history | `GET /api/patients/{id}`               | [Patient Guide](patient_guide.md)                                      |
| **View all appointments**  | View all appointments (not just own)                  | `GET /api/appointments`                | [Appointments Feature](../../engineering/features/appointments.md)     |
| **Confirm appointments**   | Confirm patient-requested appointments                | `POST /api/appointments/{id}/confirm`  | [Appointments Feature](../../engineering/features/appointments.md)     |
| **Start appointments**     | Start confirmed appointments                          | `POST /api/appointments/{id}/start`    | [Appointments Feature](../../engineering/features/appointments.md)     |
| **Complete appointments**  | Complete appointments with clinical notes             | `POST /api/appointments/{id}/complete` | [Appointments Feature](../../engineering/features/appointments.md)     |
| **Cancel appointments**    | Cancel appointments in non-terminal states            | `POST /api/appointments/{id}/cancel`   | [Appointments Feature](../../engineering/features/appointments.md)     |
| **Create prescriptions**   | Create prescriptions (if `can_prescribe=true`)        | `POST /api/prescriptions`              | [Prescriptions Feature](../../engineering/features/prescriptions.md)   |
| **View all prescriptions** | View all prescriptions (with patient filter)          | `GET /api/prescriptions`               | [Prescriptions Feature](../../engineering/features/prescriptions.md)   |
| **Review lab results**     | Review lab results and add clinical notes             | `POST /api/lab-results/{id}/review`    | [Lab Results Feature](../../engineering/features/lab_results.md)       |
| **View all lab results**   | View all lab results (with patient filter)            | `GET /api/lab-results`                 | [Lab Results Feature](../../engineering/features/lab_results.md)       |
| **Update own profile**     | Update contact information                            | `PUT /api/doctors/me`                  | -                                                                      |
| **Change password**        | Change account password                               | `POST /api/auth/change-password`       | [Authentication Feature](../../engineering/features/authentication.md) |
| **Logout**                 | End session and clear JWT token                       | `POST /api/auth/logout`                | [Authentication Feature](../../engineering/features/authentication.md) |

### ❌ What Doctors CANNOT Do

| Restriction                                         | Reason                          | RBAC Enforcement | Alternative                                |
| --------------------------------------------------- | ------------------------------- | ---------------- | ------------------------------------------ |
| **Generate invoices**                               | Billing authority required      | Admin only       | Request admin to generate invoice          |
| **Mark invoices as paid**                           | Financial authority required    | Admin only       | N/A                                        |
| **View invoices**                                   | Financial privacy               | Admin only       | N/A                                        |
| **View audit logs**                                 | Administrative access required  | Admin only       | N/A                                        |
| **Manage users**                                    | Administrative access required  | Admin only       | N/A                                        |
| **Deactivate patients**                             | Administrative access required  | Admin only       | N/A                                        |
| **Create prescriptions** (if `can_prescribe=false`) | Prescription authority required | Flag-based RBAC  | Request prescription privileges from admin |

## Doctor Dashboard

**Access**: `http://localhost:8851/dashboard` (after login as doctor)

**Sections**:

1. **Welcome Banner**: "Welcome, Dr. [First Name] [Last Name] ([Specialization])"
1. **Pending Appointment Confirmations**: Appointments in "Requested" status
1. **Today's Appointments**: Appointments scheduled for today
1. **Patients with Critical Lab Results**: Patients with unreviewed critical lab results
1. **Recent Appointments**: Last 10 completed appointments

**Navigation Sidebar**:

- **Dashboard** (overview)
- **Patients** (all patients)
- **Appointments** (all appointments)
- **Prescriptions** (all prescriptions)
- **Lab Results** (all lab results)
- **Profile** (edit profile)
- **Logout**

## Workflow 1: Confirm Appointment

**Goal**: Confirm patient-requested appointment (transition Requested → Confirmed).

**Steps**:

1. **Navigate to Dashboard**: View "Pending Appointment Confirmations" section

1. **Click Appointment**: View appointment details

   - Patient: Name, allergies, blood type
   - Scheduled Time: Date and time patient requested
   - Reason: Patient's stated reason for visit

1. **Review Patient History** (optional):

   - Click "View Patient" to see medical history
   - Review past appointments, prescriptions, lab results

1. **Confirm Appointment**: Click "Confirm Appointment" button

1. **Expected Result**:

   - Appointment status transitions: Requested → Confirmed
   - Patient notified via notification
   - Appointment appears in "Today's Appointments" (if today)

**RBAC Enforcement**:

```python
# Backend validation
match auth_state:
    case DoctorAuthorized():
        # Doctor can confirm any appointment
        # Proceed with confirmation
        pass
    case PatientAuthorized():
        raise HTTPException(403, "Patients cannot confirm appointments")
```

**Demo Data**: Try confirming appointments as Dr. Smith (Cardiology).

**Test Coverage**: `test_doctor_workflows.py::test_doctor_confirm_appointment`

## Workflow 2: Complete Appointment with Notes

**Goal**: Complete appointment with clinical notes (transition InProgress → Completed).

**Steps**:

1. **Navigate to Appointments**: Click "Appointments" in sidebar

1. **Filter to In-Progress**: Select "In Progress" status filter

1. **Click Appointment**: View appointment details

1. **Add Clinical Notes**: Click "Complete Appointment" button

   - **Chief Complaint**: Patient's main concern
   - **Physical Examination**: Findings from exam
   - **Diagnosis**: Clinical diagnosis
   - **Treatment Plan**: Recommendations and prescriptions
   - **Follow-up**: When patient should return

1. **Example Notes**:

   ```
   Chief Complaint: Patient reports occasional chest discomfort during exercise.

   Physical Examination:
   - Blood pressure: 135/85 (slightly elevated)
   - Heart rate: 72 bpm (normal)
   - Lungs: Clear, no abnormalities
   - Heart: Regular rhythm, no murmurs

   Diagnosis: Mild hypertension, requires monitoring

   Treatment Plan:
   - Prescribed Lisinopril 10mg once daily
   - Recommended dietary modifications (low sodium)
   - Regular exercise program (30 min walking daily)

   Follow-up: 3 months for blood pressure check and lipid panel
   ```

1. **Submit Notes**: Click "Complete Appointment"

1. **Expected Result**:

   - Appointment status transitions: InProgress → Completed (terminal state)
   - Notes saved and visible to patient
   - Patient notified that appointment completed
   - Appointment can be used to generate invoice

**RBAC Enforcement**:

```python
# Backend validation
match auth_state:
    case DoctorAuthorized():
        # Doctor can complete any appointment
        pass
    case PatientAuthorized():
        raise HTTPException(403, "Patients cannot complete appointments")
```

**Demo Data**: Complete Alice's appointment as Dr. Smith.

**Test Coverage**: `test_doctor_workflows.py::test_doctor_complete_appointment`

## Workflow 3: Create Prescription with Interaction Checking

**Goal**: Create prescription for patient with automated interaction checking.

**Prerequisites**: Doctor must have `can_prescribe=true` flag.

**Steps**:

1. **Navigate to Patients**: Click "Patients" in sidebar

1. **Select Patient**: Click patient name to view profile

1. **Click "Prescribe Medication"** button

1. **Fill out Prescription Form**:

   - **Medication**: Drug name (e.g., "Lisinopril")
   - **Dosage**: Amount (e.g., "10mg")
   - **Frequency**: How often (e.g., "Once daily")
   - **Duration**: Days (e.g., 90)
   - **Refills**: Number of refills (e.g., 2)
   - **Instructions**: Patient instructions (e.g., "Take in the morning with water")

1. **System Checks Interactions**:

   - **Against Patient Allergies**: Blocks if critical allergy interaction
   - **Against Current Prescriptions**: Warns if drug interaction detected

1. **Review Warnings** (if any):

   - **Critical**: Prescription blocked, must select alternative medication
   - **High**: Serious warning, proceed with caution
   - **Medium**: Moderate warning, monitor patient
   - **Low**: Minor warning, informational only

1. **Example - Blocked by Allergy**:

   ```
   Critical Allergy Interaction Detected:

   Amoxicillin may cause allergic reaction in patients with Penicillin allergy.

   Recommendation: Do not prescribe - consider alternative medication (e.g., Azithromycin)
   ```

1. **Example - Drug Interaction Warning**:

   ```
   High Drug Interaction Warning:

   Increased bleeding risk when combining Warfarin and Aspirin.

   Recommendation: Monitor INR closely, consider alternative antiplatelet.

   Do you wish to proceed? [Yes] [No]
   ```

1. **Submit Prescription**: Click "Create Prescription"

1. **Expected Result**:

   - Prescription created (if no critical interactions)
   - Patient notified that prescription ready
   - Prescription visible to patient in "Prescriptions" section

**RBAC Enforcement**:

```python
# Backend validation
match auth_state:
    case DoctorAuthorized(can_prescribe=True):
        # Authorized - proceed with prescription creation
        pass
    case DoctorAuthorized(can_prescribe=False):
        raise HTTPException(403, "Doctor not authorized to prescribe medications")
    case PatientAuthorized() | AdminAuthorized():
        raise HTTPException(403, "Only doctors can create prescriptions")
```

**Demo Data**:

- Try prescribing Lisinopril to Alice (no interactions)
- Try prescribing Amoxicillin to Alice (blocked by Penicillin allergy)

**Test Coverage**: `test_doctor_workflows.py::test_doctor_create_prescription_with_interaction_check`

## Workflow 4: Review Lab Results

**Goal**: Review lab results and add clinical interpretation for patient.

**Steps**:

1. **Navigate to Lab Results**: Click "Lab Results" in sidebar

1. **Filter to Unreviewed**: Select "Unreviewed" filter

1. **Prioritize Critical Results**: Results marked "Critical" appear at top

1. **Click Lab Result**: View test details

   - **Test Type**: Type of test (e.g., "Lipid Panel")
   - **Test Date**: When test was performed
   - **Patient**: Patient name and demographics
   - **Test Values**: All measured values with reference ranges
     - Values outside normal range highlighted
     - Critical values highlighted in red

1. **Example - Critical Lipid Panel**:

   ```
   Test Type: Lipid Panel
   Patient: Alice Anderson (O+, allergies: Penicillin, Shellfish)
   Date: 2025-11-15
   Critical: Yes

   Results:
   - Total Cholesterol: 280 mg/dL (critical high, threshold: 300)
   - LDL: 190 mg/dL (critical high, threshold: 190)
   - HDL: 35 mg/dL (critical low, threshold: 30)
   - Triglycerides: 250 mg/dL (high, normal: 50-150)
   ```

1. **Add Clinical Notes**: Click "Add Review"

   - **Interpretation**: Clinical assessment of results
   - **Recommendations**: Treatment recommendations
   - **Follow-up**: When to retest

1. **Example Clinical Notes**:

   ```
   Interpretation:
   Total cholesterol and LDL are critically elevated, indicating high cardiovascular risk.
   HDL is critically low, further increasing risk. Triglycerides are elevated but not critical.

   Recommendations:
   1. Start statin therapy immediately (Atorvastatin 40mg daily)
   2. Dietary modifications: low saturated fat, increase fiber
   3. Increase physical activity to 150 minutes moderate exercise per week
   4. Consider referral to nutritionist

   Follow-up:
   Repeat lipid panel in 3 months to assess treatment response.
   Target: LDL < 100, HDL > 40, triglycerides < 150.
   ```

1. **Submit Review**: Click "Submit Review"

1. **Expected Result**:

   - Lab result marked as reviewed
   - Review notes saved
   - Patient notified that results are ready
   - Patient can view results with your clinical interpretation

**RBAC Enforcement**:

```python
# Backend validation
match auth_state:
    case DoctorAuthorized():
        # Doctor can review any lab result
        # Optional: Verify doctor is assigned to patient
        pass
    case PatientAuthorized():
        raise HTTPException(403, "Patients cannot review lab results")
```

**Demo Data**: Review Alice's lipid panel as Dr. Smith.

**Test Coverage**: `test_doctor_workflows.py::test_doctor_review_lab_result`

## Workflow 5: View Patient Medical History

**Goal**: Review comprehensive patient medical history before appointment.

**Steps**:

1. **Navigate to Patients**: Click "Patients" in sidebar

1. **Select Patient**: Click patient name

1. **View Patient Profile**:

   - **Demographics**: Name, DOB, blood type, allergies
   - **Contact**: Email, phone, address
   - **Emergency Contact**: Name and phone

1. **View Medical History Tabs**:

   - **Appointments**: All appointments (past and upcoming)
     - Filter by status (Completed, Cancelled, Upcoming)
     - View appointment notes from previous visits
   - **Prescriptions**: All prescriptions
     - Active prescriptions (not expired)
     - Historical prescriptions
     - Current medications patient is taking
   - **Lab Results**: All lab results
     - Critical results highlighted
     - Trends over time (e.g., cholesterol levels)
   - **Allergies**: Known allergies
     - Drug allergies (e.g., Penicillin)
     - Food allergies (e.g., Shellfish, Peanuts)
     - Environmental allergies

1. **Example - Alice Anderson's Profile**:

   ```
   Patient: Alice Anderson
   DOB: 1985-03-15 (39 years old)
   Blood Type: O+
   Allergies: Penicillin, Shellfish

   Active Medications:
   - Lisinopril 10mg once daily (for hypertension)
     Expires: 2026-11-01, Refills: 2

   Recent Appointments:
   - 2025-11-15: Annual cardiac checkup (Dr. Smith) - Completed
     Notes: "Blood pressure controlled on current medication..."

   Recent Lab Results:
   - 2025-11-15: Lipid Panel (reviewed by Dr. Smith)
     Total cholesterol 195, LDL 120, HDL 55, Triglycerides 100
     Notes: "Results within normal range..."
   ```

1. **Use History for Clinical Decisions**:

   - Review current medications before prescribing (drug interactions)
   - Check allergies before prescribing (allergy interactions)
   - Review lab trends to assess treatment effectiveness
   - Review previous appointment notes for context

**Demo Data**: View Alice Anderson's comprehensive profile as Dr. Smith.

**Test Coverage**: `test_doctor_workflows.py::test_doctor_view_patient_history`

## can_prescribe Flag

**Purpose**: Controls which doctors can create prescriptions.

**Database Field**:

```sql
-- doctors table schema
CREATE TABLE doctors (
    doctor_id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    specialization VARCHAR(100) NOT NULL,
    can_prescribe BOOLEAN NOT NULL DEFAULT false,
    ...
);
```

**JWT Token**:

```json
// snippet
{
  "user_id": "10000000-0000-0000-0000-000000000001",
  "email": "dr.smith@healthhub.com",
  "role": "doctor",
  "doctor_id": "40000000-0000-0000-0000-000000000001",
  "specialization": "Cardiology",
  "can_prescribe": true,
  "exp": 1234567890
}
```

**RBAC Enforcement**:

```python
# API endpoint
@router.post("/api/prescriptions")
async def create_prescription(
    auth_state: AuthorizationState = Depends(get_auth_state)
):
    match auth_state:
        case DoctorAuthorized(can_prescribe=True):
            # Authorized - proceed
            pass
        case DoctorAuthorized(can_prescribe=False):
            raise HTTPException(403, "Doctor not authorized to prescribe medications")
        case _:
            raise HTTPException(403, "Only doctors can create prescriptions")
```

**Who Gets `can_prescribe=true`?**

- Medical Doctors (MD)
- Doctors of Osteopathic Medicine (DO)
- Nurse Practitioners (NP) with prescriptive authority
- Physician Assistants (PA) with prescriptive authority

**Who Gets `can_prescribe=false`?**

- Residents (in training)
- Fellows (in training)
- Psychologists (PhD, PsyD) - cannot prescribe in most states
- Physical Therapists (PT, DPT)
- Other non-prescribing providers

**How to Request Prescription Privileges**:
Contact admin to update `can_prescribe` flag in database.

## Security and Privacy

**Data Access Scope**:

- **All Patients**: Doctors can view all patient data (not just assigned patients)
- **HIPAA Audit Logging**: All patient data access logged for compliance
- **Clinical Justification**: Access should have clinical justification

**Best Practices**:

- Only access patient data for clinical purposes
- Do not access patient data out of curiosity
- All access is logged and subject to audit

**JWT Token Security**:

- **Access Token Expiration**: 15 minutes
- **Refresh Token**: 7 days
- **Logout**: Clears localStorage and redirects to login

## Demo Users

**Dr. Sarah Smith** (Cardiology) - Featured in tutorials

- Email: `dr.smith@healthhub.com`
- Password: `password123`
- Specialization: Cardiology
- can_prescribe: true

**Dr. John Williams** (Pediatrics)

- Email: `dr.williams@healthhub.com`
- Password: `password123`
- Specialization: Pediatrics
- can_prescribe: true

**Dr. Emily Brown** (General Practice)

- Email: `dr.brown@healthhub.com`
- Password: `password123`
- Specialization: General Practice
- can_prescribe: true

**Dr. Michael Davis** (Orthopedics)

- Email: `dr.davis@healthhub.com`
- Password: `password123`
- Specialization: Orthopedics
- can_prescribe: true

## Troubleshooting

**Issue**: Cannot create prescription

**Possible Causes**:

- `can_prescribe=false` flag in database
- Critical allergy interaction detected
- Network error

**Solution**: Check JWT token for `can_prescribe` field. If false, contact admin. If allergy interaction, select alternative medication.

______________________________________________________________________

**Issue**: Appointment confirmation fails

**Possible Causes**:

- Appointment already confirmed
- Appointment cancelled
- Network error

**Solution**: Check appointment status. Refresh page and try again.

______________________________________________________________________

**Issue**: Lab result review fails

**Possible Causes**:

- Lab result already reviewed
- Network error

**Solution**: Check if result already marked as reviewed. Refresh page.

## Summary

**Doctor role characteristics**:

- ✅ View all patients and comprehensive medical histories
- ✅ Manage appointment lifecycle (confirm, start, complete)
- ✅ Create prescriptions (if `can_prescribe=true`)
- ✅ Review lab results and add clinical interpretations
- ❌ Cannot generate or view invoices (admin-only)
- ❌ Cannot access audit logs or manage users (admin-only)

**RBAC enforcement**: DoctorAuthorized ADT variant with `can_prescribe` flag enables prescription creation.

**Key Takeaway**: Doctor role has elevated access to all patient data for clinical purposes, with specialized workflows for appointment management, prescriptions, and lab result review.

## Cross-References

- [Beginner Journey - Doctor Login](../../tutorials/01_journeys/beginner_journey.md)
- [Intermediate Journey - Doctor Workflows](../../tutorials/01_journeys/intermediate_journey.md)
- [Authentication Feature](../../engineering/features/authentication.md)
- [Appointments Feature](../../engineering/features/appointments.md)
- [Prescriptions Feature](../../engineering/features/prescriptions.md)
- [Lab Results Feature](../../engineering/features/lab_results.md)
- [Patient Guide](patient_guide.md)
- [Admin Guide](admin_guide.md)
