import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import pytest

from effectful.effects.runtime import (
    CloseDatabasePool,
    CloseObservabilityInterpreter,
    CloseRedisClientFactory,
    ConfigureCors,
    CreateDatabasePool,
    CreateObservabilityInterpreter,
    CreateRedisClientFactory,
    IncludeRouter,
    MountStatic,
    RegisterHttpRoute,
    ResourceHandle,
    SetAppMetadata,
)

from app.programs.startup import (
    HandleTypeMismatch,
    RouterSpec,
    StartupAssembly,
    StaticMountSpec,
    startup_program,
)


class _DummySettings:
    app_name = "HealthHub"
    api_prefix = "/api"
    cors_origins = ["http://localhost"]
    cors_allow_credentials = True
    cors_allow_methods = ["*"]
    cors_allow_headers = ["*"]
    postgres_host = "localhost"
    postgres_port = 5432
    postgres_db = "db"
    postgres_user = "user"
    postgres_password = "pw"
    redis_host = "localhost"
    redis_port = 6379
    redis_db = 0
    frontend_build_path = "/tmp/frontend"


def test_startup_program_yields_effects_in_order() -> None:
    settings = _DummySettings()
    app_handle = ResourceHandle(kind="fastapi_app", resource=object())
    routers = (
        RouterSpec(router="health", prefix="", tags=("health",)),
        RouterSpec(router="auth", prefix="/api/auth", tags=("auth",)),
    )
    static_mounts = (StaticMountSpec(path="/static", directory="/tmp/static", name="static"),)
    frontend_build_path = Path("/tmp/frontend")

    program = startup_program(
        settings=settings,
        app_handle=app_handle,
        routers=routers,
        static_mounts=static_mounts,
        frontend_build_path=frontend_build_path,
    )

    effects: list[object] = []
    redis_factory_handle: ResourceHandle[object] | None = None
    observability_handle: ResourceHandle[object] | None = None

    while True:
        try:
            effect = next(program)
        except StopIteration as stop_info:
            assembly: StartupAssembly = stop_info.value
            assert assembly.app_handle is app_handle
            assert assembly.redis_factory is redis_factory_handle
            assert assembly.observability is observability_handle
            assert assembly.database_pool is pool_handle
            break
        effects.append(effect)
        if isinstance(effect, CreateRedisClientFactory):
            redis_factory_handle = ResourceHandle(kind="redis_factory", resource=object())
            effect = program.send(redis_factory_handle)
            effects.append(effect)
            continue
        if isinstance(effect, CreateObservabilityInterpreter):
            observability_handle = ResourceHandle(kind="observability", resource=object())
            effect = program.send(observability_handle)
            effects.append(effect)
            continue
        if isinstance(effect, CreateDatabasePool):
            pool_handle = ResourceHandle(kind="database_pool", resource=object())
            effect = program.send(pool_handle)
            effects.append(effect)
            continue
        try:
            effect = program.send(None)
            effects.append(effect)
        except StopIteration as stop_info:
            assembly = stop_info.value
            assert assembly.app_handle is app_handle
            assert assembly.redis_factory is redis_factory_handle
            assert assembly.observability is observability_handle
            assert assembly.database_pool is pool_handle
            break

    assert isinstance(effects[0], SetAppMetadata)
    assert isinstance(effects[1], ConfigureCors)
    assert isinstance(effects[2], IncludeRouter)
    assert isinstance(effects[3], IncludeRouter)
    assert isinstance(effects[4], MountStatic)
    assert isinstance(effects[5], CreateObservabilityInterpreter)
    assert isinstance(effects[6], RegisterHttpRoute)
    assert isinstance(effects[7], CreateRedisClientFactory)
    assert isinstance(effects[8], CreateDatabasePool)
    assert isinstance(effects[9], RegisterHttpRoute)
    assert effects[9].path == "/favicon.ico"
    assert isinstance(effects[10], RegisterHttpRoute)
    assert effects[10].path == "/{full_path:path}"


def test_shutdown_program_closes_pool() -> None:
    app_handle = ResourceHandle(kind="fastapi_app", resource=object())
    pool_handle = ResourceHandle(kind="database_pool", resource=object())
    redis_factory_handle = ResourceHandle(kind="redis_factory", resource=object())
    observability_handle = ResourceHandle(kind="observability", resource=object())
    assembly = StartupAssembly(
        app_handle=app_handle,
        database_pool=pool_handle,
        redis_factory=redis_factory_handle,
        observability=observability_handle,
    )
    program = shutdown_program(assembly)

    effect = next(program)
    assert isinstance(effect, CloseRedisClientFactory)
    assert effect.handle is redis_factory_handle

    effect = program.send(None)
    assert isinstance(effect, CloseObservabilityInterpreter)
    assert effect.handle is observability_handle

    effect = program.send(None)
    assert isinstance(effect, CloseDatabasePool)
    assert effect.handle is pool_handle

    with pytest.raises(StopIteration):
        program.send(None)


def test_startup_program_returns_typed_error_on_handle_mismatch() -> None:
    settings = _DummySettings()
    app_handle = ResourceHandle(kind="fastapi_app", resource=object())
    routers: tuple[RouterSpec, ...] = ()
    static_mounts: tuple[StaticMountSpec, ...] = ()
    frontend_build_path = Path("/tmp/frontend")

    program = startup_program(
        settings=settings,
        app_handle=app_handle,
        routers=routers,
        static_mounts=static_mounts,
        frontend_build_path=frontend_build_path,
    )

    effect = next(program)
    assert isinstance(effect, SetAppMetadata)

    effect = program.send(None)
    assert isinstance(effect, ConfigureCors)

    effect = program.send(None)
    assert isinstance(effect, CreateObservabilityInterpreter)

    mismatch = program.send(ResourceHandle(kind="observability", resource=object()))
    assert isinstance(mismatch, HandleTypeMismatch)
    assert mismatch.effect == "CreateObservabilityInterpreter"
