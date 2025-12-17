"""Observability interpreter protocol for dependency injection."""

from typing import Protocol
from app.effects.observability import ObservabilityEffect, MetricRecordingResult


class ObservabilityInterpreter(Protocol):
    """Protocol for observability operations (metrics recording).

    Testing: Use pytest-mock with spec=ObservabilityInterpreter
    """

    async def handle(self, effect: ObservabilityEffect) -> MetricRecordingResult:
        """Handle an observability effect (increment counter, observe histogram)."""
        ...

    def render_latest(self) -> bytes:
        """Render registered metrics for scraping."""
        ...
