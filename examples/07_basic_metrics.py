"""Basic metrics usage example.

This example demonstrates:
1. Creating a MetricsRegistry with counter and gauge metrics
2. Using InMemoryMetricsCollector for testing/development
3. Recording metrics via effect programs
4. Querying recorded metrics

Run this example:
    docker compose -f docker/docker-compose.yml exec effectful poetry run python examples/07_basic_metrics.py

SSoT References:
    - documents/core/observability_doctrine.md - Metrics philosophy
    - documents/core/monitoring_standards.md - Naming conventions
    - documents/tutorials/11_metrics_quickstart.md - Getting started
"""

import asyncio
from collections.abc import Generator
from uuid import uuid4

from effectful.adapters.in_memory_metrics import InMemoryMetricsCollector
from effectful.domain.metrics_result import MetricRecorded, MetricRecordingFailed
from effectful.effects.metrics import IncrementCounter, RecordGauge
from effectful.interpreters.composite import CompositeInterpreter
from effectful.interpreters.metrics import MetricsInterpreter
from effectful.observability import (
    CounterDefinition,
    GaugeDefinition,
    MetricsRegistry,
)
from effectful.programs.program_types import AllEffects, EffectResult
from effectful.programs.runners import run_program
from effectful.testing import unwrap_ok


# === Define Metrics Registry ===


APP_METRICS = MetricsRegistry(
    counters=(
        CounterDefinition(
            name="http_requests_total",
            help_text="Total HTTP requests by method and status",
            label_names=("method", "status"),
        ),
        CounterDefinition(
            name="user_signups_total",
            help_text="Total user signups by source",
            label_names=("source",),
        ),
    ),
    gauges=(
        GaugeDefinition(
            name="active_connections",
            help_text="Current number of active connections",
            label_names=(),  # No labels - single value
        ),
        GaugeDefinition(
            name="queue_depth",
            help_text="Current depth of processing queue by priority",
            label_names=("priority",),
        ),
    ),
    histograms=(),  # No histograms in this example
    summaries=(),  # No summaries in this example
)


# === Effect Programs ===


def track_http_request(
    method: str, status: int
) -> Generator[AllEffects, EffectResult, bool]:
    """Effect program to track an HTTP request."""
    # Increment counter for HTTP requests
    result = yield IncrementCounter(
        metric_name="http_requests_total",
        labels={"method": method, "status": str(status)},
        value=1.0,
    )

    # Pattern match on result
    match result:
        case MetricRecorded(timestamp=ts):
            print(f"✅ Recorded HTTP request metric at {ts}")
            return True
        case MetricRecordingFailed(reason=reason):
            print(f"❌ Failed to record metric: {reason}")
            return False


def track_user_signup(source: str) -> Generator[AllEffects, EffectResult, bool]:
    """Effect program to track a user signup."""
    # Increment counter for user signups
    result = yield IncrementCounter(
        metric_name="user_signups_total", labels={"source": source}, value=1.0
    )

    match result:
        case MetricRecorded(timestamp=ts):
            print(f"✅ Recorded user signup from {source} at {ts}")
            return True
        case MetricRecordingFailed(reason=reason):
            print(f"❌ Failed to record signup metric: {reason}")
            return False


def update_active_connections(
    count: int,
) -> Generator[AllEffects, EffectResult, bool]:
    """Effect program to update active connections gauge."""
    # Record gauge value for active connections
    result = yield RecordGauge(
        metric_name="active_connections", labels={}, value=float(count)
    )

    match result:
        case MetricRecorded(timestamp=ts):
            print(f"✅ Updated active connections to {count} at {ts}")
            return True
        case MetricRecordingFailed(reason=reason):
            print(f"❌ Failed to update gauge: {reason}")
            return False


def update_queue_depth(
    priority: str, depth: int
) -> Generator[AllEffects, EffectResult, bool]:
    """Effect program to update queue depth gauge."""
    result = yield RecordGauge(
        metric_name="queue_depth",
        labels={"priority": priority},
        value=float(depth),
    )

    match result:
        case MetricRecorded(timestamp=ts):
            print(f"✅ Updated {priority} queue depth to {depth} at {ts}")
            return True
        case MetricRecordingFailed(reason=reason):
            print(f"❌ Failed to update queue depth: {reason}")
            return False


