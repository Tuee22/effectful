"""Runtime interpreter wired to asyncpg + FastAPI for HealthHub assembly."""

from __future__ import annotations

from pathlib import Path

import asyncpg
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.routing import APIRoute
from prometheus_client import CollectorRegistry

from effectful.effects.runtime import (
    CloseDatabasePool,
    CloseObservabilityInterpreter,
    CloseRedisClientFactory,
    CreateDatabasePool,
    CreateObservabilityInterpreter,
    CreateRedisClientFactory,
    ConfigureCors,
    IncludeRouter,
    MountStatic,
    RegisterHttpRoute,
    ResourceHandle,
    SetAppMetadata,
)
from effectful.interpreters.runtime import RuntimeInterpreter

from app.adapters.prometheus_observability import PrometheusObservabilityAdapter
from app.adapters.redis_factory import ProductionRedisClientFactory
from app.interpreters.observability_interpreter import (
    ObservabilityInterpreter as ConcreteObservabilityInterpreter,
)
from app.observability.registry import HEALTHHUB_METRICS, MetricsRegistry


async def _create_asyncpg_pool(
    effect: CreateDatabasePool,
) -> ResourceHandle[asyncpg.Pool[asyncpg.Record]]:
    pool = await asyncpg.create_pool(
        host=effect.host,
        port=effect.port,
        database=effect.database,
        user=effect.user,
        password=effect.password,
        min_size=effect.min_size,
        max_size=effect.max_size,
        command_timeout=effect.command_timeout,
    )
    return ResourceHandle(kind="database_pool", resource=pool)


async def _close_asyncpg_pool(effect: CloseDatabasePool[asyncpg.Pool[asyncpg.Record]]) -> None:
    await effect.handle.resource.close()


async def _close_redis_factory(
    effect: CloseRedisClientFactory[object],
) -> None:
    factory = effect.handle.resource
    if not isinstance(factory, ProductionRedisClientFactory):
        raise TypeError(f"Expected ProductionRedisClientFactory, got {type(factory).__name__}")
    await factory.close()


async def _close_observability_interpreter(
    effect: CloseObservabilityInterpreter[object],
) -> None:
    interpreter = effect.handle.resource
    if not isinstance(interpreter, PrometheusObservabilityAdapter):
        raise TypeError(
            f"Expected PrometheusObservabilityAdapter, got {type(interpreter).__name__}"
        )
    await interpreter.close()


def _require_fastapi(handle: ResourceHandle[object]) -> FastAPI:
    resource = handle.resource
    if not isinstance(resource, FastAPI):
        raise TypeError(f"Expected FastAPI resource, got {type(resource).__name__}")
    return resource


async def _configure_cors(effect: ConfigureCors) -> None:
    app = _require_fastapi(effect.app)
    for middleware in app.user_middleware:
        middleware_cls = middleware.cls
        if isinstance(middleware_cls, type) and issubclass(middleware_cls, CORSMiddleware):
            app.state.cors_configured = True
            return
    if getattr(app.state, "cors_configured", False):
        return
    try:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(effect.allow_origins),
            allow_credentials=effect.allow_credentials,
            allow_methods=list(effect.allow_methods),
            allow_headers=list(effect.allow_headers),
        )
    except RuntimeError as exc:
        if "after an application has started" not in str(exc):
            raise
    app.state.cors_configured = True
    app.state.cors_configured = True


async def _include_router(effect: IncludeRouter) -> None:
    app = _require_fastapi(effect.app)
    if not isinstance(effect.router, APIRouter):
        raise TypeError(f"Expected APIRouter, got {type(effect.router).__name__}")
    app.include_router(effect.router, prefix=effect.prefix, tags=list(effect.tags))


async def _set_app_metadata(effect: SetAppMetadata) -> None:
    app = _require_fastapi(effect.app)
    app.title = effect.title
    app.description = effect.description
    app.version = effect.version


async def _mount_static(effect: MountStatic) -> None:
    app = _require_fastapi(effect.app)
    directory_path = Path(effect.directory)
    if not directory_path.exists():
        return
    app.mount(effect.path, StaticFiles(directory=effect.directory), name=effect.name)


async def _create_redis_factory(
    effect: CreateRedisClientFactory,
) -> ResourceHandle[ProductionRedisClientFactory]:
    factory = ProductionRedisClientFactory(
        host=effect.host,
        port=effect.port,
        db=effect.db,
    )
    return ResourceHandle(kind="redis_factory", resource=factory)


async def _create_observability_interpreter(
    effect: CreateObservabilityInterpreter,
) -> ResourceHandle[PrometheusObservabilityAdapter]:
    metrics_registry = effect.metrics_registry
    if metrics_registry is not None and not isinstance(metrics_registry, MetricsRegistry):
        raise TypeError(
            f"Expected MetricsRegistry for metrics_registry, got {type(metrics_registry).__name__}"
        )
    collector_registry = effect.collector_registry
    if collector_registry is not None and not isinstance(collector_registry, CollectorRegistry):
        raise TypeError(
            f"Expected CollectorRegistry for collector_registry, got {type(collector_registry).__name__}"
        )
    interpreter = PrometheusObservabilityAdapter(
        ConcreteObservabilityInterpreter(
            registry=metrics_registry or HEALTHHUB_METRICS,
            collector_registry=collector_registry,
        )
    )
    return ResourceHandle(kind="observability", resource=interpreter)


async def _register_route(effect: RegisterHttpRoute) -> None:
    app = _require_fastapi(effect.app)
    route = APIRoute(
        path=effect.path,
        endpoint=effect.endpoint,
        methods=list(effect.methods),
        include_in_schema=effect.include_in_schema,
        response_model=effect.response_model,
    )
    app.router.routes.append(route)


def build_runtime_interpreter() -> RuntimeInterpreter[asyncpg.Pool[asyncpg.Record]]:
    """Factory for a runtime interpreter backed by asyncpg and FastAPI."""
    return RuntimeInterpreter(
        create_db_pool=_create_asyncpg_pool,
        close_db_pool=_close_asyncpg_pool,
        close_redis_factory=_close_redis_factory,
        close_observability_interpreter=_close_observability_interpreter,
        configure_cors=_configure_cors,
        include_router=_include_router,
        set_app_metadata=_set_app_metadata,
        mount_static=_mount_static,
        create_redis_factory=_create_redis_factory,
        create_observability_interpreter=_create_observability_interpreter,
        register_route=_register_route,
    )
