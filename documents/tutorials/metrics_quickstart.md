# Metrics Quickstart

**Status**: Authoritative source  
**Supersedes**: none  
**Referenced by**: documents/readme.md

> **Purpose**: Tutorial for getting started with type-safe metrics in effectful applications.

**Get started with type-safe metrics in 15 minutes.**

> **Core Doctrine**: For complete metrics philosophy, see [observability.md](../engineering/observability.md)

> **API Reference**: For complete API documentation, see [metrics.md](../api/metrics.md)

---

## Prerequisites

- Docker workflow running; commands executed via `docker compose ... exec effectful`.
- Completed [Tutorial 02: Effect Types](effect_types.md) and [Tutorial 03: ADTs and Result Types](adts_and_results.md).
- Basic familiarity with effect generators and pattern matching.

## Learning Objectives

By the end of this tutorial, you will:

1. ✅ Define a metrics registry with counters and histograms
2. ✅ Yield metrics effects from effect programs
3. ✅ Pattern match on metric results (success/failure)
4. ✅ Query metrics for debugging
5. ✅ Understand when metrics recording fails

**Time**: 15 minutes

---

## Step 1: Define Your Metrics Registry

The registry is a **frozen dataclass** that defines all metrics at application startup.

**Why frozen?** Prevents runtime metric creation, which causes cardinality explosion.

```python
# file: examples/11_metrics_quickstart.py
from effectful.observability import (
    MetricsRegistry,
    CounterDefinition,
    HistogramDefinition,
)

# Define your application's metrics
APP_METRICS = MetricsRegistry(
    counters=(
        CounterDefinition(
            name="tasks_processed_total",
            help_text="Total tasks processed by the system",
            label_names=("task_type", "status"),
        ),
    ),
    gauges=(),
    histograms=(
        HistogramDefinition(
            name="task_duration_seconds",
            help_text="Task processing duration distribution",
            label_names=("task_type",),
            buckets=(0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0),
        ),
    ),
    summaries=(),
)
```

**Key Points**:
- `counters`, `gauges`, `histograms`, `summaries` are **tuples** (immutable)
- `label_names` defines fixed label keys (prevents typos)
- Buckets for histograms cover expected range (0.1s to 60s)

---

## Step 2: Record a Counter Metric

Counters track **monotonically increasing values** (requests, errors, tasks processed).

```python
# file: examples/11_metrics_quickstart.py
from collections.abc import Generator
from effectful import AllEffects, EffectResult
from effectful.effects.metrics import IncrementCounter
from effectful.domain.metrics_result import MetricRecorded, MetricRecordingFailed

def process_task_with_metrics(
    task_type: str,
    task_id: str,
) -> Generator[AllEffects, EffectResult, bool]:
    """Process a task and record metrics."""

    # Execute business logic
    result = yield ProcessTask(task_id=task_id)

    # Determine status
    status = "success" if isinstance(result, TaskCompleted) else "failed"

    # Record counter metric
    metric_result = yield IncrementCounter(
        metric_name="tasks_processed_total",
        labels={
            "task_type": task_type,
            "status": status,
        },
        value=1.0,  # Increment by 1
    )

    # Pattern match on result
    match metric_result:
        case MetricRecorded(timestamp=ts):
            print(f"✅ Metric recorded at {ts}")
            return True
        case MetricRecordingFailed(reason=reason):
            print(f"❌ Metric failed: {reason}")
            return False
```

**Key Points**:
- `IncrementCounter` effect describes the operation (pure data)
- Labels must match registry definition (`task_type`, `status`)
- Pattern matching handles success/failure explicitly

---

## Step 3: Record a Histogram Metric

Histograms track **distributions** (latency, request size, duration).

```python
# file: examples/11_metrics_quickstart.py
import time

def measure_task_duration(
    task_type: str,
    task_id: str,
) -> Generator[AllEffects, EffectResult, None]:
    """Measure and record task duration."""

    # Start timer
    start = time.perf_counter()

    # Execute task
    yield ProcessTask(task_id=task_id)

    # Calculate duration
    duration = time.perf_counter() - start

    # Record histogram
    histogram_result = yield ObserveHistogram(
        metric_name="task_duration_seconds",
        labels={"task_type": task_type},
        value=duration,
    )

    match histogram_result:
        case MetricRecorded():
            print(f"✅ Duration recorded: {duration:.2f}s")
        case MetricRecordingFailed(reason=reason):
            print(f"❌ Histogram failed: {reason}")
```

