"""Pure startup/shutdown programs for HealthHub assembly."""

from __future__ import annotations

from collections.abc import Generator

from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar, cast

from asyncpg import Pool, Record
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry

from app.adapters.prometheus_observability import PrometheusObservabilityAdapter
from app.adapters.redis_factory import ProductionRedisClientFactory
from effectful.effects.runtime import (
    CloseDatabasePool,
    CloseObservabilityInterpreter,
    CloseRedisClientFactory,
    ConfigureCors,
    CreateObservabilityInterpreter,
    CreateDatabasePool,
    CreateRedisClientFactory,
    IncludeRouter,
    MountStatic,
    RegisterHttpRoute,
    RouteCallable,
    ResourceHandle,
    RuntimeEffect,
    SetAppMetadata,
)
from effectful.programs.program_types import AllEffects, EffectResult

from app.config import Settings
from app.observability.registry import HEALTHHUB_METRICS

T_resource = TypeVar("T_resource")


@dataclass(frozen=True)
class HandleTypeMismatch:
    """Typed startup failure when interpreter returns an unexpected handle."""

    effect: str
    expected_type: str
    actual_type: str


def _typed_handle_or_error(
    handle: ResourceHandle[object], expected_type: type[T_resource], *, effect: str
) -> ResourceHandle[T_resource] | HandleTypeMismatch:
    """Rewrap a ResourceHandle with a precise type after runtime validation."""
    if not isinstance(handle.resource, expected_type):
        return HandleTypeMismatch(
            effect=effect,
            expected_type=expected_type.__name__,
            actual_type=type(handle.resource).__name__,
        )
    return ResourceHandle(kind=handle.kind, resource=handle.resource)


@dataclass(frozen=True)
class RouterSpec:
    """Pure description of a router to include."""

    router: object
    prefix: str
    tags: tuple[str, ...]


@dataclass(frozen=True)
class StaticMountSpec:
    """Pure description of a static mount."""

    path: str
    directory: str
    name: str


@dataclass(frozen=True)
class StartupAssembly:
    """Opaque handles produced during startup."""

    app_handle: ResourceHandle[FastAPI]
    database_pool: ResourceHandle[Pool[Record]]
    redis_factory: ResourceHandle[ProductionRedisClientFactory]
    observability: ResourceHandle[PrometheusObservabilityAdapter]


type StartupProgramResult = StartupAssembly | HandleTypeMismatch


def startup_program(
    settings: Settings,
    app_handle: ResourceHandle[FastAPI],
    routers: tuple[RouterSpec, ...],
    static_mounts: tuple[StaticMountSpec, ...],
    frontend_build_path: Path,
    *,
    collector_registry: CollectorRegistry | None = None,
) -> Generator[AllEffects, EffectResult, StartupProgramResult]:
    """Configure the app and create the database pool via runtime effects."""

    yield SetAppMetadata(
        app=app_handle,
        title=settings.app_name,
        description="Healthcare portal demo with Effectful effect system",
        version="1.0.0",
    )

    yield ConfigureCors(
        app=app_handle,
        allow_origins=tuple(settings.cors_origins),
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=tuple(settings.cors_allow_methods),
        allow_headers=tuple(settings.cors_allow_headers),
    )

    for spec in routers:
        yield IncludeRouter(
            app=app_handle,
            router=spec.router,
            prefix=spec.prefix,
            tags=spec.tags,
        )

    for mount in static_mounts:
        yield MountStatic(
            app=app_handle,
            path=mount.path,
            directory=mount.directory,
            name=mount.name,
        )

    observability_result = yield CreateObservabilityInterpreter(
        metrics_registry=HEALTHHUB_METRICS,
        collector_registry=collector_registry,
    )
    if not isinstance(observability_result, ResourceHandle):
        return HandleTypeMismatch(
            effect="CreateObservabilityInterpreter",
            expected_type="ResourceHandle",
            actual_type=type(observability_result).__name__,
        )
    observability_handle = _typed_handle_or_error(
        observability_result,
        PrometheusObservabilityAdapter,
        effect="CreateObservabilityInterpreter",
    )
    if isinstance(observability_handle, HandleTypeMismatch):
        return observability_handle

    async def _metrics_endpoint(*_: object, **__: object) -> Response:
        metrics_bytes = observability_handle.resource.render_latest()
        return Response(content=metrics_bytes, media_type=CONTENT_TYPE_LATEST)

    yield RegisterHttpRoute(
        app=app_handle,
        path="/metrics",
        endpoint=_metrics_endpoint,
        methods=("GET",),
        include_in_schema=False,
        response_model=None,
    )

    redis_factory_result = yield CreateRedisClientFactory(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
    )
    if not isinstance(redis_factory_result, ResourceHandle):
        return HandleTypeMismatch(
            effect="CreateRedisClientFactory",
            expected_type="ResourceHandle",
            actual_type=type(redis_factory_result).__name__,
        )
    redis_factory_handle = _typed_handle_or_error(
        redis_factory_result,
        ProductionRedisClientFactory,
        effect="CreateRedisClientFactory",
    )
    if isinstance(redis_factory_handle, HandleTypeMismatch):
        return redis_factory_handle

    pool_result = yield CreateDatabasePool(
        host=settings.postgres_host,
        port=settings.postgres_port,
        database=settings.postgres_db,
        user=settings.postgres_user,
        password=settings.postgres_password,
        min_size=5,
        max_size=20,
        command_timeout=60.0,
    )
    if not isinstance(pool_result, ResourceHandle):
        return HandleTypeMismatch(
            effect="CreateDatabasePool",
            expected_type="ResourceHandle",
            actual_type=type(pool_result).__name__,
        )
    pool_handle = _typed_handle_or_error(pool_result, Pool, effect="CreateDatabasePool")
    if isinstance(pool_handle, HandleTypeMismatch):
        return pool_handle

    favicon_path = frontend_build_path / "favicon.ico"

    async def _favicon(*_: object, **__: object) -> FileResponse | JSONResponse:
        if favicon_path.exists():
            return FileResponse(str(favicon_path))
        return JSONResponse({"error": "favicon not available"}, status_code=404)

    yield RegisterHttpRoute(
        app=app_handle,
        path="/favicon.ico",
        endpoint=_favicon,
        methods=("GET",),
        include_in_schema=False,
        response_model=None,
    )

    async def _serve_react_app(request: Request, full_path: str) -> FileResponse | JSONResponse:
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

    yield RegisterHttpRoute(
        app=app_handle,
        path="/{full_path:path}",
        endpoint=cast(RouteCallable, _serve_react_app),
        methods=("GET",),
        include_in_schema=False,
        response_model=None,
    )

    return StartupAssembly(
        app_handle=app_handle,
        database_pool=pool_handle,
        redis_factory=redis_factory_handle,
        observability=observability_handle,
    )


def shutdown_program(
    startup: StartupAssembly,
) -> Generator[RuntimeEffect, object, None]:
    """Close runtime resources via runtime effects."""

    yield CloseRedisClientFactory(handle=startup.redis_factory)
    yield CloseObservabilityInterpreter(handle=startup.observability)
    yield CloseDatabasePool(handle=startup.database_pool)
