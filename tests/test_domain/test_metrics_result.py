"""Tests for metrics result ADTs.

Tests verify:
- All ADT types are frozen (immutable)
- Pattern matching exhaustiveness
- Type narrowing with isinstance
- Field access after type narrowing
"""

import time

import pytest

from effectful.domain.metrics_result import (
    MetricQueryResult,
    MetricRecorded,
    MetricRecordingFailed,
    MetricResult,
    QueryFailure,
    QuerySuccess,
)


# MetricRecorded tests
def test_metric_recorded_creation() -> None:
    """MetricRecorded can be created with timestamp."""
    timestamp = time.time()
    result = MetricRecorded(timestamp=timestamp)
    assert result.timestamp == timestamp


def test_metric_recorded_is_frozen() -> None:
    """MetricRecorded is immutable (frozen dataclass)."""
    result = MetricRecorded(timestamp=123.45)
    with pytest.raises(AttributeError, match="cannot assign"):
        result.timestamp = 999.99  # type: ignore


def test_metric_recorded_equality() -> None:
    """Two MetricRecorded instances with same timestamp are equal."""
    result1 = MetricRecorded(timestamp=123.45)
    result2 = MetricRecorded(timestamp=123.45)
    assert result1 == result2


def test_metric_recorded_inequality() -> None:
    """MetricRecorded instances with different timestamps are not equal."""
    result1 = MetricRecorded(timestamp=123.45)
    result2 = MetricRecorded(timestamp=678.90)
    assert result1 != result2


# MetricRecordingFailed tests
def test_metric_recording_failed_creation() -> None:
    """MetricRecordingFailed can be created with reason."""
    result = MetricRecordingFailed(reason="metric_not_registered")
    assert result.reason == "metric_not_registered"


def test_metric_recording_failed_is_frozen() -> None:
    """MetricRecordingFailed is immutable (frozen dataclass)."""
    result = MetricRecordingFailed(reason="metric_not_registered")
    with pytest.raises(AttributeError, match="cannot assign"):
        result.reason = "other_reason"  # type: ignore


def test_metric_recording_failed_all_reason_types() -> None:
    """MetricRecordingFailed handles all documented reason strings."""
    reasons = [
        "metric_not_registered",
        "type_mismatch",
        "missing_label: method",
        "unexpected_label: extra",
        "invalid_value: negative",
        "cardinality_limit_exceeded",
        "collector_error: connection timeout",
    ]
    for reason in reasons:
        result = MetricRecordingFailed(reason=reason)
        assert result.reason == reason


# QuerySuccess tests
def test_query_success_creation() -> None:
    """QuerySuccess can be created with metrics dict and timestamp."""
    metrics = {"requests_total": 100.0, "errors_total": 5.0}
    timestamp = time.time()
    result = QuerySuccess(metrics=metrics, timestamp=timestamp)
    assert result.metrics == metrics
    assert result.timestamp == timestamp


def test_query_success_is_frozen() -> None:
    """QuerySuccess is immutable (frozen dataclass)."""
    result = QuerySuccess(metrics={"test_total": 1.0}, timestamp=123.45)
    with pytest.raises(AttributeError, match="cannot assign"):
        result.timestamp = 999.99  # type: ignore


def test_query_success_empty_metrics() -> None:
    """QuerySuccess can have empty metrics dict."""
    result = QuerySuccess(metrics={}, timestamp=123.45)
    assert result.metrics == {}


# QueryFailure tests
def test_query_failure_creation() -> None:
    """QueryFailure can be created with reason."""
    result = QueryFailure(reason="metric_not_found")
    assert result.reason == "metric_not_found"


def test_query_failure_is_frozen() -> None:
    """QueryFailure is immutable (frozen dataclass)."""
    result = QueryFailure(reason="metric_not_found")
    with pytest.raises(AttributeError, match="cannot assign"):
        result.reason = "other_reason"  # type: ignore


def test_query_failure_all_reason_types() -> None:
    """QueryFailure handles all documented reason strings."""
    reasons = [
        "metric_not_found",
        "collector_unavailable",
        "invalid_query: missing metric_name",
    ]
    for reason in reasons:
        result = QueryFailure(reason=reason)
        assert result.reason == reason


# Pattern matching tests
def test_metric_result_pattern_matching_recorded() -> None:
    """MetricResult pattern matching handles MetricRecorded case."""
    result: MetricResult = MetricRecorded(timestamp=123.45)
    match result:
        case MetricRecorded(timestamp=ts):
            assert ts == 123.45
        case MetricRecordingFailed(reason=_):
            pytest.fail("Should not match MetricRecordingFailed")


def test_metric_result_pattern_matching_failed() -> None:
    """MetricResult pattern matching handles MetricRecordingFailed case."""
    result: MetricResult = MetricRecordingFailed(reason="metric_not_registered")
    match result:
        case MetricRecorded(timestamp=_):
            pytest.fail("Should not match MetricRecorded")
        case MetricRecordingFailed(reason=r):
            assert r == "metric_not_registered"


def test_metric_query_result_pattern_matching_success() -> None:
    """MetricQueryResult pattern matching handles QuerySuccess case."""
    result: MetricQueryResult = QuerySuccess(metrics={"test_total": 1.0}, timestamp=123.45)
    match result:
        case QuerySuccess(metrics=m, timestamp=ts):
            assert m == {"test_total": 1.0}
            assert ts == 123.45
        case QueryFailure(reason=_):
            pytest.fail("Should not match QueryFailure")


def test_metric_query_result_pattern_matching_failure() -> None:
    """MetricQueryResult pattern matching handles QueryFailure case."""
    result: MetricQueryResult = QueryFailure(reason="metric_not_found")
    match result:
        case QuerySuccess(metrics=_, timestamp=_):
            pytest.fail("Should not match QuerySuccess")
        case QueryFailure(reason=r):
            assert r == "metric_not_found"


# Type narrowing tests
def test_isinstance_narrowing_metric_recorded() -> None:
    """isinstance correctly narrows MetricResult to MetricRecorded."""
    result: MetricResult = MetricRecorded(timestamp=123.45)
    assert isinstance(result, MetricRecorded)
    # After isinstance check, can access timestamp directly
    assert result.timestamp == 123.45


def test_isinstance_narrowing_metric_recording_failed() -> None:
    """isinstance correctly narrows MetricResult to MetricRecordingFailed."""
    result: MetricResult = MetricRecordingFailed(reason="metric_not_registered")
    assert isinstance(result, MetricRecordingFailed)
    # After isinstance check, can access reason directly
    assert result.reason == "metric_not_registered"


def test_isinstance_narrowing_query_success() -> None:
    """isinstance correctly narrows MetricQueryResult to QuerySuccess."""
    result: MetricQueryResult = QuerySuccess(metrics={"test_total": 1.0}, timestamp=123.45)
    assert isinstance(result, QuerySuccess)
    # After isinstance check, can access metrics and timestamp directly
    assert result.metrics == {"test_total": 1.0}
    assert result.timestamp == 123.45


def test_isinstance_narrowing_query_failure() -> None:
    """isinstance correctly narrows MetricQueryResult to QueryFailure."""
    result: MetricQueryResult = QueryFailure(reason="metric_not_found")
    assert isinstance(result, QueryFailure)
    # After isinstance check, can access reason directly
    assert result.reason == "metric_not_found"
