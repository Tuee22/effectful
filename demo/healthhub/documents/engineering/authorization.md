# Authorization (HealthHub delta)

> Extends base [Authentication](../../../../documents/engineering/authentication.md), [Engineering Architecture](../../../../documents/engineering/architecture.md), and [Code Quality](../../../../documents/engineering/code_quality.md); base rules apply. This overlay lists HealthHub-specific authorization deltas only.

---

## Principle

Authorization should make illegal states unrepresentable through the type system.

**For ADT definitions and system architecture**, see [Authorization System](../product/authorization_system.md).

This document focuses on **HOW to use** the authorization system effectively in your code.

---

## Patterns

### Pattern 1: ADT Authorization States

HealthHub uses `AuthorizationState` ADT with 4 variants. See [Authorization System](../product/authorization_system.md) for complete definitions.

```python
type AuthorizationState = (
    PatientAuthorized    # Patient with patient_id
    | DoctorAuthorized   # Doctor with can_prescribe capability
    | AdminAuthorized    # Full system access
    | Unauthorized       # Failed auth with reason
)
```

**Key Benefits**:
- Compile-time safety - typos caught by type checker
- Contextual data in each variant (patient_id, doctor_id, can_prescribe, reason)
- Exhaustive pattern matching enforced by MyPy

---

### Pattern 2: Pattern Matching for Access Control

```python
# GOOD - Exhaustive pattern matching
def check_patient_access(
    auth: AuthorizationState,
    patient_id: UUID,
) -> bool:
    match auth:
        case PatientAuthorized(patient_id=pid) if pid == patient_id:
            return True  # Own record
        case DoctorAuthorized() | AdminAuthorized():
            return True  # Medical/admin access
        case PatientAuthorized() | Unauthorized():
            return False  # Other patient or unauthorized
```

---

### Pattern 3: Capability-Based Fields

Include capabilities directly in authorization state:

```python
@dataclass(frozen=True)
class DoctorAuthorized:
    user_id: UUID
    doctor_id: UUID
    email: str
    specialization: str
    can_prescribe: bool  # Capability embedded in type
    role: Literal["doctor"] = "doctor"


@dataclass(frozen=True)
class PrescriptionRequest:
    medication: str
    dosage: str
    notes: str | None


@dataclass(frozen=True)
class AuthorizationError:
    reason: str


def prescribe(
    auth: DoctorAuthorized,
    request: PrescriptionRequest,
) -> Result[None, AuthorizationError]:
    if not auth.can_prescribe:
        return Err(AuthorizationError(reason="Doctor cannot prescribe"))

    queue_prescription_order(
        doctor_id=auth.doctor_id,
        medication=request.medication,
        dosage=request.dosage,
        notes=request.notes,
    )
    return Ok(None)
```

---

### Pattern 4: Unauthorized with Reason

Capture why authorization failed:

```python
@dataclass(frozen=True)
class Unauthorized:
    reason: str
    detail: str | None = None

# Examples
Unauthorized(reason="Token expired")
Unauthorized(reason="Insufficient permissions", detail="Doctor cannot prescribe")
Unauthorized(reason="Patient not found")
```

---

## Anti-Patterns

### Anti-Pattern 1: String-Based Role Checking

```python
# BAD - String comparison is error-prone
def check_access(user: User) -> bool:
    if user.role == "doktor":  # Typo goes unnoticed
        return True
    return False

# GOOD - ADT pattern matching
def check_access(auth: AuthorizationState) -> bool:
    match auth:
        case DoctorAuthorized():
            return True
        case _:
            return False
```

---

### Anti-Pattern 2: Boolean Authorization

```python
# BAD - No context about why or who
def is_authorized(user: User) -> bool:
    return user.role in ["doctor", "admin"]

# GOOD - ADT carries context
def get_authorization(user: User) -> AuthorizationState:
    match user.role:
        case "patient":
            return PatientAuthorized(
                user_id=user.id,
                patient_id=user.patient_id,
                email=user.email,
            )
        case "doctor":
            return DoctorAuthorized(
                user_id=user.id,
                doctor_id=user.doctor_id,
                email=user.email,
                specialization=user.specialization,
                can_prescribe=user.can_prescribe,
            )
        case _:
            return Unauthorized(reason="Unknown role")
```

---

### Anti-Pattern 3: Exception-Based Authorization

```python
# BAD - Exceptions don't compose
def require_doctor(user: User) -> None:
    if user.role != "doctor":
        raise UnauthorizedException("Not a doctor")

# GOOD - Return type expresses possibility
def check_doctor(auth: AuthorizationState) -> DoctorAuthorized | Unauthorized:
    match auth:
        case DoctorAuthorized() as doctor:
            return doctor
        case _:
            return Unauthorized(reason="Not a doctor")
```

---

### Anti-Pattern 4: Optional User

```python
# BAD - None doesn't explain why
def get_current_user() -> User | None:
    # Returns None - but why?
    return None

# GOOD - ADT explains failure
def get_authorization() -> AuthorizationState:
    return Unauthorized(reason="Token missing", detail="No Authorization header")
```

---

### Anti-Pattern 5: Implicit Admin Check

```python
# BAD - Admin checks scattered everywhere
def get_patient(auth, patient_id):
    if auth.is_admin:  # Magic property check
        return get_any_patient(patient_id)
    return None

# GOOD - Explicit pattern match
def get_patient(auth: AuthorizationState, patient_id: UUID):
    match auth:
        case AdminAuthorized():
            return get_any_patient(patient_id)
        case DoctorAuthorized():
            return get_assigned_patient(patient_id)
        case PatientAuthorized(patient_id=pid) if pid == patient_id:
            return get_own_patient(patient_id)
        case _:
            return None
```

---

## Testing Authorization

```python
def test_patient_can_access_own_records() -> None:
    auth = PatientAuthorized(
        user_id=uuid4(),
        patient_id=PATIENT_ID,
        email="patient@example.com",
    )

    assert check_patient_access(auth, PATIENT_ID) is True

def test_patient_cannot_access_other_records() -> None:
    auth = PatientAuthorized(
        user_id=uuid4(),
        patient_id=PATIENT_ID,
        email="patient@example.com",
    )

    assert check_patient_access(auth, OTHER_PATIENT_ID) is False

def test_unauthorized_has_reason() -> None:
    auth = Unauthorized(reason="Token expired")

    match auth:
        case Unauthorized(reason=r):
            assert r == "Token expired"
```

---

## Related Documentation

### Product Documentation
- [Authorization System](../product/authorization_system.md) - ADT definitions and system architecture
- [Authentication](../product/authentication.md) - JWT token handling

### Best Practices
- [Testing](testing.md) - Comprehensive testing patterns

---

**Last Updated**: 2025-11-25  
**Supersedes**: none  
**Referenced by**: README.md, ../product/authorization_system.md
