# Beginner Journey

**Status**: Authoritative source
**Supersedes**: none
**Referenced by**: demo/healthhub/documents/tutorials/README.md

> **Purpose**: Tutorial on getting started with HealthHub - login, navigation, viewing data, and understanding ADTs in the healthcare domain.

> **Core Doctrines**: For comprehensive patterns, see:
> - [Effectful Quickstart](../../../../../documents/tutorials/quickstart.md)
> - [ADTs and Result Types](../../../../../documents/tutorials/adts_and_results.md)
> - [Code Quality](../../../../../documents/engineering/code_quality.md)

## Prerequisites

- Docker workflow running; commands executed via `docker compose -f docker/docker-compose.yml`.
- Completed [Effectful Quickstart](../../../../../documents/tutorials/quickstart.md).
- Familiarity with Python type hints and pattern matching.

## Learning Objectives

- Log in as patient, doctor, and admin using demo credentials
- Navigate HealthHub UI and understand role-based dashboards
- View existing data (appointments, prescriptions, lab results, invoices)
- Understand AuthorizationState ADT and RBAC patterns
- Recognize how ADTs make invalid states unrepresentable

## Step 1: Start HealthHub

**Verify Docker services are running:**

```bash
docker compose -f docker/docker-compose.yml ps
```

**Expected output**: All services (healthhub, postgres, redis, pulsar, minio) in "Up" state.

**If services not running**:

```bash
docker compose -f docker/docker-compose.yml up -d
```

**Access HealthHub**: Open browser to `http://localhost:8851`

**What's happening**:
- FastAPI serves React frontend from `/opt/healthhub/frontend-build/build/`
- Backend API available at `http://localhost:8851/api`
- All infrastructure services running in Docker network

## Step 2: Login as Patient

**Navigate to**: `http://localhost:8851/login`

**Enter credentials**:
- Email: `alice.patient@example.com`
- Password: `password123`

**Click**: "Login" button

**Expected**: Redirect to patient dashboard (`/dashboard`)

**What's happening**:

1. Frontend sends POST to `/api/auth/login` with email/password
2. Backend validates credentials (bcrypt password hash verification)
3. JWT token issued with patient role and patient_id
4. Token stored in localStorage as `healthhub-auth`
5. AuthorizationState transitions: `Hydrating` → `Authenticating` → `Authenticated`

**Verify auth state** (browser console):

```javascript
JSON.parse(localStorage.getItem('healthhub-auth')).state.authState
```

**Expected output**:
```json
{
  "type": "Authenticated",
  "user": {
    "userId": "20000000-0000-0000-0000-000000000001",
    "email": "alice.patient@example.com",
    "role": "patient"
  },
  "patientId": "30000000-0000-0000-0000-000000000001"
}
```

**ADT Pattern**:
```python
# file: demo/healthhub/backend/app/domain/auth.py
@dataclass(frozen=True)
class PatientAuthorized:
    """Patient successfully authorized."""
    user_id: UUID
    patient_id: UUID
    email: str
    role: Literal["patient"] = "patient"

type AuthorizationState = (
    PatientAuthorized
    | DoctorAuthorized
    | AdminAuthorized
    | Unauthorized
)
```

**Why ADT?**
- **Explicit**: All auth states visible in type definition
- **Safe**: Pattern matching ensures all cases handled
- **Self-documenting**: Each variant carries relevant context
- **Type-safe**: MyPy enforces exhaustive matching

## Step 3: View Patient Dashboard

**You should see**:
- Welcome message: "Welcome, Alice Anderson"
- Upcoming appointments section
- Recent prescriptions section
- Lab results section
- Invoices section

**Patient Alice's data** (from `seed_data.sql`):
- **Profile**: Alice Anderson, DOB: 1985-03-15, Blood Type: O+, Allergies: Penicillin, Shellfish
- **Appointment**: Confirmed cardiac checkup with Dr. Smith (Cardiology) on 2025-12-01
- **Prescription**: Lisinopril 10mg, once daily, expires 2026-11-01
- **Lab Result**: Lipid Panel (reviewed by Dr. Smith, results normal)

