"""FastAPI dependencies for authorization.

Implements JWT-based authentication with role-based access control.
Uses ADT pattern for authorization state: PatientAuthorized | DoctorAuthorized | AdminAuthorized | Unauthorized
"""

from dataclasses import dataclass
from typing import Annotated
from collections.abc import Generator
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import redis.asyncio as redis

from app.auth import verify_token, TokenData, TokenType
from app.auth.jwt import TokenValidationSuccess, TokenValidationError
from app.infrastructure import get_database_manager
from app.interpreters.composite_interpreter import AllEffects, CompositeInterpreter
from app.programs.runner import run_program
from app.effects.healthcare import GetDoctorById


# Security scheme for JWT Bearer authentication
security = HTTPBearer()


# ============================================================================
# Authorization ADT - Make invalid authorization states unrepresentable
# ============================================================================


@dataclass(frozen=True)
class PatientAuthorized:
    """Patient user authorization state."""

    user_id: UUID
    patient_id: UUID
    email: str
    role: str = "patient"


@dataclass(frozen=True)
class DoctorAuthorized:
    """Doctor user authorization state."""

    user_id: UUID
    doctor_id: UUID
    email: str
    specialization: str
    can_prescribe: bool
    role: str = "doctor"


@dataclass(frozen=True)
class AdminAuthorized:
    """Admin user authorization state."""

    user_id: UUID
    email: str
    role: str = "admin"


@dataclass(frozen=True)
class Unauthorized:
    """Unauthorized access attempt."""

    reason: str
    detail: str


type AuthorizationState = PatientAuthorized | DoctorAuthorized | AdminAuthorized | Unauthorized


# ============================================================================
# Token validation dependency
# ============================================================================


def get_token_data(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> TokenData:
    """Validate JWT access token and return token data.

    Raises HTTPException 401 if token is invalid or expired.
    """
    token = credentials.credentials
    result = verify_token(token, TokenType.ACCESS)

    match result:
        case TokenValidationSuccess(token_data=data):
            return data
        case TokenValidationError(reason=reason, detail=detail):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {detail}" if reason != "expired" else "Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )


# ============================================================================
# Authorization state dependency
# ============================================================================


async def get_current_user(
    token_data: Annotated[TokenData, Depends(get_token_data)],
) -> AuthorizationState:
    """Get current user authorization state from JWT token.

    Returns appropriate ADT variant based on user role:
    - PatientAuthorized: Patient with patient_id from JWT (no DB query)
    - DoctorAuthorized: Doctor with doctor_id from JWT + DB query for can_prescribe
    - AdminAuthorized: Admin user (no DB query)
    - Unauthorized: Invalid role or missing profile

    Performance optimization: Uses patient_id/doctor_id from JWT payload.
    Eliminates 1 DB query for patients, reduces to 1 query for doctors (can_prescribe only).
    """
    db_manager = get_database_manager()
    pool = db_manager.get_pool()
    redis_client: redis.Redis[bytes] = redis.Redis(
        host="redis",
        port=6379,
        decode_responses=False,
    )
    interpreter = CompositeInterpreter(pool, redis_client)

    match token_data.role:
        case "patient":
            # Use patient_id from JWT (no DB query)
            if token_data.patient_id is None:
                await redis_client.aclose()
                return Unauthorized(
                    reason="no_profile",
                    detail="Patient profile not found. Complete profile setup first.",
                )

            await redis_client.aclose()
            return PatientAuthorized(
                user_id=token_data.user_id,
                patient_id=token_data.patient_id,
                email=token_data.email,
            )

        case "doctor":
            # Use doctor_id from JWT, but query for can_prescribe capability
            if token_data.doctor_id is None:
                await redis_client.aclose()
                return Unauthorized(
                    reason="no_profile",
                    detail="Doctor profile not found. Complete profile setup first.",
                )

            # Query only for can_prescribe and specialization (capabilities can change)
            def doctor_program() -> Generator[AllEffects, object, object | None]:
                return (yield GetDoctorById(doctor_id=token_data.doctor_id))

            doctor = await run_program(doctor_program(), interpreter)

            if doctor is None:
                await redis_client.aclose()
                return Unauthorized(
                    reason="no_profile",
                    detail="Doctor profile not found or was deleted.",
                )

            await redis_client.aclose()
            return DoctorAuthorized(
                user_id=token_data.user_id,
                doctor_id=token_data.doctor_id,
                email=token_data.email,
                specialization=doctor.specialization,
                can_prescribe=doctor.can_prescribe,
            )

        case "admin":
            await redis_client.aclose()
            return AdminAuthorized(
                user_id=token_data.user_id,
                email=token_data.email,
            )

        case _:
            await redis_client.aclose()
            return Unauthorized(reason="invalid_role", detail=f"Unknown role: {token_data.role}")


# ============================================================================
# Role-specific dependencies (raise 403 if wrong role)
# ============================================================================


async def require_patient(
    auth: Annotated[AuthorizationState, Depends(get_current_user)],
) -> PatientAuthorized:
    """Require patient authorization.

    Raises HTTPException 403 if not a patient.
    """
    match auth:
        case PatientAuthorized() as patient:
            return patient
        case Unauthorized(detail=detail):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=detail,
            )
        case _:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This endpoint requires patient role",
            )


async def require_doctor(
    auth: Annotated[AuthorizationState, Depends(get_current_user)],
) -> DoctorAuthorized:
    """Require doctor authorization.

    Raises HTTPException 403 if not a doctor.
    """
    match auth:
        case DoctorAuthorized() as doctor:
            return doctor
        case Unauthorized(detail=detail):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=detail,
            )
        case _:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This endpoint requires doctor role",
            )


async def require_admin(
    auth: Annotated[AuthorizationState, Depends(get_current_user)],
) -> AdminAuthorized:
    """Require admin authorization.

    Raises HTTPException 403 if not an admin.
    """
    match auth:
        case AdminAuthorized() as admin:
            return admin
        case Unauthorized(detail=detail):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=detail,
            )
        case _:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This endpoint requires admin role",
            )


async def require_doctor_or_admin(
    auth: Annotated[AuthorizationState, Depends(get_current_user)],
) -> DoctorAuthorized | AdminAuthorized:
    """Require doctor or admin authorization.

    Raises HTTPException 403 if neither doctor nor admin.
    """
    match auth:
        case DoctorAuthorized() as doctor:
            return doctor
        case AdminAuthorized() as admin:
            return admin
        case Unauthorized(detail=detail):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=detail,
            )
        case PatientAuthorized():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This endpoint requires doctor or admin role",
            )


async def require_authenticated(
    auth: Annotated[AuthorizationState, Depends(get_current_user)],
) -> PatientAuthorized | DoctorAuthorized | AdminAuthorized:
    """Require any authenticated user (not Unauthorized).

    Raises HTTPException 403 if authorization failed.
    """
    match auth:
        case Unauthorized(detail=detail):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=detail,
            )
        case PatientAuthorized() | DoctorAuthorized() | AdminAuthorized():
            return auth
