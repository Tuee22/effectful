# Patient Guide

**Status**: Authoritative source
**Supersedes**: none
**Referenced by**: demo/healthhub/documents/tutorials/README.md

> **Purpose**: Complete guide for patient role capabilities, restrictions, and workflows in HealthHub.

> **Core Doctrines**: For comprehensive patterns, see:
> - [Beginner Journey](../01_journeys/beginner_journey.md)
> - [Authentication Feature](../03_features/authentication.md)
> - [Code Quality](../../../../../documents/engineering/code_quality.md)

## Prerequisites

- Docker workflow running; commands executed via `docker compose -f docker/docker-compose.yml`.
- Completed [Beginner Journey](../01_journeys/beginner_journey.md).
- Access to HealthHub at `http://localhost:8851`.

## Learning Objectives

- Understand complete patient capabilities and restrictions
- Navigate patient dashboard and features
- Request and manage appointments
- View prescriptions, lab results, and invoices
- Understand RBAC enforcement for patient role
- Recognize data access boundaries (own data only)

## Overview

**Patient Role**: Patients are healthcare consumers who can view their own medical data and request healthcare services. Patients have the most restricted access in HealthHub.

**Authorization**: PatientAuthorized ADT variant
```python
@dataclass(frozen=True)
class PatientAuthorized:
    user_id: UUID
    patient_id: UUID  # Links to patient-specific data
    email: str
    role: Literal["patient"] = "patient"
```

**Key Characteristic**: `patient_id` field enables filtering all data queries to patient's own data only.

## Patient Capabilities

### ✅ What Patients CAN Do

