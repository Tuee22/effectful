"""Tests for framework metrics registry."""

from effectful.observability.framework_metrics import FRAMEWORK_METRICS


def test_framework_metrics_definitions_present() -> None:
    """FRAMEWORK_METRICS should expose all framework counters, gauges, and histograms."""
    assert {c.name for c in FRAMEWORK_METRICS.counters} == {
        "effectful_effects_total",
        "effectful_programs_total",
    }
    assert {g.name for g in FRAMEWORK_METRICS.gauges} == {"effectful_effects_in_progress"}
    assert {h.name for h in FRAMEWORK_METRICS.histograms} == {
        "effectful_effect_duration_seconds",
        "effectful_program_duration_seconds",
    }
