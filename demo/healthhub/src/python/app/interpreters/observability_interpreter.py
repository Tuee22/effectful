"""Observability interpreter that records metrics via prometheus_client.

Boundary: OUTSIDE_PROOF
Target-Language: N/A (assumed correct)

Assumptions:
- [Library] prometheus_client correctly implements Prometheus exposition format
- [Registry] Metrics registry correctly aggregates values across calls
- [Thread Safety] prometheus_client handles concurrent metric updates
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from prometheus_client import CollectorRegistry, Counter, Histogram, REGISTRY, generate_latest

from app.effects.observability import (
    CounterMetricName,
    HistogramMetricName,
    IncrementCounter,
    MetricRecorded,
    MetricRecordingFailed,
    MetricRecordingResult,
    ObserveHistogram,
    ObservabilityEffect,
)
from app.observability.registry import HEALTHHUB_METRICS, MetricsRegistry


@dataclass(frozen=True)
class ObservabilityInterpreter:
    """Interpreter for observability effects.

    Manages Prometheus metric collectors as instance state, eliminating global
    mutable state while maintaining type safety and immutability.
    """

    _collector_registry: CollectorRegistry
    _counters: Mapping[str, Counter]
    _histograms: Mapping[str, Histogram]
    _counter_definitions: Mapping[str, tuple[str, ...]]
    _histogram_definitions: Mapping[str, tuple[str, ...]]

    def __init__(
        self,
        registry: MetricsRegistry = HEALTHHUB_METRICS,
        collector_registry: CollectorRegistry | None = None,
    ) -> None:
        """Initialize interpreter with metric registry.

        Args:
            registry: Metric definitions (counters and histograms)
            collector_registry: Prometheus collector registry
        """
        resolved_registry = collector_registry or REGISTRY
        # Initialize counters from registry definitions
        counters = {
            counter_definition.name: Counter(
                counter_definition.name,
                counter_definition.help_text,
                counter_definition.label_names,
                registry=resolved_registry,
            )
            for counter_definition in registry.counters
        }

        # Initialize histograms from registry definitions
        histograms = {
            histogram_definition.name: Histogram(
                histogram_definition.name,
                histogram_definition.help_text,
                histogram_definition.label_names,
                buckets=histogram_definition.buckets,
                registry=resolved_registry,
            )
            for histogram_definition in registry.histograms
        }

        # Build label definition mappings
        counter_definitions: Mapping[str, tuple[str, ...]] = {
            definition.name: definition.label_names for definition in registry.counters
        }
        histogram_definitions: Mapping[str, tuple[str, ...]] = {
            definition.name: definition.label_names for definition in registry.histograms
        }

        # Use object.__setattr__ to initialize frozen dataclass fields
        object.__setattr__(self, "_collector_registry", resolved_registry)
        object.__setattr__(self, "_counters", counters)
        object.__setattr__(self, "_histograms", histograms)
        object.__setattr__(self, "_counter_definitions", counter_definitions)
        object.__setattr__(self, "_histogram_definitions", histogram_definitions)

    async def handle(self, effect: ObservabilityEffect) -> MetricRecordingResult:
        """Execute observability effect and return typed result."""
        match effect:
            case IncrementCounter(metric_name=metric_name, labels=labels, value=value):
                return self._increment(metric_name, labels, value)
            case ObserveHistogram(metric_name=metric_name, labels=labels, value=value):
                return self._observe(metric_name, labels, value)

    def _increment(
        self, metric_name: CounterMetricName, labels: Mapping[str, str], value: float
    ) -> MetricRecordingResult:
        counter = self._counters.get(metric_name)
        expected_labels = self._counter_definitions.get(metric_name)
        if counter is None or expected_labels is None:
            return MetricRecordingFailed(
                metric_name=metric_name,
                reason="metric_not_registered",
                message=f"Unknown counter metric: {metric_name}",
            )
        label_error = self._validate_labels(expected_labels, labels, metric_name)
        if label_error is not None:
            return label_error
        counter.labels(**labels).inc(value)
        return MetricRecorded(
            metric_name=metric_name,
            metric_type="counter",
            labels=labels,
            value=value,
        )

    def _observe(
        self, metric_name: HistogramMetricName, labels: Mapping[str, str], value: float
    ) -> MetricRecordingResult:
        histogram = self._histograms.get(metric_name)
        expected_labels = self._histogram_definitions.get(metric_name)
        if histogram is None or expected_labels is None:
            return MetricRecordingFailed(
                metric_name=metric_name,
                reason="metric_not_registered",
                message=f"Unknown histogram metric: {metric_name}",
            )
        label_error = self._validate_labels(expected_labels, labels, metric_name)
        if label_error is not None:
            return label_error
        histogram.labels(**labels).observe(value)
        return MetricRecorded(
            metric_name=metric_name,
            metric_type="histogram",
            labels=labels,
            value=value,
        )

    def render_latest(self) -> bytes:
        """Render Prometheus metrics from the bound collector registry."""
        return generate_latest(self._collector_registry)

    def _validate_labels(
        self, expected: tuple[str, ...], provided: Mapping[str, str], metric_name: str
    ) -> MetricRecordingFailed | None:
        missing = [label for label in expected if label not in provided]
        extra = [label for label in provided.keys() if label not in expected]
        if missing or extra:
            return MetricRecordingFailed(
                metric_name=metric_name,
                reason="invalid_labels",
                message=f"Label mismatch for {metric_name}: missing={missing} extra={extra}",
            )
        return None


def get_observability_interpreter() -> ObservabilityInterpreter:
    """Create and return an observability interpreter instance.

    Each interpreter instance maintains its own metric collectors while sharing
    the global Prometheus registry. This allows multiple interpreter instances
    without global mutable state.

    Returns:
        ObservabilityInterpreter: New interpreter instance
    """
    return ObservabilityInterpreter()
