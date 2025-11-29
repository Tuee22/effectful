"""FastAPI application with Prometheus metrics endpoint.

This example demonstrates:
1. Setting up PrometheusMetricsCollector with FRAMEWORK_METRICS
2. Exposing /metrics endpoint for Prometheus scraping
3. Using InstrumentedInterpreter for automatic framework metrics
4. Recording custom application metrics via effects

Run this example:
    uvicorn examples.06_metrics_endpoint:app --host 0.0.0.0 --port 8000

Then access:
    - http://localhost:8000/docs - API documentation
    - http://localhost:8000/metrics - Prometheus metrics endpoint
    - http://localhost:3000 - Grafana dashboards (if Docker stack running)

Configure Prometheus to scrape this endpoint by updating:
    docker/prometheus/prometheus.yml:
        - job_name: 'effectful-app'
          static_configs:
            - targets: ['host.docker.internal:8000']  # macOS/Windows
            # - targets: ['172.17.0.1:8000']  # Linux

SSoT References:
    - documents/core/observability_doctrine.md - Dual-layer metrics
    - documents/core/monitoring_standards.md - Metric naming
    - documents/tutorials/11_metrics_quickstart.md - Setup guide
"""

from collections.abc import AsyncGenerator, Generator
from contextlib import asynccontextmanager
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException
from prometheus_client import make_asgi_app
from pydantic import BaseModel

from effectful.adapters.prometheus_metrics import PrometheusMetricsCollector
from effectful.effects.metrics import IncrementCounter, ObserveHistogram
from effectful.interpreters.composite import CompositeInterpreter
from effectful.interpreters.metrics import MetricsInterpreter
from effectful.observability.framework_metrics import FRAMEWORK_METRICS
from effectful.observability.instrumentation import create_instrumented_interpreter
from effectful.programs.program_types import AllEffects, EffectResult
from effectful.programs.runners import run_program
from effectful.testing import unwrap_ok


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


# === FastAPI Application ===


# Global metrics collector and interpreter
metrics_collector: PrometheusMetricsCollector | None = None
interpreter: CompositeInterpreter | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """FastAPI lifespan handler for metrics setup.

    This registers:
    1. FRAMEWORK_METRICS (effectful_effects_total, effectful_effect_duration_seconds)
    2. Custom application metrics (tasks_created_total, task_priority_distribution)
    """
    global metrics_collector, interpreter

    # Create Prometheus metrics collector
    metrics_collector = PrometheusMetricsCollector()

    # Register framework metrics (for automatic instrumentation)
    framework_result = metrics_collector.register_metrics(FRAMEWORK_METRICS)
    match framework_result:
        case {"registered_count": count}:
            print(f"✅ Registered {count} framework metrics")
        case {"reason": reason}:
            print(f"❌ Failed to register framework metrics: {reason}")
            raise RuntimeError(f"Metrics registration failed: {reason}")

    # Register custom application metrics
    from effectful.observability import (
        CounterDefinition,
        HistogramDefinition,
        MetricsRegistry,
    )

    app_metrics = MetricsRegistry(
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

    app_result = metrics_collector.register_metrics(app_metrics)
    match app_result:
        case {"registered_count": count}:
            print(f"✅ Registered {count} application metrics")
        case {"reason": reason}:
            print(f"❌ Failed to register application metrics: {reason}")
            raise RuntimeError(f"Application metrics registration failed: {reason}")

    # Create metrics interpreter
    metrics_interp = MetricsInterpreter(metrics_collector=metrics_collector)

    # Wrap in instrumented interpreter for automatic framework metrics
    instrumented_metrics_interp = create_instrumented_interpreter(
        wrapped=metrics_interp, metrics_collector=metrics_collector
    )

    # Create composite interpreter with instrumented metrics interpreter
    interpreter = CompositeInterpreter(interpreters=[instrumented_metrics_interp])

    print("✅ FastAPI application started with metrics enabled")
    print("📊 Metrics endpoint: http://localhost:8000/metrics")
    print("📈 Grafana dashboards: http://localhost:3000 (if Docker stack running)")

    yield

    print("🛑 FastAPI application shutting down")


# Create FastAPI app with lifespan handler
app = FastAPI(
    title="Effectful Metrics Example",
    description="FastAPI application demonstrating Prometheus metrics integration",
    version="1.0.0",
    lifespan=lifespan,
)

# Mount Prometheus /metrics endpoint
# This exposes all registered metrics in Prometheus text format
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


# === API Endpoints ===


@app.get("/")
async def root() -> dict[str, str]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "effectful-metrics-example",
        "metrics_endpoint": "/metrics",
        "docs": "/docs",
    }


@app.post("/tasks", response_model=TaskResponse, status_code=201)
async def create_task(request: TaskRequest) -> TaskResponse:
    """Create a new task and record metrics.

    This endpoint:
    1. Validates the priority level
    2. Runs the effect program to process the task
    3. Records custom metrics (tasks_created_total, task_priority_distribution)
    4. Records framework metrics automatically (effect execution count & duration)

    The metrics are fire-and-forget - they don't block the response.
    """
    if interpreter is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    # Validate priority
    valid_priorities = {"low", "medium", "high"}
    if request.priority not in valid_priorities:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid priority. Must be one of: {valid_priorities}",
        )

    # Generate task ID
    task_id = uuid4()

    # Run effect program
    program = process_task_program(
        task_id=task_id, name=request.name, priority=request.priority
    )
    result = await run_program(program, interpreter)

    # Extract result (unwrap_ok will raise if Err)
    response = unwrap_ok(result)
    assert isinstance(response, TaskResponse)

    return response


@app.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: UUID) -> TaskResponse:
    """Get task by ID (stub endpoint for demo).

    In a real application, this would query a database.
    For this example, it just demonstrates another endpoint that could record metrics.
    """
    # Stub response
    return TaskResponse(
        task_id=task_id, name="Example Task", priority="medium", status="created"
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
