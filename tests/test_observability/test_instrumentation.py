"""Tests for automatic instrumentation of interpreters.

Tests cover:
- InstrumentedInterpreter wrapping any interpreter
- Automatic metrics collection (counter, histogram)
- Effect type and result label tracking
- Pass-through behavior (no side effects on wrapped interpreter)
- Error handling and metrics failures
"""

from dataclasses import FrozenInstanceError

import pytest
from pytest_mock import MockerFixture

from effectful.algebraic.effect_return import EffectReturn
from effectful.algebraic.result import Err, Ok
from effectful.domain.metrics_result import MetricRecorded, MetricRecordingFailed
from effectful.effects.database import GetUserById
from effectful.effects.system import GetCurrentTime
from effectful.effects.websocket import SendText
from effectful.infrastructure.metrics import MetricsCollector
from effectful.interpreters.errors import UnhandledEffectError
from effectful.observability.instrumentation import (
    Interpreter,
    InstrumentedInterpreter,
    create_instrumented_interpreter,
)


# Successful wrapping and forwarding


@pytest.mark.asyncio
async def test_wraps_interpreter_and_forwards_calls(mocker: MockerFixture) -> None:
    """InstrumentedInterpreter forwards effect to wrapped interpreter."""
    # Setup mocks
    effect = GetUserById(user_id=mocker.Mock())
    expected_result = Ok(EffectReturn(value=mocker.Mock(), effect_name="GetUserById"))

    mock_wrapped = mocker.AsyncMock(spec=Interpreter)
    mock_wrapped.interpret.return_value = expected_result

    mock_collector = mocker.AsyncMock(spec=MetricsCollector)
    mock_collector.increment_counter.return_value = MetricRecorded(timestamp=1.0)
    mock_collector.observe_histogram.return_value = MetricRecorded(timestamp=1.0)

    # Create instrumented interpreter
    instrumented = InstrumentedInterpreter(
        wrapped=mock_wrapped,
        metrics_collector=mock_collector,
    )

    # Execute
    result = await instrumented.interpret(effect)

    # Verify forwarding
    assert result == expected_result
    mock_wrapped.interpret.assert_called_once_with(effect)


@pytest.mark.asyncio
async def test_returns_wrapped_interpreter_result_unchanged(
    mocker: MockerFixture,
) -> None:
    """InstrumentedInterpreter returns exact result from wrapped interpreter."""
    effect = SendText(text="hello")
    expected_result = Ok(EffectReturn(value=None, effect_name="SendText"))

    mock_wrapped = mocker.AsyncMock(spec=Interpreter)
    mock_wrapped.interpret.return_value = expected_result

    mock_collector = mocker.AsyncMock(spec=MetricsCollector)
    mock_collector.increment_counter.return_value = MetricRecorded(timestamp=1.0)
    mock_collector.observe_histogram.return_value = MetricRecorded(timestamp=1.0)

    instrumented = InstrumentedInterpreter(
        wrapped=mock_wrapped,
        metrics_collector=mock_collector,
    )

    result = await instrumented.interpret(effect)

    assert result is expected_result  # Exact same object


# Counter metrics collection


@pytest.mark.asyncio
async def test_increments_counter_on_success(mocker: MockerFixture) -> None:
    """InstrumentedInterpreter records counter with ok result on success."""
    effect = GetCurrentTime()

    mock_wrapped = mocker.AsyncMock(spec=Interpreter)
    mock_wrapped.interpret.return_value = Ok(
        EffectReturn(value=mocker.Mock(), effect_name="GetCurrentTime")
    )

    mock_collector = mocker.AsyncMock(spec=MetricsCollector)
    mock_collector.increment_counter.return_value = MetricRecorded(timestamp=1.0)
    mock_collector.observe_histogram.return_value = MetricRecorded(timestamp=1.0)

    instrumented = InstrumentedInterpreter(
        wrapped=mock_wrapped,
        metrics_collector=mock_collector,
    )

    await instrumented.interpret(effect)

    # Verify counter called
    mock_collector.increment_counter.assert_called_once()
    call_args = mock_collector.increment_counter.call_args
    assert call_args[1]["metric_name"] == "effectful_effects_total"
    assert call_args[1]["labels"] == {"effect_type": "GetCurrentTime", "result": "ok"}
    assert call_args[1]["value"] == 1.0


