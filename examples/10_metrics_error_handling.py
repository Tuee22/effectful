"""Metrics error handling example.

This example demonstrates:
1. Handling MetricRecordingFailed results
2. Fire-and-forget metrics pattern
3. Graceful degradation when metrics fail
4. Logging metrics failures without blocking business logic

Run this example:
    docker compose -f docker/docker-compose.yml exec effectful poetry run python examples/09_metrics_error_handling.py

SSoT References:
    - documents/core/observability_doctrine.md - Fire-and-forget pattern
    - documents/engineering/monitoring_and_alerting.md - Error handling guidelines
"""

import asyncio
from collections.abc import Generator

from effectful.adapters.in_memory_metrics import InMemoryMetricsCollector
from effectful.domain.metrics_result import MetricRecorded, MetricRecordingFailed
from effectful.effects.metrics import IncrementCounter
from effectful.interpreters.composite import CompositeInterpreter
from effectful.interpreters.metrics import MetricsInterpreter
from effectful.observability import CounterDefinition, MetricsRegistry
from effectful.programs.program_types import AllEffects, EffectResult
from effectful.programs.runners import run_program
from effectful.testing import unwrap_ok


# === Effect Programs ===


def process_order_with_naive_metrics(
    order_id: str, amount: float
) -> Generator[AllEffects, EffectResult, dict[str, str]]:
    """Naive approach: Assumes metrics always succeed.

    ❌ ANTI-PATTERN: This will fail if metrics recording fails!
    """
    # Record metric (assuming success)
    yield IncrementCounter(
        metric_name="orders_processed_total",
        labels={"status": "completed"},
        value=1.0,
    )

    # Process order
    print(f"Processing order {order_id} for ${amount}")
    return {"order_id": order_id, "status": "completed"}


def process_order_with_proper_error_handling(
    order_id: str, amount: float
) -> Generator[AllEffects, EffectResult, dict[str, str]]:
    """Proper approach: Handle metric failures gracefully.

    ✅ BEST PRACTICE: Business logic continues even if metrics fail.
    """
    # Record metric
    metric_result = yield IncrementCounter(
        metric_name="orders_processed_total",
        labels={"status": "completed"},
        value=1.0,
    )

    # Pattern match on metric result
    match metric_result:
        case MetricRecorded(timestamp=ts):
            print(f"✅ Metric recorded at {ts}")
        case MetricRecordingFailed(reason=reason):
            # Log failure but don't fail the business logic
            print(f"⚠️  Metric recording failed: {reason}")
            print(f"   (Order processing continues anyway)")

    # Process order (business logic is unaffected by metrics failure)
    print(f"Processing order {order_id} for ${amount}")
    return {"order_id": order_id, "status": "completed"}


def process_order_with_retry_logic(
    order_id: str, amount: float, collector: InMemoryMetricsCollector
) -> Generator[AllEffects, EffectResult, dict[str, str]]:
    """Advanced approach: Retry failed metrics with fallback.

    ✅ BEST PRACTICE: Retry metrics collection with degraded mode.
    """
    # Try to record metric
    metric_result = yield IncrementCounter(
        metric_name="orders_processed_total",
        labels={"status": "completed"},
        value=1.0,
    )

    # Handle metric result with retry logic
    match metric_result:
        case MetricRecorded():
            print("✅ Primary metric recorded")
        case MetricRecordingFailed(reason=reason):
            print(f"⚠️  Primary metric failed: {reason}")

            # Try fallback metric (simplified labels)
            fallback_result = yield IncrementCounter(
                metric_name="orders_processed_total",
                labels={},  # No labels - fallback to default
                value=1.0,
            )

            match fallback_result:
                case MetricRecorded():
                    print("✅ Fallback metric recorded (no labels)")
                case MetricRecordingFailed(fallback_reason=fallback_reason):
                    print(f"⚠️  Fallback metric also failed: {fallback_reason}")
                    print("   (Metrics collection degraded, but order processing continues)")

    # Business logic always continues
    print(f"Processing order {order_id} for ${amount}")
    return {"order_id": order_id, "status": "completed"}


def process_order_with_metrics_tracking(
    order_id: str, amount: float
) -> Generator[AllEffects, EffectResult, tuple[dict[str, str], bool]]:
    """Track metrics success/failure alongside business logic.

    ✅ BEST PRACTICE: Return both business result and metrics health.
    """
    # Record metric
    metric_result = yield IncrementCounter(
        metric_name="orders_processed_total",
        labels={"status": "completed"},
        value=1.0,
    )

    # Track metrics health
    metrics_healthy = isinstance(metric_result, dict) and "timestamp" in metric_result

    match metric_result:
        case MetricRecorded():
            print("✅ Metrics healthy")
        case MetricRecordingFailed(reason=reason):
            print(f"⚠️  Metrics degraded: {reason}")

    # Process order
    print(f"Processing order {order_id} for ${amount}")
    business_result = {"order_id": order_id, "status": "completed"}

    # Return both results
    return (business_result, metrics_healthy)


