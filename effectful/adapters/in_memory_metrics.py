"""In-memory metrics collector for testing.

This adapter stores metrics in memory using native Python dicts and lists.
Suitable for unit tests and development - NOT for production use.

For production, use PrometheusMetricsCollector which integrates with
real Prometheus infrastructure.

Pattern: Frozen dataclass with mutable dict/list fields. The frozen decorator
prevents field reassignment while allowing mutation of field contents. This
follows the adapter purity doctrine: adapters are at the I/O boundary and may
manage mutable state.
"""

import time
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


@dataclass(frozen=True)
class InMemoryMetricsCollector:
    """In-memory metrics collector for testing.

    Stores all metrics in memory using native Python dicts and lists.
    NOT thread-safe - only use in tests.

    Attributes:
        registry: Currently registered metrics
        _counters: Counter values {metric_name: {label_key: value}}
        _gauges: Gauge values {metric_name: {label_key: value}}
        _histograms: Histogram observations {metric_name: {label_key: [values]}}
        _summaries: Summary observations {metric_name: {label_key: [values]}}
    """

    registry: MetricsRegistry | None = None
    _counters: dict[str, dict[str, float]] = field(default_factory=dict, init=False)
    _gauges: dict[str, dict[str, float]] = field(default_factory=dict, init=False)
    _histograms: dict[str, dict[str, list[float]]] = field(default_factory=dict, init=False)
    _summaries: dict[str, dict[str, list[float]]] = field(default_factory=dict, init=False)

    async def register_metrics(self, registry: MetricsRegistry) -> None:
        """Register metric definitions.

        Idempotent - calling multiple times with same registry has no effect.

        Args:
            registry: MetricsRegistry containing all metric definitions
        """
        # Skip if already registered
        if self.registry is not None:
            return

        # Use object.__setattr__ to set field on frozen dataclass
        object.__setattr__(self, "registry", registry)

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

        # Increment counter using native dicts
        label_key = self._serialize_labels(labels)

        # Get or create inner dict for this metric
        if metric_name not in self._counters:
            self._counters[metric_name] = {}

        # Get or create entry for this label
        if label_key not in self._counters[metric_name]:
            self._counters[metric_name][label_key] = 0.0

        # Increment counter value
        self._counters[metric_name][label_key] += value

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

        # Set gauge value using native dicts
        label_key = self._serialize_labels(labels)

        # Get or create inner dict for this metric
        if metric_name not in self._gauges:
            self._gauges[metric_name] = {}

        # Set gauge value
        self._gauges[metric_name][label_key] = value

        return MetricRecorded(timestamp=time.time())

    async def increment_gauge(
        self,
        metric_name: str,
        labels: dict[str, str],
        value: float = 1.0,
    ) -> MetricResult:
        """Increment gauge metric by value.

        Args:
            metric_name: Name of gauge metric (must be registered)
            labels: Label key-value pairs (must match registered label_names)
            value: Amount to increment by (default: 1.0)

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

        # Increment gauge value using native dicts
        label_key = self._serialize_labels(labels)

        # Get or create inner dict for this metric
        if metric_name not in self._gauges:
            self._gauges[metric_name] = {}

        # Get current value (default to 0 if not exists) and increment
        current_value = self._gauges[metric_name].get(label_key, 0.0)
        self._gauges[metric_name][label_key] = current_value + value

        return MetricRecorded(timestamp=time.time())

    async def decrement_gauge(
        self,
        metric_name: str,
        labels: dict[str, str],
        value: float = 1.0,
    ) -> MetricResult:
        """Decrement gauge metric by value.

        Args:
            metric_name: Name of gauge metric (must be registered)
            labels: Label key-value pairs (must match registered label_names)
            value: Amount to decrement by (default: 1.0)

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

        # Decrement gauge value using native dicts
        label_key = self._serialize_labels(labels)

        # Get or create inner dict for this metric
        if metric_name not in self._gauges:
            self._gauges[metric_name] = {}

        # Get current value (default to 0 if not exists) and decrement
        current_value = self._gauges[metric_name].get(label_key, 0.0)
        self._gauges[metric_name][label_key] = current_value - value

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

        # Record observation using native dicts/lists
        label_key = self._serialize_labels(labels)

        # Get or create inner dict for this metric
        if metric_name not in self._histograms:
            self._histograms[metric_name] = {}

        # Get or create list for this label
        if label_key not in self._histograms[metric_name]:
            self._histograms[metric_name][label_key] = []

        # Append observation to list
        self._histograms[metric_name][label_key].append(value)

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

        # Record observation using native dicts/lists
        label_key = self._serialize_labels(labels)

        # Get or create inner dict for this metric
        if metric_name not in self._summaries:
            self._summaries[metric_name] = {}

        # Get or create list for this label
        if label_key not in self._summaries[metric_name]:
            self._summaries[metric_name][label_key] = []

        # Append observation to list
        self._summaries[metric_name][label_key].append(value)

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
            # Collect all counters using dict comprehension
            counter_metrics = {
                f"{name}{{{label_key}}}": value
                for name, label_values in self._counters.items()
                for label_key, value in label_values.items()
            }

            # Collect all gauges using dict comprehension
            gauge_metrics = {
                f"{name}{{{label_key}}}": value
                for name, label_values in self._gauges.items()
                for label_key, value in label_values.items()
            }

            # Collect histogram counts using dict comprehension
            histogram_metrics = {
                f"{name}_count{{{label_key}}}": float(len(hist_values))
                for name, hist_labels in self._histograms.items()
                for label_key, hist_values in hist_labels.items()
            }

            # Collect summary counts using dict comprehension
            summary_metrics = {
                f"{name}_count{{{label_key}}}": float(len(sum_values))
                for name, sum_labels in self._summaries.items()
                for label_key, sum_values in sum_labels.items()
            }

            # Combine all metrics
            metrics = {**counter_metrics, **gauge_metrics, **histogram_metrics, **summary_metrics}

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
            inner_map = self._counters.get(metric_name, {})
            if label_filter_key:
                value = inner_map.get(label_filter_key, 0.0)
                metrics = {f"{metric_name}{{{label_filter_key}}}": value}
            else:
                metrics = {
                    f"{metric_name}{{{label_key}}}": value for label_key, value in inner_map.items()
                }
            return QuerySuccess(metrics=metrics, timestamp=time.time())

        # Check gauges
        if metric_name in gauge_names:
            inner_map = self._gauges.get(metric_name, {})
            if label_filter_key:
                value = inner_map.get(label_filter_key, 0.0)
                metrics = {f"{metric_name}{{{label_filter_key}}}": value}
            else:
                metrics = {
                    f"{metric_name}{{{label_key}}}": value for label_key, value in inner_map.items()
                }
            return QuerySuccess(metrics=metrics, timestamp=time.time())

        # Check histograms
        if metric_name in histogram_names:
            histogram_map: dict[str, list[float]] = self._histograms.get(metric_name, {})
            if label_filter_key:
                hist_values: list[float] = histogram_map.get(label_filter_key, [])
                metrics = {f"{metric_name}_count{{{label_filter_key}}}": float(len(hist_values))}
            else:
                metrics = {
                    f"{metric_name}_count{{{label_key}}}": float(len(hist_values))
                    for label_key, hist_values in histogram_map.items()
                }
            return QuerySuccess(metrics=metrics, timestamp=time.time())

        # Check summaries
        if metric_name in summary_names:
            summary_map: dict[str, list[float]] = self._summaries.get(metric_name, {})
            if label_filter_key:
                sum_values: list[float] = summary_map.get(label_filter_key, [])
                metrics = {f"{metric_name}_count{{{label_filter_key}}}": float(len(sum_values))}
            else:
                metrics = {
                    f"{metric_name}_count{{{label_key}}}": float(len(sum_values))
                    for label_key, sum_values in summary_map.items()
                }
            return QuerySuccess(metrics=metrics, timestamp=time.time())

        return QueryFailure(reason=f"Metric '{metric_name}' not found")

    async def reset_metrics(self) -> MetricResult:
        """Clear all metrics.

        TESTING ONLY. Used to reset state between test cases.

        Returns:
            MetricRecorded: Success with timestamp
        """
        # Clear all metrics using native dict/list .clear()
        self._counters.clear()
        self._gauges.clear()
        self._histograms.clear()
        self._summaries.clear()
        return MetricRecorded(timestamp=time.time())

    @property
    def counters(self) -> dict[str, dict[str, float]]:
        """Public access to counter metrics (for testing)."""
        return self._counters

    @property
    def gauges(self) -> dict[str, dict[str, float]]:
        """Public access to gauge metrics (for testing)."""
        return self._gauges

    @property
    def histograms(self) -> dict[str, dict[str, list[float]]]:
        """Public access to histogram metrics (for testing)."""
        return self._histograms

    @property
    def summaries(self) -> dict[str, dict[str, list[float]]]:
        """Public access to summary metrics (for testing)."""
        return self._summaries

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
