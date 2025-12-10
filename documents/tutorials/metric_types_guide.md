# Metric Types Guide

**Status**: Authoritative source  
**Supersedes**: none  
**Referenced by**: documents/readme.md

> **Purpose**: Guide for choosing the right Prometheus metric type for effectful applications.

**Choose the right metric type for your use case.**

> **Core Doctrine**: For complete metrics philosophy, see [observability.md](../engineering/observability.md)

> **Tutorial**: For quickstart, see [metrics_quickstart.md](./metrics_quickstart.md)

---

## Prerequisites

- Docker workflow running; commands executed via `docker compose ... exec effectful`.
- Completed [Tutorial 11: Metrics Quickstart](metrics_quickstart.md).
- Familiar with observability philosophy in [observability.md](../engineering/observability.md).

## Learning Objectives

- Choose the correct Prometheus metric type for common scenarios.
- Apply decision criteria to avoid cardinality pitfalls and misused summaries.
- Reference practical patterns and examples for counters, gauges, histograms, and summaries.

## Step 1: Overview

Prometheus provides 4 metric types, each optimized for different use cases:

| Type | Purpose | Example Use Cases | Aggregation |
|------|---------|-------------------|-------------|
| **Counter** | Monotonically increasing count | Requests, errors, tasks completed | `rate()`, `increase()` |
| **Gauge** | Point-in-time value (up/down) | Memory usage, queue depth, active connections | `avg()`, `min()`, `max()` |
| **Histogram** | Distribution with buckets | Request duration, response size | `histogram_quantile()` |
| **Summary** | Distribution with quantiles | Similar to histogram (client-side) | Limited aggregation |

**TL;DR**: Use Counter for counts, Gauge for current values, Histogram for distributions. Avoid Summary.

---

## Step 2: Decision tree

```text
# file: diagrams/metric_type_decision_tree.txt
┌─ Measuring something that increases over time?
│  └─ YES → Counter (requests_total, errors_total)
│
├─ Measuring current value (can increase or decrease)?
│  └─ YES → Gauge (active_connections, queue_depth)
│
├─ Measuring distribution (latency, size)?
│  ├─ Need server-side quantiles? → Histogram (request_duration_seconds)
│  └─ Need exact client-side quantiles? → Summary (rare, use histogram instead)
│
└─ Not sure? → Start with Counter or Gauge
```

---

## Step 3: Counter (monotonically increasing values)

### When to Use

**Use Counter for**:
- ✅ Total requests received
- ✅ Total errors encountered
- ✅ Total tasks processed
- ✅ Total bytes sent/received
- ✅ Total database queries executed

**Do NOT use Counter for**:
- ❌ Current temperature (use Gauge)
- ❌ Active connections (use Gauge)
- ❌ Request duration (use Histogram)
- ❌ Values that can decrease (use Gauge)

### Characteristics

- **Starts at 0** on application start
- **Only increases** (never decreases)
- **Resets to 0** on application restart
- **Aggregated with `rate()`** to get per-second rates

### Example

```python
from effectful.effects.metrics import IncrementCounter
from effectful.observability import CounterDefinition, MetricsRegistry

# Registry definition
APP_METRICS = MetricsRegistry(
    counters=(
        CounterDefinition(
            name="http_requests_total",
            help_text="Total HTTP requests received",
            label_names=("method", "endpoint", "status"),
        ),
    ),
    gauges=(),
    histograms=(),
    summaries=(),
)

# Effect program
def handle_request(
    method: str,
    endpoint: str,
    status: int,
) -> Generator[AllEffects, EffectResult, None]:
    """Handle HTTP request and increment counter."""

    # Process request...
    yield ProcessRequest(method=method, endpoint=endpoint)

    # Increment counter
    yield IncrementCounter(
        metric_name="http_requests_total",
        labels={
            "method": method,
            "endpoint": endpoint,
            "status": str(status),
        },
        value=1.0,
    )
```

### PromQL Queries

```promql
# file: examples/12_metric_types_guide.promql
# Request rate per second (last 5 minutes)
rate(http_requests_total[5m])

# Total requests in last hour
increase(http_requests_total[1h])

# Error rate (status 5xx)
sum(rate(http_requests_total{status=~"5.."}[5m]))
/
sum(rate(http_requests_total[5m]))
```

### Best Practices

