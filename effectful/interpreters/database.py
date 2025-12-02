"""Database interpreter implementation.

This module implements the interpreter for Database effects.
"""

from dataclasses import dataclass
from uuid import UUID

from effectful.algebraic.effect_return import EffectReturn
from effectful.algebraic.result import Err, Ok, Result
from effectful.domain.user import User, UserFound, UserNotFound
from effectful.effects.base import Effect
from effectful.effects.database import (
    CreateUser,
    DeleteUser,
    GetChatMessages,
    GetUserById,
    ListMessagesForUser,
    ListUsers,
    SaveChatMessage,
    UpdateUser,
)
from effectful.infrastructure.repositories import (
    ChatMessageRepository,
    UserRepository,
)
from effectful.interpreters.errors import (
    DatabaseError,
    InterpreterError,
    UnhandledEffectError,
)
from effectful.interpreters.retry_logic import (
    DATABASE_RETRY_PATTERNS,
    is_retryable_error,
)
from effectful.programs.program_types import EffectResult


@dataclass(frozen=True)
class DatabaseInterpreter:
    """Interpreter for Database effects.

    Attributes:
        user_repo: User repository implementation
        message_repo: Chat message repository implementation
    """

    user_repo: UserRepository
    message_repo: ChatMessageRepository

    async def interpret(
        self, effect: Effect
    ) -> Result[EffectReturn[EffectResult], InterpreterError]:
        """Interpret a Database effect.

        Args:
            effect: The effect to interpret

        Returns:
            Ok(EffectReturn(value)) if successful
            Err(InterpreterError) if failed or not a Database effect
        """
        match effect:
            case GetUserById(user_id=user_id):
                return await self._handle_get_user(user_id, effect)
            case SaveChatMessage(user_id=user_id, text=text):
                return await self._handle_save_message(user_id, text, effect)
            case ListMessagesForUser(user_id=user_id):
                return await self._handle_list_messages(user_id, effect, "ListMessagesForUser")
            case GetChatMessages(user_id=user_id):
                return await self._handle_list_messages(user_id, effect, "GetChatMessages")
            case ListUsers(limit=limit, offset=offset):
                return await self._handle_list_users(limit, offset, effect)
            case CreateUser(email=email, name=name, password_hash=password_hash):
                return await self._handle_create_user(email, name, password_hash, effect)
            case UpdateUser(user_id=user_id, email=email, name=name):
                return await self._handle_update_user(user_id, email, name, effect)
            case DeleteUser(user_id=user_id):
                return await self._handle_delete_user(user_id, effect)
            case _:
                return Err(
                    UnhandledEffectError(
                        effect=effect,
                        available_interpreters=["DatabaseInterpreter"],
                    )
                )

    async def _handle_get_user(
        self, user_id: UUID, effect: Effect
    ) -> Result[EffectReturn[EffectResult], InterpreterError]:
        """Handle GetUserById effect.

        Returns the User if found, UserNotFound ADT if not found.
        ADT types provide explicit semantics instead of None.
        """
        try:
            lookup_result = await self.user_repo.get_by_id(user_id)
            # Pattern match on UserLookupResult ADT and return appropriate type
            match lookup_result:  # pragma: no branch
                case UserFound(user=user, source=_):
                    # User found - return the User object
                    return Ok(EffectReturn(value=user, effect_name="GetUserById"))
                case UserNotFound() as not_found:
                    # User not found - return the ADT type directly
                    return Ok(EffectReturn(value=not_found, effect_name="GetUserById"))
        except Exception as e:
            return Err(
                DatabaseError(
                    effect=effect,
                    db_error=str(e),
                    is_retryable=self._is_retryable_error(e),
                )
            )

    async def _handle_save_message(
        self, user_id: UUID, text: str, effect: Effect
    ) -> Result[EffectReturn[EffectResult], InterpreterError]:
        """Handle SaveChatMessage effect."""
        try:
            message = await self.message_repo.save_message(user_id, text)
            return Ok(EffectReturn(value=message, effect_name="SaveChatMessage"))
        except Exception as e:
            return Err(
                DatabaseError(
                    effect=effect,
                    db_error=str(e),
                    is_retryable=self._is_retryable_error(e),
                )
            )

    async def _handle_list_messages(
        self, user_id: UUID, effect: Effect, effect_name: str
    ) -> Result[EffectReturn[EffectResult], InterpreterError]:
        """Handle ListMessagesForUser effect."""
        try:
            messages = await self.message_repo.list_messages_for_user(user_id)
            return Ok(EffectReturn(value=messages, effect_name=effect_name))
        except Exception as e:
            return Err(
                DatabaseError(
                    effect=effect,
                    db_error=str(e),
                    is_retryable=self._is_retryable_error(e),
                )
            )

    async def _handle_list_users(
        self, limit: int | None, offset: int | None, effect: Effect
    ) -> Result[EffectReturn[EffectResult], InterpreterError]:
        """Handle ListUsers effect."""
        try:
            users = await self.user_repo.list_users(limit, offset)
            return Ok(EffectReturn(value=users, effect_name="ListUsers"))
        except Exception as e:
            return Err(
                DatabaseError(
                    effect=effect,
                    db_error=str(e),
                    is_retryable=self._is_retryable_error(e),
                )
            )

    async def _handle_create_user(
        self, email: str, name: str, password_hash: str, effect: Effect
    ) -> Result[EffectReturn[EffectResult], InterpreterError]:
        """Handle CreateUser effect."""
        try:
            user = await self.user_repo.create_user(email, name, password_hash)
            return Ok(EffectReturn(value=user, effect_name="CreateUser"))
        except Exception as e:
            return Err(
                DatabaseError(
                    effect=effect,
                    db_error=str(e),
                    is_retryable=self._is_retryable_error(e),
                )
            )

    async def _handle_update_user(
        self, user_id: UUID, email: str | None, name: str | None, effect: Effect
    ) -> Result[EffectReturn[EffectResult], InterpreterError]:
        """Handle UpdateUser effect.

        Returns the updated User if found, UserNotFound ADT if not found.
        """
        try:
            lookup_result = await self.user_repo.update_user(user_id, email, name)
            match lookup_result:  # pragma: no branch
                case UserFound(user=user, source=_):
                    return Ok(EffectReturn(value=user, effect_name="UpdateUser"))
                case UserNotFound() as not_found:
                    return Ok(EffectReturn(value=not_found, effect_name="UpdateUser"))
        except Exception as e:
            return Err(
                DatabaseError(
                    effect=effect,
                    db_error=str(e),
                    is_retryable=self._is_retryable_error(e),
                )
            )

    async def _handle_delete_user(
        self, user_id: UUID, effect: Effect
    ) -> Result[EffectReturn[EffectResult], InterpreterError]:
        """Handle DeleteUser effect."""
        try:
            await self.user_repo.delete_user(user_id)
            return Ok(EffectReturn(value=None, effect_name="DeleteUser"))
        except Exception as e:
            return Err(
                DatabaseError(
                    effect=effect,
                    db_error=str(e),
                    is_retryable=self._is_retryable_error(e),
                )
            )

    def _is_retryable_error(self, error: Exception) -> bool:
        """Determine if a database error is retryable.

        Args:
            error: The exception that was raised

        Returns:
            True if error might succeed on retry, False otherwise
        """
        return is_retryable_error(error, DATABASE_RETRY_PATTERNS)
