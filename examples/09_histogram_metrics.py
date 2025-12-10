"""Histogram and summary metrics example.

This example demonstrates:
1. Using histogram metrics to track distributions
2. Using summary metrics for percentiles
3. Observing latency and duration metrics
4. Analyzing metric distributions

Run this example:
    docker compose -f docker/docker-compose.yml exec effectful poetry run python examples/08_histogram_metrics.py

SSoT References:
    - documents/engineering/monitoring_and_alerting.md - Histogram bucket guidelines
    - documents/tutorials/metric_types_guide.md - Metric type selection
"""

import asyncio
import random
import time
from collections.abc import Generator

from effectful.adapters.in_memory_metrics import InMemoryMetricsCollector
from effectful.domain.metrics_result import MetricRecorded, MetricRecordingFailed
from effectful.effects.metrics import ObserveHistogram, RecordSummary
from effectful.interpreters.composite import CompositeInterpreter
from effectful.interpreters.metrics import MetricsInterpreter
from effectful.observability import (
    HistogramDefinition,
    MetricsRegistry,
    SummaryDefinition,
)
from effectful.programs.program_types import AllEffects, EffectResult
from effectful.programs.runners import run_program
from effectful.testing import unwrap_ok


# === Define Metrics Registry ===


PERFORMANCE_METRICS = MetricsRegistry(
    counters=(),
    gauges=(),
    histograms=(
        # HTTP request duration with standard SLO buckets
        HistogramDefinition(
            name="http_request_duration_seconds",
            help_text="HTTP request duration distribution",
            label_names=("method", "endpoint"),
            buckets=(
                0.001,
                0.005,
                0.01,
                0.025,
                0.05,
                0.1,
                0.25,
                0.5,
                1.0,
                2.5,
                5.0,
            ),  # Standard SLO buckets
        ),
        # Database query duration with tighter buckets
        HistogramDefinition(
            name="db_query_duration_seconds",
            help_text="Database query duration distribution",
            label_names=("query_type",),
            buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
        ),
        # Payload size distribution
        HistogramDefinition(
            name="request_payload_bytes",
            help_text="HTTP request payload size distribution",
            label_names=("content_type",),
            buckets=(100, 1000, 10000, 100000, 1000000),  # Bytes
        ),
    ),
    summaries=(
        # API latency summary with percentiles
        SummaryDefinition(
            name="api_latency_seconds",
            help_text="API endpoint latency summary",
            label_names=("endpoint",),
        ),
        # Processing time summary
        SummaryDefinition(
            name="processing_time_seconds",
            help_text="Background job processing time summary",
            label_names=("job_type",),
        ),
    ),
)


# === Effect Programs ===


def track_http_request(
    method: str, endpoint: str, duration: float
) -> Generator[AllEffects, EffectResult, bool]:
    """Track HTTP request duration in histogram."""
    result = yield ObserveHistogram(
        metric_name="http_request_duration_seconds",
        labels={"method": method, "endpoint": endpoint},
        value=duration,
    )

    match result:
        case MetricRecorded():
            return True
        case MetricRecordingFailed(reason=reason):
            print(f"❌ Failed to record histogram: {reason}")
            return False


def track_db_query(
    query_type: str, duration: float
) -> Generator[AllEffects, EffectResult, bool]:
    """Track database query duration in histogram."""
    result = yield ObserveHistogram(
        metric_name="db_query_duration_seconds",
        labels={"query_type": query_type},
        value=duration,
    )

    match result:
        case MetricRecorded():
            return True
        case MetricRecordingFailed(reason=reason):
            print(f"❌ Failed to record query histogram: {reason}")
            return False


def track_payload_size(
    content_type: str, size_bytes: int
) -> Generator[AllEffects, EffectResult, bool]:
    """Track request payload size in histogram."""
    result = yield ObserveHistogram(
        metric_name="request_payload_bytes",
        labels={"content_type": content_type},
        value=float(size_bytes),
    )

    match result:
        case MetricRecorded():
            return True
        case MetricRecordingFailed(reason=reason):
            print(f"❌ Failed to record payload histogram: {reason}")
            return False


def track_api_latency(
    endpoint: str, latency: float
) -> Generator[AllEffects, EffectResult, bool]:
    """Track API latency in summary metric."""
    result = yield RecordSummary(
        metric_name="api_latency_seconds",
        labels={"endpoint": endpoint},
        value=latency,
    )

    match result:
        case MetricRecorded():
            return True
        case MetricRecordingFailed(reason=reason):
            print(f"❌ Failed to record summary: {reason}")
            return False


def track_processing_time(
    job_type: str, duration: float
) -> Generator[AllEffects, EffectResult, bool]:
    """Track background job processing time in summary metric."""
    result = yield RecordSummary(
        metric_name="processing_time_seconds",
        labels={"job_type": job_type},
        value=duration,
    )

    match result:
        case MetricRecorded():
            return True
        case MetricRecordingFailed(reason=reason):
            print(f"❌ Failed to record processing summary: {reason}")
            return False


# === Simulation Helpers ===


def simulate_http_latency(endpoint: str) -> float:
    """Simulate HTTP request latency based on endpoint."""
    base_latencies = {
        "/api/users": 0.05,  # Fast endpoint
        "/api/search": 0.25,  # Moderate endpoint
        "/api/analytics": 0.75,  # Slow endpoint
    }
    base = base_latencies.get(endpoint, 0.1)
    # Add random variance
    return base + random.uniform(-0.02, 0.05)


def simulate_db_latency(query_type: str) -> float:
    """Simulate database query latency."""
    base_latencies = {"SELECT": 0.01, "INSERT": 0.02, "UPDATE": 0.025, "DELETE": 0.015}
    base = base_latencies.get(query_type, 0.02)
    return base + random.uniform(-0.005, 0.01)


