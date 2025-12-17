"""HealthHub FastAPI Application Entry Point.

Main application with lifespan management, CORS, API routing, and static assets.
"""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI

from effectful.algebraic.result import Err, Ok
from effectful.effects.runtime import ResourceHandle
from effectful.programs.runners import run_ws_program

from app.config import Settings
from app.container import ApplicationContainer
from app.adapters.asyncpg_pool import AsyncPgPoolAdapter
from app.adapters.interpreter_factory import ProductionInterpreterFactory
from app.interpreters.runtime_interpreter import build_runtime_interpreter
from app.programs.startup import (
    HandleTypeMismatch,
    RouterSpec,
    StartupAssembly,
    StaticMountSpec,
    shutdown_program,
    startup_program,
)
from app.api import (
    auth_router,
    health_router,
    patients_router,
    appointments_router,
    prescriptions_router,
    lab_results_router,
    invoices_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan manager.

    Creates ApplicationContainer with protocol implementations,
    stores in app.state for dependency injection.
    """
    # Load settings (Doctrine 7: Configuration Lifecycle Management)
    settings = Settings()
    frontend_build_path = Path(settings.frontend_build_path)

    # Pure handle to the FastAPI app
    app_handle = ResourceHandle(kind="fastapi_app", resource=app)

    routers: tuple[RouterSpec, ...] = (
        RouterSpec(router=health_router, prefix="", tags=("health",)),
        RouterSpec(router=auth_router, prefix=f"{settings.api_prefix}/auth", tags=("auth",)),
        RouterSpec(
            router=patients_router,
            prefix=f"{settings.api_prefix}/patients",
            tags=("patients",),
        ),
        RouterSpec(
            router=appointments_router,
            prefix=f"{settings.api_prefix}/appointments",
            tags=("appointments",),
        ),
        RouterSpec(
            router=prescriptions_router,
            prefix=f"{settings.api_prefix}/prescriptions",
            tags=("prescriptions",),
        ),
        RouterSpec(
            router=lab_results_router,
            prefix=f"{settings.api_prefix}/lab-results",
            tags=("lab-results",),
        ),
        RouterSpec(
            router=invoices_router,
            prefix=f"{settings.api_prefix}/invoices",
            tags=("invoices",),
        ),
    )

    static_mounts: tuple[StaticMountSpec, ...] = (
        StaticMountSpec(
            path="/static",
            directory=str(frontend_build_path / "static"),
            name="static",
        ),
        StaticMountSpec(
            path="/assets",
            directory=str(frontend_build_path / "assets"),
            name="assets",
        ),
    )

    # Startup: Create database pool via runtime interpreter
    runtime_interpreter = build_runtime_interpreter()
    startup_result = await run_ws_program(
        startup_program(
            settings,
            app_handle=app_handle,
            routers=routers,
            static_mounts=static_mounts,
            frontend_build_path=frontend_build_path,
        ),
        runtime_interpreter,
    )
    match startup_result:
        case Ok(StartupAssembly() as startup_assembly):
            pool_handle = startup_assembly.database_pool
            redis_factory_handle = startup_assembly.redis_factory
            observability_handle = startup_assembly.observability
            pool = pool_handle.resource
            redis_factory = redis_factory_handle.resource
            observability_adapter = observability_handle.resource
        case Ok(HandleTypeMismatch() as mismatch):
            raise StartupFailure(mismatch)
        case Err(error):
            raise StartupFailure(error)

    # Create protocol adapters
    database_pool_adapter = AsyncPgPoolAdapter(pool)

    # Create factories
    interpreter_factory = ProductionInterpreterFactory(
        database_pool=database_pool_adapter,
        redis_factory=redis_factory,
        observability_interpreter=observability_adapter,
    )

    # Create container with protocol implementations
    container = ApplicationContainer(
        database_pool=database_pool_adapter,
        observability_interpreter=observability_adapter,
        redis_factory=redis_factory,
        interpreter_factory=interpreter_factory,
    )

    # Store in app.state (replaces global singletons)
    app.state.container = container
    app.state.settings = settings  # Store for auth endpoints
    app.state.startup_assembly = startup_assembly
    app.state.runtime_interpreter = runtime_interpreter
    app.state.frontend_build_path = frontend_build_path

    yield

    # Shutdown
    if getattr(app.state, "startup_assembly", None) is not None:
        shutdown_result = await run_ws_program(
            shutdown_program(app.state.startup_assembly), app.state.runtime_interpreter
        )
        match shutdown_result:
            case Ok():
                pass
            case Err(error):
                raise ShutdownFailure(error)


class StartupFailure(RuntimeError):
    """Startup failed with a typed interpreter error."""

    def __init__(self, error: object) -> None:
        self.error = error
        super().__init__(f"Failed to start application: {error}")


class ShutdownFailure(RuntimeError):
    """Shutdown failed with a typed interpreter error."""

    def __init__(self, error: object) -> None:
        self.error = error
        super().__init__(f"Failed to shut down application: {error}")


app = FastAPI(
    title="HealthHub",
    description="Healthcare portal demo with Effectful effect system",
    version="1.0.0",
    lifespan=lifespan,
)
