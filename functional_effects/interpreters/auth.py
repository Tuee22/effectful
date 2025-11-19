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

from functional_effects.algebraic.effect_return import EffectReturn
from functional_effects.algebraic.result import Err, Ok, Result
from functional_effects.domain.token_result import TokenExpired, TokenInvalid, TokenValid
from functional_effects.effects.auth import GenerateToken, RefreshToken, RevokeToken, ValidateToken
from functional_effects.effects.base import Effect
from functional_effects.infrastructure.auth import AuthService
from functional_effects.interpreters.errors import InterpreterError, UnhandledEffectError
from functional_effects.programs.program_types import EffectResult


@dataclass(frozen=True)
class AuthError:
    """Auth operation failed.

    This error type represents infrastructure-level failures when executing
    auth effects (Redis connection errors, JWT encoding failures, etc.).

    Domain-level failures (token expired, token invalid) are handled via
    TokenValidationResult ADT, not this error type.

    Attributes:
        effect: The auth effect that was being interpreted
        auth_error: Error message from auth service or infrastructure
        is_retryable: Whether retry might succeed (connection vs invalid token)

    Example:
        >>> match result:
        ...     case Err(AuthError(auth_error=msg, is_retryable=True)):
        ...         # Retry with backoff
        ...         await retry_with_backoff(program)
        ...     case Err(AuthError(auth_error=msg, is_retryable=False)):
        ...         # Permanent failure - log and alert
        ...         logger.error(f"Non-retryable error: {msg}")
    """

    effect: Effect
    auth_error: str
    is_retryable: bool


@dataclass(frozen=True)
class AuthInterpreter:
    """Interpreter for auth effects.

    This interpreter handles ValidateToken, GenerateToken, RefreshToken, and
    RevokeToken effects by delegating to AuthService implementations.

    Attributes:
        auth_service: Auth service implementation (Redis, fake, etc.)

    Example:
        >>> from functional_effects.testing.fakes import FakeAuthService
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
        self, user_id, claims, ttl_seconds, effect: Effect
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

    def _is_retryable_error(self, error: Exception) -> bool:
        """Determine if an auth error is retryable.

        Args:
            error: The exception that was raised

        Returns:
            True if error might succeed on retry, False otherwise
        """
        # Common retryable error patterns for auth/Redis
        error_str = str(error).lower()
        retryable_patterns = [
            "connection",
            "timeout",
            "unavailable",
            "network",
            "redis",
        ]

        # Non-retryable patterns (token/encoding issues)
        non_retryable_patterns = [
            "invalid signature",
            "malformed",
            "decode error",
            "encoding error",
        ]

        # Check non-retryable first
        if any(pattern in error_str for pattern in non_retryable_patterns):
            return False

        # Then check retryable
        return any(pattern in error_str for pattern in retryable_patterns)
