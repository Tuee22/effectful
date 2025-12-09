# Authentication Feature

**Status**: Authoritative source
**Supersedes**: none
**Referenced by**: demo/healthhub/documents/tutorials/README.md

> **Purpose**: Complete reference for HealthHub authentication system: JWT authentication, AuthorizationState ADT, RBAC enforcement, and session management.

> **Core Doctrines**: For comprehensive patterns, see:
> - [ADTs and Result Types](../../../../../documents/tutorials/adts_and_results.md)
> - [Code Quality](../../../../../documents/engineering/code_quality.md)
> - [Authentication Engineering](../../engineering/authentication.md)

## Prerequisites

- Docker workflow running; commands executed via `docker compose -f docker/docker-compose.yml`.
- Completed [Beginner Journey](../01_journeys/beginner_journey.md).
- Familiarity with JWT, bcrypt, Python type hints, pattern matching.

## Learning Objectives

- Understand JWT authentication flow (login → token issue → refresh → logout)
- Define AuthorizationState ADT with 4 variants (PatientAuthorized, DoctorAuthorized, AdminAuthorized, Unauthorized)
- Implement RBAC enforcement using ADT pattern matching
- Manage session lifecycle (login, token refresh, logout)
- Apply bcrypt password hashing for secure credential storage
- Write e2e tests for all auth state transitions

## Overview

**Authentication System Architecture**:
- **Frontend**: React + JWT stored in localStorage
- **Backend**: FastAPI + bcrypt password hashing + JWT token generation
- **Token Storage**: JWT in localStorage as `healthhub-auth`
- **Token Validation**: FastAPI dependency injection extracts and validates JWT
- **Authorization**: AuthorizationState ADT determines user capabilities

**Authentication Flow**:
1. User submits email/password to `/api/auth/login`
2. Backend verifies password hash (bcrypt)
3. Backend generates JWT with user_id, role, and role-specific context
4. Frontend stores JWT in localStorage
5. Frontend includes JWT in `Authorization: Bearer <token>` header for all API requests
6. Backend validates JWT and extracts AuthorizationState
7. API endpoints pattern match on AuthorizationState to enforce RBAC

## Domain Models

### User Model

**File**: `demo/healthhub/backend/app/domain/user.py`

```python
# file: demo/healthhub/backend/app/domain/user.py
from dataclasses import dataclass
from uuid import UUID
from typing import Literal

@dataclass(frozen=True)
class User:
    """
    User account with role and credentials.

    Roles:
    - patient: Can view own data only
    - doctor: Can view all patients, create prescriptions
    - admin: Full system access
    """
    user_id: UUID
    email: str
    password_hash: str
    role: Literal["patient", "doctor", "admin"]
    is_active: bool
    created_at: str
    updated_at: str
```

### AuthorizationState ADT

**File**: `demo/healthhub/backend/app/domain/auth.py`

```python
# file: demo/healthhub/backend/app/domain/auth.py
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

@dataclass(frozen=True)
class PatientAuthorized:
    """
    Patient successfully authorized.

    Context:
    - user_id: Links to users table
    - patient_id: Links to patients table for data access
    - email: User email for display
    - role: Always "patient" (Literal type enforces)
    """
    user_id: UUID
    patient_id: UUID
    email: str
    role: Literal["patient"] = "patient"

@dataclass(frozen=True)
class DoctorAuthorized:
    """
    Doctor successfully authorized.

    Context:
    - user_id: Links to users table
    - doctor_id: Links to doctors table
    - email: User email for display
    - specialization: Medical specialty (shown in UI)
    - can_prescribe: Flag determining prescription creation access
    - role: Always "doctor" (Literal type enforces)
    """
    user_id: UUID
    doctor_id: UUID
    email: str
    specialization: str
    can_prescribe: bool
    role: Literal["doctor"] = "doctor"

@dataclass(frozen=True)
class AdminAuthorized:
    """
    Admin successfully authorized.

    Context:
    - user_id: Links to users table
    - email: User email for display
    - role: Always "admin" (Literal type enforces)

    Admins have full system access (no additional context needed).
    """
    user_id: UUID
    email: str
    role: Literal["admin"] = "admin"

@dataclass(frozen=True)
class Unauthorized:
    """
    Authorization failed.

    Reasons:
    - not_authenticated: No JWT token provided
    - invalid_token: JWT signature verification failed
    - expired_token: JWT expiration time passed
    - user_not_found: User ID in JWT not in database
    - user_inactive: User account deactivated
    - invalid_credentials: Email/password mismatch
    """
    reason: str
    detail: str | None = None

type AuthorizationState = (
    PatientAuthorized
    | DoctorAuthorized
    | AdminAuthorized
    | Unauthorized
)
```