@pytest.mark.asyncio
async def test_increments_counter_on_error(mocker: MockerFixture) -> None:
    """InstrumentedInterpreter records counter with error result on failure."""
    effect = GetUserById(user_id=mocker.Mock())

    mock_wrapped = mocker.AsyncMock(spec=Interpreter)
    mock_wrapped.interpret.return_value = Err(
        UnhandledEffectError(effect=effect, available_interpreters=["TestInterpreter"])
    )

    mock_collector = mocker.AsyncMock(spec=MetricsCollector)
    mock_collector.increment_counter.return_value = MetricRecorded(timestamp=1.0)
    mock_collector.observe_histogram.return_value = MetricRecorded(timestamp=1.0)

    instrumented = InstrumentedInterpreter(
        wrapped=mock_wrapped,
        metrics_collector=mock_collector,
    )

    await instrumented.interpret(effect)

    # Verify counter called with error label
    mock_collector.increment_counter.assert_called_once()
    call_args = mock_collector.increment_counter.call_args
    assert call_args[1]["labels"]["result"] == "error"


# Histogram metrics collection


@pytest.mark.asyncio
async def test_observes_histogram_with_duration(mocker: MockerFixture) -> None:
    """InstrumentedInterpreter records effect duration in histogram."""
    effect = SendText(text="test")

    mock_wrapped = mocker.AsyncMock(spec=Interpreter)
    mock_wrapped.interpret.return_value = Ok(EffectReturn(value=None, effect_name="SendText"))

    mock_collector = mocker.AsyncMock(spec=MetricsCollector)
    mock_collector.increment_counter.return_value = MetricRecorded(timestamp=1.0)
    mock_collector.observe_histogram.return_value = MetricRecorded(timestamp=1.0)

    instrumented = InstrumentedInterpreter(
        wrapped=mock_wrapped,
        metrics_collector=mock_collector,
    )

    await instrumented.interpret(effect)

    # Verify histogram called
    mock_collector.observe_histogram.assert_called_once()
    call_args = mock_collector.observe_histogram.call_args
    assert call_args[1]["metric_name"] == "effectful_effect_duration_seconds"
    assert call_args[1]["labels"] == {"effect_type": "SendText"}
    # Duration should be > 0
    assert call_args[1]["value"] > 0.0


@pytest.mark.asyncio
async def test_histogram_duration_is_reasonable(mocker: MockerFixture) -> None:
    """InstrumentedInterpreter records reasonable duration values."""
    effect = GetCurrentTime()

    mock_wrapped = mocker.AsyncMock(spec=Interpreter)
    mock_wrapped.interpret.return_value = Ok(
        EffectReturn(value=mocker.Mock(), effect_name="GetCurrentTime")
    )

    mock_collector = mocker.AsyncMock(spec=MetricsCollector)
    mock_collector.increment_counter.return_value = MetricRecorded(timestamp=1.0)
    mock_collector.observe_histogram.return_value = MetricRecorded(timestamp=1.0)

    instrumented = InstrumentedInterpreter(
        wrapped=mock_wrapped,
        metrics_collector=mock_collector,
    )

    await instrumented.interpret(effect)

    call_args = mock_collector.observe_histogram.call_args
    duration = call_args[1]["value"]

    # Duration should be very small (< 1 second for simple mock)
    assert 0.0 < duration < 1.0


# Effect type label tracking


