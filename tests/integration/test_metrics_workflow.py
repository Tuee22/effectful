"""Integration tests for metrics workflows with real InMemoryMetricsCollector.

This module tests metrics effect workflows using run_ws_program
with real InMemoryMetricsCollector infrastructure. Tests verify
end-to-end metric recording and querying.
"""

import time
from collections.abc import Generator
from uuid import uuid4

import pytest
from pytest_mock import MockerFixture

from effectful.adapters.in_memory_metrics import InMemoryMetricsCollector
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
from effectful.infrastructure.repositories import ChatMessageRepository, UserRepository
from effectful.infrastructure.websocket import WebSocketConnection
from effectful.interpreters.composite import create_composite_interpreter
from effectful.observability import (
    CounterDefinition,
    GaugeDefinition,
    HistogramDefinition,
    MetricsRegistry,
    SummaryDefinition,
)
from effectful.programs.program_types import AllEffects, EffectResult
from effectful.programs.runners import run_ws_program


@pytest.fixture
async def metrics_collector() -> InMemoryMetricsCollector:
    """Create InMemoryMetricsCollector with registered metrics."""
    collector = InMemoryMetricsCollector()

    # Register test metrics
    registry = MetricsRegistry(
        counters=(
            CounterDefinition(
                name="requests_total",
                help_text="Total HTTP requests",
                label_names=("method", "status"),
            ),
            CounterDefinition(
                name="tasks_processed_total",
                help_text="Total tasks processed",
                label_names=("task_type",),
            ),
        ),
        gauges=(
            GaugeDefinition(
                name="active_connections",
                help_text="Active connections",
                label_names=("service",),
            ),
        ),
        histograms=(
            HistogramDefinition(
                name="request_duration_seconds",
                help_text="HTTP request duration",
                label_names=("method",),
                buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
            ),
        ),
        summaries=(
            SummaryDefinition(
                name="task_processing_time",
                help_text="Task processing time",
                label_names=("task_type",),
                quantiles=(0.5, 0.9, 0.99),
            ),
        ),
    )

    await collector.register_metrics(registry)
    return collector