**Key Points**:
- Measure duration with `time.perf_counter()` (monotonic clock)
- Histogram buckets defined in registry (0.1s, 0.5s, 1.0s, ...)
- Value must be in seconds for `_seconds` metrics

---

## Step 4: Query Metrics (Debugging)

Query current metric values for debugging or health checks.

```python
# file: examples/11_metrics_quickstart.py
from effectful.effects.metrics import QueryMetrics
from effectful.domain.metrics_result import QuerySuccess, QueryFailure

def check_task_metrics() -> Generator[AllEffects, EffectResult, dict[str, float]]:
    """Query current task metrics."""

    result = yield QueryMetrics(
        metric_name="tasks_processed_total",
        labels={"task_type": "email", "status": "success"},
    )

    match result:
        case QuerySuccess(metrics=metrics, timestamp=ts):
            print(f"📊 Metrics at {ts}:")
            for name, value in metrics.items():
                print(f"  {name} = {value}")
            return metrics
        case QueryFailure(reason=reason):
            print(f"❌ Query failed: {reason}")
            return {}
```

**Output Example**:
```text
# file: examples/11_metrics_quickstart_output.txt
📊 Metrics at 1706472000.0:
  tasks_processed_total{task_type="email",status="success"} = 142.0
```

---

## Step 5: Handle Metric Failures

Metrics can fail for several reasons. Always pattern match to handle errors gracefully.

```python
# file: examples/11_metrics_quickstart.py
def robust_metric_recording(
    task_type: str,
) -> Generator[AllEffects, EffectResult, None]:
    """Record metric with robust error handling."""

    result = yield IncrementCounter(
        metric_name="tasks_processed_total",
        labels={"task_type": task_type, "status": "success"},
        value=1.0,
    )

    match result:
        case MetricRecorded():
            # Success - continue
            pass

        case MetricRecordingFailed(reason=reason):
            # Handle specific errors
            if "metric_not_registered" in reason:
                print("⚠️  Metric not in registry - register it first!")
            elif "missing_label" in reason:
                print("⚠️  Required label missing - check registry definition")
            elif "type_mismatch" in reason:
                print("⚠️  Wrong metric type - use correct effect")
            elif "collector_error" in reason:
                print("⚠️  Prometheus unreachable - check infrastructure")
            else:
                print(f"⚠️  Unknown error: {reason}")
```

**Common Errors**:

| Error | Cause | Solution |
|-------|-------|----------|
| `metric_not_registered` | Metric not in registry | Add to `MetricsRegistry` |
| `missing_label: task_type` | Required label missing | Provide all labels from definition |
| `unexpected_label: foo` | Extra label not in registry | Remove label or add to registry |
| `type_mismatch` | Using `IncrementCounter` on Gauge | Use correct effect type |
| `collector_error` | Prometheus unreachable | Check Docker services |

---

## Complete Working Example

