"""Auth lifecycle effect programs for demo app.

All programs are pure logic using the functional_effects library.
Programs yield effects and return Result types for explicit error handling.
"""

from collections.abc import Generator
from uuid import UUID

from functional_effects.algebraic.result import Err, Ok, Result
from functional_effects.effects.auth import (
    GenerateToken,
    GetUserByEmail,
    HashPassword,
    RevokeToken,
    ValidatePassword,
    ValidateToken,
)
from functional_effects.effects.database import CreateUser, GetUserById
from functional_effects.domain.token import Token, TokenMetadata
from functional_effects.domain.user import User

from demo.domain.errors import AppError, AuthError
from demo.domain.responses import LoginResponse


def login_program(
    email: str, password: str
) -> Generator[
    GetUserByEmail | ValidatePassword | GenerateToken,
    Result[User, str] | Result[bool, str] | Result[Token, str],
    Result[LoginResponse, AuthError | AppError],
]:
    """Login user with email and password.

    Program flow:
    1. Get user by email from database
    2. Validate password against stored hash
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
        - Token generation failure (AuthError with token_invalid)
    """
    # Step 1: Get user by email
    user_result = yield GetUserByEmail(email=email)
    match user_result:
        case Ok(user):
            pass
        case Err(error):
            return Err(AppError.not_found(f"User not found: {error}"))

    # Step 2: Validate password
    password_result = yield ValidatePassword(
        password=password, password_hash=user.password_hash
    )
    match password_result:
        case Ok(True):
            pass
        case Ok(False):
            return Err(
                AuthError(
                    message="Invalid email or password",
                    error_type="invalid_credentials",
                )
            )
        case Err(error):
            return Err(
                AuthError(
                    message=f"Password validation failed: {error}",
                    error_type="invalid_credentials",
                )
            )

    # Step 3: Generate access token
    access_token_result = yield GenerateToken(
        metadata=TokenMetadata(
            user_id=user.user_id,
            email=user.email,
            roles=user.roles,
            ttl_seconds=3600,  # 1 hour
        )
    )
    match access_token_result:
        case Ok(access_token):
            pass
        case Err(error):
            return Err(
                AuthError(
                    message=f"Failed to generate access token: {error}",
                    error_type="token_invalid",
                )
            )

    # Step 4: Generate refresh token (longer TTL)
    refresh_token_result = yield GenerateToken(
        metadata=TokenMetadata(
            user_id=user.user_id,
            email=user.email,
            roles=user.roles,
            ttl_seconds=604800,  # 7 days
        )
    )
    match refresh_token_result:
        case Ok(refresh_token):
            pass
        case Err(error):
            return Err(
                AuthError(
                    message=f"Failed to generate refresh token: {error}",
                    error_type="token_invalid",
                )
            )

    # Step 5: Return successful login response
    return Ok(
        LoginResponse(
            access_token=access_token.token,
            refresh_token=refresh_token.token,
            user_id=user.user_id,
            expires_in=3600,
        )
    )