**Navigate to Appointments**: Click "Appointments" in sidebar

**Expected**: List view showing Alice's confirmed appointment

**Appointment details**:
- Doctor: Dr. Sarah Smith (Cardiology)
- Reason: Annual cardiac checkup
- Scheduled Time: 2025-12-01 14:00:00
- Status: Confirmed (badge displayed)

**Navigate to Prescriptions**: Click "Prescriptions" in sidebar

**Expected**: List view showing Alice's active prescription

**Prescription details**:
- Medication: Lisinopril
- Dosage: 10mg
- Frequency: Once daily
- Duration: 90 days
- Refills Remaining: 2
- Notes: "Take in the morning with water. Monitor blood pressure."
- Expires: 2026-11-01

**Navigate to Lab Results**: Click "Lab Results" in sidebar

**Expected**: List view showing Alice's lipid panel results

**Lab result details**:
- Test Type: Lipid Panel
- Results: Total cholesterol 195, LDL 120, HDL 55, Triglycerides 100
- Critical: No
- Reviewed: Yes
- Doctor Notes: "Results within normal range. Continue current medication."

**Navigate to Invoices**: Click "Invoices" in sidebar

**Expected**: No invoices shown (Alice's completed appointment with Dr. Williams has invoice, but Alice hasn't received it yet in demo data)

## Step 4: Understand Patient RBAC Restrictions

**Try to access doctor features**:

Navigate to: `http://localhost:8851/patients` (patient management - doctor/admin only)

**Expected**: Redirect to `/dashboard` with error message "Access denied"

**Why**:
- Frontend route guard checks `authState.type !== "Authenticated" || authState.user.role !== "doctor"`
- Backend API endpoint checks AuthorizationState ADT via pattern matching

**RBAC enforcement code**:
```python
# file: demo/healthhub/backend/app/api/patients.py
def get_patients(auth_state: AuthorizationState):
    match auth_state:
        case DoctorAuthorized() | AdminAuthorized():
            # Authorized - proceed
            pass
        case PatientAuthorized():
            raise HTTPException(403, "Patients cannot view patient list")
        case Unauthorized():
            raise HTTPException(401, "Authentication required")
```

**Patient restrictions**:
- ❌ Cannot view other patients' data
- ❌ Cannot create prescriptions
- ❌ Cannot access admin features (audit logs, user management)
- ❌ Cannot create invoices

**Patient capabilities**:
- ✅ View own appointments
- ✅ Request new appointments
- ✅ Cancel own appointments
- ✅ View own prescriptions
- ✅ View own lab results
- ✅ View own invoices

## Step 5: Login as Doctor

**Logout**: Click "Logout" button (top right)

**Expected**: Auth state transitions: `Authenticated` → `Unauthenticated`, redirect to `/login`

**Login as doctor**:
- Email: `dr.smith@healthhub.com`
- Password: `password123`

**Expected**: Redirect to doctor dashboard (`/dashboard`)

**Verify auth state** (browser console):
```json
{
  "type": "Authenticated",
  "user": {
    "userId": "10000000-0000-0000-0000-000000000001",
    "email": "dr.smith@healthhub.com",
    "role": "doctor"
  },
  "doctorId": "40000000-0000-0000-0000-000000000001",
  "specialization": "Cardiology",
  "canPrescribe": true
}
```

**ADT Variant**:
```python
# file: demo/healthhub/backend/app/domain/auth.py
@dataclass(frozen=True)
class DoctorAuthorized:
    """Doctor successfully authorized."""
    user_id: UUID
    doctor_id: UUID
    email: str
    specialization: str
    can_prescribe: bool
    role: Literal["doctor"] = "doctor"
```

**Notice**:
- `can_prescribe: bool` flag determines prescription creation access
- `specialization: str` shown in UI (Dr. Smith is Cardiology)

## Step 6: View Doctor Dashboard

**You should see**:
- Welcome message: "Welcome, Dr. Sarah Smith (Cardiology)"
- Pending appointment confirmations section
- Patients with critical lab results section
- Recent appointments section

