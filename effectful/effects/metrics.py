"""Metrics effect DSL.

This module defines effects for metrics operations:
- IncrementCounter: Increment monotonic counter
- RecordGauge: Set gauge to specific value
- ObserveHistogram: Record value in histogram distribution
- RecordSummary: Record value in summary (streaming quantiles)
- QueryMetrics: Retrieve current metric values (debugging/testing)
- ResetMetrics: Clear all metrics (TESTING ONLY)

All effects are immutable (frozen dataclasses) and return ADT types
instead of raising exceptions.

Example:
    >>> def track_request() -> Generator[AllEffects, EffectResult, None]:
    ...     result = yield IncrementCounter(
    ...         metric_name="requests_total",
    ...         labels={"method": "GET", "status": "200"},
    ...         value=1.0,
    ...     )
    ...     assert isinstance(result, MetricRecorded)
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class IncrementCounter:
    """Effect: Increment counter metric.

    Counters are monotonically increasing values that track cumulative totals.
    Cannot decrease. Reset only via ResetMetrics (testing only).

    Attributes:
        metric_name: Name of counter metric (must be registered)
        labels: Label key-value pairs (must match registered label_names)
        value: Amount to increment by (default: 1.0, must be >= 0)

    Returns:
        MetricRecorded: Success with timestamp
        MetricRecordingFailed: Validation or collector error
    """

    metric_name: str
    labels: dict[str, str]
    value: float = 1.0


@dataclass(frozen=True)
class RecordGauge:
    """Effect: Set gauge metric to specific value.

    Gauges are point-in-time values that can go up or down.
    Last value wins (no accumulation).

    Attributes:
        metric_name: Name of gauge metric (must be registered)
        labels: Label key-value pairs (must match registered label_names)
        value: Value to set gauge to (can be positive, negative, or zero)

    Returns:
        MetricRecorded: Success with timestamp
        MetricRecordingFailed: Validation or collector error
    """

    metric_name: str
    labels: dict[str, str]
    value: float


@dataclass(frozen=True)
class ObserveHistogram:
    """Effect: Record value in histogram distribution.

    Histograms track distributions of values across configured buckets.
    Used for latencies, sizes, durations.

    Attributes:
        metric_name: Name of histogram metric (must be registered)
        labels: Label key-value pairs (must match registered label_names)
        value: Value to observe (must be >= 0 for most use cases)

    Returns:
        MetricRecorded: Success with timestamp
        MetricRecordingFailed: Validation or collector error
    """

    metric_name: str
    labels: dict[str, str]
    value: float


@dataclass(frozen=True)
class RecordSummary:
    """Effect: Record value in summary (streaming quantiles).

    Summaries track distributions with client-side quantile calculation.
    Less common than histograms - use histograms unless you specifically
    need streaming quantiles.

    Attributes:
        metric_name: Name of summary metric (must be registered)
        labels: Label key-value pairs (must match registered label_names)
        value: Value to record (must be >= 0 for most use cases)

    Returns:
        MetricRecorded: Success with timestamp
        MetricRecordingFailed: Validation or collector error
    """

    metric_name: str
    labels: dict[str, str]
    value: float


@dataclass(frozen=True)
class QueryMetrics:
    """Effect: Retrieve current metric values.

    Used for debugging, testing, and verification. Production code
    should use Prometheus queries instead.

    Attributes:
        metric_name: Name of metric to query (None = all metrics)
        labels: Label filters (None = all label combinations)

    Returns:
        QuerySuccess: Metrics dict with values
        QueryFailure: Metric not found or collector unavailable
    """

    metric_name: str | None = None
    labels: dict[str, str] | None = None


@dataclass(frozen=True)
class ResetMetrics:
    """Effect: Clear all metrics.

    TESTING ONLY. DO NOT use in production code.
    Used to reset state between test cases for reproducibility.

    Returns:
        MetricRecorded: Success with timestamp
        MetricRecordingFailed: Collector error
    """

    pass


# ADT: Union of all metrics effects using PEP 695 type statement
type MetricsEffect = (
    IncrementCounter | RecordGauge | ObserveHistogram | RecordSummary | QueryMetrics | ResetMetrics
)
