"""Authentication API endpoints.

Boundary: OUTSIDE_PROOF
Target-Language: N/A (assumed correct)

Implements JWT dual-token authentication pattern:
- Access token: 15 minutes (returned in response body)
- Refresh token: 7 days (set in HttpOnly cookie)

Assumptions:
- [Library] PyJWT correctly implements JWT signing/verification
- [Security] bcrypt correctly hashes and verifies passwords
- [Framework] FastAPI cookie handling is secure (HttpOnly, SameSite)
"""

from collections.abc import Generator
from dataclasses import dataclass
from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.auth import (
    TokenType,
    TokenValidationError,
    TokenValidationSuccess,
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
    verify_token,
)
from app.config import Settings
from app.domain.doctor import Doctor
from app.domain.lookup_result import (
    DoctorFound,
    DoctorMissingById,
    DoctorMissingByUserId,
    PatientFound,
    PatientMissingById,
    PatientMissingByUserId,
    UserFound,
    UserMissingByEmail,
    is_doctor_lookup_result,
    is_patient_lookup_result,
    is_user_lookup_result,
)
from effectful.domain.optional_value import (
    Absent,
    OptionalValue,
    Provided,
    from_optional_value,
    to_optional_value,
)
from app.domain.patient import Patient
from app.domain.user import User, UserRole
from app.effects.healthcare import (
    CreatePatient,
    CreateUser,
    GetDoctorByUserId,
    GetPatientByUserId,
    GetUserByEmail,
    UpdateUserLastLogin,
)
from app.api.dependencies import get_composite_interpreter
from app.effects.notification import LogAuditEvent
from app.infrastructure.rate_limiter import rate_limit
from app.interpreters.composite_interpreter import AllEffects, CompositeInterpreter
from app.programs.runner import run_program, unwrap_program_result


router = APIRouter()


class LoginRequest(BaseModel):
    """Login request body."""

    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    """Login response body with access token."""

    access_token: str
    token_type: str
    user_id: str
    email: str
    role: str


