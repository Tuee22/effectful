"""Health check endpoint."""

from collections.abc import Generator

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.effects.healthcare import CheckDatabaseHealth
from app.infrastructure import create_redis_client, get_database_manager
from app.interpreters.composite_interpreter import AllEffects, CompositeInterpreter
from app.programs.runner import run_program

router = APIRouter()


@router.get("/health")
async def health_check() -> JSONResponse:
    """Health check endpoint.

    Verifies database connectivity and returns service status.
    """
    db_manager = get_database_manager()
    pool = db_manager.get_pool()
    redis_client = create_redis_client()
    interpreter = CompositeInterpreter(pool, redis_client)

    def health_program() -> Generator[AllEffects, object, bool]:
        result = yield CheckDatabaseHealth()
        assert isinstance(result, bool)
        return result

    try:
        is_healthy = await run_program(health_program(), interpreter)
    except Exception as e:
        await redis_client.aclose()
        return JSONResponse(
            {
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e),
            },
            status_code=503,
        )

    await redis_client.aclose()

    if is_healthy:
        return JSONResponse(
            {
                "status": "healthy",
                "database": "connected",
            }
        )

    return JSONResponse(
        {
            "status": "unhealthy",
            "database": "disconnected",
        },
        status_code=503,
    )
