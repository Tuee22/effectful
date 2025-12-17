import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import pytest
from fastapi import APIRouter, FastAPI
from prometheus_client import CollectorRegistry

from effectful.algebraic.effect_return import EffectReturn
from effectful.algebraic.result import Ok
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
from effectful.interpreters.runtime import RuntimeInterpreter
from effectful.programs.runners import run_ws_program

from app.programs.startup import (
    RouterSpec,
    StaticMountSpec,
    shutdown_program,
    startup_program,
)
from app.interpreters import runtime_interpreter


@pytest.mark.asyncio
async def test_runtime_interpreter_handles_runtime_effects() -> None:
    calls: list[str] = []

    async def create_pool(effect: CreateDatabasePool) -> ResourceHandle[str]:
        calls.append("create_pool")
        return ResourceHandle(kind="database_pool", resource="pool")

    async def close_pool(effect: CloseDatabasePool[str]) -> None:
        calls.append("close_pool")

    async def close_redis_factory(effect: CloseRedisClientFactory[str]) -> None:
        calls.append("close_redis_factory")

    async def close_observability(effect: CloseObservabilityInterpreter[str]) -> None:
        calls.append("close_observability")

    async def set_metadata(effect: SetAppMetadata) -> None:
        calls.append("set_metadata")

    async def configure_cors(effect: ConfigureCors) -> None:
        calls.append("configure_cors")

    async def include_router(effect: IncludeRouter) -> None:
        calls.append("include_router")

    async def mount_static(effect: MountStatic) -> None:
        calls.append("mount_static")

    async def create_redis_factory(effect: CreateRedisClientFactory) -> ResourceHandle[str]:
        calls.append("create_redis_factory")
        return ResourceHandle(kind="redis_factory", resource="redis_factory")

    async def create_observability(effect: CreateObservabilityInterpreter) -> ResourceHandle[str]:
        calls.append("create_observability")
        return ResourceHandle(kind="observability", resource="obs")

    async def register_route(effect: RegisterHttpRoute) -> None:
        calls.append(f"register_route:{effect.path}")

    interpreter = RuntimeInterpreter(
        create_db_pool=create_pool,
        close_db_pool=close_pool,
        close_redis_factory=close_redis_factory,
        close_observability_interpreter=close_observability,
        configure_cors=configure_cors,
        include_router=include_router,
        set_app_metadata=set_metadata,
        mount_static=mount_static,
        create_redis_factory=create_redis_factory,
        create_observability_interpreter=create_observability,
        register_route=register_route,
    )

    pool_effect = CreateDatabasePool(
        host="localhost",
        port=5432,
        database="db",
        user="user",
        password="pw",
        min_size=1,
        max_size=5,
        command_timeout=60.0,
    )
    pool_result = await interpreter.interpret(pool_effect)
    assert isinstance(pool_result, Ok)
    assert isinstance(pool_result.value, EffectReturn)
    assert isinstance(pool_result.value.value, ResourceHandle)

    # Non-pool effects return None as value
    for eff in (
        SetAppMetadata(app=ResourceHandle("app", object()), title="", description="", version=""),
        ConfigureCors(
            app=ResourceHandle("app", object()),
            allow_origins=("http://localhost",),
            allow_credentials=True,
            allow_methods=("GET",),
            allow_headers=("Authorization",),
        ),
        IncludeRouter(
            app=ResourceHandle("app", object()),
            router="router",
            prefix="/api",
            tags=("tag",),
        ),
        MountStatic(
            app=ResourceHandle("app", object()),
            path="/static",
            directory="/tmp/static",
            name="static",
        ),
        CreateRedisClientFactory(host="localhost", port=6379, db=0),
        CreateObservabilityInterpreter(metrics_registry=object()),
        RegisterHttpRoute(
            app=ResourceHandle("app", object()),
            path="/metrics",
            endpoint=lambda: None,
            methods=("GET",),
            include_in_schema=False,
            response_model=None,
        ),
        CloseDatabasePool(handle=ResourceHandle("database_pool", "pool")),
        CloseRedisClientFactory(handle=ResourceHandle("redis_factory", "redis")),
        CloseObservabilityInterpreter(handle=ResourceHandle("observability", "obs")),
    ):
        result = await interpreter.interpret(eff)
        assert isinstance(result, Ok)
        assert result.value.value is None or isinstance(result.value.value, ResourceHandle)

    assert calls == [
        "create_pool",
        "set_metadata",
        "configure_cors",
        "include_router",
        "mount_static",
        "create_redis_factory",
        "create_observability",
        "register_route:/metrics",
        "close_pool",
        "close_redis_factory",
        "close_observability",
    ]


class _StubSettings:
    app_name = "HealthHub"
    api_prefix = "/api"
    cors_origins = ("http://localhost",)
    cors_allow_credentials = True
    cors_allow_methods = ("*",)
    cors_allow_headers = ("*",)
    postgres_host = "localhost"
    postgres_port = 5432
    postgres_db = "db"
    postgres_user = "user"
    postgres_password = "pw"
    redis_host = "localhost"
    redis_port = 6379
    redis_db = 0
    frontend_build_path = "/tmp/frontend"


@pytest.mark.asyncio
async def test_build_runtime_interpreter_runs_startup_and_shutdown(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    class _FakePool:
        def __init__(self) -> None:
            self.closed = False

        async def close(self) -> None:
            self.closed = True

    async def fake_create_pool(
        host: str,
        port: int,
        database: str,
        user: str,
        password: str,
        min_size: int,
        max_size: int,
        command_timeout: float,
    ) -> ResourceHandle[_FakePool]:
        pool = _FakePool()
        return ResourceHandle(kind="database_pool", resource=pool)

    monkeypatch.setattr(runtime_interpreter.asyncpg, "create_pool", fake_create_pool)

    app = FastAPI()
    router = APIRouter()

    @router.get("/health")
    async def _health() -> dict[str, str]:
        return {"status": "ok"}

    static_dir = tmp_path / "static"
    static_dir.mkdir()

    settings = _StubSettings()

    runtime = runtime_interpreter.build_runtime_interpreter()
    startup_result = await run_ws_program(
        startup_program(
            settings=settings,
            app_handle=ResourceHandle(kind="fastapi_app", resource=app),
            routers=(RouterSpec(router=router, prefix="/api", tags=("health",)),),
            static_mounts=(
                StaticMountSpec(path="/static", directory=str(static_dir), name="static"),
            ),
            frontend_build_path=tmp_path,
            collector_registry=CollectorRegistry(),
        ),
        runtime,
    )

    assert isinstance(startup_result, Ok)
    assembly = startup_result.value
    pool_resource = assembly.database_pool.resource
    assert getattr(app.state, "cors_configured", False) is True

    paths = {route.path for route in app.router.routes}
    assert "/api/health" in paths
    assert "/metrics" in paths
    assert "/favicon.ico" in paths
    assert "/{full_path:path}" in paths
    assert "/static" in paths

    shutdown_result = await run_ws_program(shutdown_program(assembly), runtime)
    assert isinstance(shutdown_result, Ok)
    assert pool_resource.closed is True
