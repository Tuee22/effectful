from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.routing import APIRoute

from app import main
from app.config import Settings


@pytest.mark.asyncio
async def test_main_lifespan_runs_startup_and_shutdown_with_real_infra(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    frontend_dir = tmp_path / "frontend-build"
    frontend_dir.mkdir(parents=True, exist_ok=True)
    static_dir = frontend_dir / "static"
    assets_dir = frontend_dir / "assets"
    static_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)
    (static_dir / "placeholder.txt").write_text("ok", encoding="utf-8")
    (assets_dir / "placeholder.txt").write_text("ok", encoding="utf-8")

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
        cors_origins=["http://localhost"],
        cors_allow_credentials=True,
        cors_allow_methods=["*"],
        cors_allow_headers=["*"],
        app_env="integration",
        log_level="INFO",
        frontend_build_path=str(frontend_dir),
    )

    monkeypatch.setattr(main, "Settings", lambda: settings)

    app_instance = FastAPI(lifespan=main.lifespan)

    async with main.lifespan(app_instance):
        container = app_instance.state.container
        assert container.database_pool is not None
        assert container.redis_factory is not None
        assert container.observability_interpreter is not None

        async with container.database_pool.acquire() as conn:
            assert await conn.fetchval("SELECT 1") == 1

        async with container.redis_factory.managed() as client:
            pong = await client.ping()
            assert pong in (True, b"PONG", "PONG")

        api_routes = [route for route in app_instance.router.routes if isinstance(route, APIRoute)]
        paths = {route.path for route in api_routes}
        assert "/metrics" in paths
        assert "/favicon.ico" in paths
        assert "/{full_path:path}" in paths
