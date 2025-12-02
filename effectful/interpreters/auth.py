"""Auth interpreter implementation for JWT authentication effects.

This module implements the interpreter for auth effects (ValidateToken, GenerateToken,
RefreshToken, RevokeToken).

Components:
    - AuthError: Error type for auth failures
    - AuthInterpreter: Interpreter for auth effects

The interpreter delegates to AuthService protocol implementations, converting
protocol results to Result[EffectReturn, InterpreterError].

Type Safety:
    All pattern matching is exhaustive. All return types use Result for explicit
    error handling.
"""

from dataclasses import dataclass
from uuid import UUID

from effectful.algebraic.effect_return import EffectReturn
from effectful.algebraic.result import Err, Ok, Result
from effectful.domain.token_result import TokenExpired, TokenInvalid, TokenValid
from effectful.domain.user import UserFound, UserNotFound
from effectful.effects.auth import (
    GenerateToken,
    GetUserByEmail,
    HashPassword,
    RefreshToken,
    RevokeToken,
    ValidatePassword,
    ValidateToken,
)
from effectful.effects.base import Effect
from effectful.infrastructure.auth import AuthService
from effectful.interpreters.errors import (
    AuthError,
    InterpreterError,
    UnhandledEffectError,
)
from effectful.interpreters.retry_logic import (
    AUTH_RETRY_PATTERNS,
    is_retryable_error,
)
from effectful.programs.program_types import EffectResult