@pytest.mark.asyncio
async def test_tracks_different_effect_types_separately(mocker: MockerFixture) -> None:
    """InstrumentedInterpreter labels metrics with effect class name."""
    effects = [
        (GetCurrentTime(), "GetCurrentTime"),
        (SendText(text="hello"), "SendText"),
        (GetUserById(user_id=mocker.Mock()), "GetUserById"),
    ]

    mock_wrapped = mocker.AsyncMock(spec=Interpreter)
    mock_wrapped.interpret.return_value = Ok(EffectReturn(value=None, effect_name="test"))

    mock_collector = mocker.AsyncMock(spec=MetricsCollector)
    mock_collector.increment_counter.return_value = MetricRecorded(timestamp=1.0)
    mock_collector.observe_histogram.return_value = MetricRecorded(timestamp=1.0)

    instrumented = InstrumentedInterpreter(
        wrapped=mock_wrapped,
        metrics_collector=mock_collector,
    )

    for effect, expected_type in effects:
        mock_collector.reset_mock()
        await instrumented.interpret(effect)

        # Check counter labels
        counter_call = mock_collector.increment_counter.call_args
        assert counter_call[1]["labels"]["effect_type"] == expected_type

        # Check histogram labels
        histogram_call = mock_collector.observe_histogram.call_args
        assert histogram_call[1]["labels"]["effect_type"] == expected_type


# Metrics failure handling


@pytest.mark.asyncio
async def test_continues_when_counter_fails(mocker: MockerFixture) -> None:
    """InstrumentedInterpreter continues execution if counter recording fails."""
    effect = SendText(text="test")
    expected_result = Ok(EffectReturn(value=None, effect_name="SendText"))

    mock_wrapped = mocker.AsyncMock(spec=Interpreter)
    mock_wrapped.interpret.return_value = expected_result

    mock_collector = mocker.AsyncMock(spec=MetricsCollector)
    # Counter fails
    mock_collector.increment_counter.return_value = MetricRecordingFailed(
        reason="metric_not_registered"
    )
    # Histogram succeeds
    mock_collector.observe_histogram.return_value = MetricRecorded(timestamp=1.0)

    instrumented = InstrumentedInterpreter(
        wrapped=mock_wrapped,
        metrics_collector=mock_collector,
    )

    result = await instrumented.interpret(effect)

    # Result unchanged
    assert result == expected_result


@pytest.mark.asyncio
async def test_continues_when_histogram_fails(mocker: MockerFixture) -> None:
    """InstrumentedInterpreter continues execution if histogram recording fails."""
    effect = GetCurrentTime()
    expected_result = Ok(EffectReturn(value=mocker.Mock(), effect_name="GetCurrentTime"))

    mock_wrapped = mocker.AsyncMock(spec=Interpreter)
    mock_wrapped.interpret.return_value = expected_result

    mock_collector = mocker.AsyncMock(spec=MetricsCollector)
    # Counter succeeds
    mock_collector.increment_counter.return_value = MetricRecorded(timestamp=1.0)
    # Histogram fails
    mock_collector.observe_histogram.return_value = MetricRecordingFailed(reason="invalid_labels")

    instrumented = InstrumentedInterpreter(
        wrapped=mock_wrapped,
        metrics_collector=mock_collector,
    )

    result = await instrumented.interpret(effect)

    # Result unchanged
    assert result == expected_result


@pytest.mark.asyncio
async def test_continues_when_all_metrics_fail(mocker: MockerFixture) -> None:
    """InstrumentedInterpreter continues execution if all metrics fail."""
    effect = SendText(text="test")
    expected_result = Ok(EffectReturn(value=None, effect_name="SendText"))

    mock_wrapped = mocker.AsyncMock(spec=Interpreter)
    mock_wrapped.interpret.return_value = expected_result

    mock_collector = mocker.AsyncMock(spec=MetricsCollector)
    # Both fail
    mock_collector.increment_counter.return_value = MetricRecordingFailed(
        reason="metric_not_registered"
    )
    mock_collector.observe_histogram.return_value = MetricRecordingFailed(
        reason="metric_not_registered"
    )

    instrumented = InstrumentedInterpreter(
        wrapped=mock_wrapped,
        metrics_collector=mock_collector,
    )

    result = await instrumented.interpret(effect)

    # Result unchanged
    assert result == expected_result


# Factory function


