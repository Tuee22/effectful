"""Storage interpreter implementation for S3 effects.

This module implements the interpreter for storage effects (GetObject, PutObject,
DeleteObject, ListObjects).

Components:
    - StorageError: Error type for storage failures
    - StorageInterpreter: Interpreter for storage effects

The interpreter delegates to ObjectStorage protocol implementations, converting
protocol results to Result[EffectReturn, InterpreterError].

Type Safety:
    All pattern matching is exhaustive. All return types use Result for explicit
    error handling.
"""

from dataclasses import dataclass
from typing import Literal

from effectful.algebraic.effect_return import EffectReturn
from effectful.algebraic.result import Err, Ok, Result
from effectful.domain.s3_object import PutFailure, PutSuccess
from effectful.effects.base import Effect
from effectful.effects.storage import DeleteObject, GetObject, ListObjects, PutObject
from effectful.infrastructure.storage import ObjectStorage
from effectful.interpreters.errors import (
    InterpreterError,
    StorageError,
    UnhandledEffectError,
)
from effectful.interpreters.retry_logic import (
    STORAGE_RETRY_PATTERNS,
    is_retryable_error,
)
from effectful.programs.program_types import EffectResult


@dataclass(frozen=True)
class StorageInterpreter:
    """Interpreter for storage effects.

    This interpreter handles GetObject, PutObject, DeleteObject, and ListObjects
    effects by delegating to ObjectStorage implementations.

    Attributes:
        storage: Object storage implementation (S3, MinIO, fake, etc.)

    Example:
        >>> from effectful.testing.fakes import FakeObjectStorage
        >>>
        >>> interpreter = StorageInterpreter(storage=FakeObjectStorage())
        >>>
        >>> effect = GetObject(bucket="my-bucket", key="data/file.txt")
        >>> result = await interpreter.interpret(effect)
        >>>
        >>> match result:
        ...     case Ok(EffectReturn(value=s3_object, effect_name="GetObject")):
        ...         if s3_object is not None:
        ...             print(f"Retrieved: {s3_object.key}")
    """

    storage: ObjectStorage

    async def interpret(
        self, effect: Effect
    ) -> Result[EffectReturn[EffectResult], InterpreterError]:
        """Interpret a storage effect.

        Args:
            effect: The effect to interpret (must be a StorageEffect)

        Returns:
            Ok(EffectReturn) with effect result on success.
            Err(StorageError) on infrastructure failure.
            Err(UnhandledEffectError) if effect is not a storage effect.

        Note:
            Domain failures (quota exceeded, etc.) return Ok with appropriate result.
            Only infrastructure failures return Err.
        """
        match effect:
            case GetObject(bucket=bucket, key=key):
                return await self._handle_get(bucket, key, effect)
            case PutObject(
                bucket=bucket,
                key=key,
                content=content,
                metadata=metadata,
                content_type=content_type,
            ):
                return await self._handle_put(bucket, key, content, metadata, content_type, effect)
            case DeleteObject(bucket=bucket, key=key):
                return await self._handle_delete(bucket, key, effect)
            case ListObjects(bucket=bucket, prefix=prefix, max_keys=max_keys):
                return await self._handle_list(bucket, prefix, max_keys, effect)
            case _:
                return Err(
                    UnhandledEffectError(
                        effect=effect,
                        available_interpreters=["StorageInterpreter"],
                    )
                )

    async def _handle_get(
        self, bucket: str, key: str, effect: Effect
    ) -> Result[EffectReturn[EffectResult], InterpreterError]:
        """Handle GetObject effect.

        Returns:
            Ok with S3Object if object exists.
            Ok with None if object does not exist (not an error).
            Err(StorageError) on infrastructure failure.
        """
        try:
            s3_object = await self.storage.get_object(bucket, key)
            return Ok(EffectReturn(value=s3_object, effect_name="GetObject"))
        except Exception as e:
            return Err(
                StorageError(
                    effect=effect,
                    storage_error=str(e),
                    is_retryable=self._is_retryable_error(e),
                )
            )

    async def _handle_put(
        self,
        bucket: str,
        key: str,
        content: bytes,
        metadata: dict[str, str] | None,
        content_type: str | None,
        effect: Effect,
    ) -> Result[EffectReturn[EffectResult], InterpreterError]:
        """Handle PutObject effect.

        Returns:
            Ok with object key (str) on successful put.
            Err(StorageError) on infrastructure failure.
            Domain failures (quota, permissions) are handled by PutResult ADT.
        """
        try:
            put_result = await self.storage.put_object(bucket, key, content, metadata, content_type)

            # Pattern match on PutResult ADT
            match put_result:
                case PutSuccess(key=object_key):
                    # Success - return the PutSuccess ADT
                    return Ok(EffectReturn(value=put_result, effect_name="PutObject"))
                case PutFailure(key=failed_key, reason=reason):
                    # Domain failure - return error with retryability
                    is_retryable = self._is_retryable_put_failure(reason)
                    return Err(
                        StorageError(
                            effect=effect,
                            storage_error=f"PutObject failed: {reason}",
                            is_retryable=is_retryable,
                        )
                    )
        except Exception as e:
            # Infrastructure exception
            return Err(
                StorageError(
                    effect=effect,
                    storage_error=str(e),
                    is_retryable=self._is_retryable_error(e),
                )
            )

    async def _handle_delete(
        self, bucket: str, key: str, effect: Effect
    ) -> Result[EffectReturn[EffectResult], InterpreterError]:
        """Handle DeleteObject effect.

        Returns:
            Ok with None (deletion always succeeds - idempotent).
            Err(StorageError) on infrastructure failure.
        """
        try:
            await self.storage.delete_object(bucket, key)
            return Ok(EffectReturn(value=None, effect_name="DeleteObject"))
        except Exception as e:
            return Err(
                StorageError(
                    effect=effect,
                    storage_error=str(e),
                    is_retryable=self._is_retryable_error(e),
                )
            )

    async def _handle_list(
        self, bucket: str, prefix: str | None, max_keys: int, effect: Effect
    ) -> Result[EffectReturn[EffectResult], InterpreterError]:
        """Handle ListObjects effect.

        Returns:
            Ok with list[str] of object keys.
            Err(StorageError) on infrastructure failure.
        """
        try:
            keys = await self.storage.list_objects(bucket, prefix, max_keys)
            return Ok(EffectReturn(value=keys, effect_name="ListObjects"))
        except Exception as e:
            return Err(
                StorageError(
                    effect=effect,
                    storage_error=str(e),
                    is_retryable=self._is_retryable_error(e),
                )
            )

    def _is_retryable_error(self, error: Exception) -> bool:
        """Determine if error is retryable based on error message patterns.

        Retryable errors:
            - Network errors (connection, timeout, unavailable)
            - Throttling (rate limit, slow down)
            - Server errors (500, 503)

        Non-retryable errors:
            - Configuration errors
            - Authentication/authorization failures
            - Bucket not found
            - Invalid request

        Args:
            error: Exception raised during storage operation

        Returns:
            True if error is likely transient and retry might succeed.
        """
        return is_retryable_error(error, STORAGE_RETRY_PATTERNS)

    def _is_retryable_put_failure(
        self, reason: Literal["quota_exceeded", "permission_denied", "invalid_object_state"]
    ) -> bool:
        """Determine if PutFailure reason is retryable.

        Args:
            reason: PutFailure reason (quota_exceeded, permission_denied, invalid_object_state)

        Returns:
            True if retry might succeed.
        """
        match reason:
            case "quota_exceeded":
                # Quota might be available later if cleanup occurs
                return True
            case "permission_denied":
                # Permissions unlikely to change - not retryable
                return False
            case "invalid_object_state":
                # Object state might change (e.g., lock released)
                return True
