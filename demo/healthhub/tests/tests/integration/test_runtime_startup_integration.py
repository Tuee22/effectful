from pathlib import Path

import asyncpg
import pytest
from fastapi import APIRouter, FastAPI
from prometheus_client import CollectorRegistry

from effectful.algebraic.result import Ok
from effectful.effects.runtime import ResourceHandle
from effectful.programs.runners import run_ws_program

from app.config import Settings
from app.interpreters.runtime_interpreter import build_runtime_interpreter
from app.programs.startup import RouterSpec, StaticMountSpec, shutdown_program, startup_program


pytestmark = [pytest.mark.integration]


@pytest.mark.asyncio
async def test_startup_and_shutdown_round_trip(tmp_path: Path) -> None:
    settings = Settings()
    app = FastAPI()
    runtime = build_runtime_interpreter()

    router = APIRouter()

    @router.get("/health")
    async def _health() -> dict[str, str]:
        return {"status": "ok"}

    frontend_root = tmp_path / "frontend"
    static_dir = frontend_root / "static"
    assets_dir = frontend_root / "assets"
    static_dir.mkdir(parents=True)
    assets_dir.mkdir(parents=True)

    startup_result = await run_ws_program(
        startup_program(
            settings=settings,
            app_handle=ResourceHandle(kind="fastapi_app", resource=app),
            routers=(RouterSpec(router=router, prefix="/api", tags=("health",)),),
            static_mounts=(
                StaticMountSpec(path="/static", directory=str(static_dir), name="static"),
                StaticMountSpec(path="/assets", directory=str(assets_dir), name="assets"),
            ),
            frontend_build_path=frontend_root,
            collector_registry=CollectorRegistry(),
        ),
        runtime,
    )

    assert isinstance(startup_result, Ok)
    assembly = startup_result.value
    assert isinstance(assembly.database_pool.resource, asyncpg.pool.Pool)
    async with assembly.redis_factory.resource.managed() as client:
        pong = await client.ping()
        assert pong in (b"PONG", "PONG")

    shutdown_result = await run_ws_program(shutdown_program(assembly), runtime)
    assert isinstance(shutdown_result, Ok)
