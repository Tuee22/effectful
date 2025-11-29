"""Framework-level metrics registry for automatic instrumentation.

This module defines FRAMEWORK_METRICS, a pre-configured MetricsRegistry containing
all metrics used by the effectful framework's automatic instrumentation layer.

When InstrumentedInterpreter is enabled, it automatically tracks:
- Effect execution counts and durations
- Effect error rates
- Effect concurrency
- Program execution counts and durations

For application-specific business metrics, create your own registry.

Example:
    >>> from effectful.observability.framework_metrics import FRAMEWORK_METRICS
    >>> from effectful.adapters.prometheus_metrics import PrometheusMetricsCollector
    >>> collector = PrometheusMetricsCollector(metrics_registry=FRAMEWORK_METRICS)

See Also:
    - documents/core/observability_doctrine.md - Metrics philosophy
    - documents/core/monitoring_standards.md - Naming conventions
"""

from effectful.observability import (
    CounterDefinition,
    GaugeDefinition,
    HistogramDefinition,
    MetricsRegistry,
)

# Framework metrics registry for automatic instrumentation
#
# Note: Currently tracks counter and histogram metrics only.
# Gauge tracking for concurrent effects (effectful_effects_in_progress)
# requires increment/decrement operations not yet in MetricsCollector protocol.
# Program-level metrics (effectful_programs_total, effectful_program_duration_seconds)
# will be implemented in future InstrumentedProgramRunner.
FRAMEWORK_METRICS = MetricsRegistry(
    counters=(
        CounterDefinition(
            name="effectful_effects_total",
            help_text="Total effect executions by type and result",
            label_names=("effect_type", "result"),
        ),
    ),
    gauges=(),
    histograms=(
        HistogramDefinition(
            name="effectful_effect_duration_seconds",
            help_text="Effect execution duration distribution",
            label_names=("effect_type",),
            buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
        ),
    ),
    summaries=(),
)
