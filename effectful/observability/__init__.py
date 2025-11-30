"""Observability and metrics registry types.

This module defines immutable metric definition types and registry for type-safe
metrics configuration. All metrics must be registered before use to ensure
schema validation and type safety.

Example:
    >>> from effectful.observability import MetricsRegistry, CounterDefinition, HistogramDefinition
    >>> registry = MetricsRegistry(
    ...     counters=(
    ...         CounterDefinition(
    ...             name="requests_total",
    ...             help_text="Total HTTP requests",
    ...             label_names=("method", "status"),
    ...         ),
    ...     ),
    ...     gauges=(),
    ...     histograms=(
    ...         HistogramDefinition(
    ...             name="request_duration_seconds",
    ...             help_text="HTTP request latency",
    ...             label_names=("method",),
    ...             buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5),
    ...         ),
    ...     ),
    ...     summaries=(),
    ... )
"""

import re
from dataclasses import dataclass

from effectful.algebraic.result import Err, Ok, Result


@dataclass(frozen=True)
class CounterDefinition:
    """Immutable counter metric definition.

    Counters are monotonically increasing values that track cumulative totals.
    Examples: requests_total, errors_total, bytes_sent_total

    Attributes:
        name: Metric name (must end with "_total", snake_case)
        help_text: Human-readable description
        label_names: Tuple of label keys (snake_case, no __reserved__)
    """

    name: str
    help_text: str
    label_names: tuple[str, ...]


@dataclass(frozen=True)
class GaugeDefinition:
    """Immutable gauge metric definition.

    Gauges are point-in-time values that can go up or down.
    Examples: active_connections, memory_usage_bytes, queue_depth

    Attributes:
        name: Metric name (snake_case)
        help_text: Human-readable description
        label_names: Tuple of label keys (snake_case, no __reserved__)
    """

    name: str
    help_text: str
    label_names: tuple[str, ...]


@dataclass(frozen=True)
class HistogramDefinition:
    """Immutable histogram metric definition.

    Histograms track distributions of values in configurable buckets.
    Examples: request_duration_seconds, payload_size_bytes

    Attributes:
        name: Metric name (should include unit: _seconds, _bytes)
        help_text: Human-readable description
        label_names: Tuple of label keys (snake_case, no __reserved__)
        buckets: Tuple of bucket boundaries (sorted ascending, must be positive)
    """

    name: str
    help_text: str
    label_names: tuple[str, ...]
    buckets: tuple[float, ...]


@dataclass(frozen=True)
class SummaryDefinition:
    """Immutable summary metric definition.

    Summaries track distributions with streaming quantiles (percentiles).
    Less common than histograms. Use histograms unless you need client-side quantiles.

    Attributes:
        name: Metric name (snake_case)
        help_text: Human-readable description
        label_names: Tuple of label keys (snake_case, no __reserved__)
        quantiles: Tuple of quantile values (0.0-1.0, e.g., 0.5 = median, 0.95 = p95)
    """

    name: str
    help_text: str
    label_names: tuple[str, ...]
    quantiles: tuple[float, ...]


@dataclass(frozen=True)
class MetricsRegistry:
    """Immutable container for all metric definitions.

    Registry must be provided to metrics collectors at initialization.
    All metrics must be registered before they can be used.

    Attributes:
        counters: Tuple of counter definitions
        gauges: Tuple of gauge definitions
        histograms: Tuple of histogram definitions
        summaries: Tuple of summary definitions
    """

    counters: tuple[CounterDefinition, ...]
    gauges: tuple[GaugeDefinition, ...]
    histograms: tuple[HistogramDefinition, ...]
    summaries: tuple[SummaryDefinition, ...]


# Validation functions


