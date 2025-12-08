"""Observability package for HealthHub."""

from typing import TYPE_CHECKING

from app.observability.registry import HEALTHHUB_METRICS, MetricsRegistry

if TYPE_CHECKING:
    from app.interpreters.observability_interpreter import ObservabilityInterpreter

# Global observability interpreter singleton (created once at startup)
_observability_interpreter: "ObservabilityInterpreter | None" = None


def get_observability_interpreter_singleton() -> "ObservabilityInterpreter":
    """Get the global ObservabilityInterpreter singleton.

    Returns:
        The singleton ObservabilityInterpreter instance created at startup.

    Raises:
        RuntimeError: If called before app startup (interpreter not initialized).
    """
    if _observability_interpreter is None:
        raise RuntimeError("ObservabilityInterpreter not initialized. App not started.")
    return _observability_interpreter


def initialize_observability_interpreter() -> "ObservabilityInterpreter":
    """Initialize the global ObservabilityInterpreter singleton.

    Should be called exactly once during app startup.

    Returns:
        The newly created ObservabilityInterpreter instance.

    Raises:
        RuntimeError: If called more than once (already initialized).
    """
    # Import here to avoid circular import at module level
    from app.interpreters.observability_interpreter import ObservabilityInterpreter

    global _observability_interpreter
    if _observability_interpreter is not None:
        raise RuntimeError("ObservabilityInterpreter already initialized.")
    _observability_interpreter = ObservabilityInterpreter()
    return _observability_interpreter


__all__ = [
    "HEALTHHUB_METRICS",
    "MetricsRegistry",
    "get_observability_interpreter_singleton",
    "initialize_observability_interpreter",
]