def test_create_instrumented_interpreter_returns_correct_type(
    mocker: MockerFixture,
) -> None:
    """create_instrumented_interpreter factory returns InstrumentedInterpreter."""
    mock_wrapped = mocker.AsyncMock(spec=Interpreter)
    mock_collector = mocker.AsyncMock(spec=MetricsCollector)

    result = create_instrumented_interpreter(
        wrapped=mock_wrapped,
        metrics_collector=mock_collector,
    )

    assert isinstance(result, InstrumentedInterpreter)
    assert result.wrapped is mock_wrapped
    assert result.metrics_collector is mock_collector


def test_create_instrumented_interpreter_with_different_interpreters(
    mocker: MockerFixture,
) -> None:
    """create_instrumented_interpreter works with any interpreter."""
    interpreters = [
        mocker.AsyncMock(spec=Interpreter),
        mocker.AsyncMock(spec=Interpreter),
        mocker.AsyncMock(spec=Interpreter),
    ]

    mock_collector = mocker.AsyncMock(spec=MetricsCollector)

    for mock_interp in interpreters:
        result = create_instrumented_interpreter(
            wrapped=mock_interp,
            metrics_collector=mock_collector,
        )
        assert result.wrapped is mock_interp


# Immutability


def test_instrumented_interpreter_is_frozen(mocker: MockerFixture) -> None:
    """InstrumentedInterpreter is immutable (frozen dataclass)."""
    mock_wrapped = mocker.AsyncMock(spec=Interpreter)
    mock_collector = mocker.AsyncMock(spec=MetricsCollector)

    instrumented = InstrumentedInterpreter(
        wrapped=mock_wrapped,
        metrics_collector=mock_collector,
    )

    with pytest.raises((FrozenInstanceError, AttributeError)):
        setattr(instrumented, "wrapped", mocker.AsyncMock(spec=Interpreter))


# Edge cases


@pytest.mark.asyncio
async def test_handles_multiple_effects_sequentially(mocker: MockerFixture) -> None:
    """InstrumentedInterpreter handles multiple effect executions correctly."""
    effects = [SendText(text="one"), SendText(text="two"), SendText(text="three")]

    mock_wrapped = mocker.AsyncMock(spec=Interpreter)
    mock_wrapped.interpret.return_value = Ok(EffectReturn(value=None, effect_name="SendText"))

    mock_collector = mocker.AsyncMock(spec=MetricsCollector)
    mock_collector.increment_counter.return_value = MetricRecorded(timestamp=1.0)
    mock_collector.observe_histogram.return_value = MetricRecorded(timestamp=1.0)

    instrumented = InstrumentedInterpreter(
        wrapped=mock_wrapped,
        metrics_collector=mock_collector,
    )

    for effect in effects:
        result = await instrumented.interpret(effect)
        assert isinstance(result, Ok)

    # Verify called 3 times
    assert mock_collector.increment_counter.call_count == 3
    assert mock_collector.observe_histogram.call_count == 3


@pytest.mark.asyncio
async def test_preserves_error_details_from_wrapped_interpreter(
    mocker: MockerFixture,
) -> None:
    """InstrumentedInterpreter preserves exact error from wrapped interpreter."""
    effect = GetUserById(user_id=mocker.Mock())
    expected_error = UnhandledEffectError(
        effect=effect,
        available_interpreters=["DatabaseInterpreter", "CacheInterpreter"],
    )

    mock_wrapped = mocker.AsyncMock(spec=Interpreter)
    mock_wrapped.interpret.return_value = Err(expected_error)

    mock_collector = mocker.AsyncMock(spec=MetricsCollector)
    mock_collector.increment_counter.return_value = MetricRecorded(timestamp=1.0)
    mock_collector.observe_histogram.return_value = MetricRecorded(timestamp=1.0)

    instrumented = InstrumentedInterpreter(
        wrapped=mock_wrapped,
        metrics_collector=mock_collector,
    )

    result = await instrumented.interpret(effect)

    # Exact error preserved
    assert isinstance(result, Err)
    assert result.error == expected_error


# Performance characteristics


