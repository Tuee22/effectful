"""Tests for Metrics interpreter.

This module tests the MetricsInterpreter using pytest mocks (via pytest-mock).
Tests cover:
- Counter increment success and failure
- Gauge record success and failure
- Histogram observe success and failure
- Summary record success and failure
- Query metrics success and failure
- Reset metrics
- Unhandled effects
- Immutability
"""

from dataclasses import FrozenInstanceError

import pytest
from pytest_mock import MockerFixture

from effectful.algebraic.effect_return import EffectReturn
from effectful.algebraic.result import Err, Ok
from effectful.domain.metrics_result import (
    MetricRecorded,
    MetricRecordingFailed,
    QueryFailure,
    QuerySuccess,
)
from effectful.effects.metrics import (
    IncrementCounter,
    ObserveHistogram,
    QueryMetrics,
    RecordGauge,
    RecordSummary,
    ResetMetrics,
)
from effectful.effects.websocket import SendText
from effectful.infrastructure.metrics import MetricsCollector
from effectful.interpreters.errors import UnhandledEffectError
from effectful.interpreters.metrics import MetricsInterpreter


class TestIncrementCounter:
    """Tests for IncrementCounter effect."""

    @pytest.mark.asyncio()
    async def test_increment_counter_success(self, mocker: MockerFixture) -> None:
        """Interpreter returns MetricRecorded when counter incremented successfully."""
        mock_collector = mocker.AsyncMock(spec=MetricsCollector)
        mock_collector.increment_counter.return_value = MetricRecorded(timestamp=123.45)

        interpreter = MetricsInterpreter(collector=mock_collector)

        effect = IncrementCounter(
            metric_name="requests_total",
            labels={"method": "GET", "status": "200"},
            value=1.0,
        )
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Ok(
                EffectReturn(value=MetricRecorded(timestamp=123.45), effect_name="IncrementCounter")
            ):
                pass  # Success
            case _:
                pytest.fail(f"Expected Ok with MetricRecorded, got {result}")

        # Verify mock called correctly
        mock_collector.increment_counter.assert_called_once_with(
            metric_name="requests_total",
            labels={"method": "GET", "status": "200"},
            value=1.0,
        )

    @pytest.mark.asyncio()
    async def test_increment_counter_failure(self, mocker: MockerFixture) -> None:
        """Interpreter returns MetricRecordingFailed when validation fails."""
        mock_collector = mocker.AsyncMock(spec=MetricsCollector)
        mock_collector.increment_counter.return_value = MetricRecordingFailed(
            reason="Counter 'unknown' not registered"
        )

        interpreter = MetricsInterpreter(collector=mock_collector)

        effect = IncrementCounter(
            metric_name="unknown",
            labels={"method": "GET"},
            value=1.0,
        )
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Ok(
                EffectReturn(value=MetricRecordingFailed(reason=r), effect_name="IncrementCounter")
            ):
                assert "not registered" in r
            case _:
                pytest.fail(f"Expected Ok with MetricRecordingFailed, got {result}")

    @pytest.mark.asyncio()
    async def test_increment_counter_negative_value(self, mocker: MockerFixture) -> None:
        """Interpreter returns MetricRecordingFailed for negative counter value."""
        mock_collector = mocker.AsyncMock(spec=MetricsCollector)
        mock_collector.increment_counter.return_value = MetricRecordingFailed(
            reason="Counter value must be >= 0, got -1.0"
        )

        interpreter = MetricsInterpreter(collector=mock_collector)

        effect = IncrementCounter(
            metric_name="requests_total",
            labels={"method": "GET", "status": "200"},
            value=-1.0,
        )
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Ok(
                EffectReturn(value=MetricRecordingFailed(reason=r), effect_name="IncrementCounter")
            ):
                assert ">= 0" in r
            case _:
                pytest.fail(f"Expected Ok with MetricRecordingFailed, got {result}")