```python
# file: examples/11_metrics_quickstart.py
from collections.abc import Generator
from dataclasses import dataclass
import time

from effectful import AllEffects, EffectResult, run_program
from effectful.effects.metrics import IncrementCounter, ObserveHistogram, QueryMetrics
from effectful.domain.metrics_result import (
    MetricRecorded,
    MetricRecordingFailed,
    QuerySuccess,
    QueryFailure,
)
from effectful.observability import (
    MetricsRegistry,
    CounterDefinition,
    HistogramDefinition,
)

# 1. Define metrics registry
APP_METRICS = MetricsRegistry(
    counters=(
        CounterDefinition(
            name="tasks_processed_total",
            help_text="Total tasks processed",
            label_names=("task_type", "status"),
        ),
    ),
    gauges=(),
    histograms=(
        HistogramDefinition(
            name="task_duration_seconds",
            help_text="Task duration distribution",
            label_names=("task_type",),
            buckets=(0.1, 0.5, 1.0, 5.0, 10.0),
        ),
    ),
    summaries=(),
)

# 2. Effect program with metrics
def process_email_task(
    email_id: str,
) -> Generator[AllEffects, EffectResult, bool]:
    """Process email task with metrics."""

    # Start timer
    start = time.perf_counter()

    # Simulate task processing
    yield SendEmail(email_id=email_id)

    # Calculate duration
    duration = time.perf_counter() - start

    # Record counter
    counter_result = yield IncrementCounter(
        metric_name="tasks_processed_total",
        labels={"task_type": "email", "status": "success"},
        value=1.0,
    )

    # Record histogram
    histogram_result = yield ObserveHistogram(
        metric_name="task_duration_seconds",
        labels={"task_type": "email"},
        value=duration,
    )

    # Check both succeeded
    match (counter_result, histogram_result):
        case (MetricRecorded(), MetricRecorded()):
            print("✅ All metrics recorded successfully")
            return True
        case (MetricRecordingFailed(reason=r), _):
            print(f"❌ Counter failed: {r}")
            return False
        case (_, MetricRecordingFailed(reason=r)):
            print(f"❌ Histogram failed: {r}")
            return False

# 3. Query metrics
def check_email_stats() -> Generator[AllEffects, EffectResult, int]:
    """Query total successful email tasks."""

    result = yield QueryMetrics(
        metric_name="tasks_processed_total",
        labels={"task_type": "email", "status": "success"},
    )

    match result:
        case QuerySuccess(metrics=metrics):
            # Extract value from metric name
            total = sum(metrics.values())
            print(f"📊 Total emails processed: {int(total)}")
            return int(total)
        case QueryFailure(reason=reason):
            print(f"❌ Query failed: {reason}")
            return 0

# 4. Execute programs
async def main() -> None:
    # Process some tasks
    for i in range(5):
        result = await run_program(
            process_email_task(email_id=f"email-{i}"),
            interpreter=composite_interpreter,
        )
        print(f"Task {i}: {result}")

    # Check stats
    stats_result = await run_program(
        check_email_stats(),
        interpreter=composite_interpreter,
    )
    print(f"Stats: {stats_result}")
```

**Expected Output**:
```text
# file: examples/11_metrics_quickstart_output.txt
✅ All metrics recorded successfully
Task 0: Ok(True)
✅ All metrics recorded successfully
Task 1: Ok(True)
✅ All metrics recorded successfully
Task 2: Ok(True)
✅ All metrics recorded successfully
Task 3: Ok(True)
✅ All metrics recorded successfully
Task 4: Ok(True)
📊 Total emails processed: 5
Stats: Ok(5)
```

---

## Testing Your Metrics

Use `ResetMetrics` effect in test fixtures for isolation.

```python
# file: examples/11_metrics_quickstart.py
import pytest
from effectful.effects.metrics import ResetMetrics

@pytest.fixture
async def clean_metrics() -> None:
    """Reset metrics before each test."""
    result = await run_program(reset_program(), test_interpreter)
    assert isinstance(result, Ok)

def reset_program() -> Generator[AllEffects, EffectResult, None]:
    result = yield ResetMetrics()
    assert isinstance(result, MetricRecorded)

@pytest.mark.asyncio
async def test_task_metrics(clean_metrics: None) -> None:
    """Test task processing increments counter."""
    # Process task
    result = await run_program(
        process_email_task(email_id="test-1"),
        interpreter=test_interpreter,
    )
    assert isinstance(result, Ok)

    # Query metrics
    query_result = await run_program(
        check_email_stats(),
        interpreter=test_interpreter,
    )
    assert isinstance(query_result, Ok)
    assert query_result.value == 1  # Counter incremented once
```

**⚠️ WARNING**: NEVER use `ResetMetrics` in production! Only in tests.

---

## Next Steps

Now that you understand basic metrics, explore advanced topics:

1. **Metric Types Guide** - When to use Counter vs Gauge vs Histogram vs Summary
   - See [metric_types_guide.md](./metric_types_guide.md)

2. **Prometheus Setup** - Run Prometheus/Grafana in Docker
   - See [prometheus_setup.md](./prometheus_setup.md)

3. **Alert Rules** - Create alerts for metric thresholds
   - See [alert_rules.md](./alert_rules.md)

4. **Grafana Dashboards** - Visualize metrics with beautiful dashboards
   - See [grafana_dashboards.md](./grafana_dashboards.md)

---

## Common Patterns

### Pattern 1: Automatic Duration Tracking