**✅ DO**:
- Name with `_total` suffix
- Increment by constant amounts (usually 1.0)
- Use for event counts

**❌ DON'T**:
- Decrement counters
- Set counter to arbitrary value (use Gauge)
- Use counter for current state (use Gauge)

---

## Step 4: Gauge (current value, up or down)

### When to Use

**Use Gauge for**:
- ✅ Current memory usage
- ✅ Active database connections
- ✅ Queue depth
- ✅ Temperature
- ✅ Number of goroutines/threads
- ✅ In-flight requests

**Do NOT use Gauge for**:
- ❌ Total requests (use Counter)
- ❌ Request duration distribution (use Histogram)
- ❌ Monotonically increasing values (use Counter)

### Characteristics

- **Can increase or decrease**
- **Represents current value** at time of observation
- **No rate calculation** (already a point-in-time value)
- **Aggregated with `avg()`, `min()`, `max()`**

### Example

```python
from effectful.effects.metrics import RecordGauge
from effectful.observability import GaugeDefinition, MetricsRegistry

# Registry definition
APP_METRICS = MetricsRegistry(
    counters=(),
    gauges=(
        GaugeDefinition(
            name="websocket_connections_active",
            help_text="Current active WebSocket connections",
            label_names=("server_id",),
        ),
        GaugeDefinition(
            name="database_connections_active",
            help_text="Current active database connections",
            label_names=("pool_name",),
        ),
    ),
    histograms=(),
    summaries=(),
)

# Effect program - increment gauge
def on_websocket_connect(
    server_id: str,
    current_count: int,
) -> Generator[AllEffects, EffectResult, None]:
    """Update gauge when WebSocket connects."""

    yield RecordGauge(
        metric_name="websocket_connections_active",
        labels={"server_id": server_id},
        value=float(current_count + 1),
    )

# Effect program - decrement gauge
def on_websocket_disconnect(
    server_id: str,
    current_count: int,
) -> Generator[AllEffects, EffectResult, None]:
    """Update gauge when WebSocket disconnects."""

    yield RecordGauge(
        metric_name="websocket_connections_active",
        labels={"server_id": server_id},
        value=float(current_count - 1),
    )
```

### PromQL Queries

```promql
# file: examples/12_metric_types_guide.promql
# Current value
websocket_connections_active

# Average over last 5 minutes
avg_over_time(websocket_connections_active[5m])

# Maximum over last hour
max_over_time(websocket_connections_active[1h])

# Alert on high connections
websocket_connections_active > 1000
```

### Best Practices

**✅ DO**:
- Set to current absolute value
- Use for state that can increase or decrease
- Update frequently for accuracy

