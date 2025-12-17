"""FastAPI metrics example using pure runtime effects (no legacy globals).

This example demonstrates:
1. Pure startup/shutdown programs using runtime effects
2. Prometheus metrics exposed via `/metrics` route
3. Instrumented interpreter emitting framework + application metrics
4. No module-level mutable state; handles stored on `app.state`

Run this example:
    uvicorn examples.07_metrics_endpoint:app --host 0.0.0.0 --port 8000

Then access:
    - http://localhost:8000/docs - API documentation
    - http://localhost:8000/metrics - Prometheus metrics endpoint
    - http://localhost:3000 - Grafana dashboards (if Docker stack running)

SSoT References:
    - documents/engineering/architecture.md#pure-interpreter-assembly-doctrine
    - documents/engineering/monitoring_and_alerting.md
    - documents/tutorials/metrics_quickstart.md
"""

from collections.abc import AsyncIterator, Generator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException
from fastapi.routing import APIRoute
from fastapi.responses import Response
from pydantic import BaseModel
from prometheus_client import CollectorRegistry, CONTENT_TYPE_LATEST, generate_latest

from effectful.adapters.prometheus_metrics import PrometheusMetricsCollector
from effectful.algebraic.result import Err, Ok
from effectful.effects.metrics import IncrementCounter, ObserveHistogram
from effectful.effects.runtime import (
    CloseObservabilityInterpreter,
    CreateObservabilityInterpreter,
    RegisterHttpRoute,
    ResourceHandle,
    RuntimeEffect,
    SetAppMetadata,
)
from effectful.interpreters.metrics import MetricsInterpreter
from effectful.interpreters.runtime import RuntimeInterpreter
from effectful.observability import CounterDefinition, HistogramDefinition, MetricsRegistry
from effectful.observability.instrumentation import create_instrumented_interpreter
from effectful.programs.program_types import AllEffects, EffectResult
from effectful.programs.runners import run_ws_program


# === Request/Response Models ===


class TaskRequest(BaseModel):
    """Request to create a task."""

    name: str
    priority: str  # "low" | "medium" | "high"


class TaskResponse(BaseModel):
    """Task creation response."""

    task_id: UUID
    name: str
    priority: str
    status: str


# === Effect Programs ===


def process_task_program(
    task_id: UUID, name: str, priority: str
) -> Generator[AllEffects, EffectResult, TaskResponse]:
    """Effect program that processes a task and records metrics.

    This program demonstrates:
    - Recording custom counter metrics (tasks_created_total)
    - Recording custom histogram metrics (task_priority_distribution)
    - Pattern matching on metric results
    - Continuing execution even if metrics fail (fire-and-forget)

    Framework metrics (effectful_effects_total, effectful_effect_duration_seconds)
    are recorded automatically by InstrumentedInterpreter.
    """
    # Record custom counter metric: tasks created by priority
    counter_result = yield IncrementCounter(
        metric_name="tasks_created_total",
        labels={"priority": priority},
        value=1.0,
    )

    # Record custom histogram metric: priority distribution
    # Map priority to numeric value for histogram
    priority_value = {"low": 1.0, "medium": 2.0, "high": 3.0}.get(priority, 2.0)
    histogram_result = yield ObserveHistogram(
        metric_name="task_priority_distribution",
        labels={"priority": priority},
        value=priority_value,
    )

    # Metrics are fire-and-forget - don't fail the business logic if they fail
    # But we can log failures for debugging
    match counter_result:
        case {"timestamp": _}:
            pass  # Metric recorded successfully
        case {"reason": reason}:
            print(f"⚠️  Counter metric failed: {reason}")

    match histogram_result:
        case {"timestamp": _}:
            pass  # Metric recorded successfully
        case {"reason": reason}:
            print(f"⚠️  Histogram metric failed: {reason}")

    # Return business logic result
    return TaskResponse(
        task_id=task_id, name=name, priority=priority, status="created"
    )


# === Metrics registry for the example ===


APP_METRICS = MetricsRegistry(
    counters=(
        CounterDefinition(
            name="tasks_created_total",
            help_text="Total tasks created by priority",
            label_names=("priority",),
        ),
    ),
    gauges=(),
    histograms=(
        HistogramDefinition(
            name="task_priority_distribution",
            help_text="Distribution of task priorities",
            label_names=("priority",),
            buckets=(0.5, 1.5, 2.5, 3.5),
        ),
    ),
    summaries=(),
)


# === Startup/shutdown programs ===


@dataclass(frozen=True)
class MetricsRuntime:
    """Opaque metrics runtime containing collector + interpreter."""

    collector: PrometheusMetricsCollector
    interpreter: object
    registry: CollectorRegistry

    def render_latest(self) -> bytes:
        return generate_latest(self.registry)

    async def close(self) -> None:
        return None


@dataclass(frozen=True)
class StartupAssembly:
    """Handles produced during startup."""

    app_handle: ResourceHandle[FastAPI]
    metrics_runtime: ResourceHandle[MetricsRuntime]


