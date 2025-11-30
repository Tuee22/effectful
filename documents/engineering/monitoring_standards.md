# Monitoring Standards

**effectful** - Metric naming, labeling, and cardinality standards for Prometheus integration.

This is the Single Source of Truth (SSoT) for effectful monitoring standards, ensuring consistent, maintainable metrics across all applications.

## Overview

Good metrics require discipline. Poor naming leads to confusion, inconsistent labels cause cardinality explosion, and undocumented metrics become technical debt. This doctrine establishes clear standards for all effectful metrics.

**Core Principles:**
1. **Consistency** - All metrics follow the same naming and labeling patterns
2. **Discoverability** - Metric names reveal purpose and subsystem
3. **Cardinality Control** - Label schemas prevent explosion
4. **Self-Documentation** - Registry serves as single source of truth

---

## Naming Conventions

### Metric Name Structure

All effectful metrics follow this format:

```
<namespace>_<subsystem>_<metric>_<unit>
```

**Components:**
- **namespace**: Always `effectful` for framework metrics, `<appname>` for application metrics
- **subsystem**: Major component (e.g., `db`, `cache`, `websocket`, `effect`, `program`)
- **metric**: What is being measured (e.g., `requests`, `duration`, `errors`)
- **unit**: Unit of measurement (e.g., `seconds`, `bytes`, `total`)

**Examples:**

| Metric Name | Namespace | Subsystem | Metric | Unit | Description |
|-------------|-----------|-----------|--------|------|-------------|
| `effectful_db_queries_total` | effectful | db | queries | total | Total database queries |
| `effectful_cache_hits_total` | effectful | cache | hits | total | Total cache hits |
| `effectful_effect_duration_seconds` | effectful | effect | duration | seconds | Effect execution time |
| `healthhub_appointments_created_total` | healthhub | appointments | created | total | HealthHub appointments |

### Base Name Rules

1. **Use lowercase with underscores** (snake_case)
   - ✅ `http_requests_total`
   - ❌ `HttpRequestsTotal`, `http-requests-total`

2. **Use descriptive names**
   - ✅ `appointment_scheduling_duration_seconds`
   - ❌ `appt_sched_dur_sec` (abbreviations unclear)

3. **Include units for numeric values**
   - ✅ `memory_usage_bytes`, `request_duration_seconds`
   - ❌ `memory_usage`, `request_duration` (ambiguous units)

4. **Use `_total` suffix for counters**
   - ✅ `requests_total`, `errors_total`
   - ❌ `requests`, `errors` (type unclear)

5. **Avoid redundant words**
   - ✅ `db_queries_total`
   - ❌ `db_database_queries_total` (redundant "database")

### Unit Conventions

**Time:**
- Use `seconds` (not milliseconds)
- Prometheus best practice for consistency
- Examples: `duration_seconds`, `latency_seconds`, `age_seconds`

**Size:**
- Use `bytes` (not KB, MB, GB)
- Prometheus will convert for display
- Examples: `size_bytes`, `memory_bytes`, `response_bytes`

**Counts:**
- Use `total` suffix for counters
- No suffix for gauges
- Examples: `requests_total` (counter), `active_connections` (gauge)

**Percentages:**
- Use `ratio` (values 0.0-1.0)
- Prometheus will convert to percentage for display
- Examples: `cache_hit_ratio`, `error_ratio`

---

## Label Standards

### Label Naming

Labels use the same snake_case convention as metric names:

```python
# ✅ CORRECT
labels = {
    "doctor_specialization": "cardiology",
    "appointment_status": "confirmed",
    "http_method": "POST",
}

# ❌ INCORRECT
labels = {
    "DoctorSpecialization": "cardiology",  # CamelCase
    "appointment-status": "confirmed",     # kebab-case
    "HttpMethod": "POST",                  # Mixed case
}
```

### Required vs Optional Labels

**Required Labels** (defined in registry):
- All metrics of same type have consistent labels
- Specified in `label_names` tuple
- Validated at runtime

**Example:**

```python
CounterDefinition(
    name="http_requests_total",
    help_text="Total HTTP requests",
    label_names=("method", "endpoint", "status_code"),  # All required
)

# ✅ VALID - All labels provided
yield IncrementCounter(
    metric_name="http_requests_total",
    labels={"method": "POST", "endpoint": "/api/appointments", "status_code": "201"},
    value=1.0,
)

# ❌ INVALID - Missing "status_code" label
yield IncrementCounter(
    metric_name="http_requests_total",
    labels={"method": "POST", "endpoint": "/api/appointments"},
    value=1.0,
)
# Returns: MetricRecordingFailed(reason="invalid_labels")
```

