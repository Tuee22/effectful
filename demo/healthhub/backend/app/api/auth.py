"""Authentication API endpoints.

Implements JWT dual-token authentication pattern:
- Access token: 15 minutes (returned in response body)
- Refresh token: 7 days (set in HttpOnly cookie)
"""

from collections.abc import Generator
from dataclasses import dataclass
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
import redis.asyncio as redis
from pydantic import BaseModel, EmailStr

from app.auth import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
    verify_token,
    TokenType,
    TokenValidationSuccess,
    TokenValidationError,
)
from app.infrastructure import get_database_manager, rate_limit
from app.interpreters.composite_interpreter import AllEffects, CompositeInterpreter
from app.programs.runner import run_program
from app.effects.notification import LogAuditEvent
from app.effects.healthcare import (
    CreateUser,
    GetDoctorByUserId,
    GetPatientByUserId,
    GetUserByEmail,
    UpdateUserLastLogin,
)
from app.domain.user import User, UserRole
from app.domain.patient import Patient
from app.domain.doctor import Doctor


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

    email: EmailStr
    password: str
    role: UserRole


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
class LoginSuccess:
    user: User
    patient: Patient | None
    doctor: Doctor | None


@dataclass(frozen=True)
class LoginInvalidCredentials:
    reason: str


@dataclass(frozen=True)
class LoginInactiveAccount:
    status: str


type LoginResult = LoginSuccess | LoginInvalidCredentials | LoginInactiveAccount


@dataclass(frozen=True)
class RegisterSuccess:
    user: User


@dataclass(frozen=True)
class RegisterEmailExists:
    email: str


type RegisterResult = RegisterSuccess | RegisterEmailExists


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    http_request: Request,
    response: Response,
    _rate_limit: Annotated[None, Depends(rate_limit(5, 60))],
) -> LoginResponse:
    """Authenticate user and return JWT tokens.

    Returns access token in response body.
    Sets refresh token in HttpOnly cookie with strict SameSite policy.

    Rate limit: 5 requests per 60 seconds per IP address.
    """
    db_manager = get_database_manager()
    pool = db_manager.get_pool()

    redis_client: redis.Redis[bytes] = redis.Redis(
        host="redis",
        port=6379,
        decode_responses=False,
    )
    interpreter = CompositeInterpreter(pool, redis_client)

    def login_program() -> Generator[AllEffects, object, LoginResult]:
        user = yield GetUserByEmail(email=request.email)
        if user is None:
            return LoginInvalidCredentials(reason="Invalid email or password")

        assert isinstance(user, User)

        if not verify_password(request.password, user.password_hash):
            return LoginInvalidCredentials(reason="Invalid email or password")

        if user.status.value != "active":
            return LoginInactiveAccount(status=user.status.value)

        yield UpdateUserLastLogin(user_id=user.id)

        patient: Patient | None = None
        doctor: Doctor | None = None

        if user.role.value == "patient":
            found_patient = yield GetPatientByUserId(user_id=user.id)
            patient = found_patient if isinstance(found_patient, Patient) else None
        elif user.role.value == "doctor":
            found_doctor = yield GetDoctorByUserId(user_id=user.id)
            doctor = found_doctor if isinstance(found_doctor, Doctor) else None

        return LoginSuccess(user=user, patient=patient, doctor=doctor)

    try:
        login_result = await run_program(login_program(), interpreter)

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
            case LoginSuccess(user=user, patient=patient, doctor=doctor):
                pass
            case _:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Unexpected login result",
                )

        # Set refresh token in HttpOnly cookie (7 days)
        refresh_token = create_refresh_token(
            user.id,
            user.email,
            user.role.value,
            patient_id=patient.id if patient else None,
            doctor_id=doctor.id if doctor else None,
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
            user.id,
            user.email,
            user.role.value,
            patient_id=patient.id if patient else None,
            doctor_id=doctor.id if doctor else None,
        )

        await interpreter.notification_interpreter.handle(
            LogAuditEvent(
                user_id=user.id,
                action="login_success",
                resource_type="auth",
                resource_id=user.id,
                ip_address=http_request.client.host if http_request.client else None,
                user_agent=http_request.headers.get("user-agent"),
                metadata=None,
            )
        )

        return LoginResponse(
            access_token=access_token,
            token_type="Bearer",
            user_id=str(user.id),
            email=user.email,
            role=user.role.value,
        )
    finally:
        await redis_client.aclose()


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    http_request: Request,
    _rate_limit: Annotated[None, Depends(rate_limit(3, 300))],
) -> RegisterResponse:
    """Register a new user account.

    Creates user with hashed password. Does NOT create patient/doctor profile.

    Rate limit: 3 requests per 300 seconds (5 minutes) per IP address.
    """
    db_manager = get_database_manager()
    pool = db_manager.get_pool()
    redis_client: redis.Redis[bytes] = redis.Redis(
        host="redis",
        port=6379,
        decode_responses=False,
    )
    interpreter = CompositeInterpreter(pool, redis_client)

    def register_program() -> Generator[AllEffects, object, RegisterResult]:
        existing_user = yield GetUserByEmail(email=request.email)
        if existing_user is not None:
            return RegisterEmailExists(email=request.email)

        password_hash = hash_password(request.password)
        created_user = yield CreateUser(
            email=request.email,
            password_hash=password_hash,
            role=request.role.value,
        )
        assert isinstance(created_user, User)
        return RegisterSuccess(user=created_user)

    try:
        register_result = await run_program(register_program(), interpreter)

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

        await interpreter.notification_interpreter.handle(
            LogAuditEvent(
                user_id=user.id,
                action="register_user",
                resource_type="auth",
                resource_id=user.id,
                ip_address=http_request.client.host if http_request.client else None,
                user_agent=http_request.headers.get("user-agent"),
                metadata=None,
            )
        )

        return RegisterResponse(
            user_id=str(user.id),
            email=user.email,
            role=user.role.value,
            message="User registered successfully. Complete profile setup in the next step.",
        )
    finally:
        await redis_client.aclose()


