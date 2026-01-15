import pytest
from fastapi import FastAPI

from effectful.algebraic.result import Err, Ok
from effectful.effects.runtime import ResourceHandle

from app import main
from app.programs.startup import StartupAssembly


class _StubSettings:
    app_name = "TestApp"
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


class _FakeObservability:
    def render_latest(self) -> bytes:
        return b"ok"

    async def close(self) -> None:
        return None


@pytest.mark.asyncio
async def test_lifespan_stores_handles_and_runs_shutdown(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime_interpreter = object()
    calls: list[str] = []

    startup_assembly = StartupAssembly(
        app_handle=ResourceHandle(kind="app", resource=object()),
        database_pool=ResourceHandle(kind="database_pool", resource=object()),
        redis_factory=ResourceHandle(kind="redis_factory", resource=object()),
        observability=ResourceHandle(kind="observability", resource=_FakeObservability()),
    )

    async def fake_run(program: object, interpreter: object) -> Ok[StartupAssembly] | Ok[None]:
        assert interpreter is runtime_interpreter
        if not calls:
            calls.append("startup")
            return Ok(startup_assembly)
        calls.append("shutdown")
        return Ok(None)

    monkeypatch.setattr(main, "Settings", _StubSettings)
    monkeypatch.setattr(main, "build_runtime_interpreter", lambda: runtime_interpreter)
    monkeypatch.setattr(main, "run_ws_program", fake_run)

    app_instance = FastAPI(lifespan=main.lifespan)

    async with main.lifespan(app_instance):
        assert calls == ["startup"]
        assert app_instance.state.startup_assembly is startup_assembly
        assert app_instance.state.runtime_interpreter is runtime_interpreter
        assert app_instance.state.container.database_pool is not None

    assert calls == ["startup", "shutdown"]


@pytest.mark.asyncio
async def test_lifespan_raises_on_startup_err(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_run(program: object, interpreter: object) -> Err[str]:
        return Err("boom")

    monkeypatch.setattr(main, "Settings", _StubSettings)
    monkeypatch.setattr(main, "build_runtime_interpreter", lambda: object())
    monkeypatch.setattr(main, "run_ws_program", fake_run)

    app_instance = FastAPI(lifespan=main.lifespan)

    with pytest.raises(main.StartupFailure):
        async with main.lifespan(app_instance):
            pass


@pytest.mark.asyncio
async def test_lifespan_raises_on_shutdown_err(monkeypatch: pytest.MonkeyPatch) -> None:
    startup_assembly = StartupAssembly(
        app_handle=ResourceHandle(kind="app", resource=object()),
        database_pool=ResourceHandle(kind="database_pool", resource=object()),
        redis_factory=ResourceHandle(kind="redis_factory", resource=object()),
        observability=ResourceHandle(kind="observability", resource=_FakeObservability()),
    )

    calls: list[str] = []

    async def fake_run(
        program: object, interpreter: object
    ) -> Err[str] | Ok[StartupAssembly] | Ok[None]:
        if not calls:
            calls.append("startup")
            return Ok(startup_assembly)
        calls.append("shutdown")
        return Err("shutdown failed")

    monkeypatch.setattr(main, "Settings", _StubSettings)
    monkeypatch.setattr(main, "build_runtime_interpreter", lambda: object())
    monkeypatch.setattr(main, "run_ws_program", fake_run)

    app_instance = FastAPI(lifespan=main.lifespan)

    with pytest.raises(main.ShutdownFailure):
        async with main.lifespan(app_instance):
            pass

    assert calls == ["startup", "shutdown"]