class TestRecordGauge:
    """Tests for RecordGauge effect."""

    @pytest.mark.asyncio()
    async def test_record_gauge_success(self, mocker: MockerFixture) -> None:
        """Interpreter returns MetricRecorded when gauge recorded successfully."""
        mock_collector = mocker.AsyncMock(spec=MetricsCollector)
        mock_collector.record_gauge.return_value = MetricRecorded(timestamp=123.45)

        interpreter = MetricsInterpreter(collector=mock_collector)

        effect = RecordGauge(
            metric_name="active_connections",
            labels={"protocol": "http"},
            value=42.0,
        )
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Ok(
                EffectReturn(value=MetricRecorded(timestamp=123.45), effect_name="RecordGauge")
            ):
                pass  # Success
            case _:
                pytest.fail(f"Expected Ok with MetricRecorded, got {result}")

        # Verify mock called correctly
        mock_collector.record_gauge.assert_called_once_with(
            metric_name="active_connections",
            labels={"protocol": "http"},
            value=42.0,
        )

    @pytest.mark.asyncio()
    async def test_record_gauge_negative_value(self, mocker: MockerFixture) -> None:
        """Interpreter allows negative gauge values (unlike counters)."""
        mock_collector = mocker.AsyncMock(spec=MetricsCollector)
        mock_collector.record_gauge.return_value = MetricRecorded(timestamp=123.45)

        interpreter = MetricsInterpreter(collector=mock_collector)

        effect = RecordGauge(
            metric_name="temperature_celsius",
            labels={"location": "arctic"},
            value=-15.5,
        )
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Ok(EffectReturn(value=MetricRecorded(), effect_name="RecordGauge")):
                pass  # Success
            case _:
                pytest.fail(f"Expected Ok with MetricRecorded, got {result}")

    @pytest.mark.asyncio()
    async def test_record_gauge_failure(self, mocker: MockerFixture) -> None:
        """Interpreter returns MetricRecordingFailed when gauge validation fails."""
        mock_collector = mocker.AsyncMock(spec=MetricsCollector)
        mock_collector.record_gauge.return_value = MetricRecordingFailed(
            reason="Gauge 'unknown' not registered"
        )

        interpreter = MetricsInterpreter(collector=mock_collector)

        effect = RecordGauge(
            metric_name="unknown",
            labels={"label": "value"},
            value=10.0,
        )
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Ok(EffectReturn(value=MetricRecordingFailed(reason=r), effect_name="RecordGauge")):
                assert "not registered" in r
            case _:
                pytest.fail(f"Expected Ok with MetricRecordingFailed, got {result}")


class TestObserveHistogram:
    """Tests for ObserveHistogram effect."""

    @pytest.mark.asyncio()
    async def test_observe_histogram_success(self, mocker: MockerFixture) -> None:
        """Interpreter returns MetricRecorded when histogram observed successfully."""
        mock_collector = mocker.AsyncMock(spec=MetricsCollector)
        mock_collector.observe_histogram.return_value = MetricRecorded(timestamp=123.45)

        interpreter = MetricsInterpreter(collector=mock_collector)

        effect = ObserveHistogram(
            metric_name="request_duration_seconds",
            labels={"endpoint": "/api/users"},
            value=0.125,
        )
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Ok(
                EffectReturn(value=MetricRecorded(timestamp=123.45), effect_name="ObserveHistogram")
            ):
                pass  # Success
            case _:
                pytest.fail(f"Expected Ok with MetricRecorded, got {result}")

        # Verify mock called correctly
        mock_collector.observe_histogram.assert_called_once_with(
            metric_name="request_duration_seconds",
            labels={"endpoint": "/api/users"},
            value=0.125,
        )

    @pytest.mark.asyncio()
    async def test_observe_histogram_failure(self, mocker: MockerFixture) -> None:
        """Interpreter returns MetricRecordingFailed when histogram validation fails."""
        mock_collector = mocker.AsyncMock(spec=MetricsCollector)
        mock_collector.observe_histogram.return_value = MetricRecordingFailed(
            reason="Histogram 'unknown' not registered"
        )

        interpreter = MetricsInterpreter(collector=mock_collector)

        effect = ObserveHistogram(
            metric_name="unknown",
            labels={"endpoint": "/api/users"},
            value=0.1,
        )
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Ok(
                EffectReturn(value=MetricRecordingFailed(reason=r), effect_name="ObserveHistogram")
            ):
                assert "not registered" in r
            case _:
                pytest.fail(f"Expected Ok with MetricRecordingFailed, got {result}")


