"""Tests for metrics effects.

Tests verify:
- All effects are frozen (immutable)
- Default parameter values work correctly
- Effects can be created with various parameter combinations
- Type union membership
"""

from dataclasses import FrozenInstanceError

import pytest

from effectful.effects.metrics import (
    IncrementCounter,
    MetricsEffect,
    ObserveHistogram,
    QueryMetrics,
    RecordGauge,
    RecordSummary,
    ResetMetrics,
)


# IncrementCounter tests
def test_increment_counter_creation() -> None:
    """IncrementCounter can be created with metric_name, labels, value."""
    effect = IncrementCounter(
        metric_name="requests_total",
        labels={"method": "GET", "status": "200"},
        value=1.0,
    )
    assert effect.metric_name == "requests_total"
    assert effect.labels == {"method": "GET", "status": "200"}
    assert effect.value == 1.0


def test_increment_counter_default_value() -> None:
    """IncrementCounter defaults to value=1.0."""
    effect = IncrementCounter(metric_name="test_total", labels={})
    assert effect.value == 1.0


def test_increment_counter_is_frozen() -> None:
    """IncrementCounter is immutable (frozen dataclass)."""
    effect = IncrementCounter(metric_name="test_total", labels={}, value=1.0)
    with pytest.raises((FrozenInstanceError, AttributeError)):
        setattr(effect, "value", 2.0)


def test_increment_counter_empty_labels() -> None:
    """IncrementCounter can have empty labels dict."""
    effect = IncrementCounter(metric_name="test_total", labels={})
    assert effect.labels == {}


# RecordGauge tests
def test_record_gauge_creation() -> None:
    """RecordGauge can be created with metric_name, labels, value."""
    effect = RecordGauge(
        metric_name="active_connections",
        labels={"protocol": "http"},
        value=42.0,
    )
    assert effect.metric_name == "active_connections"
    assert effect.labels == {"protocol": "http"}
    assert effect.value == 42.0


def test_record_gauge_is_frozen() -> None:
    """RecordGauge is immutable (frozen dataclass)."""
    effect = RecordGauge(metric_name="test_gauge", labels={}, value=1.0)
    with pytest.raises((FrozenInstanceError, AttributeError)):
        setattr(effect, "value", 2.0)


def test_record_gauge_negative_value() -> None:
    """RecordGauge can accept negative values (gauges can go down)."""
    effect = RecordGauge(metric_name="temperature_celsius", labels={}, value=-10.5)
    assert effect.value == -10.5


# ObserveHistogram tests
def test_observe_histogram_creation() -> None:
    """ObserveHistogram can be created with metric_name, labels, value."""
    effect = ObserveHistogram(
        metric_name="request_duration_seconds",
        labels={"method": "POST"},
        value=0.123,
    )
    assert effect.metric_name == "request_duration_seconds"
    assert effect.labels == {"method": "POST"}
    assert effect.value == 0.123


def test_observe_histogram_is_frozen() -> None:
    """ObserveHistogram is immutable (frozen dataclass)."""
    effect = ObserveHistogram(metric_name="test_seconds", labels={}, value=1.0)
    with pytest.raises((FrozenInstanceError, AttributeError)):
        setattr(effect, "value", 2.0)


# RecordSummary tests
def test_record_summary_creation() -> None:
    """RecordSummary can be created with metric_name, labels, value."""
    effect = RecordSummary(
        metric_name="response_size",
        labels={"endpoint": "/api/users"},
        value=1024.0,
    )
    assert effect.metric_name == "response_size"
    assert effect.labels == {"endpoint": "/api/users"}
    assert effect.value == 1024.0


def test_record_summary_is_frozen() -> None:
    """RecordSummary is immutable (frozen dataclass)."""
    effect = RecordSummary(metric_name="test_summary", labels={}, value=1.0)
    with pytest.raises((FrozenInstanceError, AttributeError)):
        setattr(effect, "value", 2.0)


# QueryMetrics tests
def test_query_metrics_all() -> None:
    """QueryMetrics with None parameters queries all metrics."""
    effect = QueryMetrics()
    assert effect.metric_name is None
    assert effect.labels is None


