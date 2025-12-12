"""Metrics interpreter implementation.

This module implements the interpreter for Metrics effects.
"""

from dataclasses import dataclass

from effectful.algebraic.effect_return import EffectReturn
from effectful.algebraic.result import Err, Ok, Result
from effectful.domain.optional_value import OptionalValue, from_optional_value
from effectful.domain.metrics_result import MetricQueryResult, MetricResult
from effectful.effects.base import Effect
from effectful.effects.metrics import (
    IncrementCounter,
    ObserveHistogram,
    QueryMetrics,
    RecordSummary,
    ResetMetrics,
    SetGauge,
)
from effectful.infrastructure.metrics import MetricsCollector
from effectful.interpreters.errors import InterpreterError, UnhandledEffectError
from effectful.programs.program_types import EffectResult


@dataclass(frozen=True)
class MetricsInterpreter:
    """Interpreter for Metrics effects.

    Routes metric recording operations to the configured MetricsCollector
    (InMemoryMetricsCollector for testing, PrometheusMetricsCollector for production).

    Attributes:
        collector: Metrics collector implementation (Prometheus or in-memory)
    """

    collector: MetricsCollector

    async def interpret(
        self, effect: Effect
    ) -> Result[EffectReturn[EffectResult], InterpreterError]:
        """Interpret a Metrics effect.

        Args:
            effect: The effect to interpret

        Returns:
            Ok(EffectReturn(value)) if successful
            Err(InterpreterError) if not a Metrics effect
        """
        match effect:
            case IncrementCounter(metric_name=name, labels=labels, value=value):
                return await self._handle_increment_counter(name, labels, value)
            case SetGauge(metric_name=name, labels=labels, value=value):
                return await self._handle_record_gauge(name, labels, value)
            case ObserveHistogram(metric_name=name, labels=labels, value=value):
                return await self._handle_observe_histogram(name, labels, value)
            case RecordSummary(metric_name=name, labels=labels, value=value):
                return await self._handle_record_summary(name, labels, value)
            case QueryMetrics(metric_name=name, labels=labels):
                return await self._handle_query_metrics(name, labels)
            case ResetMetrics():
                return await self._handle_reset_metrics()
            case _:
                return Err(
                    UnhandledEffectError(
                        effect=effect,
                        available_interpreters=["MetricsInterpreter"],
                    )
                )

    async def _handle_increment_counter(
        self, metric_name: str, labels: dict[str, str], value: float
    ) -> Result[EffectReturn[EffectResult], InterpreterError]:
        """Handle IncrementCounter effect.

        Returns MetricRecorded on success, MetricRecordingFailed on validation error.
        """
        result: MetricResult = await self.collector.increment_counter(
            metric_name=metric_name,
            labels=labels,
            value=value,
        )
        # Metrics operations don't throw - they return ADT result types
        # MetricRecorded | MetricRecordingFailed
        return Ok(EffectReturn(value=result, effect_name="IncrementCounter"))

    async def _handle_record_gauge(
        self, metric_name: str, labels: dict[str, str], value: float
    ) -> Result[EffectReturn[EffectResult], InterpreterError]:
        """Handle RecordGauge effect.

        Returns MetricRecorded on success, MetricRecordingFailed on validation error.
        """
        result: MetricResult = await self.collector.record_gauge(
            metric_name=metric_name,
            labels=labels,
            value=value,
        )
        return Ok(EffectReturn(value=result, effect_name="SetGauge"))

    async def _handle_observe_histogram(
        self, metric_name: str, labels: dict[str, str], value: float
    ) -> Result[EffectReturn[EffectResult], InterpreterError]:
        """Handle ObserveHistogram effect.

        Returns MetricRecorded on success, MetricRecordingFailed on validation error.
        """
        result: MetricResult = await self.collector.observe_histogram(
            metric_name=metric_name,
            labels=labels,
            value=value,
        )
        return Ok(EffectReturn(value=result, effect_name="ObserveHistogram"))

    async def _handle_record_summary(
        self, metric_name: str, labels: dict[str, str], value: float
    ) -> Result[EffectReturn[EffectResult], InterpreterError]:
        """Handle RecordSummary effect.

        Returns MetricRecorded on success, MetricRecordingFailed on validation error.
        """
        result: MetricResult = await self.collector.record_summary(
            metric_name=metric_name,
            labels=labels,
            value=value,
        )
        return Ok(EffectReturn(value=result, effect_name="RecordSummary"))

    async def _handle_query_metrics(
        self, metric_name: OptionalValue[str], labels: OptionalValue[dict[str, str]]
    ) -> Result[EffectReturn[EffectResult], InterpreterError]:
        """Handle QueryMetrics effect.

        Returns QuerySuccess with metrics dict, or QueryFailure if not found.
        """
        result: MetricQueryResult = await self.collector.query_metrics(
            metric_name=from_optional_value(metric_name),
            labels=from_optional_value(labels),
        )
        return Ok(EffectReturn(value=result, effect_name="QueryMetrics"))

    async def _handle_reset_metrics(
        self,
    ) -> Result[EffectReturn[EffectResult], InterpreterError]:
        """Handle ResetMetrics effect.

        TESTING ONLY. Returns MetricRecorded on success.
        """
        result: MetricResult = await self.collector.reset_metrics()
        return Ok(EffectReturn(value=result, effect_name="ResetMetrics"))


__all__ = ["MetricsInterpreter"]