class TestRecordSummary:
    """Tests for RecordSummary effect."""

    @pytest.mark.asyncio()
    async def test_record_summary_success(self, mocker: MockerFixture) -> None:
        """Interpreter returns MetricRecorded when summary recorded successfully."""
        mock_collector = mocker.AsyncMock(spec=MetricsCollector)
        mock_collector.record_summary.return_value = MetricRecorded(timestamp=123.45)

        interpreter = MetricsInterpreter(collector=mock_collector)

        effect = RecordSummary(
            metric_name="response_size_bytes",
            labels={"content_type": "application/json"},
            value=1024.0,
        )
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Ok(
                EffectReturn(value=MetricRecorded(timestamp=123.45), effect_name="RecordSummary")
            ):
                pass  # Success
            case _:
                pytest.fail(f"Expected Ok with MetricRecorded, got {result}")

        # Verify mock called correctly
        mock_collector.record_summary.assert_called_once_with(
            metric_name="response_size_bytes",
            labels={"content_type": "application/json"},
            value=1024.0,
        )

    @pytest.mark.asyncio()
    async def test_record_summary_failure(self, mocker: MockerFixture) -> None:
        """Interpreter returns MetricRecordingFailed when summary validation fails."""
        mock_collector = mocker.AsyncMock(spec=MetricsCollector)
        mock_collector.record_summary.return_value = MetricRecordingFailed(
            reason="Summary 'unknown' not registered"
        )

        interpreter = MetricsInterpreter(collector=mock_collector)

        effect = RecordSummary(
            metric_name="unknown",
            labels={"content_type": "text/html"},
            value=512.0,
        )
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Ok(
                EffectReturn(value=MetricRecordingFailed(reason=r), effect_name="RecordSummary")
            ):
                assert "not registered" in r
            case _:
                pytest.fail(f"Expected Ok with MetricRecordingFailed, got {result}")


class TestQueryMetrics:
    """Tests for QueryMetrics effect."""

    @pytest.mark.asyncio()
    async def test_query_metrics_success(self, mocker: MockerFixture) -> None:
        """Interpreter returns QuerySuccess with metrics dict."""
        mock_collector = mocker.AsyncMock(spec=MetricsCollector)
        mock_collector.query_metrics.return_value = QuerySuccess(
            metrics={"requests_total{method=GET,status=200}": 42.0},
            timestamp=123.45,
        )

        interpreter = MetricsInterpreter(collector=mock_collector)

        effect = QueryMetrics(
            metric_name="requests_total",
            labels={"method": "GET", "status": "200"},
        )
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Ok(
                EffectReturn(
                    value=QuerySuccess(metrics=m, timestamp=123.45), effect_name="QueryMetrics"
                )
            ):
                assert m == {"requests_total{method=GET,status=200}": 42.0}
            case _:
                pytest.fail(f"Expected Ok with QuerySuccess, got {result}")

        # Verify mock called correctly
        mock_collector.query_metrics.assert_called_once_with(
            metric_name="requests_total",
            labels={"method": "GET", "status": "200"},
        )

    @pytest.mark.asyncio()
    async def test_query_metrics_all(self, mocker: MockerFixture) -> None:
        """Interpreter queries all metrics when metric_name is None."""
        mock_collector = mocker.AsyncMock(spec=MetricsCollector)
        mock_collector.query_metrics.return_value = QuerySuccess(
            metrics={
                "requests_total{method=GET,status=200}": 100.0,
                "requests_total{method=POST,status=201}": 50.0,
            },
            timestamp=123.45,
        )

        interpreter = MetricsInterpreter(collector=mock_collector)

        effect = QueryMetrics(metric_name=None, labels=None)
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Ok(EffectReturn(value=QuerySuccess(metrics=m), effect_name="QueryMetrics")):
                assert len(m) == 2
            case _:
                pytest.fail(f"Expected Ok with QuerySuccess, got {result}")

        # Verify mock called correctly
        mock_collector.query_metrics.assert_called_once_with(
            metric_name=None,
            labels=None,
        )

    @pytest.mark.asyncio()
    async def test_query_metrics_failure(self, mocker: MockerFixture) -> None:
        """Interpreter returns QueryFailure when metric not found."""
        mock_collector = mocker.AsyncMock(spec=MetricsCollector)
        mock_collector.query_metrics.return_value = QueryFailure(
            reason="Metric 'unknown' not found"
        )

        interpreter = MetricsInterpreter(collector=mock_collector)

        effect = QueryMetrics(metric_name="unknown", labels=None)
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Ok(EffectReturn(value=QueryFailure(reason=r), effect_name="QueryMetrics")):
                assert "not found" in r
            case _:
                pytest.fail(f"Expected Ok with QueryFailure, got {result}")


