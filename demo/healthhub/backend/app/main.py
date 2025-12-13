"""HealthHub FastAPI Application Entry Point.

Main application with lifespan management, CORS, and API routing.
"""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from prometheus_client import CONTENT_TYPE_LATEST, REGISTRY, generate_latest

from app.config import Settings
from app.container import ApplicationContainer
from app.adapters.asyncpg_pool import AsyncPgPoolAdapter
from app.adapters.prometheus_observability import PrometheusObservabilityAdapter
from app.adapters.redis_factory import ProductionRedisClientFactory
from app.adapters.interpreter_factory import ProductionInterpreterFactory
from app.interpreters.observability_interpreter import (
    ObservabilityInterpreter as ConcreteObservabilityInterpreter,
)
from app.infrastructure.database import DatabaseManager
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

    # Startup: Create database pool
    db_manager = DatabaseManager(settings)
    await db_manager.setup()
    pool = db_manager.get_pool()

    # Create protocol adapters
    database_pool_adapter = AsyncPgPoolAdapter(pool)
    observability_adapter = PrometheusObservabilityAdapter(ConcreteObservabilityInterpreter())

    # Create factories
    redis_factory = ProductionRedisClientFactory(settings)
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

    # Configure app metadata and middleware once per startup (no module-level Settings)
    app.title = settings.app_name
    app.description = "Healthcare portal demo with Effectful effect system"
    app.version = "1.0.0"

    # CORS middleware (idempotent add guarded by state flag)
    if not getattr(app.state, "cors_configured", False):
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=settings.cors_allow_credentials,
            allow_methods=settings.cors_allow_methods,
            allow_headers=settings.cors_allow_headers,
        )
        app.state.cors_configured = True

    # Register routers using settings-derived prefixes (guard to avoid duplicate registration)
    if not getattr(app.state, "routers_registered", False):
        app.include_router(health_router, tags=["health"])
        app.include_router(auth_router, prefix=f"{settings.api_prefix}/auth", tags=["auth"])
        app.include_router(
            patients_router, prefix=f"{settings.api_prefix}/patients", tags=["patients"]
        )
        app.include_router(
            appointments_router,
            prefix=f"{settings.api_prefix}/appointments",
            tags=["appointments"],
        )
        app.include_router(
            prescriptions_router,
            prefix=f"{settings.api_prefix}/prescriptions",
            tags=["prescriptions"],
        )
        app.include_router(
            lab_results_router,
            prefix=f"{settings.api_prefix}/lab-results",
            tags=["lab-results"],
        )
        app.include_router(
            invoices_router, prefix=f"{settings.api_prefix}/invoices", tags=["invoices"]
        )
        app.state.routers_registered = True

    yield

    # Shutdown
    await database_pool_adapter.close()


# Create FastAPI application (no settings instantiated at module import)
app = FastAPI(
    title="HealthHub",
    description="Healthcare portal demo with Effectful effect system",
    version="1.0.0",
    lifespan=lifespan,
)


# Serve frontend static files (FastAPI StaticFiles + catch-all)
frontend_build_path = Path("/opt/healthhub/frontend-build/build")
static_path = frontend_build_path / "static"
assets_path = frontend_build_path / "assets"
if static_path.exists():
    app.mount(
        "/static",
        StaticFiles(directory=str(static_path)),
        name="static",
    )

if assets_path.exists():
    app.mount(
        "/assets",
        StaticFiles(directory=str(assets_path)),
        name="assets",
    )

favicon_path = frontend_build_path / "favicon.ico"


@app.get("/favicon.ico", include_in_schema=False, response_model=None)
async def favicon() -> FileResponse | JSONResponse:
    if favicon_path.exists():
        return FileResponse(str(favicon_path))
    return JSONResponse({"error": "favicon not available"}, status_code=404)


@app.get("/metrics", include_in_schema=False, response_model=None)
async def metrics() -> Response:
    """Expose Prometheus metrics for scraping."""
    data = generate_latest(REGISTRY)
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)


@app.get("/{full_path:path}", response_model=None)
async def serve_react_app(request: Request, full_path: str) -> FileResponse | JSONResponse:
    """Serve React app for all non-API routes."""
    if full_path.startswith("api/") or full_path.startswith("health"):
        return JSONResponse({"error": "Not found"}, status_code=404)

    index_file = frontend_build_path / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))

    return JSONResponse(
        {
            "error": "Frontend not built",
            "hint": "Build frontend into /opt/healthhub/frontend-build/build",
        },
        status_code=503,
    )
