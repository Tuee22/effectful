"""HealthHub FastAPI Application Entry Point.

Main application with lifespan management, CORS, and API routing.
"""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.infrastructure import get_database_manager
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

    Handles startup and shutdown tasks using AsyncExitStack pattern.
    """
    # Startup
    db_manager = get_database_manager()
    await db_manager.setup()

    yield

    # Shutdown
    await db_manager.teardown()


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="Healthcare portal demo with Effectful effect system",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)

# Include routers
app.include_router(health_router, tags=["health"])
app.include_router(auth_router, prefix=f"{settings.api_prefix}/auth", tags=["auth"])
app.include_router(patients_router, prefix=f"{settings.api_prefix}/patients", tags=["patients"])
app.include_router(
    appointments_router, prefix=f"{settings.api_prefix}/appointments", tags=["appointments"]
)
app.include_router(
    prescriptions_router, prefix=f"{settings.api_prefix}/prescriptions", tags=["prescriptions"]
)
app.include_router(
    lab_results_router, prefix=f"{settings.api_prefix}/lab-results", tags=["lab-results"]
)
app.include_router(invoices_router, prefix=f"{settings.api_prefix}/invoices", tags=["invoices"])


# Serve frontend static files
frontend_build_path = Path("/opt/healthhub/frontend-build/build")
if frontend_build_path.exists():
    app.mount(
        "/assets",
        StaticFiles(directory=str(frontend_build_path / "assets")),
        name="assets",
    )

    @app.get("/{full_path:path}", response_model=None)
    async def serve_react_app(request: Request, full_path: str) -> FileResponse | JSONResponse:
        """Serve React app for all non-API routes."""
        # API routes are already registered - shouldn't reach here
        if full_path.startswith("api/") or full_path.startswith("health"):
            return JSONResponse({"error": "Not found"}, status_code=404)

        # For React Router, serve index.html for all other routes
        index_file = frontend_build_path / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))

        return JSONResponse({"error": "Frontend not built"}, status_code=503)

else:
    # Fallback if frontend not built (development scenario)
    @app.get("/")
    async def root() -> JSONResponse:
        """Root endpoint with application info."""
        return JSONResponse(
            {
                "name": settings.app_name,
                "version": "1.0.0",
                "status": "operational",
                "environment": settings.app_env,
                "warning": "Frontend not built - access API at /api",
            }
        )