def logout_program(
    token: str,
) -> Generator[
    ValidateToken | RevokeToken,
    Result[TokenMetadata, str] | Result[bool, str],
    Result[bool, AuthError],
]:
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
        - Token revocation failure (AuthError with token_invalid)
    """
    # Step 1: Validate token
    validate_result = yield ValidateToken(token=token)
    match validate_result:
        case Ok(_metadata):
            pass
        case Err(error):
            return Err(
                AuthError(
                    message=f"Invalid token: {error}", error_type="token_invalid"
                )
            )

    # Step 2: Revoke token
    revoke_result = yield RevokeToken(token=token)
    match revoke_result:
        case Ok(True):
            return Ok(True)
        case Ok(False):
            return Err(
                AuthError(
                    message="Token revocation failed", error_type="token_invalid"
                )
            )
        case Err(error):
            return Err(
                AuthError(
                    message=f"Token revocation error: {error}",
                    error_type="token_invalid",
                )
            )


def refresh_program(
    refresh_token: str,
) -> Generator[
    ValidateToken | GetUserById | GenerateToken,
    Result[TokenMetadata, str] | Result[User, str] | Result[Token, str],
    Result[LoginResponse, AuthError | AppError],
]:
    """Refresh access token using refresh token.

    Program flow:
    1. Validate refresh token
    2. Get current user data (ensure user still exists and get latest roles)
    3. Generate new access token and refresh token
    4. Return LoginResponse with new tokens

    Args:
        refresh_token: JWT refresh token

    Returns:
        Result containing LoginResponse on success, or AuthError/AppError on failure

    Error cases:
        - Invalid/expired refresh token (AuthError with token_expired/token_invalid)
        - User no longer exists (AppError.not_found)
        - Token generation failure (AuthError with token_invalid)
    """
    # Step 1: Validate refresh token
    validate_result = yield ValidateToken(token=refresh_token)
    match validate_result:
        case Ok(metadata):
            user_id = metadata.user_id
        case Err(error):
            return Err(
                AuthError(
                    message=f"Invalid refresh token: {error}",
                    error_type="token_expired",
                )
            )

    # Step 2: Get current user data
    user_result = yield GetUserById(user_id=user_id)
    match user_result:
        case Ok(user):
            pass
        case Err(error):
            return Err(
                AppError.not_found(f"User no longer exists: {error}")
            )

    # Step 3: Generate new access token
    access_token_result = yield GenerateToken(
        metadata=TokenMetadata(
            user_id=user.user_id,
            email=user.email,
            roles=user.roles,
            ttl_seconds=3600,  # 1 hour
        )
    )
    match access_token_result:
        case Ok(access_token):
            pass
        case Err(error):
            return Err(
                AuthError(
                    message=f"Failed to generate access token: {error}",
                    error_type="token_invalid",
                )
            )

    # Step 4: Generate new refresh token
    new_refresh_token_result = yield GenerateToken(
        metadata=TokenMetadata(
            user_id=user.user_id,
            email=user.email,
            roles=user.roles,
            ttl_seconds=604800,  # 7 days
        )
    )
    match new_refresh_token_result:
        case Ok(new_refresh_token):
            pass
        case Err(error):
            return Err(
                AuthError(
                    message=f"Failed to generate refresh token: {error}",
                    error_type="token_invalid",
                )
            )

    # Step 5: Return successful refresh response
    return Ok(
        LoginResponse(
            access_token=access_token.token,
            refresh_token=new_refresh_token.token,
            user_id=user.user_id,
            expires_in=3600,
        )
    )


def register_program(
    email: str, name: str, password: str
) -> Generator[
    GetUserByEmail | HashPassword | CreateUser,
    Result[User, str] | Result[str, str] | Result[UUID, str],
    Result[User, AuthError | AppError],
]:
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
        - Password hashing failure (AuthError with invalid_credentials)
        - User creation failure (AppError.internal_error)
    """
    # Step 1: Check if user already exists
    existing_user_result = yield GetUserByEmail(email=email)
    match existing_user_result:
        case Ok(_user):
            # User already exists
            return Err(
                AppError.conflict(f"User with email {email} already exists")
            )
        case Err(_error):
            # User doesn't exist - this is expected, continue
            pass

    # Step 2: Hash password
    hash_result = yield HashPassword(password=password)
    match hash_result:
        case Ok(password_hash):
            pass
        case Err(error):
            return Err(
                AuthError(
                    message=f"Failed to hash password: {error}",
                    error_type="invalid_credentials",
                )
            )

    # Step 3: Create user
    create_result = yield CreateUser(
        email=email, name=name, password_hash=password_hash
    )
    match create_result:
        case Ok(user_id):
            pass
        case Err(error):
            return Err(
                AppError.internal_error(f"Failed to create user: {error}")
            )

    # Step 4: Get created user to return full User object
    user_result = yield GetUserById(user_id=user_id)
    match user_result:
        case Ok(user):
            return Ok(user)
        case Err(error):
            return Err(
                AppError.internal_error(
                    f"User created but failed to retrieve: {error}"
                )
            )
