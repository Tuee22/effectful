"""Cache interpreter implementation.

This module implements the interpreter for Cache effects.
"""

from dataclasses import dataclass
from uuid import UUID

from effectful.algebraic.effect_return import EffectReturn
from effectful.algebraic.result import Err, Ok, Result
from effectful.domain.cache_result import CacheHit, CacheMiss
from effectful.domain.profile import ProfileData
from effectful.effects.base import Effect
from effectful.effects.cache import GetCachedProfile, PutCachedProfile
from effectful.infrastructure.cache import ProfileCache
from effectful.interpreters.errors import (
    CacheError,
    InterpreterError,
    UnhandledEffectError,
)
from effectful.programs.program_types import EffectResult


@dataclass(frozen=True)
class CacheInterpreter:
    """Interpreter for Cache effects.

    Attributes:
        cache: Profile cache implementation
    """

    cache: ProfileCache

    async def interpret(
        self, effect: Effect
    ) -> Result[EffectReturn[EffectResult], InterpreterError]:
        """Interpret a Cache effect.

        Args:
            effect: The effect to interpret

        Returns:
            Ok(EffectReturn(value)) if successful
            Err(InterpreterError) if failed or not a Cache effect
        """
        match effect:
            case GetCachedProfile(user_id=user_id):
                return await self._handle_get_profile(user_id, effect)
            case PutCachedProfile(user_id=user_id, profile_data=profile_data, ttl_seconds=ttl):
                return await self._handle_put_profile(user_id, profile_data, ttl, effect)
            case _:
                return Err(
                    UnhandledEffectError(
                        effect=effect,
                        available_interpreters=["CacheInterpreter"],
                    )
                )

    async def _handle_get_profile(
        self, user_id: UUID, effect: Effect
    ) -> Result[EffectReturn[EffectResult], InterpreterError]:
        """Handle GetCachedProfile effect.

        Returns ProfileData if cache hit, CacheMiss ADT if cache miss.
        ADT types provide explicit semantics instead of None.
        """
        try:
            lookup_result = await self.cache.get_profile(user_id)
            # Pattern match on CacheLookupResult ADT and return appropriate type
            match lookup_result:
                case CacheHit(value=profile, ttl_remaining=_):
                    # Cache hit - return the ProfileData object
                    return Ok(EffectReturn(value=profile, effect_name="GetCachedProfile"))
                case CacheMiss() as miss:
                    # Cache miss - return the ADT type directly
                    return Ok(EffectReturn(value=miss, effect_name="GetCachedProfile"))
        except Exception as e:
            return Err(
                CacheError(
                    effect=effect,
                    cache_error=str(e),
                    is_retryable=self._is_retryable_error(e),
                )
            )

    async def _handle_put_profile(
        self, user_id: UUID, profile_data: ProfileData, ttl_seconds: int, effect: Effect
    ) -> Result[EffectReturn[EffectResult], InterpreterError]:
        """Handle PutCachedProfile effect."""
        try:
            await self.cache.put_profile(user_id, profile_data, ttl_seconds)
            return Ok(EffectReturn(value=None, effect_name="PutCachedProfile"))
        except Exception as e:
            return Err(
                CacheError(
                    effect=effect,
                    cache_error=str(e),
                    is_retryable=self._is_retryable_error(e),
                )
            )

    def _is_retryable_error(self, error: Exception) -> bool:
        """Determine if a cache error is retryable.

        Args:
            error: The exception that was raised

        Returns:
            True if error might succeed on retry, False otherwise
        """
        # Common retryable error patterns for cache
        error_str = str(error).lower()
        retryable_patterns = [
            "connection",
            "timeout",
            "unavailable",
            "network",
        ]
        return any(pattern in error_str for pattern in retryable_patterns)