### Label Value Conventions

1. **Use lowercase**
   - ✅ `{"status": "confirmed"}`
   - ❌ `{"status": "CONFIRMED"}`, `{"status": "Confirmed"}`

2. **Use underscores for multi-word values**
   - ✅ `{"status": "in_progress"}`
   - ❌ `{"status": "in-progress"}`, `{"status": "InProgress"}`

3. **Use consistent categorical values**
   - ✅ `{"result": "ok"}`, `{"result": "error"}`
   - ❌ `{"result": "success"}`, `{"result": "failure"}` (inconsistent with Result type)

4. **Avoid high-cardinality values**
   - ✅ `{"user_tier": "premium"}` (bounded: free, basic, premium)
   - ❌ `{"user_id": "12345"}` (unbounded: millions of users)

### Cardinality Limits

**Rule of Thumb**: Total unique label combinations < 10,000 per metric

**Calculation:**

```python
cardinality = product(unique_values_per_label)

# Example 1: GOOD ✅
# labels: method (4) × endpoint (50) × status_code (20)
# cardinality: 4 × 50 × 20 = 4,000 ✅

# Example 2: BAD ❌
# labels: user_id (1M) × session_id (10M)
# cardinality: 1M × 10M = 10 trillion ❌
```

**Warning Signs:**
- User IDs, session IDs, trace IDs as labels
- Timestamps, UUIDs as labels
- Free-form text as labels
- IP addresses as labels (unless internal network)

**Solutions:**
- Use categorical aggregations: `user_id` → `user_tier` (free, premium)
- Use bucketing: `timestamp` → `hour_of_day` (0-23)
- Use prefixes: `trace_id` → `trace_prefix` (first 2 hex chars)

---

## Default Effectful Metrics

When automatic instrumentation is enabled, effectful provides these framework metrics:

### Effect Execution Metrics

**Counter: `effectful_effects_total`**

```python
CounterDefinition(
    name="effectful_effects_total",
    help_text="Total effect executions by type and result",
    label_names=("effect_type", "result"),
)
```

**Labels:**
- `effect_type`: Effect class name (e.g., "GetUserById", "SendText", "IncrementCounter")
- `result`: "ok" (success) or "error" (interpreter error)

**Example Query:**
```promql
# Effect error rate (5m window)
sum(rate(effectful_effects_total{result="error"}[5m]))
/
sum(rate(effectful_effects_total[5m]))
```

---

**Histogram: `effectful_effect_duration_seconds`**

```python
HistogramDefinition(
    name="effectful_effect_duration_seconds",
    help_text="Effect execution duration distribution",
    label_names=("effect_type",),
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)
```

**Labels:**
- `effect_type`: Effect class name

**Example Query:**
```promql
# p95 effect duration by type
histogram_quantile(0.95,
  sum by (effect_type, le) (
    rate(effectful_effect_duration_seconds_bucket[5m])
  )
)
```

---

**Gauge: `effectful_effects_in_progress`**

```python
GaugeDefinition(
    name="effectful_effects_in_progress",
    help_text="Currently executing effects",
    label_names=("effect_type",),
)
```

**Labels:**
- `effect_type`: Effect class name

**Example Query:**
```promql
# Effects currently executing
sum by (effect_type) (effectful_effects_in_progress)
```

### Program Execution Metrics

**Counter: `effectful_programs_total`**

```python
CounterDefinition(
    name="effectful_programs_total",
    help_text="Total program executions by name and result",
    label_names=("program_name", "result"),
)
```

**Labels:**
- `program_name`: Function name (e.g., "schedule_appointment_program")
- `result`: "ok" (completed successfully) or "error" (failed)

**Example Query:**
```promql
# Program error rate by name
sum by (program_name) (rate(effectful_programs_total{result="error"}[5m]))
/
sum by (program_name) (rate(effectful_programs_total[5m]))
```

---

**Histogram: `effectful_program_duration_seconds`**

```python
HistogramDefinition(
    name="effectful_program_duration_seconds",
    help_text="Program execution duration distribution",
    label_names=("program_name",),
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)
```

**Labels:**
- `program_name`: Function name