class RegisterRequest(BaseModel):
    """User registration request."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    email: EmailStr
    password: str
    role: UserRole

    # Patient-specific fields (required when role="patient")
    first_name: OptionalValue[str] = Field(default_factory=lambda: Absent("not_provided"))
    last_name: OptionalValue[str] = Field(default_factory=lambda: Absent("not_provided"))
    date_of_birth: OptionalValue[date] = Field(default_factory=lambda: Absent("not_provided"))
    blood_type: OptionalValue[str] = Field(default_factory=lambda: Absent("not_provided"))
    allergies: list[str] = Field(default_factory=list)
    insurance_id: OptionalValue[str] = Field(default_factory=lambda: Absent("not_provided"))
    emergency_contact: OptionalValue[str] = Field(default_factory=lambda: Absent("not_provided"))
    phone: OptionalValue[str] = Field(default_factory=lambda: Absent("not_provided"))
    address: OptionalValue[str] = Field(default_factory=lambda: Absent("not_provided"))

    @field_validator(
        "first_name",
        "last_name",
        "blood_type",
        "insurance_id",
        "emergency_contact",
        "phone",
        "address",
        mode="before",
    )
    @classmethod
    def normalize_optional_str(cls, value: object) -> OptionalValue[str]:
        if isinstance(value, (Provided, Absent)):
            return value
        return to_optional_value(value if isinstance(value, str) else None, reason="not_provided")

    @field_validator("date_of_birth", mode="before")
    @classmethod
    def normalize_optional_date(cls, value: object) -> OptionalValue[date]:
        if isinstance(value, (Provided, Absent)):
            return value
        if value is None:
            return Absent("not_provided")
        if isinstance(value, date):
            return to_optional_value(value, reason="not_provided")
        if isinstance(value, str):
            try:
                parsed = date.fromisoformat(value)
            except Exception as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="date_of_birth must be ISO date when provided",
                ) from exc
            return to_optional_value(parsed, reason="not_provided")
        raise TypeError("date_of_birth must be a date or ISO date string when provided")


class RegisterResponse(BaseModel):
    """Registration response."""

    user_id: str
    email: str
    role: str
    message: str


class RefreshResponse(BaseModel):
    """Refresh token response with new access token."""

    access_token: str
    token_type: str
    user_id: str
    email: str
    role: str


@dataclass(frozen=True)
class PatientLoginSuccess:
    user: User
    patient: Patient


@dataclass(frozen=True)
class LoginInvalidCredentials:
    reason: str


@dataclass(frozen=True)
class LoginInactiveAccount:
    status: str


@dataclass(frozen=True)
class DoctorLoginSuccess:
    user: User
    doctor: Doctor


@dataclass(frozen=True)
class AdminLoginSuccess:
    user: User


@dataclass(frozen=True)
class PatientProfileMissing:
    user: User


@dataclass(frozen=True)
class DoctorProfileMissing:
    user: User


type LoginResult = (
    PatientLoginSuccess
    | DoctorLoginSuccess
    | AdminLoginSuccess
    | PatientProfileMissing
    | DoctorProfileMissing
    | LoginInvalidCredentials
    | LoginInactiveAccount
)


@dataclass(frozen=True)
class RegisterSuccess:
    user: User


@dataclass(frozen=True)
class RegisterEmailExists:
    email: str


type RegisterResult = RegisterSuccess | RegisterEmailExists


@dataclass(frozen=True)
class NormalizedPatientRegistration:
    first_name: str
    last_name: str
    date_of_birth: date
    blood_type: OptionalValue[str]
    allergies: list[str]
    insurance_id: OptionalValue[str]
    emergency_contact: str
    phone: OptionalValue[str]
    address: OptionalValue[str]


def _normalize_patient_registration(request: RegisterRequest) -> NormalizedPatientRegistration:
    """Normalize patient-specific registration fields to OptionalValue semantics."""
    first_name = from_optional_value(request.first_name)
    last_name = from_optional_value(request.last_name)
    date_of_birth = from_optional_value(request.date_of_birth)
    emergency_contact = from_optional_value(request.emergency_contact)

    if not first_name or not last_name or date_of_birth is None or not emergency_contact:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Patient registration requires: first_name, last_name, date_of_birth, emergency_contact",
        )

    return NormalizedPatientRegistration(
        first_name=first_name,
        last_name=last_name,
        date_of_birth=date_of_birth,
        blood_type=request.blood_type,
        allergies=request.allergies,
        insurance_id=request.insurance_id,
        emergency_contact=emergency_contact,
        phone=request.phone,
        address=request.address,
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    http_request: Request,
    response: Response,
    interpreter: Annotated[CompositeInterpreter, Depends(get_composite_interpreter)],
    _rate_limit: Annotated[None, Depends(rate_limit(5, 60))],
) -> LoginResponse:
    """Authenticate user and return JWT tokens.

    Args:
        request: Login payload containing email and password.
        http_request: Request object for audit metadata.
        response: Response used to set refresh token cookie.
        interpreter: Injected composite interpreter.
        _rate_limit: Rate limit guard (FastAPI dependency).

    Returns:
        LoginResponse with access token and user identity fields.

    Raises:
        HTTPException: For invalid credentials, inactive accounts, or unexpected errors.

    Effects:
        GetUserByEmail
        UpdateUserLastLogin
        GetPatientByUserId | GetDoctorByUserId
        LogAuditEvent
    """

    def login_program() -> Generator[AllEffects, object, LoginResult]:
        user_result = yield GetUserByEmail(email=request.email)
        assert is_user_lookup_result(user_result)
        match user_result:
            case UserMissingByEmail():
                return LoginInvalidCredentials(reason="Invalid email or password")
            case UserFound(user=user):
                current_user = user
            # MyPy enforces exhaustiveness - no fallback needed

        if not verify_password(request.password, current_user.password_hash):
            return LoginInvalidCredentials(reason="Invalid email or password")

        if current_user.status.value != "active":
            return LoginInactiveAccount(status=current_user.status.value)

        yield UpdateUserLastLogin(user_id=current_user.id)

        # Pattern match on UserRole enum for type-safe role handling
        match current_user.role:
            case UserRole.PATIENT:
                patient_result = yield GetPatientByUserId(user_id=current_user.id)
                assert is_patient_lookup_result(patient_result)
                match patient_result:
                    case PatientFound(patient=found_patient):
                        result: LoginResult = PatientLoginSuccess(
                            user=current_user, patient=found_patient
                        )
                    case PatientMissingByUserId() | PatientMissingById():
                        result = PatientProfileMissing(user=current_user)
                    # MyPy enforces exhaustiveness - no fallback needed

            case UserRole.DOCTOR:
                doctor_result = yield GetDoctorByUserId(user_id=current_user.id)
                assert is_doctor_lookup_result(doctor_result)
                match doctor_result:
                    case DoctorFound(doctor=found_doctor):
                        result = DoctorLoginSuccess(user=current_user, doctor=found_doctor)
                    case DoctorMissingByUserId() | DoctorMissingById():
                        result = DoctorProfileMissing(user=current_user)
                    # MyPy enforces exhaustiveness - no fallback needed

            case UserRole.ADMIN:
                result = AdminLoginSuccess(user=current_user)
            # MyPy enforces exhaustiveness - no fallback needed

        yield LogAuditEvent(
            user_id=current_user.id,
            action="login_success",
            resource_type="auth",
            resource_id=current_user.id,
            ip_address=to_optional_value(
                http_request.client.host if http_request.client else None,
                reason="not_provided",
            ),
            user_agent=to_optional_value(
                http_request.headers.get("user-agent"), reason="not_provided"
            ),
            metadata=to_optional_value(None, reason="not_provided"),
        )

        return result

    login_result = unwrap_program_result(await run_program(login_program(), interpreter))

    patient_id_for_token: UUID | None = None
    doctor_id_for_token: UUID | None = None

    match login_result:
        case LoginInvalidCredentials(reason=reason):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=reason,
            )
        case LoginInactiveAccount(status=acct_status):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Account is {acct_status}",
            )
        case PatientProfileMissing(user=user):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient profile not found. Complete profile setup first.",
            )
        case DoctorProfileMissing(user=user):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Doctor profile not found. Complete profile setup first.",
            )
        case PatientLoginSuccess(user=user, patient=patient):
            patient_id_for_token = patient.id
            authed_user = user
        case DoctorLoginSuccess(user=user, doctor=doctor):
            doctor_id_for_token = doctor.id
            authed_user = user
        case AdminLoginSuccess(user=user):
            authed_user = user
        case _:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unexpected login result",
            )

    # Get settings from app.state
    settings: Settings = http_request.app.state.settings

    # Set refresh token in HttpOnly cookie (7 days)
    refresh_token = create_refresh_token(
        settings,
        authed_user.id,
        authed_user.email,
        authed_user.role.value,
        patient_id=to_optional_value(patient_id_for_token, reason="not_included"),
        doctor_id=to_optional_value(doctor_id_for_token, reason="not_included"),
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=7 * 24 * 60 * 60,
    )

    access_token = create_access_token(
        settings,
        authed_user.id,
        authed_user.email,
        authed_user.role.value,
        patient_id=to_optional_value(patient_id_for_token, reason="not_included"),
        doctor_id=to_optional_value(doctor_id_for_token, reason="not_included"),
    )

    return LoginResponse(
        access_token=access_token,
        token_type="Bearer",
        user_id=str(authed_user.id),
        email=authed_user.email,
        role=authed_user.role.value,
    )


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    http_request: Request,
    interpreter: Annotated[CompositeInterpreter, Depends(get_composite_interpreter)],
    _rate_limit: Annotated[None, Depends(rate_limit(3, 300))],
) -> RegisterResponse:
    """Register a new user account.

    Args:
        request: Registration payload with email, password, and role.
        http_request: Request object for audit metadata.
        interpreter: Injected composite interpreter.
        _rate_limit: Rate limit guard (FastAPI dependency).

    Returns:
        RegisterResponse describing the created account.

    Raises:
        HTTPException: If the email already exists or an unexpected result occurs.

    Effects:
        GetUserByEmail
        CreateUser
        CreatePatient (if role="patient")
        LogAuditEvent
    """

    patient_registration: NormalizedPatientRegistration | None = None
    if request.role == UserRole.PATIENT:
        patient_registration = _normalize_patient_registration(request)

    def register_program() -> Generator[AllEffects, object, RegisterResult]:
        existing_user_result = yield GetUserByEmail(email=request.email)
        assert is_user_lookup_result(existing_user_result)
        match existing_user_result:
            case UserMissingByEmail():
                pass
            case UserFound():
                return RegisterEmailExists(email=request.email)
            # MyPy enforces exhaustiveness - no fallback needed

        password_hash = hash_password(request.password)
        created_user = yield CreateUser(
            email=request.email,
            password_hash=password_hash,
            role=request.role.value,
        )
        assert isinstance(created_user, User)

        # Create patient record if registering as patient
        if request.role == UserRole.PATIENT:
            assert patient_registration is not None
            patient = yield CreatePatient(
                user_id=created_user.id,
                first_name=patient_registration.first_name,
                last_name=patient_registration.last_name,
                date_of_birth=patient_registration.date_of_birth,
                blood_type=patient_registration.blood_type,
                allergies=patient_registration.allergies,
                insurance_id=patient_registration.insurance_id,
                emergency_contact=patient_registration.emergency_contact,
                phone=patient_registration.phone,
                address=patient_registration.address,
            )
            assert isinstance(patient, Patient)

        yield LogAuditEvent(
            user_id=created_user.id,
            action="register_user",
            resource_type="auth",
            resource_id=created_user.id,
            ip_address=to_optional_value(
                http_request.client.host if http_request.client else None,
                reason="not_provided",
            ),
            user_agent=to_optional_value(
                http_request.headers.get("user-agent"), reason="not_provided"
            ),
            metadata=to_optional_value(None, reason="not_provided"),
        )
        return RegisterSuccess(user=created_user)

    register_result = unwrap_program_result(await run_program(register_program(), interpreter))

    match register_result:
        case RegisterEmailExists(email=email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
                headers={"X-Existing-Email": email},
            )
        case RegisterSuccess(user=user):
            pass
        case _:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unexpected register result",
            )

    # Message depends on role - patients have full profile created
    message = (
        "Registration successful. Please log in."
        if request.role == UserRole.PATIENT
        else "User registered successfully. Complete profile setup in the next step."
    )

    return RegisterResponse(
        user_id=str(user.id),
        email=user.email,
        role=user.role.value,
        message=message,
    )


@router.post("/refresh", response_model=RefreshResponse)
async def refresh(
    request: Request,
    response: Response,
    refresh_token: Annotated[str | None, Cookie()] = None,
    _rate_limit: Annotated[None, Depends(rate_limit(10, 60))] = None,
) -> RefreshResponse:
    """Refresh access token using refresh token from HttpOnly cookie.

    Args:
        request: Request object to access app.state.settings
        response: Response used to set the rotated refresh token.
        refresh_token: Refresh token from HttpOnly cookie.
        _rate_limit: Rate limit guard (FastAPI dependency).

    Returns:
        RefreshResponse containing a new access token.

    Raises:
        HTTPException: If the refresh token is missing or invalid.

    Effects:
        verify_token
    """
    # Get settings from app.state
    settings: Settings = request.app.state.settings

    # Check if refresh token exists in cookie
    if refresh_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found in cookie",
        )

    # Verify refresh token
    validation_result = verify_token(settings, refresh_token, TokenType.REFRESH)

    match validation_result:
        case TokenValidationError(reason=reason, detail=detail):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid refresh token: {reason} - {detail}",
            )
        case TokenValidationSuccess(token_data=token_data):
            # Generate new tokens (token rotation) with profile IDs
            new_access_token = create_access_token(
                settings,
                token_data.user_id,
                token_data.email,
                token_data.role,
                patient_id=to_optional_value(
                    from_optional_value(token_data.patient_id), reason="not_included"
                ),
                doctor_id=to_optional_value(
                    from_optional_value(token_data.doctor_id), reason="not_included"
                ),
            )
            new_refresh_token = create_refresh_token(
                settings,
                token_data.user_id,
                token_data.email,
                token_data.role,
                patient_id=to_optional_value(
                    from_optional_value(token_data.patient_id), reason="not_included"
                ),
                doctor_id=to_optional_value(
                    from_optional_value(token_data.doctor_id), reason="not_included"
                ),
            )

            # Set new refresh token in HttpOnly cookie (7 days)
            response.set_cookie(
                key="refresh_token",
                value=new_refresh_token,
                httponly=True,
                secure=True,
                samesite="strict",
                max_age=7 * 24 * 60 * 60,
            )

            return RefreshResponse(
                access_token=new_access_token,
                token_type="Bearer",
                user_id=str(token_data.user_id),
                email=token_data.email,
                role=token_data.role,
            )
        case _:
            # Unreachable - all cases covered above
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unexpected token validation result",
            )


@router.post("/logout")
async def logout(
    response: Response,
    _rate_limit: Annotated[None, Depends(rate_limit(10, 60))] = None,
) -> dict[str, str]:
    """Logout user by clearing refresh token cookie.

    Args:
        response: Response used to clear the cookie.
        _rate_limit: Rate limit guard (FastAPI dependency).

    Returns:
        Confirmation message.

    Effects:
        delete_cookie (response mutation)
    """
    # Clear refresh token cookie
    response.delete_cookie(key="refresh_token", httponly=True, secure=True, samesite="strict")

    return {"message": "Logged out successfully"}
