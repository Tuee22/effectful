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
    - documents/engineering/monitoring_and_alerting.md - Naming conventions
"""

from effectful.observability import (
    CounterDefinition,
    GaugeDefinition,
    HistogramDefinition,
    MetricsRegistry,
)

# Framework metrics registry for automatic instrumentation
#
# Note: InstrumentedProgramRunner (for program-level metrics) is future work.
# See observability.md for automatic instrumentation requirements.
FRAMEWORK_METRICS = MetricsRegistry(
    counters=(
        CounterDefinition(
            name="effectful_effects_total",
            help_text="Total effect executions by type and result",
            label_names=("effect_type", "result"),
        ),
        CounterDefinition(
            name="effectful_programs_total",
            help_text="Total program executions by name and result",
            label_names=("program_name", "result"),
        ),
    ),
    gauges=(
        GaugeDefinition(
            name="effectful_effects_in_progress",
            help_text="Currently executing effects",
            label_names=("effect_type",),
        ),
    ),
    histograms=(
        HistogramDefinition(
            name="effectful_effect_duration_seconds",
            help_text="Effect execution duration distribution",
            label_names=("effect_type",),
            buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
        ),
        HistogramDefinition(
            name="effectful_program_duration_seconds",
            help_text="Program execution duration distribution",
            label_names=("program_name",),
            buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
        ),
    ),
    summaries=(),
)