**Doctor capabilities** (vs patient):
- ✅ View ALL patients (not just own data)
- ✅ Confirm/start/complete appointments
- ✅ Create prescriptions (if `can_prescribe=true`)
- ✅ Review lab results and add notes
- ❌ Cannot create invoices (admin-only)
- ❌ Cannot access audit logs (admin-only)

**Navigate to Patients**: Click "Patients" in sidebar

**Expected**: List of all patients in system

**Patients shown**:
- Alice Anderson (O+, allergies: Penicillin, Shellfish)
- Bob Baker (A+, allergies: Latex)
- Carol Carter (B-, no allergies)
- David Davis (AB+, allergies: Aspirin, Bee stings)
- Emily Evans (O-, allergies: Peanuts)

**Click on patient**: View patient detail page with appointments, prescriptions, lab results

**Navigate to Appointments**: Click "Appointments" in sidebar

**Expected**: ALL appointments in system (not filtered to doctor)

**Appointment actions available**:
- Confirm appointment (Requested → Confirmed)
- Start appointment (Confirmed → InProgress)
- Complete appointment (InProgress → Completed)
- Cancel appointment (any non-terminal state → Cancelled)

## Step 7: Login as Admin

**Logout and login as admin**:
- Email: `admin@healthhub.com`
- Password: `password123`

**Expected**: Redirect to admin dashboard (`/dashboard`)

**Verify auth state** (browser console):
```json
{
  "type": "Authenticated",
  "user": {
    "userId": "00000000-0000-0000-0000-000000000001",
    "email": "admin@healthhub.com",
    "role": "admin"
  }
}
```

**ADT Variant**:
```python
# file: demo/healthhub/backend/app/domain/auth.py
@dataclass(frozen=True)
class AdminAuthorized:
    """Admin successfully authorized."""
    user_id: UUID
    email: str
    role: Literal["admin"] = "admin"
```

**Admin capabilities** (full access):
- ✅ All doctor capabilities
- ✅ Create invoices
- ✅ View HIPAA audit logs
- ✅ Manage users (activate/deactivate)
- ✅ View system metrics

**Navigate to Audit Logs**: Click "Audit Logs" in sidebar (admin-only feature)

**Expected**: List of all HIPAA audit log entries

**Sample audit entries**:
- alice.patient@example.com: appointment_created (resource: appointment_id)
- dr.smith@healthhub.com: prescription_created (medication: Lisinopril)
- Timestamps, IP addresses, user agents logged

**Purpose of audit logs**:
- HIPAA compliance (all PHI access must be logged)
- Security monitoring (detect unauthorized access attempts)
- Forensic investigation (track data modifications)

## Step 8: Code Deep Dive - AuthorizationState ADT

**Open file**: `demo/healthhub/backend/app/domain/auth.py`

**AuthorizationState definition**:
```python
# file: demo/healthhub/backend/app/domain/auth.py
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

@dataclass(frozen=True)
class PatientAuthorized:
    """Patient successfully authorized."""
    user_id: UUID
    patient_id: UUID
    email: str
    role: Literal["patient"] = "patient"

@dataclass(frozen=True)
class DoctorAuthorized:
    """Doctor successfully authorized."""
    user_id: UUID
    doctor_id: UUID
    email: str
    specialization: str
    can_prescribe: bool
    role: Literal["doctor"] = "doctor"

@dataclass(frozen=True)
class AdminAuthorized:
    """Admin successfully authorized."""
    user_id: UUID
    email: str
    role: Literal["admin"] = "admin"

@dataclass(frozen=True)
class Unauthorized:
    """Authorization failed."""
    reason: str
    detail: str | None = None

type AuthorizationState = (
    PatientAuthorized
    | DoctorAuthorized
    | AdminAuthorized
    | Unauthorized
)
```

**Why four variants?**

1. **PatientAuthorized**: Carries `patient_id` for querying patient-specific data
2. **DoctorAuthorized**: Carries `doctor_id`, `specialization`, `can_prescribe` for doctor features
3. **AdminAuthorized**: Full access, no additional context needed beyond `user_id`
4. **Unauthorized**: Carries `reason` (not_authenticated, invalid_credentials, etc.) for error handling

