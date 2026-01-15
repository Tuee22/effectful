"""Metrics operation result ADTs.

This module defines ADTs for metrics operations to eliminate Optional types.
Using ADTs makes success/failure explicit and type-safe with pattern matching.

All metrics operations return one of these ADT types instead of raising exceptions,
making error handling explicit in the type system.
"""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class MetricRecorded:
    """Metric was successfully recorded.

    Attributes:
        metric_name: Name of the recorded metric
        metric_type: Metric type ("counter" | "gauge" | "histogram" | "summary")
        labels: Label key-value pairs used for this observation
        value: Observed value (increment for counters, set value for gauges, sample for histograms/summaries)
        timestamp: Unix timestamp when metric was recorded
    """

    metric_name: str
    metric_type: Literal["counter", "gauge", "histogram", "summary"]
    labels: dict[str, str]
    value: float
    timestamp: float


@dataclass(frozen=True)
class MetricRecordingFailed:
    """Metric recording failed with explicit reason.

    Attributes:
        metric_name: Name of the metric that failed to record
        reason: Categorical failure reason
        message: Human-readable context for the failure

    Possible reason values:
        - "metric_not_registered"
        - "type_mismatch"
        - "invalid_labels"
        - "invalid_value"
        - "cardinality_limit_exceeded"
        - "collector_error"
    """

    metric_name: str
    reason: Literal[
        "metric_not_registered",
        "type_mismatch",
        "invalid_labels",
        "invalid_value",
        "cardinality_limit_exceeded",
        "collector_error",
    ]
    message: str


@dataclass(frozen=True)
class QuerySuccess:
    """Metric query succeeded.

    Attributes:
        metrics: Metric values by metric name
        timestamp: Unix timestamp when query was executed
    """

    metrics: dict[str, float]
    timestamp: float


@dataclass(frozen=True)
class QueryFailure:
    """Metric query failed.

    Attributes:
        reason: Why the query failed

    Possible reason values:
        - "metric_not_found": No metrics match the query
        - "collector_unavailable": Metrics collector is not responding
        - "invalid_query: <details>": Query parameters are invalid
    """

    reason: str


# ADT: Union of metric recording results (no Optional!) using PEP 695 type statement
type MetricResult = MetricRecorded | MetricRecordingFailed

# ADT: Union of metric query results using PEP 695 type statement
type MetricQueryResult = QuerySuccess | QueryFailure
