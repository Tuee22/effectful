# Tutorial 06: Authorization

> Understanding ADT-based role authorization.

---

## Overview

HealthHub uses **Algebraic Data Types (ADT)** for authorization instead of string-based role checking. This makes invalid states unrepresentable at compile time.

---

## Authorization States

```python
type AuthorizationState = (
    PatientAuthorized
    | DoctorAuthorized
    | AdminAuthorized
    | Unauthorized
)
```

---

## Patient Authorization

Patients can only access their own records:

```bash
# Login as patient Alice
TOKEN=$(curl -s -X POST http://localhost:8850/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "alice@example.com", "password": "patient123"}' | jq -r '.access_token')

# Can view own records
curl http://localhost:8850/api/v1/patients/me \
  -H "Authorization: Bearer $TOKEN"
# 200 OK

# Cannot view other patient's records
curl http://localhost:8850/api/v1/patients/<other_patient_id> \
  -H "Authorization: Bearer $TOKEN"
# 403 Forbidden
```

---

## Doctor Authorization

Doctors can access patients assigned to them and perform medical actions:

```bash
# Login as doctor
TOKEN=$(curl -s -X POST http://localhost:8850/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "dr.smith@example.com", "password": "doctor123"}' | jq -r '.access_token')

# Can view any patient (for treatment)
curl http://localhost:8850/api/v1/patients/<any_patient_id> \
  -H "Authorization: Bearer $TOKEN"
# 200 OK

# Can confirm appointments
curl -X POST http://localhost:8850/api/v1/appointments/<id>/transition \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"new_status": "confirmed", "scheduled_time": "..."}'
# 200 OK
```

### Prescribing Authority

Doctors have a `can_prescribe` flag:

```python
@dataclass(frozen=True)
class DoctorAuthorized:
    user_id: UUID
    doctor_id: UUID
    email: str
    specialization: str
    can_prescribe: bool  # <-- Critical for prescriptions
    role: Literal["doctor"] = "doctor"
```

```bash
# Doctor without prescribing authority
curl -X POST http://localhost:8850/api/v1/prescriptions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"patient_id": "...", "medication": "..."}'
# 403 Forbidden - Doctor lacks prescribing authority
```

---

## Admin Authorization

Admins have full system access:

```bash
# Login as admin
TOKEN=$(curl -s -X POST http://localhost:8850/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@healthhub.com", "password": "admin123"}' | jq -r '.access_token')

# Can view any patient
curl http://localhost:8850/api/v1/patients/<any_id> \
  -H "Authorization: Bearer $TOKEN"
# 200 OK

# Can create invoices
curl -X POST http://localhost:8850/api/v1/invoices \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{...}'
# 201 Created
```

---

## Pattern Matching in Code

Authorization is checked using pattern matching:

```python
@router.get("/patients/{patient_id}")
async def get_patient(
    patient_id: UUID,
    current_user: AuthorizationState = Depends(get_current_user),
) -> PatientResponse:
    match current_user:
        # Patient viewing own record
        case PatientAuthorized(patient_id=pid) if pid == patient_id:
            return await get_patient_by_id(patient_id)

        # Doctor or Admin viewing any patient
        case DoctorAuthorized() | AdminAuthorized():
            return await get_patient_by_id(patient_id)

        # Patient trying to view other patient
        case PatientAuthorized():
            raise HTTPException(403, "Cannot access other patient records")

        # Not authenticated
        case Unauthorized(reason=reason):
            raise HTTPException(401, reason)
```

---

## Testing Authorization

```python
def test_patient_cannot_access_other_patient() -> None:
    auth = PatientAuthorized(
        user_id=uuid4(),
        patient_id=ALICE_ID,
        email="alice@example.com",
    )

    # Alice tries to access Bob's record
    match auth:
        case PatientAuthorized(patient_id=pid) if pid == BOB_ID:
            pytest.fail("Should not match")
        case PatientAuthorized():
            pass  # Correctly blocked

def test_doctor_can_access_any_patient() -> None:
    auth = DoctorAuthorized(
        user_id=uuid4(),
        doctor_id=uuid4(),
        email="dr.smith@example.com",
        specialization="Cardiology",
        can_prescribe=True,
    )

    match auth:
        case DoctorAuthorized():
            pass  # Can access any patient
```

---

## Permission Summary

| Action | Patient | Doctor | Admin |
|--------|---------|--------|-------|
| View own records | Yes | - | - |
| View any patient | No | Yes | Yes |
| Request appointment | Yes | No | Yes |
| Confirm appointment | No | Yes | Yes |
| Create prescription | No | If can_prescribe | No |
| Create lab result | No | Yes | Yes |
| Create invoice | No | No | Yes |

---

## Next Steps

- [Tutorial 07: Real-Time Notifications](07_notifications.md)
- [Authorization System](../product/authorization_system.md)
- [Authentication](../product/authentication.md)

---

**Last Updated**: 2025-11-25
