"""FastAPI dependencies for authorization.

Implements JWT-based authentication with role-based access control.
Uses ADT pattern for authorization state: PatientAuthorized | DoctorAuthorized | AdminAuthorized | Unauthorized
"""

from dataclasses import dataclass
from typing import Annotated
from collections.abc import AsyncGenerator, Generator
from uuid import UUID
from typing_extensions import assert_never

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth import verify_token, TokenData, TokenType
from app.auth.jwt import TokenValidationSuccess, TokenValidationError
from app.container import ApplicationContainer
from app.domain.lookup_result import (
    DoctorFound,
    DoctorMissingById,
    DoctorMissingByUserId,
    is_doctor_lookup_result,
)
from effectful.domain.optional_value import from_optional_value, to_optional_value
from app.effects.healthcare import GetDoctorById
from app.effects.notification import LogAuditEvent
from app.interpreters.auditing_interpreter import AuditContext, AuditedCompositeInterpreter
from app.interpreters.composite_interpreter import (
    AllEffects,
    CompositeInterpreter,
)
from app.protocols.database import DatabasePool
from app.protocols.observability import ObservabilityInterpreter
from app.protocols.redis_factory import RedisClientFactory
from app.protocols.interpreter_factory import InterpreterFactory
from app.programs.runner import run_program


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
# Container and resource dependencies
# ============================================================================


def get_container(request: Request) -> ApplicationContainer:
    """Get application container from app state.

    Container holds all application-scoped resources (database, metrics).
    Created once at startup, accessed via dependency injection.

    Testing: Override with app.dependency_overrides[get_container] = lambda r: test_container
    """
    container: ApplicationContainer = request.app.state.container
    return container


def get_database_pool(
    container: Annotated[ApplicationContainer, Depends(get_container)],
) -> DatabasePool:
    """Get database pool from container.

    Returns protocol type (DatabasePool), not concrete implementation.

    Testing: Container holds pytest-mock mock when using dependency overrides
    """
    return container.database_pool


def get_observability_interpreter(
    container: Annotated[ApplicationContainer, Depends(get_container)],
) -> ObservabilityInterpreter:
    """Get observability interpreter from container.

    Returns protocol type, lifecycle invisible to consumers.

    Testing: Container holds pytest-mock mock when using dependency overrides
    """
    return container.observability_interpreter


def get_redis_factory(
    container: Annotated[ApplicationContainer, Depends(get_container)],
) -> RedisClientFactory:
    """Get Redis client factory from container.

    Returns protocol type (RedisClientFactory), used for creating per-request Redis clients.

    Testing: Container holds pytest-mock mock when using dependency overrides
    """
    return container.redis_factory


def get_interpreter_factory(
    container: Annotated[ApplicationContainer, Depends(get_container)],
) -> InterpreterFactory:
    """Get interpreter factory from container.

    Returns protocol type (InterpreterFactory), used for creating interpreters with managed Redis lifecycle.

    Testing: Container holds pytest-mock mock when using dependency overrides
    """
    return container.interpreter_factory


async def get_composite_interpreter(
    interpreter_factory: Annotated[InterpreterFactory, Depends(get_interpreter_factory)],
) -> AsyncGenerator[CompositeInterpreter, None]:
    """Create CompositeInterpreter with automatic Redis cleanup.

    Uses interpreter factory from container to create interpreter with managed Redis lifecycle.
    Factory handles Redis client creation and cleanup automatically.

    Testing: interpreter_factory is pytest-mock mock from container override
    """
    async with interpreter_factory.create_composite() as interpreter:
        yield interpreter


# ============================================================================
# Token validation dependency
# ============================================================================