def test_query_metrics_specific_metric() -> None:
    """QueryMetrics can query specific metric by name."""
    effect = QueryMetrics(metric_name="requests_total")
    assert effect.metric_name == "requests_total"
    assert effect.labels is None


def test_query_metrics_with_labels() -> None:
    """QueryMetrics can filter by labels."""
    effect = QueryMetrics(
        metric_name="requests_total",
        labels={"method": "GET"},
    )
    assert effect.metric_name == "requests_total"
    assert effect.labels == {"method": "GET"}


def test_query_metrics_is_frozen() -> None:
    """QueryMetrics is immutable (frozen dataclass)."""
    effect = QueryMetrics()
    with pytest.raises((FrozenInstanceError, AttributeError)):
        setattr(effect, "metric_name", "test_total")


# ResetMetrics tests
def test_reset_metrics_creation() -> None:
    """ResetMetrics can be created with no parameters."""
    effect = ResetMetrics()
    # No fields to check - just verify it can be created
    assert isinstance(effect, ResetMetrics)


def test_reset_metrics_is_frozen() -> None:
    """ResetMetrics is immutable (frozen dataclass)."""
    effect = ResetMetrics()
    # Try to add an attribute (should fail)
    with pytest.raises((FrozenInstanceError, AttributeError)):
        setattr(effect, "new_field", "value")


# MetricsEffect union type tests
def test_metrics_effect_union_increment_counter() -> None:
    """IncrementCounter is a valid MetricsEffect."""
    effect: MetricsEffect = IncrementCounter(metric_name="test_total", labels={})
    assert isinstance(effect, IncrementCounter)


def test_metrics_effect_union_record_gauge() -> None:
    """RecordGauge is a valid MetricsEffect."""
    effect: MetricsEffect = RecordGauge(metric_name="test_gauge", labels={}, value=1.0)
    assert isinstance(effect, RecordGauge)


def test_metrics_effect_union_observe_histogram() -> None:
    """ObserveHistogram is a valid MetricsEffect."""
    effect: MetricsEffect = ObserveHistogram(metric_name="test_seconds", labels={}, value=1.0)
    assert isinstance(effect, ObserveHistogram)


def test_metrics_effect_union_record_summary() -> None:
    """RecordSummary is a valid MetricsEffect."""
    effect: MetricsEffect = RecordSummary(metric_name="test_summary", labels={}, value=1.0)
    assert isinstance(effect, RecordSummary)


def test_metrics_effect_union_query_metrics() -> None:
    """QueryMetrics is a valid MetricsEffect."""
    effect: MetricsEffect = QueryMetrics()
    assert isinstance(effect, QueryMetrics)


def test_metrics_effect_union_reset_metrics() -> None:
    """ResetMetrics is a valid MetricsEffect."""
    effect: MetricsEffect = ResetMetrics()
    assert isinstance(effect, ResetMetrics)


# Pattern matching tests
def test_pattern_matching_increment_counter() -> None:
    """MetricsEffect pattern matching works for IncrementCounter."""
    effect: MetricsEffect = IncrementCounter(
        metric_name="test_total", labels={"key": "value"}, value=5.0
    )
    match effect:
        case IncrementCounter(metric_name=name, labels=labels, value=value):
            assert name == "test_total"
            assert labels == {"key": "value"}
            assert value == 5.0
        case _:
            pytest.fail("Should match IncrementCounter")


def test_pattern_matching_query_metrics() -> None:
    """MetricsEffect pattern matching works for QueryMetrics."""
    effect: MetricsEffect = QueryMetrics(metric_name="test_total")
    match effect:
        case QueryMetrics(metric_name=name, labels=labels):
            assert name == "test_total"
            assert labels is None
        case _:
            pytest.fail("Should match QueryMetrics")


def test_pattern_matching_reset_metrics() -> None:
    """MetricsEffect pattern matching works for ResetMetrics."""
    effect: MetricsEffect = ResetMetrics()
    match effect:
        case ResetMetrics():
            pass  # Success
        case _:
            pytest.fail("Should match ResetMetrics")
