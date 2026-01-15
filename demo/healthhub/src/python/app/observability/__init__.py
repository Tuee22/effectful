"""Observability package for HealthHub."""

from typing import TYPE_CHECKING

from app.observability.registry import HEALTHHUB_METRICS, MetricsRegistry

if TYPE_CHECKING:
    from app.interpreters.observability_interpreter import ObservabilityInterpreter


def get_observability_interpreter_singleton() -> "ObservabilityInterpreter":
    """Deprecated shim for compatibility.

    Returns a fresh interpreter instance; lifecycle is managed by the container
    instead of a module-level singleton to satisfy purity doctrine.
    """
    from app.interpreters.observability_interpreter import ObservabilityInterpreter

    return ObservabilityInterpreter()


def initialize_observability_interpreter() -> "ObservabilityInterpreter":
    """Compatibility helper that delegates to container-managed creation."""
    return get_observability_interpreter_singleton()


__all__ = [
    "HEALTHHUB_METRICS",
    "MetricsRegistry",
    "get_observability_interpreter_singleton",
    "initialize_observability_interpreter",
]