class TestMetricsWorkflowIntegration:
    """Integration tests for metrics workflows with real collector."""

    @pytest.mark.asyncio
    async def test_increment_counter_workflow(
        self, metrics_collector: InMemoryMetricsCollector, mocker: MockerFixture
    ) -> None:
        """Workflow increments counter in real collector."""
        # Create interpreter with real metrics collector
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=mocker.MagicMock(),
            metrics_collector=metrics_collector,
        )

        # Define workflow
        def increment_counter_program() -> Generator[AllEffects, EffectResult, bool]:
            # Increment counter
            result = yield IncrementCounter(
                metric_name="requests_total",
                labels={"method": "GET", "status": "200"},
                value=1.0,
            )

            match result:
                case MetricRecorded():
                    yield SendText(text="Counter incremented")
                    return True
                case MetricRecordingFailed():
                    yield SendText(text="Failed to increment counter")
                    return False
                case _:
                    return False

        # Act
        result = await run_ws_program(increment_counter_program(), interpreter)

        # Assert
        match result:
            case Ok(success):
                assert success is True
                mock_ws.send_text.assert_called_once_with("Counter incremented")

                # Verify in real collector
                assert metrics_collector.counters["requests_total"]["method=GET,status=200"] == 1.0
            case Err(error):
                pytest.fail(f"Expected Ok, got Err({error})")

    @pytest.mark.asyncio
    async def test_record_gauge_workflow(
        self, metrics_collector: InMemoryMetricsCollector, mocker: MockerFixture
    ) -> None:
        """Workflow records gauge value in real collector."""
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=mocker.MagicMock(),
            metrics_collector=metrics_collector,
        )

        # Define workflow
        def record_gauge_program() -> Generator[AllEffects, EffectResult, bool]:
            # Record gauge value
            result = yield RecordGauge(
                metric_name="active_connections", labels={"service": "api"}, value=42.0
            )

            match result:
                case MetricRecorded():
                    yield SendText(text="Gauge recorded")
                    return True
                case MetricRecordingFailed():
                    return False
                case _:
                    return False

        # Act
        result = await run_ws_program(record_gauge_program(), interpreter)

        # Assert
        match result:
            case Ok(success):
                assert success is True
                # Verify in real collector
                assert metrics_collector.gauges["active_connections"]["service=api"] == 42.0
            case Err(error):
                pytest.fail(f"Expected Ok, got Err({error})")

    @pytest.mark.asyncio
    async def test_observe_histogram_workflow(
        self, metrics_collector: InMemoryMetricsCollector, mocker: MockerFixture
    ) -> None:
        """Workflow observes histogram values in real collector."""
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=mocker.MagicMock(),
            metrics_collector=metrics_collector,
        )

        # Define workflow
        def observe_histogram_program() -> Generator[AllEffects, EffectResult, int]:
            # Observe multiple values
            observations = (0.023, 0.15, 0.8)
            count = 0

            for duration in observations:
                result = yield ObserveHistogram(
                    metric_name="request_duration_seconds",
                    labels={"method": "POST"},
                    value=duration,
                )
                match result:
                    case MetricRecorded():
                        count += 1
                    case MetricRecordingFailed():
                        pass

            return count

        # Act
        result = await run_ws_program(observe_histogram_program(), interpreter)

        # Assert
        match result:
            case Ok(count):
                assert count == 3
                # Verify in real collector
                observed = metrics_collector.histograms["request_duration_seconds"]["method=POST"]
                assert len(observed) == 3
                assert 0.023 in observed
                assert 0.15 in observed
                assert 0.8 in observed
            case Err(error):
                pytest.fail(f"Expected Ok, got Err({error})")

    @pytest.mark.asyncio
    async def test_record_summary_workflow(
        self, metrics_collector: InMemoryMetricsCollector, mocker: MockerFixture
    ) -> None:
        """Workflow records summary observations in real collector."""
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=mocker.MagicMock(),
            metrics_collector=metrics_collector,
        )

        # Define workflow
        def record_summary_program() -> Generator[AllEffects, EffectResult, bool]:
            # Record summary values
            result = yield RecordSummary(
                metric_name="task_processing_time", labels={"task_type": "email"}, value=1.234
            )

            match result:
                case MetricRecorded():
                    return True
                case MetricRecordingFailed():
                    return False
                case _:
                    return False

        # Act
        result = await run_ws_program(record_summary_program(), interpreter)

        # Assert
        match result:
            case Ok(success):
                assert success is True
                # Verify in real collector
                values = metrics_collector.summaries["task_processing_time"]["task_type=email"]
                assert len(values) == 1
                assert values[0] == 1.234
            case Err(error):
                pytest.fail(f"Expected Ok, got Err({error})")

    @pytest.mark.asyncio
    async def test_query_metrics_workflow(
        self, metrics_collector: InMemoryMetricsCollector, mocker: MockerFixture
    ) -> None:
        """Workflow queries metrics from real collector."""
        # Pre-populate metrics
        await metrics_collector.increment_counter(
            metric_name="requests_total", labels={"method": "GET", "status": "200"}, value=5.0
        )
        await metrics_collector.record_gauge(
            metric_name="active_connections", labels={"service": "api"}, value=10.0
        )

        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=mocker.MagicMock(),
            metrics_collector=metrics_collector,
        )

        # Define workflow
        def query_metrics_program() -> Generator[AllEffects, EffectResult, int]:
            # Query all metrics
            result = yield QueryMetrics(metric_name=None, labels=None)

            match result:
                case QuerySuccess(metrics=metrics):
                    return len(metrics)
                case QueryFailure():
                    return 0
                case _:
                    return 0

        # Act
        result = await run_ws_program(query_metrics_program(), interpreter)

        # Assert
        match result:
            case Ok(count):
                assert count >= 2  # At least counter and gauge
            case Err(error):
                pytest.fail(f"Expected Ok, got Err({error})")

    @pytest.mark.asyncio
    async def test_query_specific_metric_workflow(
        self, metrics_collector: InMemoryMetricsCollector, mocker: MockerFixture
    ) -> None:
        """Workflow queries specific metric from real collector."""
        # Pre-populate metric
        await metrics_collector.increment_counter(
            metric_name="requests_total", labels={"method": "POST", "status": "201"}, value=3.0
        )

        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=mocker.MagicMock(),
            metrics_collector=metrics_collector,
        )

        # Define workflow
        def query_specific_program() -> Generator[AllEffects, EffectResult, float]:
            # Query specific metric
            result = yield QueryMetrics(
                metric_name="requests_total", labels={"method": "POST", "status": "201"}
            )

            match result:
                case QuerySuccess(metrics=metrics):
                    # Extract value
                    key = "requests_total{method=POST,status=201}"
                    return metrics.get(key, 0.0)
                case QueryFailure():
                    return 0.0
                case _:
                    return 0.0

        # Act
        result = await run_ws_program(query_specific_program(), interpreter)

        # Assert
        match result:
            case Ok(value):
                assert value == 3.0
            case Err(error):
                pytest.fail(f"Expected Ok, got Err({error})")

    @pytest.mark.asyncio
    async def test_reset_metrics_workflow(
        self, metrics_collector: InMemoryMetricsCollector, mocker: MockerFixture
    ) -> None:
        """Workflow resets metrics in real collector."""
        # Pre-populate metrics
        await metrics_collector.increment_counter(
            metric_name="requests_total", labels={"method": "GET", "status": "200"}, value=10.0
        )

        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=mocker.MagicMock(),
            metrics_collector=metrics_collector,
        )

        # Define workflow
        def reset_metrics_program() -> Generator[AllEffects, EffectResult, bool]:
            # Reset all metrics
            result = yield ResetMetrics()

            match result:
                case MetricRecorded():
                    return True
                case MetricRecordingFailed():
                    return False
                case _:
                    return False

        # Act
        result = await run_ws_program(reset_metrics_program(), interpreter)

        # Assert
        match result:
            case Ok(success):
                assert success is True
                # Verify metrics are cleared
                assert len(metrics_collector.counters["requests_total"]) == 0
            case Err(error):
                pytest.fail(f"Expected Ok, got Err({error})")

    @pytest.mark.asyncio
    async def test_counter_negative_value_workflow(
        self, metrics_collector: InMemoryMetricsCollector, mocker: MockerFixture
    ) -> None:
        """Workflow handles counter negative value validation."""
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=mocker.MagicMock(),
            metrics_collector=metrics_collector,
        )

        # Define workflow
        def negative_counter_program() -> Generator[AllEffects, EffectResult, str]:
            # Try to increment counter with negative value
            result = yield IncrementCounter(
                metric_name="requests_total",
                labels={"method": "GET", "status": "200"},
                value=-1.0,
            )

            match result:
                case MetricRecorded():
                    return "success"
                case MetricRecordingFailed(reason=reason):
                    return reason
                case _:
                    return "unknown"

        # Act
        result = await run_ws_program(negative_counter_program(), interpreter)

        # Assert
        match result:
            case Ok(reason):
                assert "must be >= 0" in reason
            case Err(error):
                pytest.fail(f"Expected Ok, got Err({error})")

    @pytest.mark.asyncio
    async def test_unregistered_metric_workflow(
        self, metrics_collector: InMemoryMetricsCollector, mocker: MockerFixture
    ) -> None:
        """Workflow handles unregistered metric gracefully."""
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=mocker.MagicMock(),
            metrics_collector=metrics_collector,
        )

        # Define workflow
        def unregistered_metric_program() -> Generator[AllEffects, EffectResult, str]:
            # Try to increment unregistered counter
            result = yield IncrementCounter(
                metric_name="unknown_metric",
                labels={"foo": "bar"},
                value=1.0,
            )

            match result:
                case MetricRecorded():
                    return "success"
                case MetricRecordingFailed(reason=reason):
                    return reason
                case _:
                    return "unknown"

        # Act
        result = await run_ws_program(unregistered_metric_program(), interpreter)

        # Assert
        match result:
            case Ok(reason):
                assert "not registered" in reason
            case Err(error):
                pytest.fail(f"Expected Ok, got Err({error})")

    @pytest.mark.asyncio
    async def test_label_mismatch_workflow(
        self, metrics_collector: InMemoryMetricsCollector, mocker: MockerFixture
    ) -> None:
        """Workflow handles label mismatch validation."""
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=mocker.MagicMock(),
            metrics_collector=metrics_collector,
        )

        # Define workflow
        def label_mismatch_program() -> Generator[AllEffects, EffectResult, str]:
            # Try to increment counter with wrong labels
            result = yield IncrementCounter(
                metric_name="requests_total",
                labels={"wrong": "labels"},  # Expects method, status
                value=1.0,
            )

            match result:
                case MetricRecorded():
                    return "success"
                case MetricRecordingFailed(reason=reason):
                    return reason
                case _:
                    return "unknown"

        # Act
        result = await run_ws_program(label_mismatch_program(), interpreter)

        # Assert
        match result:
            case Ok(reason):
                assert "don't match" in reason
            case Err(error):
                pytest.fail(f"Expected Ok, got Err({error})")

    @pytest.mark.asyncio
    async def test_multi_metric_workflow(
        self, metrics_collector: InMemoryMetricsCollector, mocker: MockerFixture
    ) -> None:
        """Workflow records multiple metric types in sequence."""
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=mocker.MagicMock(),
            metrics_collector=metrics_collector,
        )

        # Define workflow
        def multi_metric_program() -> Generator[AllEffects, EffectResult, int]:
            success_count = 0

            # Increment counter
            counter_result = yield IncrementCounter(
                metric_name="requests_total",
                labels={"method": "GET", "status": "200"},
                value=1.0,
            )
            if isinstance(counter_result, MetricRecorded):
                success_count += 1

            # Record gauge
            gauge_result = yield RecordGauge(
                metric_name="active_connections", labels={"service": "api"}, value=5.0
            )
            if isinstance(gauge_result, MetricRecorded):
                success_count += 1

            # Observe histogram
            histogram_result = yield ObserveHistogram(
                metric_name="request_duration_seconds", labels={"method": "GET"}, value=0.042
            )
            if isinstance(histogram_result, MetricRecorded):
                success_count += 1

            # Record summary
            summary_result = yield RecordSummary(
                metric_name="task_processing_time", labels={"task_type": "email"}, value=2.5
            )
            if isinstance(summary_result, MetricRecorded):
                success_count += 1

            return success_count

        # Act
        result = await run_ws_program(multi_metric_program(), interpreter)

        # Assert
        match result:
            case Ok(count):
                assert count == 4  # All metrics succeeded
                # Verify all metrics were recorded
                assert metrics_collector.counters["requests_total"]["method=GET,status=200"] == 1.0
                assert metrics_collector.gauges["active_connections"]["service=api"] == 5.0
                assert (
                    len(metrics_collector.histograms["request_duration_seconds"]["method=GET"]) == 1
                )
                assert (
                    len(metrics_collector.summaries["task_processing_time"]["task_type=email"]) == 1
                )
            case Err(error):
                pytest.fail(f"Expected Ok, got Err({error})")

    @pytest.mark.asyncio
    async def test_query_not_found_workflow(
        self, metrics_collector: InMemoryMetricsCollector, mocker: MockerFixture
    ) -> None:
        """Workflow handles metric not found gracefully."""
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=mocker.MagicMock(),
            metrics_collector=metrics_collector,
        )

        # Define workflow
        def query_not_found_program() -> Generator[AllEffects, EffectResult, str]:
            # Query non-existent metric
            result = yield QueryMetrics(metric_name="does_not_exist", labels=None)

            match result:
                case QuerySuccess():
                    return "success"
                case QueryFailure(reason=reason):
                    return reason
                case _:
                    return "unknown"

        # Act
        result = await run_ws_program(query_not_found_program(), interpreter)

        # Assert
        match result:
            case Ok(reason):
                assert "not found" in reason
            case Err(error):
                pytest.fail(f"Expected Ok, got Err({error})")


__all__ = ["TestMetricsWorkflowIntegration"]
