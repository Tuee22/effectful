"""Metrics registry for HealthHub observability."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CounterDefinition:
    """Immutable counter definition."""

    name: str
    help_text: str
    label_names: tuple[str, ...]


@dataclass(frozen=True)
class HistogramDefinition:
    """Immutable histogram definition."""

    name: str
    help_text: str
    label_names: tuple[str, ...]
    buckets: tuple[float, ...]


@dataclass(frozen=True)
class MetricsRegistry:
    """Immutable registry for all metrics."""

    counters: tuple[CounterDefinition, ...]
    histograms: tuple[HistogramDefinition, ...]


HEALTHHUB_METRICS = MetricsRegistry(
    counters=(
        CounterDefinition(
            name="healthhub_appointments_created_total",
            help_text="Total appointments created",
            label_names=("doctor_specialization",),
        ),
        CounterDefinition(
            name="healthhub_prescriptions_created_total",
            help_text="Total prescriptions created",
            label_names=("doctor_specialization", "severity"),
        ),
        CounterDefinition(
            name="healthhub_lab_results_created_total",
            help_text="Total lab results recorded",
            label_names=("doctor_specialization", "critical"),
        ),
        CounterDefinition(
            name="healthhub_audit_events_total",
            help_text="Total audit events emitted",
            label_names=("action",),
        ),
    ),
    histograms=(
        HistogramDefinition(
            name="healthhub_appointment_transition_latency_seconds",
            help_text="Time from request to state transition in seconds",
            label_names=("new_status",),
            buckets=(0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0),
        ),
    ),
)