**Example Query:**
```promql
# p99 program duration
histogram_quantile(0.99,
  sum by (program_name, le) (
    rate(effectful_program_duration_seconds_bucket[5m])
  )
)
```

---

## Application Metrics Patterns

Application metrics track domain-specific business KPIs. Follow these patterns:

### Business Event Counters

Track domain events as counters:

```python
CounterDefinition(
    name="healthhub_appointments_created_total",
    help_text="Total appointments created",
    label_names=("doctor_specialization", "appointment_type", "insurance_provider"),
)
```

**Labels:**
- Use categorical business dimensions
- Keep cardinality product < 10,000
- Example: 30 specializations × 5 types × 10 providers = 1,500 combinations ✅

### State Machine Transitions

Track state transitions:

```python
CounterDefinition(
    name="healthhub_appointment_transitions_total",
    help_text="Appointment status transitions",
    label_names=("from_status", "to_status", "actor_role"),
)
```

**Example Values:**
- `from_status`: "requested", "confirmed", "in_progress", "completed", "cancelled"
- `to_status`: Same values
- `actor_role`: "patient", "doctor", "admin"

**Cardinality**: 5 × 5 × 3 = 75 combinations ✅

### Resource Pool Gauges

Track current resource usage:

```python
GaugeDefinition(
    name="healthhub_unreviewed_critical_results_current",
    help_text="Critical lab results awaiting review",
    label_names=("test_type", "age_bucket"),
)
```

**Labels:**
- `test_type`: Categorical (e.g., "blood_glucose", "cholesterol", "blood_pressure")
- `age_bucket`: Time bucketed (e.g., "0_1h", "1_6h", "6_24h", "24h_plus")

### Duration Histograms

Track operation latencies:

```python
HistogramDefinition(
    name="healthhub_prescription_creation_duration_seconds",
    help_text="Prescription creation duration from request to fulfillment",
    label_names=("doctor_id", "has_interactions"),
    buckets=(1.0, 5.0, 10.0, 30.0, 60.0, 120.0),  # 1s to 2m
)
```

**Labels:**
- `doctor_id`: If < 100 doctors (otherwise use "doctor_tier")
- `has_interactions`: Boolean as string ("true", "false")

---

## Anti-Patterns

### 1. High-Cardinality Labels

```python
# ❌ WRONG - Unbounded cardinality
CounterDefinition(
    name="requests_total",
    label_names=("user_id", "session_id"),  # Millions × Millions = Explosion!
)

# ✅ CORRECT - Bounded cardinality
CounterDefinition(
    name="requests_total",
    label_names=("user_tier", "endpoint"),  # 3 × 50 = 150
)
```

### 2. Timestamps as Labels

```python
# ❌ WRONG - Infinite cardinality
labels = {"timestamp": str(datetime.utcnow())}

# ✅ CORRECT - Use metric timestamp, bucket in label if needed
labels = {"hour_of_day": str(datetime.utcnow().hour)}  # 0-23
```

### 3. Dynamic Metric Names

```python
# ❌ WRONG - Runtime metric creation
metric_name = f"user_{user_id}_requests_total"

# ✅ CORRECT - Static name, dynamic label value
metric_name = "user_requests_total"
labels = {"user_tier": user.tier}  # Categorical
```

### 4. Missing Units

```python
# ❌ WRONG - Ambiguous units
HistogramDefinition(
    name="request_duration",  # Seconds? Milliseconds?
    ...
)

# ✅ CORRECT - Explicit units
HistogramDefinition(
    name="request_duration_seconds",
    ...
)
```

### 5. Inconsistent Naming

```python
# ❌ WRONG - Mixed conventions
counters = (
    CounterDefinition(name="RequestsTotal", ...),       # CamelCase
    CounterDefinition(name="errors-total", ...),        # kebab-case
    CounterDefinition(name="cache_hits", ...),          # Missing _total
)

# ✅ CORRECT - Consistent snake_case with _total
counters = (
    CounterDefinition(name="requests_total", ...),
    CounterDefinition(name="errors_total", ...),
    CounterDefinition(name="cache_hits_total", ...),
)
```

### 6. Boolean Labels with Many Values

```python
# ❌ WRONG - Boolean represented as many values
labels = {"is_critical": "yes"}   # Should be "true"
labels = {"is_critical": "1"}     # Should be "true"
labels = {"is_critical": "Y"}     # Should be "true"

# ✅ CORRECT - Consistent boolean representation
labels = {"is_critical": "true"}  # Or "false"
```