**Why 4 variants?**
1. **PatientAuthorized**: Carries `patient_id` for querying patient-specific data
2. **DoctorAuthorized**: Carries `doctor_id`, `specialization`, `can_prescribe` for doctor features
3. **AdminAuthorized**: Full access, no additional context needed beyond `user_id`
4. **Unauthorized**: Carries `reason` for error handling and user feedback

**Benefits over string roles**:
- **Type-safe**: MyPy enforces exhaustive pattern matching
- **Self-documenting**: Each variant carries role-specific context
- **Explicit**: All auth states visible in type definition
- **Compiler-enforced**: Missing case = MyPy error

## JWT Authentication Flow

### Step 1: Login

**Endpoint**: `POST /api/auth/login`

**Request**:
```json
{
  "email": "alice.patient@example.com",
  "password": "password123"
}
```

**Backend Program**: `demo/healthhub/backend/app/programs/auth_programs.py`

```python
# file: demo/healthhub/backend/app/programs/auth_programs.py
from effectful import Effect, Result, Ok, Err
from effectful.effects import DatabaseEffect
from uuid import UUID
from typing import Generator
import bcrypt
import jwt
from datetime import datetime, timedelta

def login_program(email: str, password: str) -> Generator[Effect, Result, Result[dict]]:
    """
    Authenticate user and generate JWT token.

    Flow:
    1. Query user by email
    2. Verify password hash (bcrypt)
    3. Fetch role-specific context (patient_id, doctor_id, etc.)
    4. Generate JWT with AuthorizationState context
    5. Return JWT + user data
    """

    # Step 1: Query user by email
    user_result = yield DatabaseEffect.Query(
        query="SELECT * FROM users WHERE email = $1 AND is_active = true",
        params=(email,)
    )

    match user_result:
        case Ok(rows) if len(rows) > 0:
            user = rows[0]
        case Ok([]):
            return Err("Invalid credentials")
        case Err(error):
            return Err(f"Database error: {error}")

    # Step 2: Verify password hash
    password_bytes = password.encode('utf-8')
    hash_bytes = user["password_hash"].encode('utf-8')

    if not bcrypt.checkpw(password_bytes, hash_bytes):
        return Err("Invalid credentials")

    # Step 3: Fetch role-specific context
    match user["role"]:
        case "patient":
            context_result = yield DatabaseEffect.Query(
                query="SELECT patient_id FROM patients WHERE user_id = $1",
                params=(user["user_id"],)
            )
            match context_result:
                case Ok(rows) if len(rows) > 0:
                    patient_id = rows[0]["patient_id"]
                case _:
                    return Err("Patient record not found")

            auth_state = PatientAuthorized(
                user_id=user["user_id"],
                patient_id=patient_id,
                email=user["email"],
            )

        case "doctor":
            context_result = yield DatabaseEffect.Query(
                query="SELECT doctor_id, specialization, can_prescribe FROM doctors WHERE user_id = $1",
                params=(user["user_id"],)
            )
            match context_result:
                case Ok(rows) if len(rows) > 0:
                    doctor = rows[0]
                case _:
                    return Err("Doctor record not found")

            auth_state = DoctorAuthorized(
                user_id=user["user_id"],
                doctor_id=doctor["doctor_id"],
                email=user["email"],
                specialization=doctor["specialization"],
                can_prescribe=doctor["can_prescribe"],
            )

        case "admin":
            auth_state = AdminAuthorized(
                user_id=user["user_id"],
                email=user["email"],
            )

        case _:
            return Err("Unknown role")

    # Step 4: Generate JWT
    jwt_payload = {
        "user_id": str(auth_state.user_id),
        "email": auth_state.email,
        "role": auth_state.role,
        "exp": datetime.utcnow() + timedelta(minutes=15),  # 15 minute expiration
    }

    # Add role-specific claims
    match auth_state:
        case PatientAuthorized(patient_id=pid):
            jwt_payload["patient_id"] = str(pid)
        case DoctorAuthorized(doctor_id=did, specialization=spec, can_prescribe=can_rx):
            jwt_payload["doctor_id"] = str(did)
            jwt_payload["specialization"] = spec
            jwt_payload["can_prescribe"] = can_rx
        case AdminAuthorized():
            pass  # No additional claims
        case _:
            return Err("Invalid auth state")

    token = jwt.encode(jwt_payload, "healthhub-secret", algorithm="HS256")

    # Step 5: Return JWT + user data
    return Ok({
        "token": token,
        "user": {
            "user_id": str(auth_state.user_id),
            "email": auth_state.email,
            "role": auth_state.role,
        },
        "auth_state": auth_state,
    })
```