# === Main Program ===


async def main() -> None:
    """Main program demonstrating metrics error handling."""
    print("=" * 60)
    print("Metrics Error Handling Example")
    print("=" * 60)
    print()

    # Create collector and register metrics
    print("📊 Setting up metrics...")
    collector = InMemoryMetricsCollector()

    metrics_registry = MetricsRegistry(
        counters=(
            CounterDefinition(
                name="orders_processed_total",
                help_text="Total orders processed",
                label_names=("status",),  # Note: Requires 'status' label
            ),
        ),
        gauges=(),
        histograms=(),
        summaries=(),
    )

    registration_result = collector.register_metrics(metrics_registry)
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

    # Example 1: Proper error handling
    print("=" * 60)
    print("Example 1: Proper Error Handling")
    print("=" * 60)
    print()

    program1 = process_order_with_proper_error_handling("ORDER-001", 99.99)
    result1 = await run_program(program1, interpreter)
    order1 = unwrap_ok(result1)
    print(f"Result: {order1}")
    print()

    # Example 2: Missing required labels (will fail)
    print("=" * 60)
    print("Example 2: Invalid Metric (Missing Required Labels)")
    print("=" * 60)
    print()

    def process_order_with_invalid_metric(
        order_id: str,
    ) -> Generator[AllEffects, EffectResult, dict[str, str]]:
        """This will fail because 'status' label is required."""
        metric_result = yield IncrementCounter(
            metric_name="orders_processed_total",
            labels={},  # ❌ Missing required 'status' label
            value=1.0,
        )

        match metric_result:
            case MetricRecorded():
                print("✅ Metric recorded")
            case MetricRecordingFailed(reason=reason):
                print(f"⚠️  Metric failed (as expected): {reason}")

        # Business logic continues
        print(f"Processing order {order_id}")
        return {"order_id": order_id, "status": "completed"}

    program2 = process_order_with_invalid_metric("ORDER-002")
    result2 = await run_program(program2, interpreter)
    order2 = unwrap_ok(result2)
    print(f"Result: {order2}")
    print()

    # Example 3: Unregistered metric (will fail)
    print("=" * 60)
    print("Example 3: Unregistered Metric")
    print("=" * 60)
    print()

    def process_order_with_unregistered_metric(
        order_id: str,
    ) -> Generator[AllEffects, EffectResult, dict[str, str]]:
        """This will fail because metric is not registered."""
        metric_result = yield IncrementCounter(
            metric_name="unregistered_metric",  # ❌ Not registered
            labels={},
            value=1.0,
        )

        match metric_result:
            case MetricRecorded():
                print("✅ Metric recorded")
            case MetricRecordingFailed(reason=reason):
                print(f"⚠️  Metric failed (as expected): {reason}")

        # Business logic continues
        print(f"Processing order {order_id}")
        return {"order_id": order_id, "status": "completed"}

    program3 = process_order_with_unregistered_metric("ORDER-003")
    result3 = await run_program(program3, interpreter)
    order3 = unwrap_ok(result3)
    print(f"Result: {order3}")
    print()

    # Example 4: Track metrics health
    print("=" * 60)
    print("Example 4: Tracking Metrics Health")
    print("=" * 60)
    print()

    program4 = process_order_with_metrics_tracking("ORDER-004", 149.99)
    result4 = await run_program(program4, interpreter)
    order4, metrics_healthy = unwrap_ok(result4)
    print(f"Result: {order4}")
    print(f"Metrics Healthy: {metrics_healthy}")
    print()

    # Summary
    print("=" * 60)
    print("✅ Metrics error handling example complete!")
    print()
    print("Key Takeaways:")
    print("  • ALWAYS pattern match on metric results")
    print("  • Metrics failures should NEVER block business logic")
    print("  • Fire-and-forget pattern is critical for resilience")
    print("  • Log metrics failures for debugging")
    print("  • Consider fallback metrics with simplified labels")
    print("  • Track metrics health separately from business logic")
    print()
    print("Common Metric Failure Reasons:")
    print("  • Metric not registered in MetricsRegistry")
    print("  • Missing required label names")
    print("  • Extra labels not defined in registry")
    print("  • Collector infrastructure unavailable")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
