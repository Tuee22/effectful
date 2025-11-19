"""Database interpreter implementation.

This module implements the interpreter for Database effects.
"""

from dataclasses import dataclass
from uuid import UUID

from functional_effects.algebraic.effect_return import EffectReturn
from functional_effects.algebraic.result import Err, Ok, Result
from functional_effects.domain.user import UserFound, UserNotFound
from functional_effects.effects.base import Effect
from functional_effects.effects.database import (
    GetUserById,
    ListMessagesForUser,
    SaveChatMessage,
)
from functional_effects.infrastructure.repositories import (
    ChatMessageRepository,
    UserRepository,
)
from functional_effects.interpreters.errors import (
    DatabaseError,
    InterpreterError,
    UnhandledEffectError,
)
from functional_effects.programs.program_types import EffectResult


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
                return await self._handle_list_messages(user_id, effect)
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

        Returns the User if found, None if not found (following ADT pattern).
        The interpreter unwraps UserLookupResult ADT to Optional[User] for EffectResult.
        """
        try:
            lookup_result = await self.user_repo.get_by_id(user_id)
            # Pattern match on UserLookupResult ADT and unwrap to Optional[User]
            match lookup_result:
                case UserFound(user=user, source=_):
                    # User found - return the User object
                    return Ok(EffectReturn(value=user, effect_name="GetUserById"))
                case UserNotFound(user_id=_, reason=_):
                    # User not found - return None (part of EffectResult union)
                    return Ok(EffectReturn(value=None, effect_name="GetUserById"))
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
        self, user_id: UUID, effect: Effect
    ) -> Result[EffectReturn[EffectResult], InterpreterError]:
        """Handle ListMessagesForUser effect."""
        try:
            messages = await self.message_repo.list_messages_for_user(user_id)
            return Ok(EffectReturn(value=messages, effect_name="ListMessagesForUser"))
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
        # Common retryable error patterns
        error_str = str(error).lower()
        retryable_patterns = [
            "connection",
            "timeout",
            "deadlock",
            "lock",
            "unavailable",
        ]
        return any(pattern in error_str for pattern in retryable_patterns)
