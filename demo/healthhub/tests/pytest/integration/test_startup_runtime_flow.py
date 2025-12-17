import asyncio
from pathlib import Path

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.routing import APIRoute
from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry

from effectful.algebraic.result import Ok
from effectful.effects.runtime import ResourceHandle
from effectful.programs.runners import run_ws_program

from app.config import Settings
from app.interpreters.runtime_interpreter import build_runtime_interpreter
from app.programs.startup import (
    RouterSpec,
    StaticMountSpec,
    shutdown_program,
    startup_program,
)


@pytest.mark.asyncio
async def test_startup_and_shutdown_run_against_real_infrastructure(tmp_path: Path) -> None:
    """End-to-end runtime flow with real Postgres/Redis via Docker compose."""

    # Settings are injected once; values match the compose stack
    settings = Settings(
        postgres_host="postgres",
        postgres_port=5432,
        postgres_db="healthhub_db",
        postgres_user="healthhub",
        postgres_password="healthhub_secure_pass",
        redis_host="redis",
        redis_port=6379,
        redis_db=0,
        pulsar_url="pulsar://pulsar:6650",
        pulsar_admin_url="http://pulsar:8080",
        minio_endpoint="minio:9000",
        minio_access_key="minioadmin",
        minio_secret_key="minioadmin",
        minio_bucket="healthhub",
        minio_secure=False,
        jwt_secret_key="dev-secret",
        jwt_algorithm="HS256",
        jwt_access_token_expire_minutes=15,
        jwt_refresh_token_expire_days=7,
        cors_origins=["http://localhost:8851"],
        cors_allow_credentials=True,
        cors_allow_methods=["*"],
        cors_allow_headers=["*"],
        app_env="integration",
        log_level="INFO",
    )

    app = FastAPI()
    app_handle = ResourceHandle(kind="fastapi_app", resource=app)

    router = APIRouter()

    @router.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    routers = (RouterSpec(router=router, prefix=f"{settings.api_prefix}/health", tags=("health",)),)

    static_dir = tmp_path / "static"
    static_dir.mkdir()
    (static_dir / "ok.txt").write_text("ok", encoding="utf-8")
    static_mounts = (StaticMountSpec(path="/static", directory=str(static_dir), name="static"),)

    runtime_interpreter = build_runtime_interpreter()

    startup_result = await run_ws_program(
        startup_program(
            settings,
            app_handle=app_handle,
            routers=routers,
            static_mounts=static_mounts,
            frontend_build_path=tmp_path,
            collector_registry=CollectorRegistry(),
        ),
        runtime_interpreter,
    )
    assert isinstance(startup_result, Ok)
    startup = startup_result.value

    # Database handle works against real Postgres
    pool = startup.database_pool.resource
    async with pool.acquire() as conn:
        value = await conn.fetchval("SELECT 1")
        assert value == 1

    # Redis factory produces usable clients
    async with startup.redis_factory.resource.managed() as client:
        pong = await client.ping()
        assert pong in (True, b"PONG", "PONG")

    # Metrics route registered by the pure program
    api_routes = [route for route in app.router.routes if isinstance(route, APIRoute)]
    paths = {route.path for route in api_routes}
    assert "/metrics" in paths
    assert "/favicon.ico" in paths
    assert "/{full_path:path}" in paths

    metrics_route = next(route for route in api_routes if route.path == "/metrics")
    metrics_response = await metrics_route.endpoint()
    assert metrics_response.media_type == CONTENT_TYPE_LATEST
    assert metrics_response.body  # non-empty scrape output from registry

    # Teardown closes resources cleanly
    shutdown_result = await run_ws_program(shutdown_program(startup), runtime_interpreter)
    assert isinstance(shutdown_result, Ok)

    # Wait a moment to allow pools to close cleanly in CI
    await asyncio.sleep(0.05)
