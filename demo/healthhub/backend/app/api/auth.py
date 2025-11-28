"""Authentication API endpoints.

Implements JWT dual-token authentication pattern:
- Access token: 15 minutes (returned in response body)
- Refresh token: 7 days (set in HttpOnly cookie)
"""

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
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
from app.repositories import UserRepository, PatientRepository, DoctorRepository
from app.domain.user import UserRole


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


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
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
    user_repo = UserRepository(pool)

    # Get user by email
    user = await user_repo.get_by_email(request.email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Verify password
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Check user status
    if user.status.value != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account is {user.status.value}",
        )

    # Update last login timestamp
    await user_repo.update_last_login(user.id)

    # Resolve profile IDs based on role (performance optimization)
    patient_id = None
    doctor_id = None

    if user.role.value == "patient":
        patient_repo = PatientRepository(pool)
        patient = await patient_repo.get_by_user_id(user.id)
        if patient is not None:
            patient_id = patient.id
    elif user.role.value == "doctor":
        doctor_repo = DoctorRepository(pool)
        doctor = await doctor_repo.get_by_user_id(user.id)
        if doctor is not None:
            doctor_id = doctor.id

    # Generate tokens with profile IDs
    access_token = create_access_token(
        user.id, user.email, user.role.value, patient_id=patient_id, doctor_id=doctor_id
    )
    refresh_token = create_refresh_token(
        user.id, user.email, user.role.value, patient_id=patient_id, doctor_id=doctor_id
    )

    # Set refresh token in HttpOnly cookie (7 days)
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=7 * 24 * 60 * 60,
    )

    return LoginResponse(
        access_token=access_token,
        token_type="Bearer",
        user_id=str(user.id),
        email=user.email,
        role=user.role.value,
    )


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    _rate_limit: Annotated[None, Depends(rate_limit(3, 300))],
) -> RegisterResponse:
    """Register a new user account.

    Creates user with hashed password. Does NOT create patient/doctor profile.

    Rate limit: 3 requests per 300 seconds (5 minutes) per IP address.
    """
    db_manager = get_database_manager()
    pool = db_manager.get_pool()
    user_repo = UserRepository(pool)

    # Check if email already exists
    existing_user = await user_repo.get_by_email(request.email)
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Hash password
    password_hash = hash_password(request.password)

    # Create user
    user = await user_repo.create(
        email=request.email,
        password_hash=password_hash,
        role=request.role,
    )

    return RegisterResponse(
        user_id=str(user.id),
        email=user.email,
        role=user.role.value,
        message="User registered successfully. Complete profile setup in the next step.",
    )


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
