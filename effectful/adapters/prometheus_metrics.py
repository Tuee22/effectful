"""Prometheus metrics collector for production use.

This adapter integrates with the official prometheus-client library,
storing metrics in Prometheus's global registry for scraping.

For testing, use InMemoryMetricsCollector which doesn't require
Prometheus infrastructure.
"""

import time
from dataclasses import dataclass, field

from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    Summary,
)

from effectful.domain.metrics_result import (
    MetricQueryResult,
    MetricRecorded,
    MetricRecordingFailed,
    MetricResult,
    QueryFailure,
    QuerySuccess,
)
from effectful.observability import MetricsRegistry


@dataclass(frozen=True)
class PrometheusMetricsCollector:
    """Prometheus metrics collector for production use.

    Integrates with prometheus_client to expose metrics for scraping.
    Thread-safe - safe to use in production with multiple workers.

    Attributes:
        registry: Prometheus CollectorRegistry (defaults to global REGISTRY)
        _metrics_registry: Currently registered metric definitions
        _counters: Prometheus Counter objects {metric_name: Counter}
        _gauges: Prometheus Gauge objects {metric_name: Gauge}
        _histograms: Prometheus Histogram objects {metric_name: Histogram}
        _summaries: Prometheus Summary objects {metric_name: Summary}
    """

    registry: CollectorRegistry | None = None
    _metrics_registry: MetricsRegistry | None = field(default=None, init=False)
    _counters: dict[str, Counter] = field(default_factory=dict, init=False)
    _gauges: dict[str, Gauge] = field(default_factory=dict, init=False)
    _histograms: dict[str, Histogram] = field(default_factory=dict, init=False)
    _summaries: dict[str, Summary] = field(default_factory=dict, init=False)

    async def register_metrics(self, metrics_registry: MetricsRegistry) -> None:
        """Register metric definitions with Prometheus.

        Creates Prometheus Counter, Gauge, Histogram, and Summary objects.
        Idempotent - calling multiple times with same registry has no effect.

        Args:
            metrics_registry: MetricsRegistry containing all metric definitions
        """
        # Skip if already registered
        if self._metrics_registry is not None:
            return

        # Use object.__setattr__ to set field on frozen dataclass
        object.__setattr__(self, "_metrics_registry", metrics_registry)

        # Register counters
        self._counters.update(
            {
                counter_def.name: Counter(
                    name=counter_def.name,
                    documentation=counter_def.help_text,
                    labelnames=counter_def.label_names,
                    registry=self.registry,
                )
                for counter_def in metrics_registry.counters
            }
        )

        # Register gauges
        self._gauges.update(
            {
                gauge_def.name: Gauge(
                    name=gauge_def.name,
                    documentation=gauge_def.help_text,
                    labelnames=gauge_def.label_names,
                    registry=self.registry,
                )
                for gauge_def in metrics_registry.gauges
            }
        )

        # Register histograms
        self._histograms.update(
            {
                histogram_def.name: Histogram(
                    name=histogram_def.name,
                    documentation=histogram_def.help_text,
                    labelnames=histogram_def.label_names,
                    buckets=histogram_def.buckets,
                    registry=self.registry,
                )
                for histogram_def in metrics_registry.histograms
            }
        )

        # Register summaries
        self._summaries.update(
            {
                summary_def.name: Summary(
                    name=summary_def.name,
                    documentation=summary_def.help_text,
                    labelnames=summary_def.label_names,
                    registry=self.registry,
                )
                for summary_def in metrics_registry.summaries
            }
        )

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
        if self._metrics_registry is None:
            return MetricRecordingFailed(
                reason="No metrics registered - call register_metrics() first"
            )

        # Validate value is non-negative
        if value < 0:
            return MetricRecordingFailed(reason=f"Counter value must be >= 0, got {value}")

        # Validate metric is registered
        if metric_name not in self._counters:
            counter_names = tuple(self._counters.keys())
            return MetricRecordingFailed(
                reason=f"Counter '{metric_name}' not registered. "
                f"Registered counters: {counter_names}"
            )

        # Get counter and validate labels
        counter = self._counters[metric_name]
        counter_def = next((c for c in self._metrics_registry.counters if c.name == metric_name))

        if set(labels.keys()) != set(counter_def.label_names):
            return MetricRecordingFailed(
                reason=f"Labels {set(labels.keys())} don't match "
                f"registered label_names {set(counter_def.label_names)}"
            )

        # Increment counter
        try:
            counter.labels(**labels).inc(value)
            return MetricRecorded(timestamp=time.time())
        except Exception as e:
            return MetricRecordingFailed(reason=f"Prometheus error: {str(e)}")

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
        if self._metrics_registry is None:
            return MetricRecordingFailed(
                reason="No metrics registered - call register_metrics() first"
            )

        # Validate metric is registered
        if metric_name not in self._gauges:
            gauge_names = tuple(self._gauges.keys())
            return MetricRecordingFailed(
                reason=f"Gauge '{metric_name}' not registered. " f"Registered gauges: {gauge_names}"
            )

        # Get gauge and validate labels
        gauge = self._gauges[metric_name]
        gauge_def = next((g for g in self._metrics_registry.gauges if g.name == metric_name))

        if set(labels.keys()) != set(gauge_def.label_names):
            return MetricRecordingFailed(
                reason=f"Labels {set(labels.keys())} don't match "
                f"registered label_names {set(gauge_def.label_names)}"
            )

        # Set gauge value
        try:
            gauge.labels(**labels).set(value)
            return MetricRecorded(timestamp=time.time())
        except Exception as e:
            return MetricRecordingFailed(reason=f"Prometheus error: {str(e)}")

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
        if self._metrics_registry is None:
            return MetricRecordingFailed(
                reason="No metrics registered - call register_metrics() first"
            )

        # Validate metric is registered
        if metric_name not in self._gauges:
            gauge_names = tuple(self._gauges.keys())
            return MetricRecordingFailed(
                reason=f"Gauge '{metric_name}' not registered. " f"Registered gauges: {gauge_names}"
            )

        # Get gauge and validate labels
        gauge = self._gauges[metric_name]
        gauge_def = next((g for g in self._metrics_registry.gauges if g.name == metric_name))

        if set(labels.keys()) != set(gauge_def.label_names):
            return MetricRecordingFailed(
                reason=f"Labels {set(labels.keys())} don't match "
                f"registered label_names {set(gauge_def.label_names)}"
            )

        # Increment gauge value
        try:
            gauge.labels(**labels).inc(value)
            return MetricRecorded(timestamp=time.time())
        except Exception as e:
            return MetricRecordingFailed(reason=f"Prometheus error: {str(e)}")

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
        if self._metrics_registry is None:
            return MetricRecordingFailed(
                reason="No metrics registered - call register_metrics() first"
            )

        # Validate metric is registered
        if metric_name not in self._gauges:
            gauge_names = tuple(self._gauges.keys())
            return MetricRecordingFailed(
                reason=f"Gauge '{metric_name}' not registered. " f"Registered gauges: {gauge_names}"
            )

        # Get gauge and validate labels
        gauge = self._gauges[metric_name]
        gauge_def = next((g for g in self._metrics_registry.gauges if g.name == metric_name))

        if set(labels.keys()) != set(gauge_def.label_names):
            return MetricRecordingFailed(
                reason=f"Labels {set(labels.keys())} don't match "
                f"registered label_names {set(gauge_def.label_names)}"
            )

        # Decrement gauge value
        try:
            gauge.labels(**labels).dec(value)
            return MetricRecorded(timestamp=time.time())
        except Exception as e:
            return MetricRecordingFailed(reason=f"Prometheus error: {str(e)}")

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
        if self._metrics_registry is None:
            return MetricRecordingFailed(
                reason="No metrics registered - call register_metrics() first"
            )

        # Validate metric is registered
        if metric_name not in self._histograms:
            histogram_names = tuple(self._histograms.keys())
            return MetricRecordingFailed(
                reason=f"Histogram '{metric_name}' not registered. "
                f"Registered histograms: {histogram_names}"
            )

        # Get histogram and validate labels
        histogram = self._histograms[metric_name]
        histogram_def = next(
            (h for h in self._metrics_registry.histograms if h.name == metric_name)
        )

        if set(labels.keys()) != set(histogram_def.label_names):
            return MetricRecordingFailed(
                reason=f"Labels {set(labels.keys())} don't match "
                f"registered label_names {set(histogram_def.label_names)}"
            )

        # Record observation
        try:
            histogram.labels(**labels).observe(value)
            return MetricRecorded(timestamp=time.time())
        except Exception as e:
            return MetricRecordingFailed(reason=f"Prometheus error: {str(e)}")

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
        if self._metrics_registry is None:
            return MetricRecordingFailed(
                reason="No metrics registered - call register_metrics() first"
            )

        # Validate metric is registered
        if metric_name not in self._summaries:
            summary_names = tuple(self._summaries.keys())
            return MetricRecordingFailed(
                reason=f"Summary '{metric_name}' not registered. "
                f"Registered summaries: {summary_names}"
            )

        # Get summary and validate labels
        summary = self._summaries[metric_name]
        summary_def = next((s for s in self._metrics_registry.summaries if s.name == metric_name))

        if set(labels.keys()) != set(summary_def.label_names):
            return MetricRecordingFailed(
                reason=f"Labels {set(labels.keys())} don't match "
                f"registered label_names {set(summary_def.label_names)}"
            )

        # Record observation
        try:
            summary.labels(**labels).observe(value)
            return MetricRecorded(timestamp=time.time())
        except Exception as e:
            return MetricRecordingFailed(reason=f"Prometheus error: {str(e)}")

    async def query_metrics(
        self,
        metric_name: str | None,
        labels: dict[str, str] | None,
    ) -> MetricQueryResult:
        """Query current metric values from Prometheus.

        TESTING/DEBUG ONLY. Production code should query Prometheus directly.

        Args:
            metric_name: Name of metric to query (None = all metrics)
            labels: Label filters (None = all label combinations)

        Returns:
            QuerySuccess: Dict of metric values with timestamp
            QueryFailure: Metric not found or no metrics registered
        """
        if self._metrics_registry is None:
            return QueryFailure(reason="No metrics registered - call register_metrics() first")

        # For Prometheus, querying is typically done via HTTP API
        # This implementation is simplified for testing purposes
        return QueryFailure(
            reason="query_metrics() not supported for Prometheus - "
            "use Prometheus HTTP API or /metrics endpoint instead"
        )

    async def reset_metrics(self) -> MetricResult:
        """Clear all metrics.

        NOT SUPPORTED for Prometheus. Metrics are managed by Prometheus server.
        Use this only with testing frameworks that provide registry cleanup.

        Returns:
            MetricRecordingFailed: Operation not supported
        """
        return MetricRecordingFailed(
            reason="reset_metrics() not supported for Prometheus - "
            "metrics are managed by Prometheus server"
        )


__all__ = ["PrometheusMetricsCollector"]