@dataclass(frozen=True)
class AuthInterpreter:
    """Interpreter for auth effects.

    This interpreter handles ValidateToken, GenerateToken, RefreshToken, and
    RevokeToken effects by delegating to AuthService implementations.

    Attributes:
        auth_service: Auth service implementation (Redis, fake, etc.)

    Example:
        >>> from effectful.testing.fakes import FakeAuthService
        >>>
        >>> interpreter = AuthInterpreter(auth_service=FakeAuthService())
        >>>
        >>> effect = ValidateToken(token="eyJhbGciOiJIUzI1NiIsInR5...")
        >>> result = await interpreter.interpret(effect)
        >>>
        >>> match result:
        ...     case Ok(EffectReturn(value=TokenValid(user_id=uid, claims=claims))):
        ...         print(f"User {uid} authenticated")
        ...     case Ok(EffectReturn(value=TokenExpired() | TokenInvalid())):
        ...         print("Authentication failed")
        ...     case Err(AuthError(auth_error=error)):
        ...         print(f"Infrastructure error: {error}")
    """

    auth_service: AuthService

    async def interpret(
        self, effect: Effect
    ) -> Result[EffectReturn[EffectResult], InterpreterError]:
        """Interpret an auth effect.

        Args:
            effect: The effect to interpret

        Returns:
            Ok(EffectReturn(value)) if successful
            Err(AuthError) if infrastructure failure
            Err(UnhandledEffectError) if not an auth effect
        """
        match effect:
            case ValidateToken(token=token):
                return await self._handle_validate_token(token, effect)
            case GenerateToken(user_id=user_id, claims=claims, ttl_seconds=ttl):
                return await self._handle_generate_token(user_id, claims, ttl, effect)
            case RefreshToken(refresh_token=refresh_token):
                return await self._handle_refresh_token(refresh_token, effect)
            case RevokeToken(token=token):
                return await self._handle_revoke_token(token, effect)
            case GetUserByEmail(email=email):
                return await self._handle_get_user_by_email(email, effect)
            case ValidatePassword(password=password, password_hash=password_hash):
                return await self._handle_validate_password(password, password_hash, effect)
            case HashPassword(password=password):
                return await self._handle_hash_password(password, effect)
            case _:
                return Err(
                    UnhandledEffectError(
                        effect=effect,
                        available_interpreters=["AuthInterpreter"],
                    )
                )

    async def _handle_validate_token(
        self, token: str, effect: Effect
    ) -> Result[EffectReturn[EffectResult], InterpreterError]:
        """Handle ValidateToken effect.

        Returns TokenValidationResult ADT (TokenValid | TokenExpired | TokenInvalid).
        """
        try:
            validation_result = await self.auth_service.validate_token(token)
            # Return the ADT directly - it's part of EffectResult union
            return Ok(EffectReturn(value=validation_result, effect_name="ValidateToken"))
        except Exception as e:
            return Err(
                AuthError(
                    effect=effect,
                    auth_error=str(e),
                    is_retryable=self._is_retryable_error(e),
                )
            )

    async def _handle_generate_token(
        self, user_id: UUID, claims: dict[str, str], ttl_seconds: int, effect: Effect
    ) -> Result[EffectReturn[EffectResult], InterpreterError]:
        """Handle GenerateToken effect.

        Returns JWT token as string.
        """
        try:
            token = await self.auth_service.generate_token(user_id, claims, ttl_seconds)
            return Ok(EffectReturn(value=token, effect_name="GenerateToken"))
        except Exception as e:
            return Err(
                AuthError(
                    effect=effect,
                    auth_error=str(e),
                    is_retryable=self._is_retryable_error(e),
                )
            )

    async def _handle_refresh_token(
        self, refresh_token: str, effect: Effect
    ) -> Result[EffectReturn[EffectResult], InterpreterError]:
        """Handle RefreshToken effect.

        Returns new JWT token as string, or None if refresh token is invalid/expired.
        """
        try:
            new_token = await self.auth_service.refresh_token(refresh_token)
            return Ok(EffectReturn(value=new_token, effect_name="RefreshToken"))
        except Exception as e:
            return Err(
                AuthError(
                    effect=effect,
                    auth_error=str(e),
                    is_retryable=self._is_retryable_error(e),
                )
            )

    async def _handle_revoke_token(
        self, token: str, effect: Effect
    ) -> Result[EffectReturn[EffectResult], InterpreterError]:
        """Handle RevokeToken effect.

        Returns None (fire-and-forget operation).
        """
        try:
            await self.auth_service.revoke_token(token)
            return Ok(EffectReturn(value=None, effect_name="RevokeToken"))
        except Exception as e:
            return Err(
                AuthError(
                    effect=effect,
                    auth_error=str(e),
                    is_retryable=self._is_retryable_error(e),
                )
            )

    async def _handle_get_user_by_email(
        self, email: str, effect: Effect
    ) -> Result[EffectReturn[EffectResult], InterpreterError]:
        """Handle GetUserByEmail effect.

        Returns User if found, UserNotFound ADT if not found.
        """
        try:
            lookup_result = await self.auth_service.get_user_by_email(email)
            match lookup_result:  # pragma: no branch
                case UserFound(user=user, source=_):
                    return Ok(EffectReturn(value=user, effect_name="GetUserByEmail"))
                case UserNotFound() as not_found:
                    return Ok(EffectReturn(value=not_found, effect_name="GetUserByEmail"))
        except Exception as e:
            return Err(
                AuthError(
                    effect=effect,
                    auth_error=str(e),
                    is_retryable=self._is_retryable_error(e),
                )
            )

    async def _handle_validate_password(
        self, password: str, password_hash: str, effect: Effect
    ) -> Result[EffectReturn[EffectResult], InterpreterError]:
        """Handle ValidatePassword effect.

        Returns True if password matches hash, False otherwise.
        """
        try:
            is_valid = await self.auth_service.validate_password(password, password_hash)
            return Ok(EffectReturn(value=is_valid, effect_name="ValidatePassword"))
        except Exception as e:
            return Err(
                AuthError(
                    effect=effect,
                    auth_error=str(e),
                    is_retryable=self._is_retryable_error(e),
                )
            )

    async def _handle_hash_password(
        self, password: str, effect: Effect
    ) -> Result[EffectReturn[EffectResult], InterpreterError]:
        """Handle HashPassword effect.

        Returns bcrypt hash as string.
        """
        try:
            hashed = await self.auth_service.hash_password(password)
            return Ok(EffectReturn(value=hashed, effect_name="HashPassword"))
        except Exception as e:
            return Err(
                AuthError(
                    effect=effect,
                    auth_error=str(e),
                    is_retryable=self._is_retryable_error(e),
                )
            )

    def _is_retryable_error(self, error: Exception) -> bool:
        """Determine if an auth error is retryable.

        Args:
            error: The exception that was raised

        Returns:
            True if error might succeed on retry, False otherwise
        """
        return is_retryable_error(error, AUTH_RETRY_PATTERNS)