@pytest.mark.asyncio
async def test_metrics_collection_does_not_block_execution(
    mocker: MockerFixture,
) -> None:
    """InstrumentedInterpreter does not wait for metrics before returning."""
    effect = SendText(text="test")

    mock_wrapped = mocker.AsyncMock(spec=Interpreter)
    mock_wrapped.interpret.return_value = Ok(EffectReturn(value=None, effect_name="SendText"))

    # Slow metrics collector
    mock_collector = mocker.AsyncMock(spec=MetricsCollector)

    async def slow_increment(*args: object, **kwargs: object) -> MetricRecorded:
        # Simulate slow metrics recording
        import asyncio

        await asyncio.sleep(0.001)
        return MetricRecorded(timestamp=1.0)

    mock_collector.increment_counter.side_effect = slow_increment
    mock_collector.observe_histogram.return_value = MetricRecorded(timestamp=1.0)

    instrumented = InstrumentedInterpreter(
        wrapped=mock_wrapped,
        metrics_collector=mock_collector,
    )

    # Should complete quickly despite slow metrics
    result = await instrumented.interpret(effect)
    assert isinstance(result, Ok)


# Integration-style tests with multiple effects


@pytest.mark.asyncio
async def test_tracks_success_and_error_rates_correctly(mocker: MockerFixture) -> None:
    """InstrumentedInterpreter correctly labels successes and errors."""
    effects_and_results = [
        (SendText(text="one"), Ok(EffectReturn(value=None, effect_name="SendText"))),
        (SendText(text="two"), Ok(EffectReturn(value=None, effect_name="SendText"))),
        (
            GetUserById(user_id=mocker.Mock()),
            Err(UnhandledEffectError(effect=mocker.Mock(), available_interpreters=[])),
        ),
        (SendText(text="three"), Ok(EffectReturn(value=None, effect_name="SendText"))),
        (
            GetCurrentTime(),
            Err(UnhandledEffectError(effect=mocker.Mock(), available_interpreters=[])),
        ),
    ]

    mock_wrapped = mocker.AsyncMock(spec=Interpreter)
    mock_collector = mocker.AsyncMock(spec=MetricsCollector)
    mock_collector.increment_counter.return_value = MetricRecorded(timestamp=1.0)
    mock_collector.observe_histogram.return_value = MetricRecorded(timestamp=1.0)

    instrumented = InstrumentedInterpreter(
        wrapped=mock_wrapped,
        metrics_collector=mock_collector,
    )

    ok_count = 0
    error_count = 0

    for effect, result in effects_and_results:
        mock_wrapped.interpret.return_value = result
        await instrumented.interpret(effect)

        call_args = mock_collector.increment_counter.call_args
        result_label = call_args[1]["labels"]["result"]

        if result_label == "ok":
            ok_count += 1
        elif result_label == "error":
            error_count += 1

    assert ok_count == 3
    assert error_count == 2


@pytest.mark.asyncio
async def test_mixed_effect_types_tracked_independently(mocker: MockerFixture) -> None:
    """InstrumentedInterpreter tracks each effect type with correct labels."""
    effects = [
        SendText(text="test"),
        GetCurrentTime(),
        GetUserById(user_id=mocker.Mock()),
        SendText(text="test2"),
    ]

    mock_wrapped = mocker.AsyncMock(spec=Interpreter)
    mock_wrapped.interpret.return_value = Ok(EffectReturn(value=None, effect_name="test"))

    mock_collector = mocker.AsyncMock(spec=MetricsCollector)
    mock_collector.increment_counter.return_value = MetricRecorded(timestamp=1.0)
    mock_collector.observe_histogram.return_value = MetricRecorded(timestamp=1.0)

    instrumented = InstrumentedInterpreter(
        wrapped=mock_wrapped,
        metrics_collector=mock_collector,
    )

    effect_type_counts: dict[str, int] = {}

    for effect in effects:
        await instrumented.interpret(effect)

        call_args = mock_collector.increment_counter.call_args
        effect_type = call_args[1]["labels"]["effect_type"]

        effect_type_counts[effect_type] = effect_type_counts.get(effect_type, 0) + 1

    assert effect_type_counts["SendText"] == 2
    assert effect_type_counts["GetCurrentTime"] == 1
    assert effect_type_counts["GetUserById"] == 1