**❌ DON'T**:
- Use `rate()` on gauges (they're already current values)
- Name with `_total` suffix
- Use for event counts (use Counter)

---

## Step 5: Histogram (distribution with buckets)

### When to Use

**Use Histogram for**:
- ✅ Request/response duration
- ✅ Request/response size
- ✅ Database query latency
- ✅ Effect execution time
- ✅ Any distribution you want quantiles for (p50, p95, p99)

**Do NOT use Histogram for**:
- ❌ Event counts (use Counter)
- ❌ Current values (use Gauge)
- ❌ Values without meaningful distribution

### Characteristics

- **Records observations in buckets**
- **Provides count, sum, and buckets**
- **Server-side quantile calculation** with `histogram_quantile()`
- **Pre-defined buckets** (set at registration time)
- **Low cardinality** (buckets are fixed)

### Example

```python
from effectful.effects.metrics import ObserveHistogram
from effectful.observability import HistogramDefinition, MetricsRegistry
import time

# Registry definition
APP_METRICS = MetricsRegistry(
    counters=(),
    gauges=(),
    histograms=(
        HistogramDefinition(
            name="http_request_duration_seconds",
            help_text="HTTP request duration distribution",
            label_names=("method", "endpoint"),
            buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
        ),
        HistogramDefinition(
            name="database_query_duration_seconds",
            help_text="Database query duration distribution",
            label_names=("query_type",),
            buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0),
        ),
    ),
    summaries=(),
)

# Effect program
def measure_request_duration(
    method: str,
    endpoint: str,
) -> Generator[AllEffects, EffectResult, None]:
    """Measure and record request duration."""

    start = time.perf_counter()

    # Execute request
    yield ProcessHTTPRequest(method=method, endpoint=endpoint)

    duration = time.perf_counter() - start

    # Record in histogram
    yield ObserveHistogram(
        metric_name="http_request_duration_seconds",
        labels={"method": method, "endpoint": endpoint},
        value=duration,
    )
```

### Bucket Design

**Good Buckets** (exponential distribution):
```python
buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
# Roughly doubles each step, covers 5ms to 10s
```

**Bad Buckets** (linear distribution):
```python
buckets=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0)
# Poor resolution at extremes
```

**Bucket Guidelines**:
- Cover expected range (p1 to p99+)
- Use exponential distribution (~2x each step)
- Include SLO thresholds (e.g., 0.1s, 0.5s, 1.0s)
- Typical range: 7-15 buckets

### PromQL Queries

```promql
# file: examples/12_metric_types_guide.promql
# p95 latency (95th percentile)
histogram_quantile(0.95,
  sum by (le) (rate(http_request_duration_seconds_bucket[5m]))
)

# p50 latency by endpoint
histogram_quantile(0.5,
  sum by (endpoint, le) (rate(http_request_duration_seconds_bucket[5m]))
)

# Average duration
rate(http_request_duration_seconds_sum[5m])
/
rate(http_request_duration_seconds_count[5m])

# Requests slower than 1s
sum(rate(http_request_duration_seconds_bucket{le="1.0"}[5m]))
```

### Prometheus Output

```text
# file: examples/12_metric_types_histogram_output.txt
http_request_duration_seconds_bucket{method="GET",endpoint="/api/users",le="0.005"} 24
http_request_duration_seconds_bucket{method="GET",endpoint="/api/users",le="0.01"} 78
http_request_duration_seconds_bucket{method="GET",endpoint="/api/users",le="0.025"} 156
http_request_duration_seconds_bucket{method="GET",endpoint="/api/users",le="0.05"} 234
http_request_duration_seconds_bucket{method="GET",endpoint="/api/users",le="+Inf"} 250
http_request_duration_seconds_sum{method="GET",endpoint="/api/users"} 3.14
http_request_duration_seconds_count{method="GET",endpoint="/api/users"} 250
```

### Best Practices

**✅ DO**:
- Use for latency/duration measurements
- Name with `_seconds` or `_bytes` suffix
- Design buckets to cover expected range
- Use `histogram_quantile()` for percentiles

**❌ DON'T**:
- Use too many buckets (>15 usually wasteful)
- Use linear buckets
- Forget `+Inf` bucket (added automatically)

---

## Step 6: Summary (distribution with quantiles, rare)

### When to Use

**Use Summary for**:
- ⚠️ **Rarely used** - prefer Histogram instead
- ⚠️ When you need exact quantiles (not approximate)
- ⚠️ When aggregation across labels is not needed

**Prefer Histogram because**:
- ✅ Server-side aggregation possible
- ✅ Lower cardinality
- ✅ Can calculate any quantile later (not fixed at registration)
- ✅ Works with `histogram_quantile()` function

### Characteristics

- **Client-side quantile calculation**
- **Streaming quantiles** (φ-quantiles)
- **Fixed quantiles** (set at registration time)
- **High cardinality** (timeseries per label combination)
- **Cannot aggregate** across labels

### Example

```python
from effectful.effects.metrics import RecordSummary
from effectful.observability import SummaryDefinition, MetricsRegistry

# Registry definition (rare - prefer Histogram)
APP_METRICS = MetricsRegistry(
    counters=(),
    gauges=(),
    histograms=(),
    summaries=(
        SummaryDefinition(
            name="response_size_bytes",
            help_text="HTTP response size summary",
            label_names=("endpoint",),
            quantiles=(0.5, 0.9, 0.95, 0.99),  # Fixed at registration!
        ),
    ),
)

# Effect program
def record_response_size(
    endpoint: str,
    size_bytes: int,
) -> Generator[AllEffects, EffectResult, None]:
    """Record response size in summary."""

    yield RecordSummary(
        metric_name="response_size_bytes",
        labels={"endpoint": endpoint},
        value=float(size_bytes),
    )
```

### Prometheus Output

```text
# file: examples/12_metric_types_summary_output.txt
response_size_bytes{endpoint="/api/users",quantile="0.5"} 1234
response_size_bytes{endpoint="/api/users",quantile="0.9"} 4567
response_size_bytes{endpoint="/api/users",quantile="0.95"} 6789
response_size_bytes{endpoint="/api/users",quantile="0.99"} 9012
response_size_bytes_sum{endpoint="/api/users"} 125000
response_size_bytes_count{endpoint="/api/users"} 100
```

### Histogram vs Summary Comparison

| Aspect | Histogram | Summary |
|--------|-----------|---------|
| **Quantile calculation** | Server-side (PromQL) | Client-side (library) |
| **Accuracy** | Approximate | Exact |
| **Aggregation** | ✅ Possible | ❌ Not possible |
| **Cardinality** | Low (fixed buckets) | High (per label) |
| **PromQL flexibility** | ✅ Any quantile | ❌ Fixed quantiles |
| **Recommendation** | ✅ Prefer | ⚠️ Avoid |

**Recommendation**: **Always use Histogram** unless you have a specific reason for Summary.

---

## Step 7: Real-world examples

### Example 1: HealthHub Appointments

```python
from effectful.observability import MetricsRegistry, CounterDefinition, HistogramDefinition, GaugeDefinition

HEALTHHUB_METRICS = MetricsRegistry(
    counters=(
        # Total appointments created
        CounterDefinition(
            name="appointments_created_total",
            help_text="Total appointments created",
            label_names=("doctor_specialization", "appointment_type"),
        ),
        # Total prescriptions issued
        CounterDefinition(
            name="prescriptions_issued_total",
            help_text="Total prescriptions issued",
            label_names=("doctor_id", "medication_type"),
        ),
        # Total HIPAA audit events
        CounterDefinition(
            name="hipaa_audit_events_total",
            help_text="Total HIPAA audit events",
            label_names=("event_type", "authorization_result"),
        ),
    ),
    gauges=(
        # Unreviewed critical lab results
        GaugeDefinition(
            name="unreviewed_critical_results_current",
            help_text="Current unreviewed critical lab results",
            label_names=("age_bucket",),  # 0_1h, 1_6h, 6_24h, 24h_plus
        ),
        # Active WebSocket connections
        GaugeDefinition(
            name="active_websocket_connections",
            help_text="Current active WebSocket connections",
            label_names=("server_id",),
        ),
    ),
    histograms=(
        # Appointment duration
        HistogramDefinition(
            name="appointment_duration_seconds",
            help_text="Appointment duration distribution",
            label_names=("doctor_id", "status"),
            buckets=(60, 300, 600, 1800, 3600),  # 1m, 5m, 10m, 30m, 1h
        ),
        # Database query duration
        HistogramDefinition(
            name="database_query_duration_seconds",
            help_text="Database query duration",
            label_names=("query_type",),
            buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0),
        ),
    ),
    summaries=(),
)
```

### Example 2: E-commerce System

```python
ECOMMERCE_METRICS = MetricsRegistry(
    counters=(
        # Orders
        CounterDefinition(
            name="orders_total",
            help_text="Total orders processed",
            label_names=("status", "payment_method"),
        ),
        # Revenue (in cents)
        CounterDefinition(
            name="revenue_cents_total",
            help_text="Total revenue in cents",
            label_names=("product_category",),
        ),
        # Errors
        CounterDefinition(
            name="payment_errors_total",
            help_text="Total payment errors",
            label_names=("error_type",),
        ),
    ),
    gauges=(
        # Shopping cart items
        GaugeDefinition(
            name="shopping_cart_items",
            help_text="Items in shopping carts",
            label_names=("user_tier",),
        ),
        # Inventory
        GaugeDefinition(
            name="inventory_items_available",
            help_text="Available inventory items",
            label_names=("product_id", "warehouse"),
        ),
    ),
    histograms=(
        # Checkout duration
        HistogramDefinition(
            name="checkout_duration_seconds",
            help_text="Checkout process duration",
            label_names=("payment_method",),
            buckets=(1, 5, 10, 30, 60, 120),
        ),
        # Order value
        HistogramDefinition(
            name="order_value_dollars",
            help_text="Order value distribution",
            label_names=("product_category",),
            buckets=(10, 25, 50, 100, 250, 500, 1000),
        ),
    ),
    summaries=(),
)
```

---

## Step 8: Common patterns

### Pattern 1: Counter + Histogram (Request Tracking)

Track both count and duration for requests:

```python
def handle_api_request(
    endpoint: str,
) -> Generator[AllEffects, EffectResult, None]:
    """Handle API request with count and duration metrics."""

    start = time.perf_counter()

    # Execute request
    result = yield ProcessRequest(endpoint=endpoint)

    duration = time.perf_counter() - start
    status = "success" if isinstance(result, Success) else "error"

    # Counter: total requests
    yield IncrementCounter(
        metric_name="api_requests_total",
        labels={"endpoint": endpoint, "status": status},
        value=1.0,
    )

    # Histogram: request duration
    yield ObserveHistogram(
        metric_name="api_request_duration_seconds",
        labels={"endpoint": endpoint},
        value=duration,
    )
```

### Pattern 2: Gauge Updates (Resource Tracking)

Update gauge when resource count changes:

```python
def update_connection_gauge(
    pool_name: str,
    connections: int,
) -> Generator[AllEffects, EffectResult, None]:
    """Update connection gauge to current value."""

    yield RecordGauge(
        metric_name="database_connections_active",
        labels={"pool_name": pool_name},
        value=float(connections),
    )

# Call on connect
yield from update_connection_gauge("main", current_connections + 1)

# Call on disconnect
yield from update_connection_gauge("main", current_connections - 1)
```

### Pattern 3: Error Rate (Counter Labels)

Use labels to separate success/error counts:

```python
def track_operation_result(
    operation: str,
    result: OperationResult,
) -> Generator[AllEffects, EffectResult, None]:
    """Track operation success/failure."""

    status = "success" if isinstance(result, Success) else "error"
    error_type = result.error_type if isinstance(result, Failure) else "none"

    yield IncrementCounter(
        metric_name="operations_total",
        labels={
            "operation": operation,
            "status": status,
            "error_type": error_type,
        },
        value=1.0,
    )
```

**PromQL for error rate**:
```promql
# file: examples/12_metric_types_guide.promql
sum(rate(operations_total{status="error"}[5m]))
/
sum(rate(operations_total[5m]))
```

---

## Step 9: Quick reference card

### Counter

```python
# Define
CounterDefinition(name="events_total", help_text="...", label_names=(...))

# Use
yield IncrementCounter(metric_name="events_total", labels={...}, value=1.0)

# Query
rate(events_total[5m])
increase(events_total[1h])
```

### Gauge

```python
# Define
GaugeDefinition(name="active_connections", help_text="...", label_names=(...))

# Use
yield RecordGauge(metric_name="active_connections", labels={...}, value=42.0)

# Query
active_connections
avg_over_time(active_connections[5m])
```

### Histogram

```python
# Define
HistogramDefinition(
    name="duration_seconds",
    help_text="...",
    label_names=(...),
    buckets=(0.1, 0.5, 1.0, 5.0)
)

# Use
yield ObserveHistogram(metric_name="duration_seconds", labels={...}, value=0.42)

# Query
histogram_quantile(0.95, rate(duration_seconds_bucket[5m]))
```

### Summary (Rare)

```python
# Define
SummaryDefinition(
    name="size_bytes",
    help_text="...",
    label_names=(...),
    quantiles=(0.5, 0.95, 0.99)
)

# Use
yield RecordSummary(metric_name="size_bytes", labels={...}, value=1234.0)

# Query
size_bytes{quantile="0.95"}
```

---

## Summary

- Selected the right metric type using explicit criteria and a decision tree.
- Applied guardrails for counters, gauges, histograms, and rare summaries to avoid misuse.
- Collected quick references and examples for implementing and querying each type.

## Next Steps

- Wire metrics into your application with [Metrics Quickstart](metrics_quickstart.md) if you have not already.
- Add alerting semantics for the chosen metrics in [Alert Rules](alert_rules.md).
- Review monitoring policy in [Monitoring & Alerting](../engineering/monitoring_and_alerting.md).

---

## See Also

- [Metrics Quickstart](./metrics_quickstart.md) - Getting started guide
- [Prometheus Setup](./prometheus_setup.md) - Docker integration
- [Alert Rules](./alert_rules.md) - Creating alerts
- [Observability](../engineering/observability.md) - Metrics philosophy

---

## Cross-References
- [Documentation Standards](../documentation_standards.md)
- [Engineering Standards](../engineering/README.md)
