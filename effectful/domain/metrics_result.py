"""Metrics operation result ADTs.

This module defines ADTs for metrics operations to eliminate Optional types.
Using ADTs makes success/failure explicit and type-safe with pattern matching.

All metrics operations return one of these ADT types instead of raising exceptions,
making error handling explicit in the type system.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class MetricRecorded:
    """Metric was successfully recorded.

    Attributes:
        timestamp: Unix timestamp when metric was recorded
    """

    timestamp: float


@dataclass(frozen=True)
class MetricRecordingFailed:
    """Metric recording failed with explicit reason.

    Attributes:
        reason: Why the metric wasn't recorded

    Possible reason values:
        - "metric_not_registered": Metric not found in MetricsRegistry
        - "type_mismatch": Metric exists but is different type (counter vs gauge)
        - "missing_label: <label_name>": Required label not provided
        - "unexpected_label: <label_name>": Label provided but not in schema
        - "invalid_value: <details>": Value is invalid (negative, NaN, etc.)
        - "cardinality_limit_exceeded": Too many unique label combinations
        - "collector_error: <message>": Internal collector error
    """

    reason: str


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
