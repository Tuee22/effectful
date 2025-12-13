"""Health check endpoint."""

from collections.abc import Generator
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.api.dependencies import get_composite_interpreter
from app.effects.healthcare import CheckDatabaseHealth
from app.interpreters.composite_interpreter import AllEffects, CompositeInterpreter
from app.programs.runner import run_program, unwrap_program_result

router = APIRouter()


@router.get("/health")
async def health_check(
    interpreter: Annotated[CompositeInterpreter, Depends(get_composite_interpreter)],
) -> JSONResponse:
    """Health check endpoint.

    Verifies database connectivity and returns service status.
    """

    def health_program() -> Generator[AllEffects, object, bool]:
        result = yield CheckDatabaseHealth()
        assert isinstance(result, bool)
        return result

    try:
        is_healthy = unwrap_program_result(await run_program(health_program(), interpreter))
    except Exception as e:
        return JSONResponse(
            {
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e),
            },
            status_code=503,
        )

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