**Pattern matching example**:
```python
# file: demo/healthhub/backend/app/api/appointments.py
def get_appointments(auth_state: AuthorizationState):
    match auth_state:
        case PatientAuthorized(patient_id=pid):
            # Patient can only view own appointments
            return repo.get_appointments_for_patient(pid)

        case DoctorAuthorized():
            # Doctor can view all appointments
            return repo.get_all_appointments()

        case AdminAuthorized():
            # Admin can view all appointments
            return repo.get_all_appointments()

        case Unauthorized(reason=reason):
            raise HTTPException(401, f"Unauthorized: {reason}")
```

**Benefits over Optional or string roles**:

❌ **Bad - String-based roles**:
```python
# file: examples/bad_auth.py
if user.role == "patient":  # Typo risk: "paitent"
    # What patient_id to use? Not in type!
    appointments = get_patient_appointments(???)
elif user.role == "doctor":
    appointments = get_all_appointments()
# Forgot admin case - no compiler error!
```

✅ **Good - ADT pattern matching**:
```python
# file: examples/good_auth.py
match auth_state:  # Exhaustive checking enforced by MyPy
    case PatientAuthorized(patient_id=pid):  # patient_id guaranteed present
        appointments = get_patient_appointments(pid)
    case DoctorAuthorized():
        appointments = get_all_appointments()
    case AdminAuthorized():
        appointments = get_all_appointments()
    case Unauthorized():
        raise HTTPException(401)
# Forgot a case? MyPy error: "Pattern matching not exhaustive"
```

## Step 9: Verify E2E Test Coverage

**Open test file**: `demo/healthhub/tests/pytest/e2e/test_login_flow.py`

**Test cases covering this tutorial**:
- `test_patient_login_success` - Alice login verified
- `test_doctor_login_success` - Dr. Smith login verified
- `test_admin_login_success` - Admin login verified
- `test_patient_dashboard_access` - Dashboard data verified
- `test_logout_clears_state` - Logout flow verified

**Run tests**:
```bash
docker compose -f docker/docker-compose.yml exec healthhub poetry run pytest tests/pytest/e2e/test_login_flow.py -v
```

**Expected**: All tests pass, verifying every step you performed manually

**Why tests matter**:
- Regression prevention: Future changes won't break login flow
- Documentation: Tests show expected behavior programmatically
- Confidence: Every tutorial step backed by automated verification

## Summary

**You have successfully**:
- ✅ Logged in as patient, doctor, and admin
- ✅ Understood AuthorizationState ADT with 4 variants
- ✅ Explored role-based dashboards and RBAC restrictions
- ✅ Viewed appointments, prescriptions, lab results, invoices
- ✅ Recognized how ADTs make invalid states unrepresentable
- ✅ Verified tutorial steps match e2e test coverage

**Key Takeaways**:

1. **ADTs > String Roles**: Type-safe, exhaustive, self-documenting
2. **Pattern Matching**: Compiler-enforced case coverage
3. **RBAC via ADTs**: Each role variant carries role-specific context
4. **Frozen Dataclasses**: Immutability prevents accidental state mutations
5. **E2E Tests**: Every workflow verified programmatically

## Next Steps

- [Intermediate Journey](intermediate_journey.md) - Appointment state machines, prescriptions, lab results
- [Patient Guide](../02_roles/patient_guide.md) - Complete patient capabilities and restrictions
- [Doctor Guide](../02_roles/doctor_guide.md) - Complete doctor capabilities and restrictions
- [Authentication Feature](../03_features/authentication.md) - Deep dive into JWT auth and RBAC

## Cross-References

- [Effectful Quickstart](../../../../../documents/tutorials/quickstart.md)
- [ADTs and Result Types](../../../../../documents/tutorials/adts_and_results.md)
- [HealthHub Authentication Engineering](../../engineering/authentication.md)
- [Code Quality - Type Safety](../../../../../documents/engineering/code_quality.md#type-safety-doctrines)
