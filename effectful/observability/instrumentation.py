"""Automatic instrumentation for effect system observability.

This module provides InstrumentedInterpreter, a decorator that wraps any interpreter
to automatically collect framework metrics without code changes.

When enabled, tracks:
- Effect execution counts and error rates (effectful_effects_total)
- Effect duration distributions (effectful_effect_duration_seconds)

Metrics are collected for every effect execution with zero performance overhead
beyond the metrics recording itself (fire-and-forget async calls).

Example:
    >>> from effectful.observability.instrumentation import create_instrumented_interpreter
    >>> from effectful.adapters.prometheus_metrics import PrometheusMetricsCollector
    >>>
    >>> # Wrap existing interpreter with instrumentation
    >>> instrumented = create_instrumented_interpreter(
    ...     wrapped=db_interpreter,
    ...     metrics_collector=prometheus_collector,
    ... )
    >>>
    >>> # All effect executions now tracked automatically
    >>> result = await instrumented.interpret(effect)

See Also:
    - documents/core/observability_doctrine.md - Dual-layer metrics architecture
    - documents/core/monitoring_standards.md - Framework metric definitions
"""

import time
from dataclasses import dataclass
from typing import Protocol

from effectful.algebraic.effect_return import EffectReturn
from effectful.algebraic.result import Err, Ok, Result
from effectful.domain.metrics_result import MetricRecorded
from effectful.effects.base import Effect
from effectful.infrastructure.metrics import MetricsCollector
from effectful.interpreters.errors import InterpreterError
from effectful.programs.program_types import EffectResult


class Interpreter(Protocol):
    """Protocol for any interpreter that can be instrumented.

    Any class with an async interpret method matching this signature
    can be wrapped with InstrumentedInterpreter.
    """

    async def interpret(
        self, effect: Effect
    ) -> Result[EffectReturn[EffectResult], InterpreterError]:
        """Interpret an effect and return result."""
        ...


@dataclass(frozen=True)
class InstrumentedInterpreter:
    """Decorator interpreter that automatically collects framework metrics.

    Wraps any interpreter to track effect execution metrics without
    modifying the wrapped interpreter's behavior or return values.

    Metrics collected:
        - effectful_effects_total: Counter with labels (effect_type, result)
        - effectful_effect_duration_seconds: Histogram with label (effect_type)

    The wrapped interpreter's behavior is unchanged. Metrics recording
    failures are silently ignored (fire-and-forget pattern).

    Attributes:
        wrapped: The interpreter to wrap with instrumentation
        metrics_collector: Collector for recording framework metrics
    """

    wrapped: Interpreter
    metrics_collector: MetricsCollector

    async def interpret(
        self, effect: Effect
    ) -> Result[EffectReturn[EffectResult], InterpreterError]:
        """Interpret effect with automatic metrics collection.

        Args:
            effect: The effect to interpret

        Returns:
            Same result as wrapped interpreter, with metrics recorded

        Metrics collected:
            - effectful_effects_total: Incremented with effect_type and result labels
            - effectful_effect_duration_seconds: Observed with effect_type label
        """
        effect_type = type(effect).__name__

        # Start timing
        start_time = time.perf_counter()

        # Execute wrapped interpreter
        result = await self.wrapped.interpret(effect)

        # Calculate duration
        duration = time.perf_counter() - start_time

        # Determine result label
        match result:  # pragma: no branch
            case Ok(_):
                result_label = "ok"
            case Err(_):
                result_label = "error"

        # Record counter (fire-and-forget - don't block on metrics)
        await self.metrics_collector.increment_counter(
            metric_name="effectful_effects_total",
            labels={"effect_type": effect_type, "result": result_label},
            value=1.0,
        )

        # Record histogram (fire-and-forget - don't block on metrics)
        await self.metrics_collector.observe_histogram(
            metric_name="effectful_effect_duration_seconds",
            labels={"effect_type": effect_type},
            value=duration,
        )

        return result


def create_instrumented_interpreter(
    wrapped: Interpreter,
    metrics_collector: MetricsCollector,
) -> InstrumentedInterpreter:
    """Factory function to create instrumented interpreter.

    Args:
        wrapped: Any interpreter to wrap with metrics
        metrics_collector: Metrics collector (must have FRAMEWORK_METRICS registered)

    Returns:
        InstrumentedInterpreter wrapping the provided interpreter

    Example:
        >>> db_interp = DatabaseInterpreter(user_repo=repo)
        >>> instrumented_db = create_instrumented_interpreter(
        ...     wrapped=db_interp,
        ...     metrics_collector=prometheus_collector,
        ... )
    """
    return InstrumentedInterpreter(
        wrapped=wrapped,
        metrics_collector=metrics_collector,
    )
