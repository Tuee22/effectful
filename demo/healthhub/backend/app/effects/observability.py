"""Observability effects for metrics recording.

Metrics are immutable data structures; interpreters perform the side effects.
Metric names are tied to the registry to prevent typos and label mismatches.
"""

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping, Literal


type CounterMetricName = Literal[
    "healthhub_appointments_created_total",
    "healthhub_prescriptions_created_total",
    "healthhub_lab_results_created_total",
    "healthhub_audit_events_total",
]

type HistogramMetricName = Literal["healthhub_appointment_transition_latency_seconds"]


@dataclass(frozen=True)
class IncrementCounter:
    """Increment a counter metric by value.

    Attributes:
        metric_name: Name of the counter metric to increment.
        labels: Label key-value pairs for metric dimension.
        value: Increment amount (defaults to 1.0).
    """

    metric_name: CounterMetricName
    labels: Mapping[str, str]
    value: float = 1.0

    def __post_init__(self) -> None:
        # Freeze labels to keep the effect immutable end-to-end
        object.__setattr__(self, "labels", MappingProxyType(dict(self.labels)))


@dataclass(frozen=True)
class ObserveHistogram:
    """Record an observation for a histogram metric.

    Attributes:
        metric_name: Name of the histogram metric to observe.
        labels: Label key-value pairs for metric dimension.
        value: Observed value to record.
    """

    metric_name: HistogramMetricName
    labels: Mapping[str, str]
    value: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "labels", MappingProxyType(dict(self.labels)))


@dataclass(frozen=True)
class MetricRecorded:
    """Successful metric recording.

    Attributes:
        metric_name: Name of the recorded metric.
        metric_type: Type of metric (counter or histogram).
        labels: Label key-value pairs used for recording.
        value: Value that was recorded.
    """

    metric_name: CounterMetricName | HistogramMetricName
    metric_type: Literal["counter", "histogram"]
    labels: Mapping[str, str]
    value: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "labels", MappingProxyType(dict(self.labels)))


@dataclass(frozen=True)
class MetricRecordingFailed:
    """Domain failure when recording a metric.

    Attributes:
        metric_name: Name of the metric that failed to record.
        reason: Failure reason category.
        message: Human-readable failure description.
    """

    metric_name: CounterMetricName | HistogramMetricName | str
    reason: Literal["metric_not_registered", "invalid_labels"]
    message: str


type MetricRecordingResult = MetricRecorded | MetricRecordingFailed


type ObservabilityEffect = IncrementCounter | ObserveHistogram
