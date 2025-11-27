"""Authentication API endpoints.

Implements JWT dual-token authentication pattern:
- Access token: 15 minutes (returned in response body)
- Refresh token: 7 days (set in HttpOnly cookie)
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr

from app.auth import create_access_token, create_refresh_token, hash_password, verify_password
from app.infrastructure import get_database_manager
from app.repositories import UserRepository
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


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest) -> LoginResponse:
    """Authenticate user and return JWT tokens.

    Returns access token in response body.
    Sets refresh token in HttpOnly cookie (TODO: implement cookie setting).
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

    # Generate tokens
    access_token = create_access_token(user.id, user.email, user.role.value)
    refresh_token = create_refresh_token(user.id, user.email, user.role.value)

    # TODO: Set refresh token in HttpOnly cookie
    # response.set_cookie(
    #     key="refresh_token",
    #     value=refresh_token,
    #     httponly=True,
    #     secure=True,
    #     samesite="lax",
    #     max_age=settings.jwt_refresh_token_expire_days * 24 * 60 * 60,
    # )

    return LoginResponse(
        access_token=access_token,
        token_type="Bearer",
        user_id=str(user.id),
        email=user.email,
        role=user.role.value,
    )


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest) -> RegisterResponse:
    """Register a new user account.

    Creates user with hashed password. Does NOT create patient/doctor profile.
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