def get_token_data(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> TokenData:
    """Validate JWT access token and return token data.

    Args:
        credentials: Parsed bearer credentials from the Authorization header.

    Returns:
        Decoded token payload.

    Raises:
        HTTPException: When the token is missing, expired, or invalid.

    Effects:
        verify_token (JWT validation)
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
    request: Request,
    token_data: Annotated[TokenData, Depends(get_token_data)],
    interpreter_factory: Annotated[InterpreterFactory, Depends(get_interpreter_factory)],
) -> AuthorizationState:
    """Get current user authorization state from JWT token.

    Returns appropriate ADT variant based on user role:
    - PatientAuthorized: Patient with patient_id from JWT (no DB query)
    - DoctorAuthorized: Doctor with doctor_id from JWT + DB query for can_prescribe
    - AdminAuthorized: Admin user (no DB query)
    - Unauthorized: Invalid role or missing profile

    Performance optimization: Uses patient_id/doctor_id from JWT payload.
    Eliminates 1 DB query for patients, reduces to 1 query for doctors (can_prescribe only).

    Args:
        request: FastAPI request for capturing audit context.
        token_data: Validated JWT payload from `get_token_data`.
        interpreter_factory: Injected interpreter factory from container.

    Returns:
        AuthorizationState ADT variant representing the caller.

    Raises:
        HTTPException: If the token is invalid (propagated from dependencies).

    Effects:
        GetDoctorById
        LogAuditEvent
    """
    async with interpreter_factory.create_composite() as interpreter:
        match token_data.role:
            case "patient":
                # Use patient_id from JWT (no DB query)
                patient_id_value = from_optional_value(token_data.patient_id)
                if patient_id_value is None:
                    return Unauthorized(
                        reason="no_profile",
                        detail="Patient profile not found. Complete profile setup first.",
                    )

                auth_state: AuthorizationState = PatientAuthorized(
                    user_id=token_data.user_id,
                    patient_id=patient_id_value,
                    email=token_data.email,
                )

            case "doctor":
                # Use doctor_id from JWT, but query for can_prescribe capability
                doctor_id_value = from_optional_value(token_data.doctor_id)
                if doctor_id_value is None:
                    return Unauthorized(
                        reason="no_profile",
                        detail="Doctor profile not found. Complete profile setup first.",
                    )

                doctor_id = doctor_id_value

                # Query only for can_prescribe and specialization (capabilities can change)
                def doctor_program() -> (
                    Generator[
                        AllEffects, object, DoctorFound | DoctorMissingById | DoctorMissingByUserId
                    ]
                ):
                    result = yield GetDoctorById(doctor_id=doctor_id)
                    assert is_doctor_lookup_result(result)
                    return result

                doctor_result = await run_program(doctor_program(), interpreter)

                match doctor_result:
                    case DoctorFound(doctor=doctor):
                        auth_state = DoctorAuthorized(
                            user_id=token_data.user_id,
                            doctor_id=doctor_id_value,
                            email=token_data.email,
                            specialization=doctor.specialization,
                            can_prescribe=doctor.can_prescribe,
                        )
                    case DoctorMissingById() | DoctorMissingByUserId():
                        return Unauthorized(
                            reason="no_profile",
                            detail="Doctor profile not found or was deleted.",
                        )
                    case _:
                        assert_never(doctor_result)

            case "admin":
                auth_state = AdminAuthorized(
                    user_id=token_data.user_id,
                    email=token_data.email,
                )

            case _:
                return Unauthorized(
                    reason="invalid_role", detail=f"Unknown role: {token_data.role}"
                )

        def audit_program() -> Generator[AllEffects, object, bool]:
            yield LogAuditEvent(
                user_id=token_data.user_id,
                action="authorize_user",
                resource_type="auth",
                resource_id=token_data.user_id,
                ip_address=to_optional_value(
                    request.client.host if request.client else None,
                    reason="not_provided",
                ),
                user_agent=to_optional_value(
                    request.headers.get("user-agent"), reason="not_provided"
                ),
                metadata=to_optional_value({"role": token_data.role}),
            )
            return True

        await run_program(audit_program(), interpreter)

        return auth_state


async def get_audited_composite_interpreter(
    request: Request,
    interpreter_factory: Annotated[InterpreterFactory, Depends(get_interpreter_factory)],
    auth: Annotated[AuthorizationState, Depends(get_current_user)],
) -> AsyncGenerator[AuditedCompositeInterpreter, None]:
    """Create AuditedCompositeInterpreter with audit context + Redis cleanup.

    Uses interpreter factory from container to create audited interpreter with managed Redis lifecycle.
    Factory handles Redis client creation and cleanup automatically.

    Testing: interpreter_factory is pytest-mock mock from container override
    """
    # Extract request metadata for audit context
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    # Extract user_id from authorized state (auth is always authorized at this point)
    user_id: UUID
    match auth:
        case (
            PatientAuthorized(user_id=uid)
            | DoctorAuthorized(user_id=uid)
            | AdminAuthorized(user_id=uid)
        ):
            user_id = uid
        case Unauthorized():
            # This should never happen - get_current_user raises HTTPException for unauthorized
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    # Create audit context
    audit_context = AuditContext(
        user_id=user_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    # Use factory to create audited interpreter with automatic Redis cleanup
    async with interpreter_factory.create_audited(audit_context) as interpreter:
        yield interpreter


# ============================================================================
# Role-specific dependencies (raise 403 if wrong role)
# ============================================================================


async def require_patient(
    auth: Annotated[AuthorizationState, Depends(get_current_user)],
) -> PatientAuthorized:
    """Require patient authorization.

    Args:
        auth: Authorization state provided by `get_current_user`.

    Returns:
        PatientAuthorized state when the caller is a patient.

    Raises:
        HTTPException: If the caller is not a patient or is unauthorized.
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

    Args:
        auth: Authorization state provided by `get_current_user`.

    Returns:
        DoctorAuthorized state when the caller is a doctor.

    Raises:
        HTTPException: If the caller is not a doctor or is unauthorized.
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

    Args:
        auth: Authorization state provided by `get_current_user`.

    Returns:
        AdminAuthorized state when the caller is an admin.

    Raises:
        HTTPException: If the caller is not an admin or is unauthorized.
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

    Args:
        auth: Authorization state provided by `get_current_user`.

    Returns:
        DoctorAuthorized or AdminAuthorized state when the caller has privileges.

    Raises:
        HTTPException: If the caller is neither doctor nor admin or is unauthorized.
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

    Args:
        auth: Authorization state provided by `get_current_user`.

    Returns:
        PatientAuthorized, DoctorAuthorized, or AdminAuthorized state.

    Raises:
        HTTPException: If authorization failed.
    """
    match auth:
        case Unauthorized(detail=detail):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=detail,
            )
        case PatientAuthorized() | DoctorAuthorized() | AdminAuthorized():
            return auth