```python
# file: examples/11_metrics_quickstart.py
def with_duration_tracking[T] (
    metric_name: str,
    labels: dict[str, str],
    program: Generator[AllEffects, EffectResult, T],
) -> Generator[AllEffects, EffectResult, T]:
    """Wrap program with duration tracking."""
    start = time.perf_counter()

    # Delegate to wrapped program
    result = yield from program

    # Record duration
    duration = time.perf_counter() - start
    yield ObserveHistogram(
        metric_name=metric_name,
        labels=labels,
        value=duration,
    )

    return result

# Usage
user = yield from with_duration_tracking(
    metric_name="database_query_duration_seconds",
    labels={"query_type": "get_user_by_id"},
    program=get_user_by_id(user_id),
)
```

### Pattern 2: Conditional Metrics

```python
# file: examples/11_metrics_quickstart.py
def process_with_status_metrics(
    task_id: str,
) -> Generator[AllEffects, EffectResult, None]:
    """Record different metrics based on result."""

    result = yield ProcessTask(task_id=task_id)

    # Conditional label based on result type
    status = "success" if isinstance(result, TaskCompleted) else "failed"
    error_type = result.error_type if isinstance(result, TaskFailed) else "none"

    yield IncrementCounter(
        metric_name="tasks_processed_total",
        labels={"status": status, "error_type": error_type},
        value=1.0,
    )
```

---

## Troubleshooting

### "Metric not registered" Error

**Problem**: `MetricRecordingFailed(reason="metric_not_registered")`

**Solution**: Add metric to registry before using it.

```python
# file: examples/11_metrics_quickstart.py
# ❌ WRONG - Metric not in registry
yield IncrementCounter(
    metric_name="unknown_metric_total",
    labels={},
    value=1.0,
)

# ✅ CORRECT - Add to registry first
APP_METRICS = MetricsRegistry(
    counters=(
        CounterDefinition(
            name="unknown_metric_total",
            help_text="Description",
            label_names=(),
        ),
    ),
    ...
)
```

### "Missing label" Error

**Problem**: `MetricRecordingFailed(reason="missing_label: task_type")`

**Solution**: Provide all labels defined in registry.

```python
# file: examples/11_metrics_quickstart.py
# Registry defines: label_names=("task_type", "status")

# ❌ WRONG - Missing "status" label
yield IncrementCounter(
    metric_name="tasks_processed_total",
    labels={"task_type": "email"},  # Missing "status"!
    value=1.0,
)

# ✅ CORRECT - All labels provided
yield IncrementCounter(
    metric_name="tasks_processed_total",
    labels={"task_type": "email", "status": "success"},
    value=1.0,
)
```

### "Type mismatch" Error

**Problem**: `MetricRecordingFailed(reason="type_mismatch")`

**Solution**: Use correct effect type for metric.

```python
# file: examples/11_metrics_quickstart.py
# Registry defines as CounterDefinition

# ❌ WRONG - Using RecordGauge on Counter
yield RecordGauge(
    metric_name="tasks_processed_total",  # This is a Counter!
    labels={...},
    value=42.0,
)

# ✅ CORRECT - Use IncrementCounter
yield IncrementCounter(
    metric_name="tasks_processed_total",
    labels={...},
    value=1.0,
)
```

---

## Summary

You've learned:
- ✅ How to define a metrics registry with frozen dataclasses
- ✅ How to record counter and histogram metrics from effect programs
- ✅ How to query metrics for debugging
- ✅ How to handle metric failures gracefully
- ✅ Common error patterns and solutions

**Key Takeaways**:
1. **Registry First** - Define all metrics at startup (frozen, immutable)
2. **Explicit Errors** - Pattern match on `MetricRecorded | MetricRecordingFailed`
3. **Label Discipline** - Match registry definition exactly (no typos!)
4. **Testing** - Use `ResetMetrics` in fixtures for isolation

---

## See Also

- [Observability](../engineering/observability.md) - Metrics philosophy
- [Monitoring & Alerting](../engineering/monitoring_and_alerting.md#monitoring-standards) - Naming conventions
- [Metrics API Reference](../api/metrics.md) - Complete API documentation
- [Metric Types Guide](./metric_types_guide.md) - When to use each type

---

## Cross-References
- [Documentation Standards](../documentation_standards.md)
- [Engineering Standards](../engineering/README.md)