---

## Registry Pattern

### Pre-Registration

All metrics **must** be registered in a frozen registry before use:

```python
from effectful.observability import MetricsRegistry, CounterDefinition

HEALTHHUB_METRICS = MetricsRegistry(
    counters=(
        CounterDefinition(
            name="healthhub_appointments_created_total",
            help_text="Total appointments created",
            label_names=("doctor_specialization", "appointment_type"),
        ),
        CounterDefinition(
            name="healthhub_prescriptions_created_total",
            help_text="Total prescriptions created",
            label_names=("doctor_id", "has_interactions"),
        ),
    ),
    gauges=(),
    histograms=(),
    summaries=(),
)
```

**Benefits:**
1. **Compile-time validation** - MyPy catches typos
2. **Self-documentation** - Registry serves as metrics catalog
3. **Cardinality control** - Label schemas fixed upfront
4. **No runtime errors** - Metrics pre-created at startup

### Validation at Initialization

PrometheusMetricsCollector validates registry on initialization:

```python
from prometheus_client import CollectorRegistry
from effectful.adapters.prometheus_adapter import PrometheusMetricsCollector

# Initialize collector with registry
collector = PrometheusMetricsCollector(
    registry=CollectorRegistry(),
    metrics_registry=HEALTHHUB_METRICS,
)
# All metrics pre-created and validated here
```

**Errors Detected:**
- Duplicate metric names
- Invalid metric names (non-Prometheus-compliant)
- Invalid label names
- Conflicting metric types

### Runtime Validation

When recording metrics, PrometheusMetricsCollector validates:

```python
result = yield IncrementCounter(
    metric_name="healthhub_appointments_created_total",
    labels={"doctor_specialization": "cardiology", "appointment_type": "scheduled"},
    value=1.0,
)

match result:
    case MetricRecorded():
        # Success - metric recorded
        pass
    case MetricRecordingFailed(reason="metric_not_registered"):
        # Metric not in registry
        pass
    case MetricRecordingFailed(reason="invalid_labels"):
        # Labels don't match schema (wrong names or missing labels)
        pass
    case MetricRecordingFailed(reason="cardinality_limit_exceeded"):
        # Too many unique label combinations
        pass
```

---

## Prometheus Best Practices

### Metric Name Prefixes

Use consistent prefixes for namespacing:

```python
# Effectful framework metrics
"effectful_effect_duration_seconds"
"effectful_db_queries_total"

# HealthHub application metrics
"healthhub_appointments_created_total"
"healthhub_prescription_review_duration_seconds"

# Infrastructure metrics (if using exporters)
"postgres_connections_total"
"redis_commands_total"
```

### Help Text Standards

Write clear, concise help text:

```python
# ✅ GOOD
help_text="Total appointments created by doctor specialization and type"

# ❌ BAD
help_text="Appointments"  # Too vague
help_text="This metric tracks the total number of appointments that have been created in the system, broken down by the doctor's specialization field and the appointment type category"  # Too verbose
```

**Format:**
- Start with metric type (implied by definition type)
- Describe what is measured
- Mention key label dimensions
- Keep under 80 characters

### Bucket Selection

Choose histogram buckets based on expected distribution:

```python
# HTTP request latency (milliseconds to seconds)
buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)

# Database query latency (faster)
buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0)

# Background job duration (seconds to minutes)
buckets=(1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0)

# File size (bytes to MB)
buckets=(1024, 10240, 102400, 1048576, 10485760, 104857600)
```

**Guidelines:**
- Cover expected range (p1 to p99)
- Use exponential distribution (roughly double each bucket)
- Add buckets at critical thresholds (e.g., SLO targets)

---

## Cross-References

> **Core Doctrine**: For observability architecture, see [observability_doctrine.md](./observability.md)

> **Core Doctrine**: For type safety patterns, see [type_safety_doctrine.md](./type_safety.md)

---

## See Also

- [Observability](./observability.md) - Metrics philosophy and architecture
- [Alerting](./alerting.md) - Alert rules and severity levels
- [Metrics API Reference](../api/metrics.md) - Complete metrics effects API
- [Metrics Quickstart](../tutorials/11_metrics_quickstart.md) - Getting started guide

---

**Status**: Single Source of Truth (SSoT) for monitoring standards
**Last Updated**: 2025-01-28