# === Main Program ===


async def main() -> None:
    """Main program demonstrating basic metrics usage."""
    print("=" * 60)
    print("Basic Metrics Example")
    print("=" * 60)
    print()

    # Create in-memory metrics collector
    print("📊 Creating InMemoryMetricsCollector...")
    collector = InMemoryMetricsCollector()

    # Register metrics
    print("📝 Registering metrics...")
    registration_result = collector.register_metrics(APP_METRICS)
    match registration_result:
        case {"registered_count": count}:
            print(f"✅ Registered {count} metrics")
        case {"reason": reason}:
            print(f"❌ Failed to register metrics: {reason}")
            return

    print()

    # Create interpreter
    metrics_interp = MetricsInterpreter(metrics_collector=collector)
    interpreter = CompositeInterpreter(interpreters=[metrics_interp])

    # Simulate HTTP requests
    print("🌐 Simulating HTTP requests...")
    for method, status in [
        ("GET", 200),
        ("GET", 200),
        ("POST", 201),
        ("GET", 404),
        ("PUT", 200),
    ]:
        program = track_http_request(method, status)
        result = await run_program(program, interpreter)
        unwrap_ok(result)

    print()

    # Simulate user signups
    print("👤 Simulating user signups...")
    for source in ["web", "mobile", "web", "api", "mobile", "web"]:
        program = track_user_signup(source)
        result = await run_program(program, interpreter)
        unwrap_ok(result)

    print()

    # Update gauges
    print("📈 Updating gauges...")
    for connections in [10, 15, 12, 20]:
        program = update_active_connections(connections)
        result = await run_program(program, interpreter)
        unwrap_ok(result)

    for priority, depth in [("high", 5), ("medium", 15), ("low", 30)]:
        program = update_queue_depth(priority, depth)
        result = await run_program(program, interpreter)
        unwrap_ok(result)

    print()

    # Query and display metrics
    print("=" * 60)
    print("Recorded Metrics Summary")
    print("=" * 60)
    print()

    print("📊 Counter Metrics:")
    print("-" * 60)

    # HTTP requests by method/status
    http_metrics = [
        m
        for m in collector._metrics.values()
        if m["name"] == "http_requests_total" and m["type"] == "counter"
    ]
    for metric in sorted(http_metrics, key=lambda m: (m["labels"].get("method", ""), m["labels"].get("status", ""))):
        method = metric["labels"].get("method", "")
        status = metric["labels"].get("status", "")
        value = metric["value"]
        print(f"  http_requests_total{{method=\"{method}\", status=\"{status}\"}} = {value}")

    print()

    # User signups by source
    signup_metrics = [
        m
        for m in collector._metrics.values()
        if m["name"] == "user_signups_total" and m["type"] == "counter"
    ]
    for metric in sorted(signup_metrics, key=lambda m: m["labels"].get("source", "")):
        source = metric["labels"].get("source", "")
        value = metric["value"]
        print(f"  user_signups_total{{source=\"{source}\"}} = {value}")

    print()
    print("📊 Gauge Metrics:")
    print("-" * 60)

    # Active connections (no labels)
    connections_metric = next(
        (
            m
            for m in collector._metrics.values()
            if m["name"] == "active_connections" and m["type"] == "gauge"
        ),
        None,
    )
    if connections_metric:
        print(f"  active_connections = {connections_metric['value']}")

    # Queue depth by priority
    queue_metrics = [
        m
        for m in collector._metrics.values()
        if m["name"] == "queue_depth" and m["type"] == "gauge"
    ]
    for metric in sorted(queue_metrics, key=lambda m: m["labels"].get("priority", "")):
        priority = metric["labels"].get("priority", "")
        value = metric["value"]
        print(f"  queue_depth{{priority=\"{priority}\"}} = {value}")

    print()
    print("=" * 60)
    print("✅ Basic metrics example complete!")
    print()
    print("Key Takeaways:")
    print("  • Metrics are recorded via effect programs (pure functions)")
    print("  • Pattern matching handles success/failure explicitly")
    print("  • InMemoryMetricsCollector is great for testing")
    print("  • PrometheusMetricsCollector is used for production")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
