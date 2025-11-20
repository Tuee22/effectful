"""User management effect programs for demo app.

All programs are pure logic using the functional_effects library.
Programs yield effects and receive results directly (not wrapped in Result).
Program returns are wrapped in Result types for explicit error handling.
"""

from collections.abc import Generator
from uuid import UUID

from effectful.algebraic.result import Err, Ok, Result
from effectful.effects.cache import InvalidateCache
from effectful.effects.database import (
    DeleteUser,
    GetUserById,
    ListUsers,
    UpdateUser,
)
from effectful.domain.user import User
from effectful.programs.program_types import AllEffects, EffectResult

from demo.domain.errors import AppError


def get_user_program(
    user_id: UUID,
) -> Generator[AllEffects, EffectResult, Result[User, AppError]]:
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
    """
    # Get user from database
    user = yield GetUserById(user_id=user_id)

    if user is None:
        return Err(AppError.not_found(f"User {user_id} not found"))

    assert isinstance(user, User)
    return Ok(user)


def list_users_program(
    limit: int | None = None, offset: int | None = None
) -> Generator[AllEffects, EffectResult, Result[list[User], AppError]]:
    """List all users with optional pagination.

    Program flow:
    1. Validate pagination parameters
    2. Query database for users with pagination
    3. Return user list

    Args:
        limit: Maximum number of users to return (optional)
        offset: Number of users to skip (optional)

    Returns:
        Result containing list of Users on success, or AppError on failure

    Error cases:
        - Invalid pagination parameters (AppError.validation_error)
    """
    # Validate pagination parameters
    if limit is not None and limit < 0:
        return Err(AppError.validation_error("Limit must be non-negative"))
    if offset is not None and offset < 0:
        return Err(AppError.validation_error("Offset must be non-negative"))

    # List users from database
    users_result = yield ListUsers(limit=limit, offset=offset)
    assert isinstance(users_result, list)

    # Type narrow to list[User]
    users: list[User] = []
    for user in users_result:
        if isinstance(user, User):
            users.append(user)

    return Ok(users)


def update_user_program(
    user_id: UUID,
    email: str | None = None,
    name: str | None = None,
) -> Generator[AllEffects, EffectResult, Result[User, AppError]]:
    """Update user fields.

    Program flow:
    1. Validate inputs
    2. Verify user exists
    3. Update user in database
    4. Invalidate user cache
    5. Return updated user

    Args:
        user_id: UUID of user to update
        email: New email address (optional)
        name: New display name (optional)

    Returns:
        Result containing updated User on success, or AppError on failure

    Error cases:
        - User not found (AppError.not_found)
        - No fields to update (AppError.validation_error)
        - Invalid email format (AppError.validation_error)
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
    user = yield GetUserById(user_id=user_id)

    if user is None:
        return Err(AppError.not_found(f"User {user_id} not found"))

    # Step 2: Update user in database
    updated_result = yield UpdateUser(user_id=user_id, email=email, name=name)

    # Type narrow: UpdateUser returns bool
    if not isinstance(updated_result, bool):
        return Err(AppError.internal_error("User update returned unexpected type"))

    if not updated_result:
        return Err(AppError.internal_error("User update returned false"))

    # Step 3: Invalidate user cache
    cache_key = f"user:{user_id}"
    yield InvalidateCache(key=cache_key)

    # Step 4: Get updated user to return
    updated_user = yield GetUserById(user_id=user_id)

    if updated_user is None:
        return Err(
            AppError.internal_error("User updated but failed to retrieve")
        )

    assert isinstance(updated_user, User)
    return Ok(updated_user)


def delete_user_program(
    user_id: UUID,
) -> Generator[AllEffects, EffectResult, Result[bool, AppError]]:
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
    """
    # Step 1: Verify user exists
    user = yield GetUserById(user_id=user_id)

    if user is None:
        return Err(AppError.not_found(f"User {user_id} not found"))

    # Step 2: Delete user from database
    deleted_result = yield DeleteUser(user_id=user_id)

    # Type narrow: DeleteUser returns bool
    if not isinstance(deleted_result, bool):
        return Err(AppError.internal_error("User deletion returned unexpected type"))

    if not deleted_result:
        return Err(AppError.internal_error("User deletion returned false"))

    # Step 3: Invalidate user cache
    cache_key = f"user:{user_id}"
    yield InvalidateCache(key=cache_key)

    return Ok(True)