def validate_metric_name(name: str, metric_type: str) -> Result[None, str]:
    """Validate metric naming conventions.

    Rules:
    - Must match [a-z_][a-z0-9_]* (snake_case, starts with letter or underscore)
    - Counters must end with "_total"
    - Histograms should include unit suffix (_seconds, _bytes, etc.)
    - Must not start with double underscore (reserved for Prometheus internals)

    Args:
        name: Metric name to validate
        metric_type: Type of metric ("counter", "gauge", "histogram", "summary")

    Returns:
        Ok(None) if valid
        Err(reason) if invalid
    """
    # Check basic pattern
    if not re.match(r"^[a-z_][a-z0-9_]*$", name):
        return Err(
            f"Metric name '{name}' must match [a-z_][a-z0-9_]* (snake_case, "
            "starts with letter or underscore)"
        )

    # Check for reserved prefix
    if name.startswith("__"):
        return Err(f"Metric name '{name}' must not start with __ (reserved)")

    # Counter-specific validation
    if metric_type == "counter" and not name.endswith("_total"):
        return Err(f"Counter metric '{name}' must end with '_total'")

    # Histogram-specific validation (recommendation, not error)
    if metric_type == "histogram":
        unit_suffixes = ("_seconds", "_bytes", "_bits", "_meters", "_celsius", "_ratio")
        has_unit = any(name.endswith(suffix) for suffix in unit_suffixes)
        if not has_unit:
            # Just a warning, not an error - return Ok
            pass

    return Ok(None)


def validate_label_names(labels: tuple[str, ...]) -> Result[None, str]:
    """Validate label naming conventions.

    Rules:
    - Each label must match [a-z_][a-z0-9_]* (snake_case)
    - Must not start with double underscore (reserved)
    - No duplicate labels

    Args:
        labels: Tuple of label names to validate

    Returns:
        Ok(None) if valid
        Err(reason) if invalid
    """
    # Check basic pattern
    invalid_pattern = [
        (label, f"Label '{label}' must match [a-z_][a-z0-9_]* (snake_case, starts with letter or underscore)")
        for label in labels
        if not re.match(r"^[a-z_][a-z0-9_]*$", label)
    ]
    if invalid_pattern:
        return Err(invalid_pattern[0][1])

    # Check for reserved prefix
    reserved_labels = [
        (label, f"Label '{label}' must not start with __ (reserved)")
        for label in labels
        if label.startswith("__")
    ]
    if reserved_labels:
        return Err(reserved_labels[0][1])

    # Check for duplicates
    seen: set[str] = set()
    duplicates = [
        label for label in labels
        if label in seen or (seen.add(label) or False)  # type: ignore[func-returns-value]
    ]
    if duplicates:
        return Err(f"Duplicate label '{duplicates[0]}' in label_names")

    return Ok(None)


def validate_histogram_buckets(buckets: tuple[float, ...]) -> Result[None, str]:
    """Validate histogram bucket configuration.

    Rules:
    - Must have at least one bucket
    - All buckets must be positive
    - Must be sorted ascending
    - No duplicate buckets

    Args:
        buckets: Tuple of bucket boundaries

    Returns:
        Ok(None) if valid
        Err(reason) if invalid
    """
    if len(buckets) == 0:
        return Err("Histogram must have at least one bucket")

    # Check all positive
    non_positive = [bucket for bucket in buckets if bucket <= 0]
    if non_positive:
        return Err(f"Histogram bucket {non_positive[0]} must be positive")

    # Check sorted ascending
    unordered_pairs = [
        (buckets[i], buckets[i + 1])
        for i in range(len(buckets) - 1)
        if buckets[i] >= buckets[i + 1]
    ]
    if unordered_pairs:
        return Err(f"Histogram buckets must be sorted ascending: {unordered_pairs[0][0]} >= {unordered_pairs[0][1]}")

    return Ok(None)


def validate_summary_quantiles(quantiles: tuple[float, ...]) -> Result[None, str]:
    """Validate summary quantile configuration.

    Rules:
    - Must have at least one quantile
    - All quantiles must be in range [0.0, 1.0]
    - Must be sorted ascending
    - No duplicate quantiles

    Args:
        quantiles: Tuple of quantile values

    Returns:
        Ok(None) if valid
        Err(reason) if invalid
    """
    if len(quantiles) == 0:
        return Err("Summary must have at least one quantile")

    # Check all in range [0.0, 1.0]
    out_of_range = [q for q in quantiles if not (0.0 <= q <= 1.0)]
    if out_of_range:
        return Err(f"Summary quantile {out_of_range[0]} must be in range [0.0, 1.0]")

    # Check sorted ascending
    unordered_pairs = [
        (quantiles[i], quantiles[i + 1])
        for i in range(len(quantiles) - 1)
        if quantiles[i] >= quantiles[i + 1]
    ]
    if unordered_pairs:
        return Err(
            f"Summary quantiles must be sorted ascending: "
            f"{unordered_pairs[0][0]} >= {unordered_pairs[0][1]}"
        )

    return Ok(None)