@router.post("/refresh", response_model=RefreshResponse)
async def refresh(
    response: Response,
    refresh_token: Annotated[str | None, Cookie()] = None,
    _rate_limit: Annotated[None, Depends(rate_limit(10, 60))] = None,
) -> RefreshResponse:
    """Refresh access token using refresh token from HttpOnly cookie.

    Implements token rotation: generates new access token AND new refresh token.
    Sets new refresh token in HttpOnly cookie with strict SameSite policy.

    Rate limit: 10 requests per 60 seconds per IP address.
    """
    # Check if refresh token exists in cookie
    if refresh_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found in cookie",
        )

    # Verify refresh token
    validation_result = verify_token(refresh_token, TokenType.REFRESH)

    match validation_result:
        case TokenValidationError(reason=reason, detail=detail):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid refresh token: {reason} - {detail}",
            )
        case TokenValidationSuccess(token_data=token_data):
            # Generate new tokens (token rotation) with profile IDs
            new_access_token = create_access_token(
                token_data.user_id,
                token_data.email,
                token_data.role,
                patient_id=token_data.patient_id,
                doctor_id=token_data.doctor_id,
            )
            new_refresh_token = create_refresh_token(
                token_data.user_id,
                token_data.email,
                token_data.role,
                patient_id=token_data.patient_id,
                doctor_id=token_data.doctor_id,
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

    Clears the refresh token HttpOnly cookie by setting max_age=0.
    Client should also discard the access token.

    Rate limit: 10 requests per 60 seconds per IP address.
    """
    # Clear refresh token cookie
    response.delete_cookie(key="refresh_token", httponly=True, secure=True, samesite="strict")

    return {"message": "Logged out successfully"}
