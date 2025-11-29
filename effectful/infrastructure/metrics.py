"""Metrics collector protocol for observability.

This module defines Protocol interface (port) for metrics operations.
Concrete implementations (adapters) like Prometheus or in-memory are provided elsewhere.
Uses ADTs instead of Optional for type safety.

The metrics system supports:
- Counters: Monotonic increasing values (requests, errors)
- Gauges: Point-in-time values (memory usage, active connections)
- Histograms: Distributions with buckets (latencies, sizes)
- Summaries: Distributions with quantiles (response times)
"""

from typing import Protocol

from effectful.domain.metrics_result import MetricQueryResult, MetricResult
from effectful.observability import (
    CounterDefinition,
    GaugeDefinition,
    HistogramDefinition,
    MetricsRegistry,
    SummaryDefinition,
)


class MetricsCollector(Protocol):
    """Protocol for metrics collection and querying."""

    async def register_metrics(self, registry: MetricsRegistry) -> None:
        """Register metric definitions with the collector.

        Must be called before recording any metrics. Idempotent - calling
        multiple times with same registry has no effect.

        Args:
            registry: MetricsRegistry containing all metric definitions
        """
        ...

    async def increment_counter(
        self,
        metric_name: str,
        labels: dict[str, str],
        value: float,
    ) -> MetricResult:
        """Increment counter metric by value.

        Args:
            metric_name: Name of counter metric (must be registered)
            labels: Label key-value pairs (must match registered label_names)
            value: Amount to increment by (must be >= 0)

        Returns:
            MetricRecorded: Success with timestamp
            MetricRecordingFailed: Validation error (unregistered metric,
                invalid labels, negative value) or collector unavailable
        """
        ...

    async def record_gauge(
        self,
        metric_name: str,
        labels: dict[str, str],
        value: float,
    ) -> MetricResult:
        """Set gauge metric to specific value.

        Args:
            metric_name: Name of gauge metric (must be registered)
            labels: Label key-value pairs (must match registered label_names)
            value: Value to set gauge to (can be positive, negative, or zero)

        Returns:
            MetricRecorded: Success with timestamp
            MetricRecordingFailed: Validation error or collector unavailable
        """
        ...

    async def observe_histogram(
        self,
        metric_name: str,
        labels: dict[str, str],
        value: float,
    ) -> MetricResult:
        """Record value in histogram distribution.

        Args:
            metric_name: Name of histogram metric (must be registered)
            labels: Label key-value pairs (must match registered label_names)
            value: Value to observe (must be >= 0 for most use cases)

        Returns:
            MetricRecorded: Success with timestamp
            MetricRecordingFailed: Validation error or collector unavailable
        """
        ...

    async def record_summary(
        self,
        metric_name: str,
        labels: dict[str, str],
        value: float,
    ) -> MetricResult:
        """Record value in summary (streaming quantiles).

        Args:
            metric_name: Name of summary metric (must be registered)
            labels: Label key-value pairs (must match registered label_names)
            value: Value to record (must be >= 0 for most use cases)

        Returns:
            MetricRecorded: Success with timestamp
            MetricRecordingFailed: Validation error or collector unavailable
        """
        ...

    async def query_metrics(
        self,
        metric_name: str | None,
        labels: dict[str, str] | None,
    ) -> MetricQueryResult:
        """Query current metric values.

        Used for debugging, testing, and verification. Production code
        should use Prometheus queries instead.

        Args:
            metric_name: Name of metric to query (None = all metrics)
            labels: Label filters (None = all label combinations)

        Returns:
            QuerySuccess: Dict of metric values with timestamp
            QueryFailure: Metric not found or collector unavailable
        """
        ...

    async def reset_metrics(self) -> MetricResult:
        """Clear all metrics.

        TESTING ONLY. DO NOT use in production code.
        Used to reset state between test cases for reproducibility.

        Returns:
            MetricRecorded: Success with timestamp
            MetricRecordingFailed: Collector error
        """
        ...


__all__ = [
    "MetricsCollector",
]
