"""Tests for observability registry types and validation.

Tests verify:
- All registry types are frozen (immutable)
- Validation functions work correctly
- Invalid configurations are rejected
"""

import pytest

from effectful.algebraic.result import Err, Ok
from effectful.observability import (
    CounterDefinition,
    GaugeDefinition,
    HistogramDefinition,
    MetricsRegistry,
    SummaryDefinition,
    validate_histogram_buckets,
    validate_label_names,
    validate_metric_name,
    validate_summary_quantiles,
)


# CounterDefinition tests
def test_counter_definition_creation() -> None:
    """CounterDefinition can be created with name, help_text, and label_names."""
    counter = CounterDefinition(
        name="requests_total",
        help_text="Total requests",
        label_names=("method", "status"),
    )
    assert counter.name == "requests_total"
    assert counter.help_text == "Total requests"
    assert counter.label_names == ("method", "status")


def test_counter_definition_is_frozen() -> None:
    """CounterDefinition is immutable (frozen dataclass)."""
    counter = CounterDefinition(name="requests_total", help_text="Total requests", label_names=())
    with pytest.raises(AttributeError, match="cannot assign"):
        counter.name = "other_total"  # type: ignore


# GaugeDefinition tests
def test_gauge_definition_creation() -> None:
    """GaugeDefinition can be created with name, help_text, and label_names."""
    gauge = GaugeDefinition(
        name="active_connections",
        help_text="Current connections",
        label_names=("protocol",),
    )
    assert gauge.name == "active_connections"
    assert gauge.help_text == "Current connections"
    assert gauge.label_names == ("protocol",)


def test_gauge_definition_is_frozen() -> None:
    """GaugeDefinition is immutable (frozen dataclass)."""
    gauge = GaugeDefinition(name="test_gauge", help_text="Test", label_names=())
    with pytest.raises(AttributeError, match="cannot assign"):
        gauge.name = "other_gauge"  # type: ignore


# HistogramDefinition tests
def test_histogram_definition_creation() -> None:
    """HistogramDefinition can be created with name, help_text, label_names, buckets."""
    histogram = HistogramDefinition(
        name="request_duration_seconds",
        help_text="Request latency",
        label_names=("method",),
        buckets=(0.005, 0.01, 0.025, 0.05, 0.1),
    )
    assert histogram.name == "request_duration_seconds"
    assert histogram.help_text == "Request latency"
    assert histogram.label_names == ("method",)
    assert histogram.buckets == (0.005, 0.01, 0.025, 0.05, 0.1)


def test_histogram_definition_is_frozen() -> None:
    """HistogramDefinition is immutable (frozen dataclass)."""
    histogram = HistogramDefinition(
        name="test_seconds", help_text="Test", label_names=(), buckets=(0.1,)
    )
    with pytest.raises(AttributeError, match="cannot assign"):
        histogram.name = "other_seconds"  # type: ignore


# SummaryDefinition tests
def test_summary_definition_creation() -> None:
    """SummaryDefinition can be created with name, help_text, label_names, quantiles."""
    summary = SummaryDefinition(
        name="response_size",
        help_text="Response payload size",
        label_names=("endpoint",),
        quantiles=(0.5, 0.9, 0.99),
    )
    assert summary.name == "response_size"
    assert summary.help_text == "Response payload size"
    assert summary.label_names == ("endpoint",)
    assert summary.quantiles == (0.5, 0.9, 0.99)


def test_summary_definition_is_frozen() -> None:
    """SummaryDefinition is immutable (frozen dataclass)."""
    summary = SummaryDefinition(
        name="test_summary", help_text="Test", label_names=(), quantiles=(0.5,)
    )
    with pytest.raises(AttributeError, match="cannot assign"):
        summary.name = "other_summary"  # type: ignore


# MetricsRegistry tests
def test_metrics_registry_creation() -> None:
    """MetricsRegistry can be created with all metric types."""
    registry = MetricsRegistry(
        counters=(CounterDefinition(name="requests_total", help_text="Requests", label_names=()),),
        gauges=(GaugeDefinition(name="connections", help_text="Connections", label_names=()),),
        histograms=(
            HistogramDefinition(
                name="duration_seconds",
                help_text="Duration",
                label_names=(),
                buckets=(0.1,),
            ),
        ),
        summaries=(
            SummaryDefinition(name="size", help_text="Size", label_names=(), quantiles=(0.5,)),
        ),
    )
    assert len(registry.counters) == 1
    assert len(registry.gauges) == 1
    assert len(registry.histograms) == 1
    assert len(registry.summaries) == 1


def test_metrics_registry_is_frozen() -> None:
    """MetricsRegistry is immutable (frozen dataclass)."""
    registry = MetricsRegistry(counters=(), gauges=(), histograms=(), summaries=())
    with pytest.raises(AttributeError, match="cannot assign"):
        registry.counters = ()  # type: ignore


def test_metrics_registry_empty() -> None:
    """MetricsRegistry can be created with no metrics."""
    registry = MetricsRegistry(counters=(), gauges=(), histograms=(), summaries=())
    assert registry.counters == ()
    assert registry.gauges == ()
    assert registry.histograms == ()
    assert registry.summaries == ()


# validate_metric_name tests
def test_validate_metric_name_valid_counter() -> None:
    """Valid counter names pass validation."""
    result = validate_metric_name("requests_total", "counter")
    assert result == Ok(None)


