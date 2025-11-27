"""Health check endpoint."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.infrastructure import get_database_manager

router = APIRouter()


@router.get("/health")
async def health_check() -> JSONResponse:
    """Health check endpoint.

    Verifies database connectivity and returns service status.
    """
    try:
        db_manager = get_database_manager()
        pool = db_manager.get_pool()

        # Test database connectivity with simple query
        await pool.fetchval("SELECT 1")

        return JSONResponse(
            {
                "status": "healthy",
                "database": "connected",
            }
        )
    except Exception as e:
        return JSONResponse(
            {
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e),
            },
            status_code=503,
        )
