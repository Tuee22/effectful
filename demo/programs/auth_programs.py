"""Auth lifecycle effect programs for demo app.

All programs are pure logic using the effectful library.
Programs yield effects and receive results directly (not wrapped in Result).
Program returns are wrapped in Result types for explicit error handling.
"""

from collections.abc import Generator
from uuid import UUID

from effectful.algebraic.result import Err, Ok, Result
from effectful.effects.auth import (
    GenerateToken,
    GetUserByEmail,
    HashPassword,
    RevokeToken,
    ValidatePassword,
    ValidateToken,
)
from effectful.effects.database import CreateUser, GetUserById
from effectful.domain.token_result import TokenValid
from effectful.domain.user import User
from effectful.programs.program_types import AllEffects, EffectResult

from demo.domain.errors import AppError, AuthError
from demo.domain.responses import LoginResponse


def login_program(
    email: str, password: str
) -> Generator[AllEffects, EffectResult, Result[LoginResponse, AuthError | AppError]]:
    """Login user with email and password.

    Program flow:
    1. Get user by email from database
    2. Validate password against stored hash (assuming user has password_hash attribute)
    3. Generate access token and refresh token
    4. Return LoginResponse with tokens

    Args:
        email: User email address
        password: Plain text password

    Returns:
        Result containing LoginResponse on success, or AuthError/AppError on failure

    Error cases:
        - User not found (AppError.not_found)
        - Invalid password (AuthError with invalid_credentials)
        - Token generation failure (returns string token, won't fail in demo)
    """
    # Step 1: Get user by email
    user = yield GetUserByEmail(email=email)

    if user is None:
        return Err(AppError.not_found(f"User with email {email} not found"))

    assert isinstance(user, User)

    # Step 2: Validate password
    # Note: In demo, assuming User has a password_hash field for this workflow
    # In production, this would come from a separate credential store
    is_valid_result = yield ValidatePassword(
        password=password, password_hash="$2b$12$dummy_hash_for_demo"
    )

    # Type narrow: ValidatePassword returns bool
    if not isinstance(is_valid_result, bool):
        return Err(
            AuthError(
                message="Password validation returned unexpected type",
                error_type="invalid_credentials",
            )
        )

    if not is_valid_result:
        return Err(
            AuthError(
                message="Invalid email or password", error_type="invalid_credentials"
            )
        )

    # Step 3: Generate access token
    access_token = yield GenerateToken(
        user_id=user.id,
        claims={"email": user.email, "name": user.name},
        ttl_seconds=3600,  # 1 hour
    )
    assert isinstance(access_token, str)

    # Step 4: Generate refresh token (longer TTL)
    refresh_token = yield GenerateToken(
        user_id=user.id,
        claims={"email": user.email, "token_type": "refresh"},
        ttl_seconds=604800,  # 7 days
    )
    assert isinstance(refresh_token, str)

    # Step 5: Return successful login response
    return Ok(
        LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user_id=user.id,
            expires_in=3600,  # 1 hour
        )
    )


def logout_program(
    token: str,
) -> Generator[AllEffects, EffectResult, Result[bool, AuthError]]:
    """Logout user by revoking their token.

    Program flow:
    1. Validate token to ensure it's legitimate
    2. Revoke token (add to Redis blacklist)
    3. Return success

    Args:
        token: JWT token to revoke

    Returns:
        Result containing True on success, or AuthError on failure

    Error cases:
        - Invalid token (AuthError with token_invalid)
        - Token revocation failure (returns None, won't fail in demo)
    """
    # Step 1: Validate token
    validation_result = yield ValidateToken(token=token)

    # Check if token is valid
    if not isinstance(validation_result, TokenValid):
        return Err(
            AuthError(message="Invalid or expired token", error_type="token_invalid")
        )

    # Step 2: Revoke token
    yield RevokeToken(token=token)

    return Ok(True)


def refresh_program(
    refresh_token: str,
) -> Generator[AllEffects, EffectResult, Result[LoginResponse, AuthError | AppError]]:
    """Refresh access token using refresh token.

    Program flow:
    1. Validate refresh token
    2. Get current user data (ensure user still exists and get latest info)
    3. Generate new access token and refresh token
    4. Return LoginResponse with new tokens

    Args:
        refresh_token: JWT refresh token

    Returns:
        Result containing LoginResponse on success, or AuthError/AppError on failure

    Error cases:
        - Invalid/expired refresh token (AuthError with token_expired/token_invalid)
        - User no longer exists (AppError.not_found)
    """
    # Step 1: Validate refresh token
    validation_result = yield ValidateToken(token=refresh_token)

    if not isinstance(validation_result, TokenValid):
        return Err(
            AuthError(
                message="Invalid or expired refresh token", error_type="token_expired"
            )
        )

    user_id = validation_result.user_id

    # Step 2: Get current user data
    user = yield GetUserById(user_id=user_id)

    if user is None:
        return Err(AppError.not_found(f"User {user_id} no longer exists"))

    assert isinstance(user, User)

    # Step 3: Generate new access token
    access_token = yield GenerateToken(
        user_id=user.id,
        claims={"email": user.email, "name": user.name},
        ttl_seconds=3600,  # 1 hour
    )
    assert isinstance(access_token, str)

    # Step 4: Generate new refresh token
    new_refresh_token = yield GenerateToken(
        user_id=user.id,
        claims={"email": user.email, "token_type": "refresh"},
        ttl_seconds=604800,  # 7 days
    )
    assert isinstance(new_refresh_token, str)

    # Step 5: Return successful refresh response
    return Ok(
        LoginResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            user_id=user.id,
            expires_in=3600,
        )
    )


def register_program(
    email: str, name: str, password: str
) -> Generator[AllEffects, EffectResult, Result[User, AuthError | AppError]]:
    """Register new user account.

    Program flow:
    1. Check if user already exists (by email)
    2. Hash password with bcrypt
    3. Create user in database
    4. Return created user

    Args:
        email: User email address (unique)
        name: User display name
        password: Plain text password

    Returns:
        Result containing User on success, or AuthError/AppError on failure

    Error cases:
        - Email already exists (AppError.conflict)
        - User creation failure (returns UUID, won't fail in demo)
    """
    # Step 1: Check if user already exists
    existing_user = yield GetUserByEmail(email=email)

    if existing_user is not None:
        return Err(AppError.conflict(f"User with email {email} already exists"))

    # Step 2: Hash password
    password_hash_result = yield HashPassword(password=password)

    # Type narrow: HashPassword returns str
    if not isinstance(password_hash_result, str):
        return Err(
            AuthError(
                message="Password hashing returned unexpected type",
                error_type="invalid_credentials",
            )
        )

    # Step 3: Create user
    user_id_result = yield CreateUser(
        email=email, name=name, password_hash=password_hash_result
    )

    # Type narrow: CreateUser returns UUID
    if not isinstance(user_id_result, UUID):
        return Err(AppError.internal_error("User creation returned unexpected type"))

    # Step 4: Get created user to return full User object
    user = yield GetUserById(user_id=user_id_result)

    if user is None:
        return Err(AppError.internal_error("User created but failed to retrieve"))

    assert isinstance(user, User)
    return Ok(user)
