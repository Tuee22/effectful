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
from effectful.effects.cache import (
    DeleteCachedProfile,
    GetCachedProfile,
    GetCachedValue,
    InvalidateCache,
    PutCachedProfile,
    PutCachedValue,
)
from effectful.infrastructure.cache import ProfileCache
from effectful.interpreters.errors import (
    CacheError,
    InterpreterError,
    UnhandledEffectError,
)
from effectful.interpreters.retry_logic import (
    CACHE_RETRY_PATTERNS,
    is_retryable_error,
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
            case GetCachedValue(key=key):
                return await self._handle_get_value(key, effect)
            case PutCachedValue(key=key, value=value, ttl_seconds=ttl):
                return await self._handle_put_value(key, value, ttl, effect)
            case InvalidateCache(key=key):
                return await self._handle_invalidate(key, effect)
            case DeleteCachedProfile(user_id=user_id):
                return await self._handle_invalidate(str(user_id), effect, "DeleteCachedProfile")
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
            match lookup_result:  # pragma: no branch
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

    async def _handle_get_value(
        self, key: str, effect: Effect
    ) -> Result[EffectReturn[EffectResult], InterpreterError]:
        """Handle GetCachedValue effect.

        Returns bytes if cache hit, CacheMiss ADT if cache miss.
        """
        try:
            lookup_result = await self.cache.get_value(key)
            match lookup_result:  # pragma: no branch
                case CacheHit(value=value, ttl_remaining=_):
                    return Ok(EffectReturn(value=value, effect_name="GetCachedValue"))
                case CacheMiss() as miss:
                    return Ok(EffectReturn(value=miss, effect_name="GetCachedValue"))
        except Exception as e:
            return Err(
                CacheError(
                    effect=effect,
                    cache_error=str(e),
                    is_retryable=self._is_retryable_error(e),
                )
            )

    async def _handle_put_value(
        self, key: str, value: bytes, ttl_seconds: int, effect: Effect
    ) -> Result[EffectReturn[EffectResult], InterpreterError]:
        """Handle PutCachedValue effect."""
        try:
            await self.cache.put_value(key, value, ttl_seconds)
            return Ok(EffectReturn(value=True, effect_name="PutCachedValue"))
        except Exception as e:
            return Err(
                CacheError(
                    effect=effect,
                    cache_error=str(e),
                    is_retryable=self._is_retryable_error(e),
                )
            )

    async def _handle_invalidate(
        self, key: str, effect: Effect, effect_name: str = "InvalidateCache"
    ) -> Result[EffectReturn[EffectResult], InterpreterError]:
        """Handle InvalidateCache effect."""
        try:
            deleted = await self.cache.invalidate(key)
            return Ok(EffectReturn(value=deleted, effect_name=effect_name))
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
        return is_retryable_error(error, CACHE_RETRY_PATTERNS)
