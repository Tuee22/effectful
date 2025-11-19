"""User management effect programs for demo app.

All programs are pure logic using the functional_effects library.
Programs yield effects and return Result types for explicit error handling.
"""

from collections.abc import Generator
from uuid import UUID

from functional_effects.algebraic.result import Err, Ok, Result
from functional_effects.effects.cache import InvalidateCache, PutCachedValue
from functional_effects.effects.database import (
    DeleteUser,
    GetUserById,
    ListUsers,
    UpdateUser,
)
from functional_effects.domain.user import User

from demo.domain.errors import AppError


def get_user_program(
    user_id: UUID,
) -> Generator[
    GetUserById,
    Result[User, str],
    Result[User, AppError],
]:
    """Get user by ID.

    Program flow:
    1. Get user from database by ID
    2. Return user

    Args:
        user_id: UUID of user to retrieve

    Returns:
        Result containing User on success, or AppError on failure

    Error cases:
        - User not found (AppError.not_found)
        - Database error (AppError.internal_error)
    """
    # Get user from database
    user_result = yield GetUserById(user_id=user_id)
    match user_result:
        case Ok(user):
            return Ok(user)
        case Err(error):
            return Err(AppError.not_found(f"User {user_id} not found: {error}"))


def list_users_program(
    limit: int | None = None, offset: int | None = None
) -> Generator[
    ListUsers,
    Result[list[User], str],
    Result[list[User], AppError],
]:
    """List all users with optional pagination.

    Program flow:
    1. Query database for users with pagination
    2. Return user list

    Args:
        limit: Maximum number of users to return (optional)
        offset: Number of users to skip (optional)

    Returns:
        Result containing list of Users on success, or AppError on failure

    Error cases:
        - Database error (AppError.internal_error)
        - Invalid pagination parameters (AppError.validation_error)
    """
    # Validate pagination parameters
    if limit is not None and limit < 0:
        return Err(AppError.validation_error("Limit must be non-negative"))
    if offset is not None and offset < 0:
        return Err(AppError.validation_error("Offset must be non-negative"))

    # List users from database
    users_result = yield ListUsers(limit=limit, offset=offset)
    match users_result:
        case Ok(users):
            return Ok(users)
        case Err(error):
            return Err(AppError.internal_error(f"Failed to list users: {error}"))


def update_user_program(
    user_id: UUID,
    email: str | None = None,
    name: str | None = None,
) -> Generator[
    GetUserById | UpdateUser | InvalidateCache,
    Result[User, str] | Result[bool, str] | Result[bool, str],
    Result[User, AppError],
]:
    """Update user fields.

    Program flow:
    1. Verify user exists
    2. Update user in database
    3. Invalidate user cache
    4. Return updated user

    Args:
        user_id: UUID of user to update
        email: New email address (optional)
        name: New display name (optional)

    Returns:
        Result containing updated User on success, or AppError on failure

    Error cases:
        - User not found (AppError.not_found)
        - No fields to update (AppError.validation_error)
        - Database error (AppError.internal_error)
    """
    # Validate that at least one field is being updated
    if email is None and name is None:
        return Err(
            AppError.validation_error("At least one field must be provided for update")
        )

    # Validate email format if provided
    if email is not None and "@" not in email:
        return Err(AppError.validation_error("Invalid email format"))

    # Step 1: Verify user exists
    user_result = yield GetUserById(user_id=user_id)
    match user_result:
        case Ok(_user):
            pass
        case Err(error):
            return Err(AppError.not_found(f"User {user_id} not found: {error}"))

    # Step 2: Update user in database
    update_result = yield UpdateUser(user_id=user_id, email=email, name=name)
    match update_result:
        case Ok(True):
            pass
        case Ok(False):
            return Err(AppError.internal_error("User update returned false"))
        case Err(error):
            return Err(AppError.internal_error(f"Failed to update user: {error}"))

    # Step 3: Invalidate user cache
    cache_key = f"user:{user_id}"
    invalidate_result = yield InvalidateCache(key=cache_key)
    match invalidate_result:
        case Ok(_):
            pass
        case Err(_error):
            # Cache invalidation failure is non-critical, continue
            pass

    # Step 4: Get updated user to return
    updated_user_result = yield GetUserById(user_id=user_id)
    match updated_user_result:
        case Ok(updated_user):
            return Ok(updated_user)
        case Err(error):
            return Err(
                AppError.internal_error(
                    f"User updated but failed to retrieve: {error}"
                )
            )


def delete_user_program(
    user_id: UUID,
) -> Generator[
    GetUserById | DeleteUser | InvalidateCache,
    Result[User, str] | Result[bool, str] | Result[bool, str],
    Result[bool, AppError],
]:
    """Delete user by ID.

    Program flow:
    1. Verify user exists
    2. Delete user from database
    3. Invalidate user cache
    4. Return success

    Args:
        user_id: UUID of user to delete

    Returns:
        Result containing True on success, or AppError on failure

    Error cases:
        - User not found (AppError.not_found)
        - Database error (AppError.internal_error)
    """
    # Step 1: Verify user exists
    user_result = yield GetUserById(user_id=user_id)
    match user_result:
        case Ok(_user):
            pass
        case Err(error):
            return Err(AppError.not_found(f"User {user_id} not found: {error}"))

    # Step 2: Delete user from database
    delete_result = yield DeleteUser(user_id=user_id)
    match delete_result:
        case Ok(True):
            pass
        case Ok(False):
            return Err(AppError.internal_error("User deletion returned false"))
        case Err(error):
            return Err(AppError.internal_error(f"Failed to delete user: {error}"))

    # Step 3: Invalidate user cache
    cache_key = f"user:{user_id}"
    invalidate_result = yield InvalidateCache(key=cache_key)
    match invalidate_result:
        case Ok(_):
            pass
        case Err(_error):
            # Cache invalidation failure is non-critical, continue
            pass

    return Ok(True)