**Response** (200 OK):
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "user_id": "20000000-0000-0000-0000-000000000001",
    "email": "alice.patient@example.com",
    "role": "patient"
  }
}
```

**Frontend Storage**:
```javascript
// Store JWT in localStorage
localStorage.setItem('healthhub-auth', JSON.stringify({
  token: response.token,
  user: response.user,
}));
```

### Step 2: Token Validation (Dependency Injection)

**File**: `demo/healthhub/backend/app/api/dependencies.py`

```python
# file: demo/healthhub/backend/app/api/dependencies.py
from fastapi import Depends, HTTPException, Header
from demo.healthhub.backend.app.domain.auth import AuthorizationState, Unauthorized
import jwt

async def get_auth_state(
    authorization: str | None = Header(None)
) -> AuthorizationState:
    """
    FastAPI dependency: Extract and validate JWT from Authorization header.

    Returns AuthorizationState ADT.
    """

    if not authorization or not authorization.startswith("Bearer "):
        return Unauthorized(reason="not_authenticated", detail="No token provided")

    token = authorization.split(" ")[1]

    try:
        payload = jwt.decode(token, "healthhub-secret", algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return Unauthorized(reason="expired_token")
    except jwt.InvalidTokenError:
        return Unauthorized(reason="invalid_token")

    # Reconstruct AuthorizationState from JWT claims
    role = payload["role"]
    user_id = UUID(payload["user_id"])
    email = payload["email"]

    match role:
        case "patient":
            return PatientAuthorized(
                user_id=user_id,
                patient_id=UUID(payload["patient_id"]),
                email=email,
            )
        case "doctor":
            return DoctorAuthorized(
                user_id=user_id,
                doctor_id=UUID(payload["doctor_id"]),
                email=email,
                specialization=payload["specialization"],
                can_prescribe=payload["can_prescribe"],
            )
        case "admin":
            return AdminAuthorized(
                user_id=user_id,
                email=email,
            )
        case _:
            return Unauthorized(reason="invalid_token", detail="Unknown role")
```

**Usage in API endpoints**:
```python
# file: demo/healthhub/backend/app/api/patients.py
from fastapi import APIRouter, Depends, HTTPException
from demo.healthhub.backend.app.api.dependencies import get_auth_state
from demo.healthhub.backend.app.domain.auth import AuthorizationState, PatientAuthorized, DoctorAuthorized, AdminAuthorized, Unauthorized

router = APIRouter(prefix="/api/patients")

@router.get("/")
async def get_patients(
    auth_state: AuthorizationState = Depends(get_auth_state)
):
    """
    Get all patients (doctor/admin only).

    RBAC: Pattern matching on AuthorizationState enforces access control.
    """

    match auth_state:
        case DoctorAuthorized() | AdminAuthorized():
            # Authorized - fetch all patients
            # ... program execution ...
            pass

        case PatientAuthorized():
            raise HTTPException(403, "Patients cannot view patient list")

        case Unauthorized(reason=reason):
            raise HTTPException(401, f"Unauthorized: {reason}")
```

### Step 3: Token Refresh

**Endpoint**: `POST /api/auth/refresh`

**Request**:
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Backend Program**:
```python
# file: demo/healthhub/backend/app/programs/auth_programs.py
def refresh_token_program(refresh_token: str) -> Generator[Effect, Result, Result[dict]]:
    """
    Refresh expired access token using refresh token.

    Flow:
    1. Validate refresh token (7 day expiration)
    2. Query user to ensure still active
    3. Generate new access token (15 minute expiration)
    4. Return new access token
    """

    # Step 1: Validate refresh token
    try:
        payload = jwt.decode(refresh_token, "healthhub-secret", algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return Err("Refresh token expired")
    except jwt.InvalidTokenError:
        return Err("Invalid refresh token")

    user_id = UUID(payload["user_id"])

    # Step 2: Query user to ensure still active
    user_result = yield DatabaseEffect.Query(
        query="SELECT * FROM users WHERE user_id = $1 AND is_active = true",
        params=(user_id,)
    )

    match user_result:
        case Ok(rows) if len(rows) > 0:
            user = rows[0]
        case Ok([]):
            return Err("User not found or inactive")
        case Err(error):
            return Err(f"Database error: {error}")

    # Step 3: Generate new access token
    new_payload = {
        "user_id": str(user["user_id"]),
        "email": user["email"],
        "role": user["role"],
        "exp": datetime.utcnow() + timedelta(minutes=15),
    }

    # Add role-specific claims (same as login)
    # ... (fetch patient_id, doctor_id, etc.) ...

    new_token = jwt.encode(new_payload, "healthhub-secret", algorithm="HS256")

    return Ok({"token": new_token})
```

### Step 4: Logout

**Endpoint**: `POST /api/auth/logout`

**Frontend**:
```javascript
// Remove JWT from localStorage
localStorage.removeItem('healthhub-auth');

// Redirect to login page
window.location.href = '/login';
```

**Backend**: No server-side action needed (JWT is stateless). Optional: Implement token blacklist for revocation.

## RBAC Enforcement Patterns

### Pattern 1: Route Guards (Frontend)

**File**: `demo/healthhub/frontend/src/components/ProtectedRoute.tsx`

```typescript
// file: demo/healthhub/frontend/src/components/ProtectedRoute.tsx
import { Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

interface ProtectedRouteProps {
  children: React.ReactNode;
  allowedRoles: ('patient' | 'doctor' | 'admin')[];
}

export function ProtectedRoute({ children, allowedRoles }: ProtectedRouteProps) {
  const { authState } = useAuth();

  // Not authenticated
  if (authState.type !== 'Authenticated') {
    return <Navigate to="/login" />;
  }

  // Authenticated but wrong role
  if (!allowedRoles.includes(authState.user.role)) {
    return <Navigate to="/dashboard" />;
  }

  // Authorized
  return <>{children}</>;
}
```

**Usage**:
```typescript
// file: demo/healthhub/frontend/src/App.tsx
<Route
  path="/patients"
  element={
    <ProtectedRoute allowedRoles={['doctor', 'admin']}>
      <PatientsPage />
    </ProtectedRoute>
  }
/>

<Route
  path="/audit-logs"
  element={
    <ProtectedRoute allowedRoles={['admin']}>
      <AuditLogsPage />
    </ProtectedRoute>
  }
/>
```

### Pattern 2: API Protection (Backend)

**File**: `demo/healthhub/backend/app/api/appointments.py`

```python
# file: demo/healthhub/backend/app/api/appointments.py
from fastapi import APIRouter, Depends, HTTPException
from demo.healthhub.backend.app.api.dependencies import get_auth_state
from demo.healthhub.backend.app.domain.auth import AuthorizationState, PatientAuthorized, DoctorAuthorized, AdminAuthorized, Unauthorized

router = APIRouter(prefix="/api/appointments")

@router.get("/")
async def get_appointments(
    auth_state: AuthorizationState = Depends(get_auth_state)
):
    """
    Get appointments with role-based filtering.

    - Patient: Own appointments only
    - Doctor/Admin: All appointments
    """

    match auth_state:
        case PatientAuthorized(patient_id=pid):
            # Patient can only view own appointments
            program = get_appointments_for_patient(pid)
            result = await interpreter.run(program)

            match result:
                case Ok(appointments):
                    return {"appointments": appointments}
                case Err(error):
                    raise HTTPException(500, str(error))

        case DoctorAuthorized() | AdminAuthorized():
            # Doctor/Admin can view all appointments
            program = get_all_appointments()
            result = await interpreter.run(program)

            match result:
                case Ok(appointments):
                    return {"appointments": appointments}
                case Err(error):
                    raise HTTPException(500, str(error))

        case Unauthorized(reason=reason):
            raise HTTPException(401, f"Unauthorized: {reason}")
```

### Pattern 3: Feature Flags (Doctor Prescription Access)

```python
# file: demo/healthhub/backend/app/api/prescriptions.py
@router.post("/")
async def create_prescription(
    prescription_data: dict,
    auth_state: AuthorizationState = Depends(get_auth_state)
):
    """
    Create prescription (doctors only, with can_prescribe flag).
    """

    match auth_state:
        case DoctorAuthorized(doctor_id=did, can_prescribe=True):
            # Authorized - doctor can prescribe
            program = create_prescription_program(prescription_data, did)
            result = await interpreter.run(program)

            match result:
                case Ok(prescription):
                    return {"prescription": prescription}
                case Err(error):
                    raise HTTPException(400, str(error))

        case DoctorAuthorized(can_prescribe=False):
            raise HTTPException(403, "Doctor not authorized to prescribe medications")

        case PatientAuthorized() | AdminAuthorized():
            raise HTTPException(403, "Only doctors can create prescriptions")

        case Unauthorized(reason=reason):
            raise HTTPException(401, f"Unauthorized: {reason}")
```

## Password Hashing (Bcrypt)

**Registration Program**:
```python
# file: demo/healthhub/backend/app/programs/auth_programs.py
import bcrypt

def register_user_program(
    email: str, password: str, role: str
) -> Generator[Effect, Result, Result[dict]]:
    """
    Register new user with bcrypt password hashing.
    """

    # Hash password with bcrypt (salt rounds: 12)
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt(rounds=12)
    password_hash = bcrypt.hashpw(password_bytes, salt)
    password_hash_str = password_hash.decode('utf-8')

    # Insert user into database
    user_result = yield DatabaseEffect.Execute(
        query="""
            INSERT INTO users (email, password_hash, role, is_active)
            VALUES ($1, $2, $3, true)
            RETURNING user_id, email, role, created_at
        """,
        params=(email, password_hash_str, role)
    )

    match user_result:
        case Ok(rows):
            return Ok(rows[0])
        case Err(error):
            return Err(f"Registration failed: {error}")
```

**Security Properties**:
- **Salt**: Unique per password (prevents rainbow table attacks)
- **Cost factor**: 12 rounds (2^12 = 4096 iterations)
- **Slow hashing**: ~250ms per hash (protects against brute force)
- **Adaptive**: Can increase cost factor as hardware improves

## E2E Tests

**File**: `demo/healthhub/tests/pytest/e2e/test_login_flow.py`

```python
# file: demo/healthhub/tests/pytest/e2e/test_login_flow.py
import pytest
from demo.healthhub.backend.app.programs.auth_programs import login_program
from effectful import Ok, Err

@pytest.mark.asyncio
async def test_patient_login_success(clean_healthhub_state, postgres_interpreter):
    """E2E: Patient login with valid credentials."""

    program = login_program("alice.patient@example.com", "password123")
    result = await postgres_interpreter.run(program)

    match result:
        case Ok(auth_data):
            assert auth_data["user"]["role"] == "patient"
            assert "token" in auth_data
            assert auth_data["user"]["email"] == "alice.patient@example.com"
        case Err(error):
            pytest.fail(f"Expected Ok, got Err: {error}")

@pytest.mark.asyncio
async def test_login_invalid_password(clean_healthhub_state, postgres_interpreter):
    """E2E: Login fails with invalid password."""

    program = login_program("alice.patient@example.com", "wrong_password")
    result = await postgres_interpreter.run(program)

    match result:
        case Err(error):
            assert "invalid credentials" in error.lower()
        case Ok(_):
            pytest.fail("Expected Err for invalid password, got Ok")

@pytest.mark.asyncio
async def test_doctor_login_includes_can_prescribe(clean_healthhub_state, postgres_interpreter):
    """E2E: Doctor login includes can_prescribe flag."""

    program = login_program("dr.smith@healthhub.com", "password123")
    result = await postgres_interpreter.run(program)

    match result:
        case Ok(auth_data):
            assert auth_data["user"]["role"] == "doctor"
            # JWT payload should include can_prescribe
            import jwt
            decoded = jwt.decode(auth_data["token"], "healthhub-secret", algorithms=["HS256"])
            assert decoded["can_prescribe"] is True
        case Err(error):
            pytest.fail(f"Expected Ok, got Err: {error}")
```

## Summary

**You have learned**:
- ✅ JWT authentication flow (login → token → validation → refresh → logout)
- ✅ AuthorizationState ADT with 4 variants (type-safe RBAC)
- ✅ Pattern matching for RBAC enforcement (frontend + backend)
- ✅ Bcrypt password hashing (secure credential storage)
- ✅ FastAPI dependency injection for auth state extraction
- ✅ E2E testing for auth workflows

**Key Takeaways**:
1. **ADT > String Roles**: Type-safe, exhaustive, self-documenting
2. **JWT Stateless**: No server-side session storage needed
3. **Dependency Injection**: Centralized auth validation in FastAPI
4. **Pattern Matching**: Compiler-enforced RBAC coverage
5. **Bcrypt**: Slow hashing protects against brute force
6. **Context in ADT**: Each role variant carries role-specific data

## Cross-References

- [Beginner Journey - AuthorizationState ADT](../01_journeys/beginner_journey.md#step-2-login-as-patient)
- [HealthHub Authentication Engineering](../../engineering/authentication.md)
- [ADTs and Result Types](../../../../../documents/tutorials/adts_and_results.md)
- [Code Quality - Type Safety](../../../../../documents/engineering/code_quality.md#type-safety-doctrines)
- [Patient Guide](../02_roles/patient_guide.md)
- [Doctor Guide](../02_roles/doctor_guide.md)
