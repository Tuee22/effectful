"""Interpreter for runtime assembly effects."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Generic, TypeVar

from effectful.algebraic.effect_return import EffectReturn
from effectful.algebraic.result import Err, Ok, Result
from effectful.effects.base import Effect
from effectful.effects.runtime import (
    CloseDatabasePool,
    CloseObservabilityInterpreter,
    CloseRedisClientFactory,
    CreateDatabasePool,
    ConfigureCors,
    IncludeRouter,
    MountStatic,
    CreateObservabilityInterpreter,
    CreateRedisClientFactory,
    RegisterHttpRoute,
    ResourceHandle,
    SetAppMetadata,
)
from effectful.interpreters.errors import (
    CacheError,
    DatabaseError,
    InterpreterError,
    ObservabilityError,
    RuntimeAssemblyError,
    UnhandledEffectError,
)
from effectful.programs.program_types import EffectResult

T_pool = TypeVar("T_pool")


@dataclass(frozen=True)
class RuntimeInterpreter(Generic[T_pool]):
    """Interpreter for runtime assembly effects (e.g., database pool lifecycle)."""

    create_db_pool: Callable[[CreateDatabasePool], Awaitable[ResourceHandle[T_pool]]] | None = None
    close_db_pool: Callable[[CloseDatabasePool[T_pool]], Awaitable[None]] | None = None
    close_redis_factory: (
        Callable[[CloseRedisClientFactory[object]], Awaitable[None]] | None
    ) = None
    close_observability_interpreter: (
        Callable[[CloseObservabilityInterpreter[object]], Awaitable[None]] | None
    ) = None
    configure_cors: Callable[[ConfigureCors], Awaitable[None]] | None = None
    include_router: Callable[[IncludeRouter], Awaitable[None]] | None = None
    set_app_metadata: Callable[[SetAppMetadata], Awaitable[None]] | None = None
    mount_static: Callable[[MountStatic], Awaitable[None]] | None = None
    create_redis_factory: (
        Callable[[CreateRedisClientFactory], Awaitable[ResourceHandle[object]]] | None
    ) = None
    create_observability_interpreter: (
        Callable[[CreateObservabilityInterpreter], Awaitable[ResourceHandle[object]]] | None
    ) = None
    register_route: Callable[[RegisterHttpRoute], Awaitable[None]] | None = None

    async def interpret(
        self, effect: Effect
    ) -> Result[EffectReturn[EffectResult], InterpreterError]:
        match effect:
            case CreateDatabasePool():
                if self.create_db_pool is None:
                    return Err(
                        UnhandledEffectError(
                            effect=effect,
                            available_interpreters=["RuntimeInterpreter"],
                        )
                    )
                try:
                    handle: ResourceHandle[T_pool] = await self.create_db_pool(effect)
                except Exception as exc:
                    return Err(
                        DatabaseError(
                            effect=effect,
                            db_error=str(exc),
                            is_retryable=False,
                        )
                    )
                return Ok(EffectReturn(value=handle, effect_name="CreateDatabasePool"))

            case CloseDatabasePool():
                if self.close_db_pool is None:
                    return Err(
                        UnhandledEffectError(
                            effect=effect,
                            available_interpreters=["RuntimeInterpreter"],
                        )
                    )
                try:
                    await self.close_db_pool(effect)
                except Exception as exc:
                    return Err(
                        DatabaseError(
                            effect=effect,
                            db_error=str(exc),
                            is_retryable=False,
                        )
                    )
                return Ok(EffectReturn(value=None, effect_name="CloseDatabasePool"))

            case CloseRedisClientFactory():
                if self.close_redis_factory is None:
                    return Err(
                        UnhandledEffectError(
                            effect=effect,
                            available_interpreters=["RuntimeInterpreter"],
                        )
                    )
                try:
                    await self.close_redis_factory(effect)
                except Exception as exc:
                    return Err(
                        CacheError(
                            effect=effect,
                            cache_error=str(exc),
                            is_retryable=False,
                        )
                    )
                return Ok(EffectReturn(value=None, effect_name="CloseRedisClientFactory"))

            case CloseObservabilityInterpreter():
                if self.close_observability_interpreter is None:
                    return Err(
                        UnhandledEffectError(
                            effect=effect,
                            available_interpreters=["RuntimeInterpreter"],
                        )
                    )
                try:
                    await self.close_observability_interpreter(effect)
                except Exception as exc:
                    return Err(
                        ObservabilityError(
                            effect=effect,
                            observability_error=str(exc),
                            is_retryable=False,
                        )
                    )
                return Ok(EffectReturn(value=None, effect_name="CloseObservabilityInterpreter"))

            case ConfigureCors():
                if self.configure_cors is None:
                    return Err(
                        UnhandledEffectError(
                            effect=effect,
                            available_interpreters=["RuntimeInterpreter"],
                        )
                    )
                try:
                    await self.configure_cors(effect)
                except Exception as exc:
                    return Err(
                        RuntimeAssemblyError(
                            effect=effect,
                            runtime_error=str(exc),
                        )
                    )
                return Ok(EffectReturn(value=None, effect_name="ConfigureCors"))

            case IncludeRouter():
                if self.include_router is None:
                    return Err(
                        UnhandledEffectError(
                            effect=effect,
                            available_interpreters=["RuntimeInterpreter"],
                        )
                    )
                try:
                    await self.include_router(effect)
                except Exception as exc:
                    return Err(
                        RuntimeAssemblyError(
                            effect=effect,
                            runtime_error=str(exc),
                        )
                    )
                return Ok(EffectReturn(value=None, effect_name="IncludeRouter"))

            case SetAppMetadata():
                if self.set_app_metadata is None:
                    return Err(
                        UnhandledEffectError(
                            effect=effect,
                            available_interpreters=["RuntimeInterpreter"],
                        )
                    )
                try:
                    await self.set_app_metadata(effect)
                except Exception as exc:
                    return Err(
                        RuntimeAssemblyError(
                            effect=effect,
                            runtime_error=str(exc),
                        )
                    )
                return Ok(EffectReturn(value=None, effect_name="SetAppMetadata"))

            case MountStatic():
                if self.mount_static is None:
                    return Err(
                        UnhandledEffectError(
                            effect=effect,
                            available_interpreters=["RuntimeInterpreter"],
                        )
                    )
                try:
                    await self.mount_static(effect)
                except Exception as exc:
                    return Err(
                        RuntimeAssemblyError(
                            effect=effect,
                            runtime_error=str(exc),
                        )
                    )
                return Ok(EffectReturn(value=None, effect_name="MountStatic"))

            case CreateRedisClientFactory():
                if self.create_redis_factory is None:
                    return Err(
                        UnhandledEffectError(
                            effect=effect,
                            available_interpreters=["RuntimeInterpreter"],
                        )
                    )
                try:
                    redis_handle: ResourceHandle[object] = await self.create_redis_factory(effect)
                except Exception as exc:
                    return Err(
                        CacheError(
                            effect=effect,
                            cache_error=str(exc),
                            is_retryable=False,
                        )
                    )
                return Ok(EffectReturn(value=redis_handle, effect_name="CreateRedisClientFactory"))

            case CreateObservabilityInterpreter():
                if self.create_observability_interpreter is None:
                    return Err(
                        UnhandledEffectError(
                            effect=effect,
                            available_interpreters=["RuntimeInterpreter"],
                        )
                    )
                try:
                    observability_handle: ResourceHandle[
                        object
                    ] = await self.create_observability_interpreter(effect)
                except Exception as exc:
                    return Err(
                        ObservabilityError(
                            effect=effect,
                            observability_error=str(exc),
                            is_retryable=False,
                        )
                    )
                return Ok(
                    EffectReturn(
                        value=observability_handle, effect_name="CreateObservabilityInterpreter"
                    )
                )

            case RegisterHttpRoute():
                if self.register_route is None:
                    return Err(
                        UnhandledEffectError(
                            effect=effect,
                            available_interpreters=["RuntimeInterpreter"],
                        )
                    )
                try:
                    await self.register_route(effect)
                except Exception as exc:
                    return Err(
                        RuntimeAssemblyError(
                            effect=effect,
                            runtime_error=str(exc),
                        )
                    )
                return Ok(EffectReturn(value=None, effect_name="RegisterHttpRoute"))

            case _:
                return Err(
                    UnhandledEffectError(
                        effect=effect,
                        available_interpreters=["RuntimeInterpreter"],
                    )
                )