def startup_program(
    app_handle: ResourceHandle[FastAPI],
) -> Generator[RuntimeEffect, ResourceHandle[object], StartupAssembly]:
    """Pure program describing FastAPI + metrics wiring."""

    yield SetAppMetadata(
        app=app_handle,
        title="Effectful Metrics Example",
        description="FastAPI application demonstrating Prometheus metrics integration",
        version="1.0.0",
    )

    metrics_runtime = yield CreateObservabilityInterpreter(metrics_registry=APP_METRICS)

    async def _metrics() -> Response:
        return Response(
            content=metrics_runtime.resource.render_latest(),
            media_type=CONTENT_TYPE_LATEST,
        )

    async def _root() -> dict[str, str]:
        return {
            "status": "healthy",
            "service": "effectful-metrics-example",
            "metrics_endpoint": "/metrics",
            "docs": "/docs",
        }

    async def _create_task(request: TaskRequest) -> TaskResponse:
        runtime = metrics_runtime.resource

        valid_priorities = {"low", "medium", "high"}
        if request.priority not in valid_priorities:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid priority. Must be one of: {valid_priorities}",
            )

        program = process_task_program(
            task_id=uuid4(), name=request.name, priority=request.priority
        )
        result = await run_ws_program(program, runtime.interpreter)
        match result:
            case Ok(task_response):
                assert isinstance(task_response, TaskResponse)
                return task_response
            case Err(error):
                raise HTTPException(status_code=500, detail=str(error))

    yield RegisterHttpRoute(
        app=app_handle,
        path="/",
        endpoint=_root,
        methods=("GET",),
        include_in_schema=False,
    )

    yield RegisterHttpRoute(
        app=app_handle,
        path="/tasks",
        endpoint=_create_task,
        methods=("POST",),
        include_in_schema=True,
        response_model=TaskResponse,
    )

    yield RegisterHttpRoute(
        app=app_handle,
        path="/metrics",
        endpoint=_metrics,
        methods=("GET",),
        include_in_schema=False,
        response_model=None,
    )

    return StartupAssembly(
        app_handle=app_handle,
        metrics_runtime=metrics_runtime,
    )


def shutdown_program(startup: StartupAssembly) -> Generator[RuntimeEffect, object, None]:
    """Close runtime resources via runtime effects."""

    yield CloseObservabilityInterpreter(handle=startup.metrics_runtime)


# === Runtime interpreter ===


async def _set_app_metadata(effect: SetAppMetadata) -> None:
    app: FastAPI = effect.app.resource
    app.title = effect.title
    app.description = effect.description
    app.version = effect.version


async def _register_route(effect: RegisterHttpRoute) -> None:
    app: FastAPI = effect.app.resource
    route = APIRoute(
        path=effect.path,
        endpoint=effect.endpoint,
        methods=list(effect.methods),
        include_in_schema=effect.include_in_schema,
        response_model=effect.response_model,
    )
    app.router.routes.append(route)


async def _create_observability_interpreter(
    effect: CreateObservabilityInterpreter,
) -> ResourceHandle[MetricsRuntime]:
    registry = CollectorRegistry()
    collector = PrometheusMetricsCollector(registry=registry)

    if effect.metrics_registry is not None:
        await collector.register_metrics(effect.metrics_registry)

    metrics_interp = MetricsInterpreter(metrics_collector=collector)
    instrumented_interpreter = await create_instrumented_interpreter(
        wrapped=metrics_interp, metrics_collector=collector
    )

    runtime = MetricsRuntime(
        collector=collector,
        interpreter=instrumented_interpreter,
        registry=registry,
    )

    return ResourceHandle(kind="metrics_runtime", resource=runtime)


async def _close_observability_interpreter(
    effect: CloseObservabilityInterpreter[MetricsRuntime],
) -> None:
    await effect.handle.resource.close()


def build_runtime_interpreter() -> RuntimeInterpreter:
    return RuntimeInterpreter(
        set_app_metadata=_set_app_metadata,
        register_route=_register_route,
        create_observability_interpreter=_create_observability_interpreter,
        close_observability_interpreter=_close_observability_interpreter,
    )


# === FastAPI Application ===


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan manager built on pure runtime effects."""

    app_handle = ResourceHandle(kind="fastapi_app", resource=app)
    runtime_interpreter = build_runtime_interpreter()

    startup_result = await run_ws_program(
        startup_program(app_handle),
        runtime_interpreter,
    )
    match startup_result:
        case Ok(assembly):
            app.state.startup_assembly = assembly
            app.state.runtime_interpreter = runtime_interpreter
            app.state.metrics_runtime = assembly.metrics_runtime.resource
        case Err(error):
            raise StartupFailure(error)

    try:
        yield
    finally:
        if getattr(app.state, "startup_assembly", None) is not None:
            shutdown_result = await run_ws_program(
                shutdown_program(app.state.startup_assembly),
                app.state.runtime_interpreter,
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
    title="Effectful Metrics Example",
    description="FastAPI application demonstrating Prometheus metrics integration",
    version="1.0.0",
    lifespan=lifespan,
)


if __name__ == "__main__":
    import uvicorn

    print("🚀 Starting FastAPI server with metrics...")
    print("📍 API: http://localhost:8000")
    print("📊 Metrics: http://localhost:8000/metrics")
    print("📚 Docs: http://localhost:8000/docs")
    print("")
    print("To configure Prometheus scraping, update docker/prometheus/prometheus.yml:")
    print("  - job_name: 'effectful-app'")
    print("    static_configs:")
    print("      - targets: ['host.docker.internal:8000']  # macOS/Windows")
    print("      # - targets: ['172.17.0.1:8000']  # Linux")
    print("")

    uvicorn.run(app, host="0.0.0.0", port=8000)
