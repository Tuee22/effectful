"""Production Prometheus observability adapter."""

from app.effects.observability import ObservabilityEffect, MetricRecordingResult
from app.interpreters.observability_interpreter import (
    ObservabilityInterpreter as ConcreteInterpreter,
)


class PrometheusObservabilityAdapter:
    """Production observability using Prometheus client.

    Wraps the existing ObservabilityInterpreter implementation.
    Implements ObservabilityInterpreter protocol.

    Testing: Mock with mocker.AsyncMock(spec=ObservabilityInterpreter)
    """

    def __init__(self, interpreter: ConcreteInterpreter) -> None:
        """Initialize with concrete interpreter."""
        self._interpreter = interpreter

    async def handle(self, effect: ObservabilityEffect) -> MetricRecordingResult:
        """Handle observability effect (implements protocol)."""
        return await self._interpreter.handle(effect)

    async def close(self) -> None:
        """Close underlying interpreter resources (no-op for Prometheus)."""
        return None

    def render_latest(self) -> bytes:
        """Render all registered metrics for the bound registry."""
        return self._interpreter.render_latest()