def test_validate_metric_name_counter_missing_total_suffix() -> None:
    """Counter without _total suffix fails validation."""
    result = validate_metric_name("requests", "counter")
    assert isinstance(result, Err)
    assert "_total" in result.error


def test_validate_metric_name_valid_gauge() -> None:
    """Valid gauge names pass validation."""
    result = validate_metric_name("active_connections", "gauge")
    assert result == Ok(None)


def test_validate_metric_name_valid_histogram() -> None:
    """Valid histogram names pass validation."""
    result = validate_metric_name("request_duration_seconds", "histogram")
    assert result == Ok(None)


def test_validate_metric_name_invalid_pattern() -> None:
    """Invalid characters in metric name fail validation."""
    # Uppercase not allowed
    result = validate_metric_name("RequestsTotal", "counter")
    assert isinstance(result, Err)
    assert "snake_case" in result.error


def test_validate_metric_name_reserved_prefix() -> None:
    """Metric names starting with __ fail validation."""
    result = validate_metric_name("__internal_total", "counter")
    assert isinstance(result, Err)
    assert "reserved" in result.error


def test_validate_metric_name_starting_with_number() -> None:
    """Metric names starting with number fail validation."""
    result = validate_metric_name("1_requests_total", "counter")
    assert isinstance(result, Err)


# validate_label_names tests
def test_validate_label_names_valid() -> None:
    """Valid label names pass validation."""
    result = validate_label_names(("method", "status", "path"))
    assert result == Ok(None)


def test_validate_label_names_empty() -> None:
    """Empty label names pass validation."""
    result = validate_label_names(())
    assert result == Ok(None)


def test_validate_label_names_invalid_pattern() -> None:
    """Invalid characters in label names fail validation."""
    result = validate_label_names(("Method", "status"))
    assert isinstance(result, Err)
    assert "snake_case" in result.error


def test_validate_label_names_reserved_prefix() -> None:
    """Label names starting with __ fail validation."""
    result = validate_label_names(("__internal", "status"))
    assert isinstance(result, Err)
    assert "reserved" in result.error


def test_validate_label_names_duplicates() -> None:
    """Duplicate label names fail validation."""
    result = validate_label_names(("method", "status", "method"))
    assert isinstance(result, Err)
    assert "Duplicate" in result.error


# validate_histogram_buckets tests
def test_validate_histogram_buckets_valid() -> None:
    """Valid histogram buckets pass validation."""
    result = validate_histogram_buckets((0.005, 0.01, 0.025, 0.05, 0.1, 0.5, 1.0))
    assert result == Ok(None)


def test_validate_histogram_buckets_empty() -> None:
    """Empty histogram buckets fail validation."""
    result = validate_histogram_buckets(())
    assert isinstance(result, Err)
    assert "at least one bucket" in result.error


def test_validate_histogram_buckets_negative() -> None:
    """Negative bucket values fail validation."""
    result = validate_histogram_buckets((-0.1, 0.5, 1.0))
    assert isinstance(result, Err)
    assert "positive" in result.error


def test_validate_histogram_buckets_zero() -> None:
    """Zero bucket value fails validation."""
    result = validate_histogram_buckets((0.0, 0.5, 1.0))
    assert isinstance(result, Err)
    assert "positive" in result.error


def test_validate_histogram_buckets_not_sorted() -> None:
    """Unsorted histogram buckets fail validation."""
    result = validate_histogram_buckets((0.1, 0.05, 0.5))
    assert isinstance(result, Err)
    assert "sorted ascending" in result.error


def test_validate_histogram_buckets_duplicates() -> None:
    """Duplicate histogram buckets fail validation."""
    result = validate_histogram_buckets((0.1, 0.5, 0.5, 1.0))
    assert isinstance(result, Err)
    assert "sorted ascending" in result.error


# validate_summary_quantiles tests
def test_validate_summary_quantiles_valid() -> None:
    """Valid summary quantiles pass validation."""
    result = validate_summary_quantiles((0.5, 0.9, 0.95, 0.99))
    assert result == Ok(None)


def test_validate_summary_quantiles_empty() -> None:
    """Empty summary quantiles fail validation."""
    result = validate_summary_quantiles(())
    assert isinstance(result, Err)
    assert "at least one quantile" in result.error


def test_validate_summary_quantiles_below_range() -> None:
    """Quantile values below 0.0 fail validation."""
    result = validate_summary_quantiles((-0.1, 0.5, 0.9))
    assert isinstance(result, Err)
    assert "[0.0, 1.0]" in result.error


def test_validate_summary_quantiles_above_range() -> None:
    """Quantile values above 1.0 fail validation."""
    result = validate_summary_quantiles((0.5, 0.9, 1.5))
    assert isinstance(result, Err)
    assert "[0.0, 1.0]" in result.error


def test_validate_summary_quantiles_not_sorted() -> None:
    """Unsorted summary quantiles fail validation."""
    result = validate_summary_quantiles((0.9, 0.5, 0.95))
    assert isinstance(result, Err)
    assert "sorted ascending" in result.error


def test_validate_summary_quantiles_duplicates() -> None:
    """Duplicate summary quantiles fail validation."""
    result = validate_summary_quantiles((0.5, 0.9, 0.9))
    assert isinstance(result, Err)
    assert "sorted ascending" in result.error


def test_validate_summary_quantiles_boundary_values() -> None:
    """Quantiles at boundary values (0.0, 1.0) pass validation."""
    result = validate_summary_quantiles((0.0, 0.5, 1.0))
    assert result == Ok(None)
