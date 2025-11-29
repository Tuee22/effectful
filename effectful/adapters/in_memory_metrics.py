"""In-memory metrics collector for testing.

This adapter stores metrics in memory using dictionaries. Suitable for
unit tests and development - NOT for production use.

For production, use PrometheusMetricsCollector which integrates with
real Prometheus infrastructure.
"""

import time
from collections import defaultdict
from dataclasses import dataclass, field

from effectful.domain.metrics_result import (
    MetricQueryResult,
    MetricRecorded,
    MetricRecordingFailed,
    MetricResult,
    QueryFailure,
    QuerySuccess,
)
from effectful.observability import (
    MetricsRegistry,
    validate_histogram_buckets,
    validate_label_names,
    validate_metric_name,
    validate_summary_quantiles,
)


@dataclass
class InMemoryMetricsCollector:
    """In-memory metrics collector for testing.

    Stores all metrics in memory. NOT thread-safe - only use in tests.

    Attributes:
        registry: Currently registered metrics
        counters: Counter values {metric_name: {label_combo: value}}
        gauges: Gauge values {metric_name: {label_combo: value}}
        histograms: Histogram observations {metric_name: {label_combo: [values]}}
        summaries: Summary observations {metric_name: {label_combo: [values]}}
    """

    registry: MetricsRegistry | None = None
    counters: dict[str, dict[str, float]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(float))
    )
    gauges: dict[str, dict[str, float]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(float))
    )
    histograms: dict[str, dict[str, list[float]]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(list))
    )
    summaries: dict[str, dict[str, list[float]]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(list))
    )

    async def register_metrics(self, registry: MetricsRegistry) -> None:
        """Register metric definitions.

        Idempotent - calling multiple times with same registry has no effect.

        Args:
            registry: MetricsRegistry containing all metric definitions
        """
        self.registry = registry

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
            MetricRecordingFailed: Validation error or unregistered metric
        """
        # Validate registry exists
        if self.registry is None:
            return MetricRecordingFailed(
                reason="No metrics registered - call register_metrics() first"
            )

        # Validate value is non-negative
        if value < 0:
            return MetricRecordingFailed(reason=f"Counter value must be >= 0, got {value}")

        # Validate metric is registered
        counter_names = tuple(c.name for c in self.registry.counters)
        if metric_name not in counter_names:
            return MetricRecordingFailed(
                reason=f"Counter '{metric_name}' not registered. "
                f"Registered counters: {counter_names}"
            )

        # Get counter definition
        counter_def = next((c for c in self.registry.counters if c.name == metric_name))

        # Validate labels match definition
        if set(labels.keys()) != set(counter_def.label_names):
            return MetricRecordingFailed(
                reason=f"Labels {set(labels.keys())} don't match "
                f"registered label_names {set(counter_def.label_names)}"
            )

        # Increment counter
        label_key = self._serialize_labels(labels)
        self.counters[metric_name][label_key] += value
        return MetricRecorded(timestamp=time.time())

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
            MetricRecordingFailed: Validation error or unregistered metric
        """
        # Validate registry exists
        if self.registry is None:
            return MetricRecordingFailed(
                reason="No metrics registered - call register_metrics() first"
            )

        # Validate metric is registered
        gauge_names = tuple(g.name for g in self.registry.gauges)
        if metric_name not in gauge_names:
            return MetricRecordingFailed(
                reason=f"Gauge '{metric_name}' not registered. " f"Registered gauges: {gauge_names}"
            )

        # Get gauge definition
        gauge_def = next((g for g in self.registry.gauges if g.name == metric_name))

        # Validate labels match definition
        if set(labels.keys()) != set(gauge_def.label_names):
            return MetricRecordingFailed(
                reason=f"Labels {set(labels.keys())} don't match "
                f"registered label_names {set(gauge_def.label_names)}"
            )

        # Set gauge value
        label_key = self._serialize_labels(labels)
        self.gauges[metric_name][label_key] = value
        return MetricRecorded(timestamp=time.time())

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
            MetricRecordingFailed: Validation error or unregistered metric
        """
        # Validate registry exists
        if self.registry is None:
            return MetricRecordingFailed(
                reason="No metrics registered - call register_metrics() first"
            )

        # Validate metric is registered
        histogram_names = tuple(h.name for h in self.registry.histograms)
        if metric_name not in histogram_names:
            return MetricRecordingFailed(
                reason=f"Histogram '{metric_name}' not registered. "
                f"Registered histograms: {histogram_names}"
            )

        # Get histogram definition
        histogram_def = next((h for h in self.registry.histograms if h.name == metric_name))

        # Validate labels match definition
        if set(labels.keys()) != set(histogram_def.label_names):
            return MetricRecordingFailed(
                reason=f"Labels {set(labels.keys())} don't match "
                f"registered label_names {set(histogram_def.label_names)}"
            )

        # Record observation
        label_key = self._serialize_labels(labels)
        self.histograms[metric_name][label_key].append(value)
        return MetricRecorded(timestamp=time.time())

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
            MetricRecordingFailed: Validation error or unregistered metric
        """
        # Validate registry exists
        if self.registry is None:
            return MetricRecordingFailed(
                reason="No metrics registered - call register_metrics() first"
            )

        # Validate metric is registered
        summary_names = tuple(s.name for s in self.registry.summaries)
        if metric_name not in summary_names:
            return MetricRecordingFailed(
                reason=f"Summary '{metric_name}' not registered. "
                f"Registered summaries: {summary_names}"
            )

        # Get summary definition
        summary_def = next((s for s in self.registry.summaries if s.name == metric_name))

        # Validate labels match definition
        if set(labels.keys()) != set(summary_def.label_names):
            return MetricRecordingFailed(
                reason=f"Labels {set(labels.keys())} don't match "
                f"registered label_names {set(summary_def.label_names)}"
            )

        # Record observation
        label_key = self._serialize_labels(labels)
        self.summaries[metric_name][label_key].append(value)
        return MetricRecorded(timestamp=time.time())

    async def query_metrics(
        self,
        metric_name: str | None,
        labels: dict[str, str] | None,
    ) -> MetricQueryResult:
        """Query current metric values.

        Args:
            metric_name: Name of metric to query (None = all metrics)
            labels: Label filters (None = all label combinations)

        Returns:
            QuerySuccess: Dict of metric values with timestamp
            QueryFailure: Metric not found or no metrics registered
        """
        if self.registry is None:
            return QueryFailure(reason="No metrics registered - call register_metrics() first")

        metrics: dict[str, float] = {}

        # Query all metrics if metric_name is None
        if metric_name is None:
            # Collect all counters
            for name, label_values in self.counters.items():
                for label_key, value in label_values.items():
                    key = f"{name}{{{label_key}}}"
                    metrics[key] = value

            # Collect all gauges
            for name, label_values in self.gauges.items():
                for label_key, value in label_values.items():
                    key = f"{name}{{{label_key}}}"
                    metrics[key] = value

            # Collect histogram counts
            for name, hist_labels in self.histograms.items():
                for label_key, hist_values in hist_labels.items():
                    key = f"{name}_count{{{label_key}}}"
                    metrics[key] = float(len(hist_values))

            # Collect summary counts
            for name, sum_labels in self.summaries.items():
                for label_key, sum_values in sum_labels.items():
                    key = f"{name}_count{{{label_key}}}"
                    metrics[key] = float(len(sum_values))

            return QuerySuccess(metrics=metrics, timestamp=time.time())

        # Query specific metric
        label_filter_key = self._serialize_labels(labels) if labels else None

        # Check if metric is registered
        counter_names = tuple(c.name for c in self.registry.counters)
        gauge_names = tuple(g.name for g in self.registry.gauges)
        histogram_names = tuple(h.name for h in self.registry.histograms)
        summary_names = tuple(s.name for s in self.registry.summaries)

        # Check counters
        if metric_name in counter_names:
            if label_filter_key:
                value = self.counters[metric_name].get(label_filter_key, 0.0)
                metrics[f"{metric_name}{{{label_filter_key}}}"] = value
            else:
                for label_key, value in self.counters[metric_name].items():
                    metrics[f"{metric_name}{{{label_key}}}"] = value
            return QuerySuccess(metrics=metrics, timestamp=time.time())

        # Check gauges
        if metric_name in gauge_names:
            if label_filter_key:
                value = self.gauges[metric_name].get(label_filter_key, 0.0)
                metrics[f"{metric_name}{{{label_filter_key}}}"] = value
            else:
                for label_key, value in self.gauges[metric_name].items():
                    metrics[f"{metric_name}{{{label_key}}}"] = value
            return QuerySuccess(metrics=metrics, timestamp=time.time())

        # Check histograms
        if metric_name in histogram_names:
            if label_filter_key:
                hist_values = self.histograms[metric_name].get(label_filter_key, [])
                metrics[f"{metric_name}_count{{{label_filter_key}}}"] = float(len(hist_values))
            else:
                for label_key, hist_values in self.histograms[metric_name].items():
                    metrics[f"{metric_name}_count{{{label_key}}}"] = float(len(hist_values))
            return QuerySuccess(metrics=metrics, timestamp=time.time())

        # Check summaries
        if metric_name in summary_names:
            if label_filter_key:
                sum_values = self.summaries[metric_name].get(label_filter_key, [])
                metrics[f"{metric_name}_count{{{label_filter_key}}}"] = float(len(sum_values))
            else:
                for label_key, sum_values in self.summaries[metric_name].items():
                    metrics[f"{metric_name}_count{{{label_key}}}"] = float(len(sum_values))
            return QuerySuccess(metrics=metrics, timestamp=time.time())

        return QueryFailure(reason=f"Metric '{metric_name}' not found")

    async def reset_metrics(self) -> MetricResult:
        """Clear all metrics.

        TESTING ONLY. Used to reset state between test cases.

        Returns:
            MetricRecorded: Success with timestamp
        """
        self.counters.clear()
        self.gauges.clear()
        self.histograms.clear()
        self.summaries.clear()
        return MetricRecorded(timestamp=time.time())

    def _serialize_labels(self, labels: dict[str, str]) -> str:
        """Serialize labels dict to string for dict keys.

        Args:
            labels: Label key-value pairs

        Returns:
            Sorted, comma-separated key=value pairs
        """
        if not labels:
            return ""
        # Sort by key for consistent ordering
        sorted_labels = sorted(labels.items())
        return ",".join(f"{k}={v}" for k, v in sorted_labels)


__all__ = ["InMemoryMetricsCollector"]
