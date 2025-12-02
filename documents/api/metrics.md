# Metrics API Reference

**effectful** - Complete reference for metrics effects, ADT return types, and observability primitives.

> **Core Doctrine**: For metrics philosophy and architecture, see [observability_doctrine.md](../engineering/observability.md)

> **Core Doctrine**: For metric naming and labeling standards, see [monitoring_and_alerting.md](../engineering/monitoring_and_alerting.md#monitoring-standards)

---

## Overview

The metrics API provides **type-safe, compile-time validated** observability primitives for Prometheus/Grafana integration.

**Key Features**:
- **6 Effect Types**: Counter, Gauge, Histogram, Summary, Query, Reset
- **ADT Return Types**: Explicit success/failure cases (no exceptions)
- **Cardinality Protection**: Registry pattern prevents metric explosion
- **Frozen Dataclasses**: All metrics immutable (thread-safe)
- **Protocol-Based**: Infrastructure-agnostic (Prometheus, testing, custom collectors)

---

## Quick Reference

### Effect Types

| Effect | Purpose | Returns | Idempotent? |
|--------|---------|---------|-------------|
| `IncrementCounter` | Monotonically increasing count | `MetricRecorded \| MetricRecordingFailed` | No |
| `RecordGauge` | Point-in-time value | `MetricRecorded \| MetricRecordingFailed` | Yes |
| `ObserveHistogram` | Duration/size distribution | `MetricRecorded \| MetricRecordingFailed` | No |
| `RecordSummary` | Streaming quantiles (p50, p95, p99) | `MetricRecorded \| MetricRecordingFailed` | No |
| `QueryMetrics` | Retrieve current metric values | `QuerySuccess \| QueryFailure` | Yes |
| `ResetMetrics` | Clear all metrics (testing only) | `MetricRecorded \| MetricRecordingFailed` | No |

### ADT Return Types

```python
from effectful.domain.metrics_result import (
    MetricRecorded,         # Success case with timestamp
    MetricRecordingFailed,  # Failure case with error reason
    QuerySuccess,           # Query success with metric values
    QueryFailure,           # Query failure with error message
)

# Union types for pattern matching
type MetricResult = MetricRecorded | MetricRecordingFailed
type MetricQueryResult = QuerySuccess | QueryFailure
```

---

## Effect Definitions

### IncrementCounter

**Purpose**: Increment a monotonically increasing counter.

**Use Cases**: Request counts, error counts, events processed, tasks completed.

```python
from dataclasses import dataclass
from effectful.effects.metrics import IncrementCounter

@dataclass(frozen=True)
class IncrementCounter:
    """Effect: Increment a counter metric."""
    metric_name: str
    labels: dict[str, str]
    value: float = 1.0
```

**Parameters**:
- `metric_name: str` - Registered counter name (must end with `_total`)
- `labels: dict[str, str]` - Label key-value pairs (must match registry definition)
- `value: float` - Amount to increment (default: 1.0, must be > 0)

**Returns**: `MetricRecorded | MetricRecordingFailed`

**Example**:
```python
from collections.abc import Generator
from effectful import AllEffects, EffectResult

def track_appointment_created(
    doctor_id: str,
    specialization: str
) -> Generator[AllEffects, EffectResult, None]:
    result = yield IncrementCounter(
        metric_name="appointments_created_total",
        labels={"doctor_id": doctor_id, "specialization": specialization},
        value=1.0,
    )

    match result:
        case MetricRecorded(timestamp=ts):
            print(f"Metric recorded at {ts}")
        case MetricRecordingFailed(reason=reason):
            print(f"Failed to record metric: {reason}")
```

**Validation Rules**:
- Metric name must exist in registry
- Metric must be registered as `CounterDefinition`
- All label keys must match registry definition
- Label values must be non-empty strings
- Value must be positive (> 0)

**Common Errors**:
```python
# ❌ Metric not registered
MetricRecordingFailed(reason="metric_not_registered")

# ❌ Wrong metric type (registered as Gauge)
MetricRecordingFailed(reason="type_mismatch")

# ❌ Missing required label
MetricRecordingFailed(reason="missing_label: doctor_id")

# ❌ Extra unexpected label
MetricRecordingFailed(reason="unexpected_label: patient_id")

# ❌ Negative increment value
MetricRecordingFailed(reason="invalid_value: must be > 0")
```

---

### RecordGauge

**Purpose**: Set a gauge to a specific value (can go up or down).

**Use Cases**: Active connections, queue depth, memory usage, temperature.

```python
@dataclass(frozen=True)
class RecordGauge:
    """Effect: Set a gauge metric to a specific value."""
    metric_name: str
    labels: dict[str, str]
    value: float
```

**Parameters**:
- `metric_name: str` - Registered gauge name
- `labels: dict[str, str]` - Label key-value pairs
- `value: float` - Current value (can be negative)

**Returns**: `MetricRecorded | MetricRecordingFailed`

**Example**:
```python
def track_active_websocket_connections(
    connection_count: int
) -> Generator[AllEffects, EffectResult, None]:
    result = yield RecordGauge(
        metric_name="active_websocket_connections",
        labels={"server": "ws-01"},
        value=float(connection_count),
    )

    match result:
        case MetricRecorded():
            pass  # Success
        case MetricRecordingFailed(reason=reason):
            print(f"Gauge recording failed: {reason}")
```

**Validation Rules**:
- Metric name must exist in registry
- Metric must be registered as `GaugeDefinition`
- All label keys must match registry definition
- Value can be any float (including negative)

**Idempotency**: Safe to call multiple times with same value.

---

### ObserveHistogram

**Purpose**: Record a value in a histogram (tracks distribution).

**Use Cases**: Request duration, response size, database query latency.

```python
@dataclass(frozen=True)
class ObserveHistogram:
    """Effect: Observe a value in a histogram metric."""
    metric_name: str
    labels: dict[str, str]
    value: float
```

**Parameters**:
- `metric_name: str` - Registered histogram name (must end with `_seconds`, `_bytes`, etc.)
- `labels: dict[str, str]` - Label key-value pairs
- `value: float` - Observed value (duration in seconds, size in bytes)

**Returns**: `MetricRecorded | MetricRecordingFailed`

**Example**:
```python
import time

def measure_effect_duration(
    effect_type: str
) -> Generator[AllEffects, EffectResult, None]:
    start = time.perf_counter()

    # Execute effect...
    yield GetUserById(user_id=user_id)

    duration = time.perf_counter() - start

    result = yield ObserveHistogram(
        metric_name="effect_duration_seconds",
        labels={"effect_type": effect_type},
        value=duration,
    )

    match result:
        case MetricRecorded():
            pass
        case MetricRecordingFailed(reason=reason):
            print(f"Histogram observation failed: {reason}")
```

**Buckets**: Defined in `HistogramDefinition` at registry time.

**Validation Rules**:
- Metric name must exist in registry
- Metric must be registered as `HistogramDefinition`
- Value must be non-negative (>= 0)

**Prometheus Output**:
```
effect_duration_seconds_bucket{effect_type="GetUserById",le="0.1"} 45
effect_duration_seconds_bucket{effect_type="GetUserById",le="0.5"} 89
effect_duration_seconds_bucket{effect_type="GetUserById",le="1.0"} 95
effect_duration_seconds_bucket{effect_type="GetUserById",le="+Inf"} 100
effect_duration_seconds_sum{effect_type="GetUserById"} 42.5
effect_duration_seconds_count{effect_type="GetUserById"} 100
```

---

### RecordSummary

**Purpose**: Record a value in a summary (streaming quantiles).

**Use Cases**: Similar to histogram but computes p50/p95/p99 on client side.

```python
@dataclass(frozen=True)
class RecordSummary:
    """Effect: Record a value in a summary metric."""
    metric_name: str
    labels: dict[str, str]
    value: float
```

**Parameters**:
- `metric_name: str` - Registered summary name
- `labels: dict[str, str]` - Label key-value pairs
- `value: float` - Observed value

**Returns**: `MetricRecorded | MetricRecordingFailed`

**Example**:
```python
def track_request_size(
    endpoint: str,
    request_bytes: int
) -> Generator[AllEffects, EffectResult, None]:
    result = yield RecordSummary(
        metric_name="request_size_bytes",
        labels={"endpoint": endpoint},
        value=float(request_bytes),
    )
```

**Histogram vs Summary**:

| Aspect | Histogram | Summary |
|--------|-----------|---------|
| **Aggregation** | Server-side (PromQL) | Client-side (library) |
| **Quantiles** | Approximate (`histogram_quantile`) | Exact (but expensive) |
| **Buckets** | Pre-defined at registration | N/A |
| **Cardinality** | Low (buckets fixed) | High (per-label timeseries) |
| **Recommendation** | ✅ Prefer for latency | ⚠️ Use sparingly |

**Recommendation**: Use `ObserveHistogram` unless you need exact quantiles.

---

### QueryMetrics

**Purpose**: Retrieve current metric values (for debugging, dashboards, tests).

**Use Cases**: Health checks, admin dashboards, integration tests.

```python
@dataclass(frozen=True)
class QueryMetrics:
    """Effect: Query current metric values."""
    metric_name: str | None = None
    labels: dict[str, str] | None = None
```

**Parameters**:
- `metric_name: str | None` - Filter by metric name (None = all metrics)
- `labels: dict[str, str] | None` - Filter by labels (None = all label combinations)

**Returns**: `QuerySuccess | QueryFailure`

**Example**:
```python
def check_metrics_health() -> Generator[AllEffects, EffectResult, dict[str, float]]:
    result = yield QueryMetrics(
        metric_name="appointments_created_total",
        labels={"specialization": "cardiology"},
    )

    match result:
        case QuerySuccess(metrics=metrics):
            return metrics
        case QueryFailure(reason=reason):
            print(f"Query failed: {reason}")
            return {}
```

**QuerySuccess Structure**:
```python
@dataclass(frozen=True)
class QuerySuccess:
    """Metric query succeeded."""
    metrics: dict[str, float]
    timestamp: float
```

**Example Response**:
```python
QuerySuccess(
    metrics={
        "appointments_created_total{specialization='cardiology',doctor_id='d1'}": 42.0,
        "appointments_created_total{specialization='cardiology',doctor_id='d2'}": 38.0,
    },
    timestamp=1706472000.0,
)
```

---

### ResetMetrics

**Purpose**: Clear all metrics (TESTING ONLY - never use in production).

**Use Cases**: Integration test isolation, test fixture cleanup.

```python
@dataclass(frozen=True)
class ResetMetrics:
    """Effect: Reset all metrics (TESTING ONLY)."""
    pass
```

**Returns**: `MetricRecorded | MetricRecordingFailed`

**Example**:
```python
@pytest.fixture
async def clean_metrics() -> None:
    """Reset metrics before each test."""
    result = await run_program(reset_all_metrics())
    assert isinstance(result, Ok)

def reset_all_metrics() -> Generator[AllEffects, EffectResult, None]:
    result = yield ResetMetrics()
    assert isinstance(result, MetricRecorded)
```

**⚠️ WARNING**: NEVER use ResetMetrics in production. Metrics are append-only in production systems.

---

## ADT Return Types

### MetricRecorded

**Purpose**: Success case for metric recording operations.

```python
@dataclass(frozen=True)
class MetricRecorded:
    """Metric successfully recorded."""
    timestamp: float
```

**Fields**:
- `timestamp: float` - Unix timestamp when metric was recorded (UTC)

**Usage**:
```python
match result:
    case MetricRecorded(timestamp=ts):
        print(f"Recorded at {datetime.fromtimestamp(ts)}")
```

---

### MetricRecordingFailed

**Purpose**: Failure case for metric recording operations.

```python
@dataclass(frozen=True)
class MetricRecordingFailed:
    """Metric recording failed."""
    reason: str
```

**Fields**:
- `reason: str` - Human-readable error message

**Common Reasons**:
- `"metric_not_registered"` - Metric name not found in registry
- `"type_mismatch"` - Wrong effect type for metric definition
- `"missing_label: <key>"` - Required label not provided
- `"unexpected_label: <key>"` - Extra label not in definition
- `"invalid_value: <reason>"` - Value validation failed
- `"collector_error: <message>"` - Infrastructure error (Prometheus unreachable)

**Usage**:
```python
match result:
    case MetricRecordingFailed(reason=reason):
        if "metric_not_registered" in reason:
            # Register metric first
            pass
        elif "collector_error" in reason:
            # Infrastructure issue
            pass
```

---

### QuerySuccess

**Purpose**: Success case for metric queries.

```python
@dataclass(frozen=True)
class QuerySuccess:
    """Metric query succeeded."""
    metrics: dict[str, float]
    timestamp: float
```

**Fields**:
- `metrics: dict[str, float]` - Metric name (with labels) → current value
- `timestamp: float` - Query execution timestamp

**Example**:
```python
QuerySuccess(
    metrics={
        "requests_total{endpoint='/api/users',method='GET'}": 1523.0,
        "requests_total{endpoint='/api/posts',method='GET'}": 842.0,
    },
    timestamp=1706472000.0,
)
```

---

### QueryFailure

**Purpose**: Failure case for metric queries.

```python
@dataclass(frozen=True)
class QueryFailure:
    """Metric query failed."""
    reason: str
```

**Fields**:
- `reason: str` - Human-readable error message

**Common Reasons**:
- `"metric_not_found"` - No metrics match query
- `"collector_unavailable"` - Prometheus unreachable
- `"invalid_query: <reason>"` - Malformed query parameters

---

## Registry Types

### MetricsRegistry

**Purpose**: Type-safe registry preventing metric cardinality explosion.

```python
from dataclasses import dataclass
from effectful.observability import MetricsRegistry

@dataclass(frozen=True)
class MetricsRegistry:
    """Immutable registry of metric definitions."""
    counters: tuple[CounterDefinition, ...]
    gauges: tuple[GaugeDefinition, ...]
    histograms: tuple[HistogramDefinition, ...]
    summaries: tuple[SummaryDefinition, ...]
```

**Example**:
```python
from effectful.observability import (
    MetricsRegistry,
    CounterDefinition,
    GaugeDefinition,
    HistogramDefinition,
)

APP_METRICS = MetricsRegistry(
    counters=(
        CounterDefinition(
            name="appointments_created_total",
            help_text="Total appointments created",
            label_names=("doctor_id", "specialization"),
        ),
        CounterDefinition(
            name="prescriptions_issued_total",
            help_text="Total prescriptions issued",
            label_names=("doctor_id", "medication_type"),
        ),
    ),
    gauges=(
        GaugeDefinition(
            name="active_websocket_connections",
            help_text="Current active WebSocket connections",
            label_names=("server_id",),
        ),
    ),
    histograms=(
        HistogramDefinition(
            name="effect_duration_seconds",
            help_text="Effect execution duration",
            label_names=("effect_type",),
            buckets=(0.001, 0.01, 0.1, 0.5, 1.0, 5.0, 10.0),
        ),
    ),
    summaries=(),
)
```

**Why Frozen?**: Prevents runtime modifications that could cause cardinality explosion.

---

### CounterDefinition

**Purpose**: Define a monotonically increasing counter metric.

```python
@dataclass(frozen=True)
class CounterDefinition:
    """Definition of a counter metric."""
    name: str
    help_text: str
    label_names: tuple[str, ...]
```

**Fields**:
- `name: str` - Metric name (must end with `_total`)
- `help_text: str` - Human-readable description
- `label_names: tuple[str, ...]` - Fixed label keys (empty tuple = no labels)

**Example**:
```python
CounterDefinition(
    name="http_requests_total",
    help_text="Total HTTP requests received",
    label_names=("method", "endpoint", "status"),
)
```

**Validation**:
- Name must end with `_total`
- Label names must be valid identifiers
- No duplicate label names

---

### GaugeDefinition

**Purpose**: Define a gauge metric (value that can increase or decrease).

```python
@dataclass(frozen=True)
class GaugeDefinition:
    """Definition of a gauge metric."""
    name: str
    help_text: str
    label_names: tuple[str, ...]
```

**Fields**: Same as `CounterDefinition`

**Example**:
```python
GaugeDefinition(
    name="database_connections_active",
    help_text="Current active database connections",
    label_names=("pool_id",),
)
```

---

### HistogramDefinition

**Purpose**: Define a histogram metric with buckets.

```python
@dataclass(frozen=True)
class HistogramDefinition:
    """Definition of a histogram metric."""
    name: str
    help_text: str
    label_names: tuple[str, ...]
    buckets: tuple[float, ...]
```

**Fields**:
- `name: str` - Metric name (should include unit: `_seconds`, `_bytes`)
- `help_text: str` - Human-readable description
- `label_names: tuple[str, ...]` - Fixed label keys
- `buckets: tuple[float, ...]` - Bucket boundaries (must be sorted ascending)

**Example**:
```python
HistogramDefinition(
    name="http_request_duration_seconds",
    help_text="HTTP request duration distribution",
    label_names=("method", "endpoint"),
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)
```

**Bucket Design**:
- Cover expected range (p1 to p99+)
- Use exponential distribution (~2x each step)
- Include SLO thresholds (e.g., 0.5s, 1.0s)

---

### SummaryDefinition

**Purpose**: Define a summary metric with quantiles.

```python
@dataclass(frozen=True)
class SummaryDefinition:
    """Definition of a summary metric."""
    name: str
    help_text: str
    label_names: tuple[str, ...]
    quantiles: tuple[float, ...]
```

**Fields**:
- `quantiles: tuple[float, ...]` - Quantiles to track (0.0-1.0, e.g., 0.5, 0.95, 0.99)

**Example**:
```python
SummaryDefinition(
    name="response_size_bytes",
    help_text="HTTP response size summary",
    label_names=("endpoint",),
    quantiles=(0.5, 0.9, 0.95, 0.99),
)
```

---

## MetricsCollector Protocol

**Purpose**: Infrastructure-agnostic interface for metrics collection.

```python
from typing import Protocol
from effectful.domain.metrics_result import MetricResult, MetricQueryResult

class MetricsCollector(Protocol):
    """Protocol for metrics collection infrastructure."""

    async def increment_counter(
        self,
        metric_name: str,
        labels: dict[str, str],
        value: float,
    ) -> MetricResult:
        """Increment a counter metric."""
        ...

    async def record_gauge(
        self,
        metric_name: str,
        labels: dict[str, str],
        value: float,
    ) -> MetricResult:
        """Set a gauge metric."""
        ...

    async def observe_histogram(
        self,
        metric_name: str,
        labels: dict[str, str],
        value: float,
    ) -> MetricResult:
        """Observe a histogram value."""
        ...

    async def record_summary(
        self,
        metric_name: str,
        labels: dict[str, str],
        value: float,
    ) -> MetricResult:
        """Record a summary value."""
        ...

    async def query_metrics(
        self,
        metric_name: str | None,
        labels: dict[str, str] | None,
    ) -> MetricQueryResult:
        """Query current metric values."""
        ...

    async def reset_metrics(self) -> MetricResult:
        """Reset all metrics (TESTING ONLY)."""
        ...
```

**Implementations**:
- `PrometheusMetricsCollector` - Production (Prometheus client)
- `InMemoryMetricsCollector` - Testing (dict-based storage)

---

## Complete Example

```python
from collections.abc import Generator
from dataclasses import dataclass
from uuid import UUID

from effectful import AllEffects, EffectResult, run_program
from effectful.effects.metrics import IncrementCounter, ObserveHistogram
from effectful.domain.metrics_result import MetricRecorded, MetricRecordingFailed
from effectful.observability import (
    MetricsRegistry,
    CounterDefinition,
    HistogramDefinition,
)

# 1. Define metrics registry
APP_METRICS = MetricsRegistry(
    counters=(
        CounterDefinition(
            name="appointments_created_total",
            help_text="Total appointments created",
            label_names=("doctor_specialization", "appointment_type"),
        ),
    ),
    gauges=(),
    histograms=(
        HistogramDefinition(
            name="appointment_duration_seconds",
            help_text="Appointment duration distribution",
            label_names=("doctor_id", "status"),
            buckets=(60, 300, 600, 1800, 3600),  # 1m, 5m, 10m, 30m, 1h
        ),
    ),
    summaries=(),
)

# 2. Effect program with metrics
def create_appointment_with_metrics(
    doctor_id: str,
    specialization: str,
    appointment_type: str,
    duration_seconds: float,
) -> Generator[AllEffects, EffectResult, bool]:
    """Create appointment and record metrics."""

    # Business logic...
    appointment = yield CreateAppointment(
        doctor_id=doctor_id,
        specialization=specialization,
        appointment_type=appointment_type,
    )

    # Record counter metric
    counter_result = yield IncrementCounter(
        metric_name="appointments_created_total",
        labels={
            "doctor_specialization": specialization,
            "appointment_type": appointment_type,
        },
        value=1.0,
    )

    # Record histogram metric
    histogram_result = yield ObserveHistogram(
        metric_name="appointment_duration_seconds",
        labels={
            "doctor_id": doctor_id,
            "status": "completed",
        },
        value=duration_seconds,
    )

    # Pattern match results
    match (counter_result, histogram_result):
        case (MetricRecorded(), MetricRecorded()):
            return True
        case (MetricRecordingFailed(reason=r1), _):
            print(f"Counter failed: {r1}")
            return False
        case (_, MetricRecordingFailed(reason=r2)):
            print(f"Histogram failed: {r2}")
            return False

# 3. Execute program
async def main() -> None:
    result = await run_program(
        create_appointment_with_metrics(
            doctor_id="d123",
            specialization="cardiology",
            appointment_type="consultation",
            duration_seconds=1200.0,  # 20 minutes
        ),
        interpreter=composite_interpreter,
    )

    match result:
        case Ok(success):
            print(f"Success: {success}")
        case Err(error):
            print(f"Error: {error}")
```

---

## Cross-References

> **Core Doctrine**: For observability architecture, see [observability_doctrine.md](../engineering/observability.md)

> **Core Doctrine**: For metric naming standards, see [monitoring_and_alerting.md](../engineering/monitoring_and_alerting.md#monitoring-standards)

> **Core Doctrine**: For alert rules, see [monitoring_and_alerting.md](../engineering/monitoring_and_alerting.md#alerting-policy)

---

## See Also

- [Metrics Quickstart](../tutorials/11_metrics_quickstart.md) - Get started in 15 minutes
- [Metric Types Guide](../tutorials/12_metric_types_guide.md) - When to use each metric type
- [Prometheus Setup](../tutorials/13_prometheus_setup.md) - Docker integration
- [Testing Guide](../tutorials/04_testing_guide.md) - Testing metrics effects

---

**Status**: API Reference for metrics effect system
**Last Updated**: 2025-01-28