| Capability | Description | API Endpoint | Tutorial Reference |
|------------|-------------|--------------|-------------------|
| **View own profile** | View demographics, allergies, blood type | `GET /api/patients/me` | [Beginner Journey](../01_journeys/beginner_journey.md#step-3-view-patient-dashboard) |
| **Request appointments** | Request new appointments with doctors | `POST /api/appointments` | [Appointments Feature](../03_features/appointments.md#workflow-1-patient-requests-appointment) |
| **View own appointments** | View all own appointments (past and future) | `GET /api/appointments` | [Appointments Feature](../03_features/appointments.md) |
| **Cancel own appointments** | Cancel appointments in non-terminal states | `POST /api/appointments/{id}/cancel` | [Appointments Feature](../03_features/appointments.md#cancellation-workflow) |
| **View own prescriptions** | View all prescriptions prescribed to self | `GET /api/prescriptions` | [Prescriptions Feature](../03_features/prescriptions.md#patient-view-own-prescriptions-only) |
| **Request prescription refills** | Request refills for active prescriptions | `POST /api/prescriptions/{id}/refill` | [Prescriptions Feature](../03_features/prescriptions.md#refill-management) |
| **View own lab results** | View lab results with doctor notes | `GET /api/lab-results` | [Lab Results Feature](../03_features/lab_results.md#patient-viewing) |
| **View own invoices** | View invoices with line items | `GET /api/invoices` | [Invoices Feature](../03_features/invoices.md#patient-viewing) |
| **Update profile** | Update contact information, allergies | `PUT /api/patients/me` | - |
| **Change password** | Change account password | `POST /api/auth/change-password` | [Authentication Feature](../03_features/authentication.md) |
| **Logout** | End session and clear JWT token | `POST /api/auth/logout` | [Authentication Feature](../03_features/authentication.md#step-4-logout) |

### ❌ What Patients CANNOT Do

| Restriction | Reason | RBAC Enforcement | Alternative |
|-------------|--------|------------------|-------------|
| **View other patients' data** | Privacy/HIPAA compliance | Pattern matching on `patient_id` | N/A |
| **Create prescriptions** | Medical authority required | Doctor-only with `can_prescribe=true` | Request from doctor during appointment |
| **Access patient list** | Privacy/HIPAA compliance | Doctor/Admin only | N/A |
| **Confirm appointments** | Doctor confirmation required | Doctor/Admin only | Wait for doctor to confirm request |
| **Start/complete appointments** | Doctor workflow | Doctor only | N/A |
| **Review lab results** | Medical interpretation required | Doctor only | View results after doctor review |
| **Generate invoices** | Billing authority required | Admin only | N/A |
| **Mark invoices as paid** | Financial authority required | Admin only | Payment processed externally |
| **View audit logs** | Administrative access required | Admin only | N/A |
| **Manage users** | Administrative access required | Admin only | N/A |

## Patient Dashboard

**Access**: `http://localhost:8851/dashboard` (after login)

**Sections**:
1. **Welcome Banner**: "Welcome, [First Name] [Last Name]"
2. **Upcoming Appointments**: Next 5 appointments (confirmed or in-progress)
3. **Recent Prescriptions**: Active prescriptions (not expired)
4. **Lab Results**: Recent lab results with review status
5. **Invoices**: Unpaid invoices with due dates

**Navigation Sidebar**:
- **Dashboard** (overview)
- **Appointments** (all appointments)
- **Prescriptions** (all prescriptions)
- **Lab Results** (all lab results)
- **Invoices** (all invoices)
- **Profile** (edit profile)
- **Logout**

## Workflow 1: Request Appointment

**Goal**: Request new appointment with doctor.

**Steps**:

1. **Navigate to Appointments**: Click "Appointments" in sidebar

2. **Click "Request Appointment"** button

3. **Fill out form**:
   - **Doctor**: Select from dropdown (shows all doctors with specializations)
   - **Appointment Time**: Select date and time
   - **Reason**: Enter reason for visit (e.g., "Annual physical examination")

4. **Submit Request**: Click "Submit Request"

5. **Expected Result**:
   - Appointment created with status: "Requested"
   - Notification sent to doctor
   - Appointment appears in dashboard under "Upcoming Appointments"

**RBAC Enforcement**:
```python
# Backend validation
match auth_state:
    case PatientAuthorized(patient_id=pid):
        # Patient can only request appointments for self
        if request_data["patient_id"] != pid:
            raise HTTPException(403, "Cannot request appointment for another patient")
        # Proceed with appointment request
```

**Demo Data**: Try requesting appointment with Dr. Smith (Cardiology) as Alice.

**Test Coverage**: `test_patient_workflows.py::test_patient_request_appointment`

## Workflow 2: View Appointments

**Goal**: View all own appointments with status.

**Steps**:

1. **Navigate to Appointments**: Click "Appointments" in sidebar

2. **View Appointment List**:
   - **Requested**: Yellow badge, awaiting doctor confirmation
   - **Confirmed**: Green badge, doctor confirmed
   - **InProgress**: Blue badge, appointment in progress
   - **Completed**: Gray badge, appointment finished
   - **Cancelled**: Red badge, appointment cancelled

3. **Click Appointment**: View details
   - Doctor name and specialization
   - Scheduled time
   - Reason for visit
   - Status with timestamp
   - Doctor notes (if completed)

4. **Actions Available**:
   - **Cancel** (if Requested, Confirmed, or InProgress)
   - **Reschedule** (if Requested or Confirmed)

**Data Filtering**:
```python
# Backend query filters by patient_id
SELECT * FROM appointments
WHERE patient_id = $1  -- PatientAuthorized.patient_id
ORDER BY scheduled_time DESC
```

**Demo Data**: Alice has confirmed appointment with Dr. Smith (Cardiology) on 2025-12-01.

**Test Coverage**: `test_patient_workflows.py::test_patient_view_appointments`

## Workflow 3: View Prescriptions

**Goal**: View all prescriptions prescribed to self.

**Steps**:

1. **Navigate to Prescriptions**: Click "Prescriptions" in sidebar

2. **View Prescription List**:
   - **Medication**: Drug name (e.g., "Lisinopril")
   - **Dosage**: Amount (e.g., "10mg")
   - **Frequency**: How often (e.g., "Once daily")
   - **Refills Remaining**: Number of refills left
   - **Expires**: Expiration date
   - **Prescribing Doctor**: Doctor name and specialization

3. **Filter Options**:
   - **Active**: Prescriptions not yet expired
   - **Expired**: Past expiration date
   - **All**: All prescriptions

4. **Click Prescription**: View details
   - Doctor's instructions/notes
   - Created date
   - Duration (days)
   - Expiration date

5. **Actions Available**:
   - **Request Refill** (if refills remaining > 0 and not expired)

**Data Filtering**:
```python
# Backend query filters by patient_id
SELECT * FROM prescriptions
WHERE patient_id = $1  -- PatientAuthorized.patient_id
ORDER BY created_at DESC
```

**Demo Data**: Alice has active Lisinopril prescription (10mg once daily, expires 2026-11-01).

**Test Coverage**: `test_patient_workflows.py::test_patient_view_prescriptions`

## Workflow 4: View Lab Results

**Goal**: View lab test results with doctor's clinical notes.

**Steps**:

1. **Navigate to Lab Results**: Click "Lab Results" in sidebar

2. **View Lab Results List**:
   - **Test Type**: Type of test (e.g., "Lipid Panel", "CBC")
   - **Date**: When test was performed
   - **Critical**: Red badge if critical values detected
   - **Reviewed**: Green checkmark if doctor reviewed
   - **Doctor**: Ordering physician

3. **Click Lab Result**: View details
   - **Test Values**: All measured values with reference ranges
     - Values outside normal range highlighted in yellow
     - Critical values highlighted in red
   - **Doctor Review Status**: Reviewed or pending review
   - **Doctor Notes**: Clinical interpretation (if reviewed)
   - **Ordering Physician**: Doctor who ordered test

4. **Example - Alice's Lipid Panel**:
   ```
   Test Type: Lipid Panel
   Date: 2025-11-15
   Critical: No
   Reviewed: Yes

   Results:
   - Total Cholesterol: 195 mg/dL (normal: 125-200)
   - LDL: 120 mg/dL (normal: 50-130)
   - HDL: 55 mg/dL (normal: 40-100)
   - Triglycerides: 100 mg/dL (normal: 50-150)

   Doctor Notes: "Results within normal range. Continue current medication (Lisinopril). Follow-up lipid panel in 6 months."
   ```

**Data Filtering**:
```python
# Backend query filters by patient_id
SELECT * FROM lab_results
WHERE patient_id = $1  -- PatientAuthorized.patient_id
ORDER BY created_at DESC
```

**Demo Data**: Alice has lipid panel result reviewed by Dr. Smith (results normal).

**Test Coverage**: `test_patient_workflows.py::test_patient_view_lab_results`

## Workflow 5: View Invoices

**Goal**: View invoices for healthcare services.

**Steps**:

1. **Navigate to Invoices**: Click "Invoices" in sidebar

2. **View Invoice List**:
   - **Invoice Number**: Unique invoice ID
   - **Date**: Invoice issue date
   - **Total**: Total amount due
   - **Due Date**: Payment due date
   - **Status**:
     - **Sent**: Green badge, invoice issued (not yet due)
     - **Overdue**: Red badge, past due date
     - **Paid**: Gray badge, payment received

3. **Click Invoice**: View details
   - **Line Items**: Itemized charges
     - Description (e.g., "Office Visit - Cardiology")
     - Quantity
     - Unit Price
     - Amount
   - **Subtotal**: Sum of line items
   - **Tax**: Tax amount (7%)
   - **Total**: Total amount due
   - **Due Date**: Payment deadline
   - **Payment Status**: Sent, Paid, or Overdue

4. **Example Invoice**:
   ```
   Invoice #50000000-0000-0000-0000-000000000001
   Issued: 2025-11-20
   Due: 2025-12-20
   Status: Sent

   Line Items:
   1. Office Visit - Cardiology (1 × $250.00) = $250.00
   2. Annual Physical Examination (1 × $50.00) = $50.00

   Subtotal: $300.00
   Tax (7%): $21.00
   Total: $321.00
   ```

**Data Filtering**:
```python
# Backend query filters by patient_id
SELECT * FROM invoices
WHERE patient_id = $1  -- PatientAuthorized.patient_id
ORDER BY issued_date DESC
```

**Demo Data**: Alice may have invoice from completed appointment with Dr. Williams.

**Test Coverage**: `test_patient_workflows.py::test_patient_view_invoices`

## Profile Management

**Access**: Click "Profile" in sidebar

**Editable Fields**:
- **Contact Information**:
  - Email (username)
  - Phone number
  - Address
- **Medical Information**:
  - Blood type (read-only, set by doctor)
  - Allergies (editable - comma-separated list)
  - Emergency contact

**Non-Editable Fields** (doctor/admin only):
- First name, Last name
- Date of birth
- Medical record number
- Patient ID

**Update Process**:
1. Click "Edit Profile" button
2. Modify editable fields
3. Click "Save Changes"
4. Confirmation message: "Profile updated successfully"

**RBAC Enforcement**:
```python
# Backend validation
match auth_state:
    case PatientAuthorized(patient_id=pid):
        # Patient can only update own profile
        if profile_id != pid:
            raise HTTPException(403, "Cannot update another patient's profile")
        # Verify only editable fields modified
        if "first_name" in updates or "last_name" in updates or "date_of_birth" in updates:
            raise HTTPException(403, "Cannot modify protected fields")
```

## Security and Privacy

**Data Access Boundaries**:
- **Own Data Only**: All API queries filtered by `patient_id` from AuthorizationState
- **No Cross-Patient Access**: Cannot view other patients' appointments, prescriptions, lab results, or invoices
- **HIPAA Audit Logging**: All data access logged for compliance

**JWT Token**:
```json
{
  "user_id": "20000000-0000-0000-0000-000000000001",
  "email": "alice.patient@example.com",
  "role": "patient",
  "patient_id": "30000000-0000-0000-0000-000000000001",
  "exp": 1234567890
}
```

**Session Management**:
- **Access Token Expiration**: 15 minutes
- **Refresh Token**: 7 days (stored securely)
- **Logout**: Clears localStorage and redirects to login

## Demo Users

**Alice Anderson** (Featured in tutorials)
- Email: `alice.patient@example.com`
- Password: `password123`
- Blood Type: O+
- Allergies: Penicillin, Shellfish
- Active Prescription: Lisinopril 10mg once daily
- Upcoming Appointment: Dr. Smith (Cardiology) - Confirmed

**Bob Baker**
- Email: `bob.patient@example.com`
- Password: `password123`
- Blood Type: A+
- Allergies: Latex

**Carol Carter**
- Email: `carol.patient@example.com`
- Password: `password123`
- Blood Type: B-
- Allergies: None

**David Davis**
- Email: `david.patient@example.com`
- Password: `password123`
- Blood Type: AB+
- Allergies: Aspirin, Bee stings

**Emily Evans**
- Email: `emily.patient@example.com`
- Password: `password123`
- Blood Type: O-
- Allergies: Peanuts

## Troubleshooting

**Issue**: "Access denied" error when trying to view data

**Solution**: Verify you're logged in as correct patient. Check JWT token in localStorage:
```javascript
JSON.parse(localStorage.getItem('healthhub-auth'))
```

---

**Issue**: Cannot request appointment

**Possible Causes**:
- Doctor not available at selected time
- Past appointment time selected
- Network error

**Solution**: Check browser console for error messages, try different time slot.

---

**Issue**: Prescription refill request fails

**Possible Causes**:
- Prescription expired
- No refills remaining
- Network error

**Solution**: Check prescription expiration date and refills remaining. Contact doctor if prescription needs renewal.

## Summary

**Patient role characteristics**:
- ✅ View own medical data (appointments, prescriptions, lab results, invoices)
- ✅ Request appointments and services
- ✅ Manage own profile (contact info, allergies)
- ❌ Cannot view other patients' data
- ❌ Cannot prescribe medications
- ❌ Cannot confirm appointments or complete medical workflows
- ❌ Cannot access administrative features

**RBAC enforcement**: PatientAuthorized ADT variant with `patient_id` enables automatic data filtering to own data only.

**Key Takeaway**: Patient role is most restrictive, designed for healthcare consumers to view and manage their own care.

## Cross-References

- [Beginner Journey - Patient Login](../01_journeys/beginner_journey.md#step-2-login-as-patient)
- [Authentication Feature](../03_features/authentication.md)
- [Appointments Feature](../03_features/appointments.md)
- [Prescriptions Feature](../03_features/prescriptions.md)
- [Lab Results Feature](../03_features/lab_results.md)
- [Invoices Feature](../03_features/invoices.md)
- [Doctor Guide](doctor_guide.md)
- [Admin Guide](admin_guide.md)