class TestResetMetrics:
    """Tests for ResetMetrics effect."""

    @pytest.mark.asyncio()
    async def test_reset_metrics_success(self, mocker: MockerFixture) -> None:
        """Interpreter returns MetricRecorded when metrics reset successfully."""
        mock_collector = mocker.AsyncMock(spec=MetricsCollector)
        mock_collector.reset_metrics.return_value = MetricRecorded(timestamp=123.45)

        interpreter = MetricsInterpreter(collector=mock_collector)

        effect = ResetMetrics()
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Ok(
                EffectReturn(value=MetricRecorded(timestamp=123.45), effect_name="ResetMetrics")
            ):
                pass  # Success
            case _:
                pytest.fail(f"Expected Ok with MetricRecorded, got {result}")

        # Verify mock called correctly
        mock_collector.reset_metrics.assert_called_once()

    @pytest.mark.asyncio()
    async def test_reset_metrics_not_supported(self, mocker: MockerFixture) -> None:
        """Interpreter returns MetricRecordingFailed when reset not supported (Prometheus)."""
        mock_collector = mocker.AsyncMock(spec=MetricsCollector)
        mock_collector.reset_metrics.return_value = MetricRecordingFailed(
            reason="reset_metrics() not supported for Prometheus"
        )

        interpreter = MetricsInterpreter(collector=mock_collector)

        effect = ResetMetrics()
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Ok(
                EffectReturn(value=MetricRecordingFailed(reason=r), effect_name="ResetMetrics")
            ):
                assert "not supported" in r
            case _:
                pytest.fail(f"Expected Ok with MetricRecordingFailed, got {result}")


class TestUnhandledEffect:
    """Tests for unhandled effects."""

    @pytest.mark.asyncio()
    async def test_unhandled_effect(self, mocker: MockerFixture) -> None:
        """Interpreter returns UnhandledEffectError for non-Metrics effects."""
        mock_collector = mocker.AsyncMock(spec=MetricsCollector)
        interpreter = MetricsInterpreter(collector=mock_collector)

        # Non-Metrics effect
        effect = SendText(text="Hello")
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Err(UnhandledEffectError(effect=e, available_interpreters=interpreters)):
                assert e == effect
                assert "MetricsInterpreter" in interpreters
            case _:
                pytest.fail(f"Expected UnhandledEffectError, got {result}")


class TestMetricsInterpreterImmutability:
    """Tests for MetricsInterpreter immutability."""

    def test_interpreter_is_immutable(self, mocker: MockerFixture) -> None:
        """MetricsInterpreter must be immutable (frozen dataclass)."""
        mock_collector = mocker.AsyncMock(spec=MetricsCollector)
        interpreter = MetricsInterpreter(collector=mock_collector)

        # Attempt to mutate should raise FrozenInstanceError
        with pytest.raises(FrozenInstanceError):
            interpreter.collector = mocker.AsyncMock(spec=MetricsCollector)  # type: ignore