def simulate_payload_size(content_type: str) -> int:
    """Simulate request payload size."""
    if content_type == "application/json":
        return random.randint(100, 5000)
    elif content_type == "multipart/form-data":
        return random.randint(10000, 500000)
    else:
        return random.randint(50, 1000)


# === Main Program ===


async def main() -> None:
    """Main program demonstrating histogram and summary metrics."""
    print("=" * 60)
    print("Histogram and Summary Metrics Example")
    print("=" * 60)
    print()

    # Create collector and register metrics
    print("📊 Setting up metrics...")
    collector = InMemoryMetricsCollector()
    registration_result = collector.register_metrics(PERFORMANCE_METRICS)

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
    endpoints = ["/api/users", "/api/search", "/api/analytics"]
    methods = ["GET", "POST"]

    for _ in range(100):
        endpoint = random.choice(endpoints)
        method = random.choice(methods)
        duration = simulate_http_latency(endpoint)

        program = track_http_request(method, endpoint, duration)
        result = await run_program(program, interpreter)
        unwrap_ok(result)

    print("✅ Recorded 100 HTTP request durations")
    print()

    # Simulate database queries
    print("💾 Simulating database queries...")
    query_types = ["SELECT", "INSERT", "UPDATE", "DELETE"]

    for _ in range(150):
        query_type = random.choice(query_types)
        duration = simulate_db_latency(query_type)

        program = track_db_query(query_type, duration)
        result = await run_program(program, interpreter)
        unwrap_ok(result)

    print("✅ Recorded 150 database query durations")
    print()

    # Simulate payload sizes
    print("📦 Simulating payload sizes...")
    content_types = ["application/json", "multipart/form-data", "text/plain"]

    for _ in range(75):
        content_type = random.choice(content_types)
        size = simulate_payload_size(content_type)

        program = track_payload_size(content_type, size)
        result = await run_program(program, interpreter)
        unwrap_ok(result)

    print("✅ Recorded 75 payload sizes")
    print()

    # Simulate API latencies (summary)
    print("⚡ Simulating API latencies...")
    api_endpoints = ["/api/users", "/api/search"]

    for _ in range(50):
        endpoint = random.choice(api_endpoints)
        latency = simulate_http_latency(endpoint)

        program = track_api_latency(endpoint, latency)
        result = await run_program(program, interpreter)
        unwrap_ok(result)

    print("✅ Recorded 50 API latencies")
    print()

    # Simulate background job processing
    print("⚙️  Simulating background jobs...")
    job_types = ["email", "report", "cleanup"]

    for _ in range(30):
        job_type = random.choice(job_types)
        duration = random.uniform(0.5, 3.0)

        program = track_processing_time(job_type, duration)
        result = await run_program(program, interpreter)
        unwrap_ok(result)

    print("✅ Recorded 30 background job durations")
    print()

    # Display statistics
    print("=" * 60)
    print("Metrics Statistics")
    print("=" * 60)
    print()

    print("📊 Histogram Metrics:")
    print("-" * 60)

    # HTTP request durations
    http_histograms = [
        m
        for m in collector._metrics.values()
        if m["name"] == "http_request_duration_seconds" and m["type"] == "histogram"
    ]
    print(f"\nHTTP Request Durations: {len(http_histograms)} label combinations")
    for hist in sorted(http_histograms, key=lambda m: (m["labels"].get("endpoint", ""), m["labels"].get("method", ""))):
        endpoint = hist["labels"].get("endpoint", "")
        method = hist["labels"].get("method", "")
        observations = hist["value"].get("observations", [])
        if observations:
            avg = sum(observations) / len(observations)
            min_val = min(observations)
            max_val = max(observations)
            print(f"  {method} {endpoint}:")
            print(f"    Observations: {len(observations)}")
            print(f"    Min: {min_val:.4f}s, Max: {max_val:.4f}s, Avg: {avg:.4f}s")

    # Database query durations
    db_histograms = [
        m
        for m in collector._metrics.values()
        if m["name"] == "db_query_duration_seconds" and m["type"] == "histogram"
    ]
    print(f"\nDatabase Query Durations: {len(db_histograms)} query types")
    for hist in sorted(db_histograms, key=lambda m: m["labels"].get("query_type", "")):
        query_type = hist["labels"].get("query_type", "")
        observations = hist["value"].get("observations", [])
        if observations:
            avg = sum(observations) / len(observations)
            print(f"  {query_type}: {len(observations)} queries, avg {avg:.4f}s")

    print()
    print("📊 Summary Metrics:")
    print("-" * 60)

    # API latencies
    api_summaries = [
        m
        for m in collector._metrics.values()
        if m["name"] == "api_latency_seconds" and m["type"] == "summary"
    ]
    print(f"\nAPI Latencies: {len(api_summaries)} endpoints")
    for summary in sorted(api_summaries, key=lambda m: m["labels"].get("endpoint", "")):
        endpoint = summary["labels"].get("endpoint", "")
        observations = summary["value"].get("observations", [])
        if observations:
            avg = sum(observations) / len(observations)
            print(f"  {endpoint}: {len(observations)} requests, avg {avg:.4f}s")

    print()
    print("=" * 60)
    print("✅ Histogram and summary metrics example complete!")
    print()
    print("Key Takeaways:")
    print("  • Histograms track distributions with predefined buckets")
    print("  • Summaries calculate percentiles over sliding windows")
    print("  • Choose buckets based on your SLOs")
    print("  • Histograms are cheaper than summaries in Prometheus")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
