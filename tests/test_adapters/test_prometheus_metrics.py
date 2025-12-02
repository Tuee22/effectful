"""Tests for Prometheus metrics collector adapter.

Validates PrometheusMetricsCollector implementation that integrates
with the official prometheus_client library.
"""

import pytest
from prometheus_client import CollectorRegistry

from effectful.adapters.prometheus_metrics import PrometheusMetricsCollector
from effectful.domain.metrics_result import (
    MetricRecorded,
    MetricRecordingFailed,
    QueryFailure,
)
from effectful.observability import (
    CounterDefinition,
    GaugeDefinition,
    HistogramDefinition,
    MetricsRegistry,
    SummaryDefinition,
)


@pytest.fixture
def prometheus_registry() -> CollectorRegistry:
    """Create fresh Prometheus registry for each test."""
    return CollectorRegistry()


@pytest.fixture
def metrics_registry() -> MetricsRegistry:
    """Create test metrics registry with all metric types."""
    return MetricsRegistry(
        counters=(
            CounterDefinition(
                name="requests_total",
                help_text="Total HTTP requests",
                label_names=("method", "status"),
            ),
        ),
        gauges=(
            GaugeDefinition(
                name="active_connections",
                help_text="Current active connections",
                label_names=("protocol",),
            ),
        ),
        histograms=(
            HistogramDefinition(
                name="request_duration_seconds",
                help_text="HTTP request duration",
                label_names=("endpoint",),
                buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
            ),
        ),
        summaries=(
            SummaryDefinition(
                name="response_size_bytes",
                help_text="HTTP response size",
                label_names=("content_type",),
                quantiles=(0.5, 0.9, 0.99),
            ),
        ),
    )


@pytest.fixture
async def collector(
    prometheus_registry: CollectorRegistry,
    metrics_registry: MetricsRegistry,
) -> PrometheusMetricsCollector:
    """Create PrometheusMetricsCollector with registered metrics."""
    collector = PrometheusMetricsCollector(registry=prometheus_registry)
    await collector.register_metrics(metrics_registry)
    return collector


# Registration Tests


@pytest.mark.asyncio
async def test_register_metrics_creates_prometheus_objects(
    prometheus_registry: CollectorRegistry,
    metrics_registry: MetricsRegistry,
) -> None:
    """Registering metrics creates Prometheus Counter/Gauge/Histogram/Summary objects."""
    collector = PrometheusMetricsCollector(registry=prometheus_registry)
    await collector.register_metrics(metrics_registry)

    # Verify internal objects created
    assert "requests_total" in collector._counters
    assert "active_connections" in collector._gauges
    assert "request_duration_seconds" in collector._histograms
    assert "response_size_bytes" in collector._summaries


@pytest.mark.asyncio
async def test_register_metrics_is_idempotent(
    prometheus_registry: CollectorRegistry,
    metrics_registry: MetricsRegistry,
) -> None:
    """Calling register_metrics multiple times with same registry is idempotent."""
    collector = PrometheusMetricsCollector(registry=prometheus_registry)

    await collector.register_metrics(metrics_registry)
    await collector.register_metrics(metrics_registry)  # Second call

    # Should still have same metrics
    assert "requests_total" in collector._counters
    assert len(collector._counters) == 1


# Counter Tests


@pytest.mark.asyncio
async def test_increment_counter_success(
    collector: PrometheusMetricsCollector,
) -> None:
    """Incrementing counter succeeds with valid parameters."""
    result = await collector.increment_counter(
        metric_name="requests_total",
        labels={"method": "GET", "status": "200"},
        value=1.0,
    )

    assert isinstance(result, MetricRecorded)
    assert result.timestamp > 0


@pytest.mark.asyncio
async def test_increment_counter_accumulates_value(
    collector: PrometheusMetricsCollector,
    prometheus_registry: CollectorRegistry,
) -> None:
    """Multiple increments accumulate the counter value."""
    await collector.increment_counter(
        metric_name="requests_total",
        labels={"method": "GET", "status": "200"},
        value=5.0,
    )
    await collector.increment_counter(
        metric_name="requests_total",
        labels={"method": "GET", "status": "200"},
        value=3.0,
    )

    # Verify via Prometheus registry
    counter = collector._counters["requests_total"]
    metric_value = counter.labels(method="GET", status="200")._value._value
    assert metric_value == 8.0


@pytest.mark.asyncio
async def test_increment_counter_different_labels_separate(
    collector: PrometheusMetricsCollector,
) -> None:
    """Different label combinations create separate time series."""
    await collector.increment_counter(
        metric_name="requests_total",
        labels={"method": "GET", "status": "200"},
        value=5.0,
    )
    await collector.increment_counter(
        metric_name="requests_total",
        labels={"method": "POST", "status": "201"},
        value=3.0,
    )

    # Verify both time series exist
    counter = collector._counters["requests_total"]
    get_value = counter.labels(method="GET", status="200")._value._value
    post_value = counter.labels(method="POST", status="201")._value._value

    assert get_value == 5.0
    assert post_value == 3.0


@pytest.mark.asyncio
async def test_increment_counter_fails_without_registry(
    prometheus_registry: CollectorRegistry,
) -> None:
    """Incrementing counter without register_metrics() fails."""
    collector = PrometheusMetricsCollector(registry=prometheus_registry)

    result = await collector.increment_counter(
        metric_name="requests_total",
        labels={"method": "GET", "status": "200"},
        value=1.0,
    )

    assert isinstance(result, MetricRecordingFailed)
    assert result.reason == "collector_error"
    assert "No metrics registered" in result.message


@pytest.mark.asyncio
async def test_increment_counter_fails_with_negative_value(
    collector: PrometheusMetricsCollector,
) -> None:
    """Incrementing counter with negative value fails."""
    result = await collector.increment_counter(
        metric_name="requests_total",
        labels={"method": "GET", "status": "200"},
        value=-1.0,
    )

    assert isinstance(result, MetricRecordingFailed)
    assert result.reason == "invalid_value"
    assert "must be >= 0" in result.message


@pytest.mark.asyncio
async def test_increment_counter_fails_with_unregistered_metric(
    collector: PrometheusMetricsCollector,
) -> None:
    """Incrementing unregistered counter fails."""
    result = await collector.increment_counter(
        metric_name="unknown_counter",
        labels={"method": "GET"},
        value=1.0,
    )

    assert isinstance(result, MetricRecordingFailed)
    assert result.reason == "metric_not_registered"
    assert "not registered" in result.message


@pytest.mark.asyncio
async def test_increment_counter_fails_with_wrong_labels(
    collector: PrometheusMetricsCollector,
) -> None:
    """Incrementing counter with wrong label names fails."""
    result = await collector.increment_counter(
        metric_name="requests_total",
        labels={"wrong_label": "value"},
        value=1.0,
    )

    assert isinstance(result, MetricRecordingFailed)
    assert result.reason == "invalid_labels"
    assert "don't match" in result.message


@pytest.mark.asyncio
async def test_increment_counter_fails_with_missing_labels(
    collector: PrometheusMetricsCollector,
) -> None:
    """Incrementing counter with incomplete labels fails."""
    result = await collector.increment_counter(
        metric_name="requests_total",
        labels={"method": "GET"},  # Missing 'status'
        value=1.0,
    )

    assert isinstance(result, MetricRecordingFailed)
    assert result.reason == "invalid_labels"
    assert "don't match" in result.message


# Gauge Tests


@pytest.mark.asyncio
async def test_record_gauge_success(
    collector: PrometheusMetricsCollector,
) -> None:
    """Recording gauge succeeds with valid parameters."""
    result = await collector.record_gauge(
        metric_name="active_connections",
        labels={"protocol": "http"},
        value=42.0,
    )

    assert isinstance(result, MetricRecorded)
    assert result.timestamp > 0


@pytest.mark.asyncio
async def test_record_gauge_overwrites_value(
    collector: PrometheusMetricsCollector,
) -> None:
    """Recording gauge overwrites previous value."""
    await collector.record_gauge(
        metric_name="active_connections",
        labels={"protocol": "http"},
        value=10.0,
    )
    await collector.record_gauge(
        metric_name="active_connections",
        labels={"protocol": "http"},
        value=20.0,
    )

    # Verify value was overwritten
    gauge = collector._gauges["active_connections"]
    metric_value = gauge.labels(protocol="http")._value._value
    assert metric_value == 20.0


@pytest.mark.asyncio
async def test_record_gauge_accepts_negative_value(
    collector: PrometheusMetricsCollector,
) -> None:
    """Gauge accepts negative values (unlike counters)."""
    result = await collector.record_gauge(
        metric_name="active_connections",
        labels={"protocol": "http"},
        value=-5.0,
    )

    assert isinstance(result, MetricRecorded)


@pytest.mark.asyncio
async def test_record_gauge_accepts_zero(
    collector: PrometheusMetricsCollector,
) -> None:
    """Gauge accepts zero value."""
    result = await collector.record_gauge(
        metric_name="active_connections",
        labels={"protocol": "http"},
        value=0.0,
    )

    assert isinstance(result, MetricRecorded)


@pytest.mark.asyncio
async def test_record_gauge_fails_without_registry(
    prometheus_registry: CollectorRegistry,
) -> None:
    """Recording gauge without register_metrics() fails."""
    collector = PrometheusMetricsCollector(registry=prometheus_registry)

    result = await collector.record_gauge(
        metric_name="active_connections",
        labels={"protocol": "http"},
        value=10.0,
    )

    assert isinstance(result, MetricRecordingFailed)
    assert result.reason == "collector_error"
    assert "No metrics registered" in result.message


@pytest.mark.asyncio
async def test_record_gauge_fails_with_unregistered_metric(
    collector: PrometheusMetricsCollector,
) -> None:
    """Recording unregistered gauge fails."""
    result = await collector.record_gauge(
        metric_name="unknown_gauge",
        labels={"label": "value"},
        value=10.0,
    )

    assert isinstance(result, MetricRecordingFailed)
    assert result.reason == "metric_not_registered"
    assert "not registered" in result.message


@pytest.mark.asyncio
async def test_record_gauge_fails_with_wrong_labels(
    collector: PrometheusMetricsCollector,
) -> None:
    """Recording gauge with wrong label names fails."""
    result = await collector.record_gauge(
        metric_name="active_connections",
        labels={"wrong_label": "value"},
        value=10.0,
    )

    assert isinstance(result, MetricRecordingFailed)
    assert result.reason == "invalid_labels"
    assert "don't match" in result.message


# Histogram Tests


@pytest.mark.asyncio
async def test_observe_histogram_success(
    collector: PrometheusMetricsCollector,
) -> None:
    """Observing histogram succeeds with valid parameters."""
    result = await collector.observe_histogram(
        metric_name="request_duration_seconds",
        labels={"endpoint": "/api/users"},
        value=0.123,
    )

    assert isinstance(result, MetricRecorded)
    assert result.timestamp > 0


@pytest.mark.asyncio
async def test_observe_histogram_accumulates_observations(
    collector: PrometheusMetricsCollector,
) -> None:
    """Multiple observations accumulate in histogram buckets."""
    result1 = await collector.observe_histogram(
        metric_name="request_duration_seconds",
        labels={"endpoint": "/api/users"},
        value=0.05,
    )
    result2 = await collector.observe_histogram(
        metric_name="request_duration_seconds",
        labels={"endpoint": "/api/users"},
        value=0.15,
    )
    result3 = await collector.observe_histogram(
        metric_name="request_duration_seconds",
        labels={"endpoint": "/api/users"},
        value=0.25,
    )

    # Verify all observations succeeded
    assert isinstance(result1, MetricRecorded)
    assert isinstance(result2, MetricRecorded)
    assert isinstance(result3, MetricRecorded)


@pytest.mark.asyncio
async def test_observe_histogram_different_labels_separate(
    collector: PrometheusMetricsCollector,
) -> None:
    """Different label combinations create separate histogram time series."""
    result1 = await collector.observe_histogram(
        metric_name="request_duration_seconds",
        labels={"endpoint": "/api/users"},
        value=0.1,
    )
    result2 = await collector.observe_histogram(
        metric_name="request_duration_seconds",
        labels={"endpoint": "/api/posts"},
        value=0.2,
    )

    # Verify both observations succeeded (creating separate time series)
    assert isinstance(result1, MetricRecorded)
    assert isinstance(result2, MetricRecorded)


@pytest.mark.asyncio
async def test_observe_histogram_fails_without_registry(
    prometheus_registry: CollectorRegistry,
) -> None:
    """Observing histogram without register_metrics() fails."""
    collector = PrometheusMetricsCollector(registry=prometheus_registry)

    result = await collector.observe_histogram(
        metric_name="request_duration_seconds",
        labels={"endpoint": "/api/users"},
        value=0.1,
    )

    assert isinstance(result, MetricRecordingFailed)
    assert result.reason == "collector_error"
    assert "No metrics registered" in result.message


@pytest.mark.asyncio
async def test_observe_histogram_fails_with_unregistered_metric(
    collector: PrometheusMetricsCollector,
) -> None:
    """Observing unregistered histogram fails."""
    result = await collector.observe_histogram(
        metric_name="unknown_histogram",
        labels={"label": "value"},
        value=0.1,
    )

    assert isinstance(result, MetricRecordingFailed)
    assert result.reason == "metric_not_registered"
    assert "not registered" in result.message


@pytest.mark.asyncio
async def test_observe_histogram_fails_with_wrong_labels(
    collector: PrometheusMetricsCollector,
) -> None:
    """Observing histogram with wrong label names fails."""
    result = await collector.observe_histogram(
        metric_name="request_duration_seconds",
        labels={"wrong_label": "value"},
        value=0.1,
    )

    assert isinstance(result, MetricRecordingFailed)
    assert result.reason == "invalid_labels"
    assert "don't match" in result.message


# Summary Tests


@pytest.mark.asyncio
async def test_record_summary_success(
    collector: PrometheusMetricsCollector,
) -> None:
    """Recording summary succeeds with valid parameters."""
    result = await collector.record_summary(
        metric_name="response_size_bytes",
        labels={"content_type": "application/json"},
        value=1024.0,
    )

    assert isinstance(result, MetricRecorded)
    assert result.timestamp > 0


@pytest.mark.asyncio
async def test_record_summary_accumulates_observations(
    collector: PrometheusMetricsCollector,
) -> None:
    """Multiple observations accumulate in summary."""
    await collector.record_summary(
        metric_name="response_size_bytes",
        labels={"content_type": "application/json"},
        value=512.0,
    )
    await collector.record_summary(
        metric_name="response_size_bytes",
        labels={"content_type": "application/json"},
        value=1024.0,
    )

    # Verify count increased
    summary = collector._summaries["response_size_bytes"]
    count = summary.labels(content_type="application/json")._count._value
    assert count == 2


@pytest.mark.asyncio
async def test_record_summary_fails_without_registry(
    prometheus_registry: CollectorRegistry,
) -> None:
    """Recording summary without register_metrics() fails."""
    collector = PrometheusMetricsCollector(registry=prometheus_registry)

    result = await collector.record_summary(
        metric_name="response_size_bytes",
        labels={"content_type": "application/json"},
        value=1024.0,
    )

    assert isinstance(result, MetricRecordingFailed)
    assert result.reason == "collector_error"
    assert "No metrics registered" in result.message


@pytest.mark.asyncio
async def test_record_summary_fails_with_unregistered_metric(
    collector: PrometheusMetricsCollector,
) -> None:
    """Recording unregistered summary fails."""
    result = await collector.record_summary(
        metric_name="unknown_summary",
        labels={"label": "value"},
        value=100.0,
    )

    assert isinstance(result, MetricRecordingFailed)
    assert result.reason == "metric_not_registered"
    assert "not registered" in result.message


@pytest.mark.asyncio
async def test_record_summary_fails_with_wrong_labels(
    collector: PrometheusMetricsCollector,
) -> None:
    """Recording summary with wrong label names fails."""
    result = await collector.record_summary(
        metric_name="response_size_bytes",
        labels={"wrong_label": "value"},
        value=100.0,
    )

    assert isinstance(result, MetricRecordingFailed)
    assert result.reason == "invalid_labels"
    assert "don't match" in result.message


# Query Tests


@pytest.mark.asyncio
async def test_query_metrics_not_supported(
    collector: PrometheusMetricsCollector,
) -> None:
    """Query metrics returns failure for Prometheus (use HTTP API instead)."""
    result = await collector.query_metrics(
        metric_name="requests_total",
        labels={"method": "GET", "status": "200"},
    )

    assert isinstance(result, QueryFailure)
    assert "not supported" in result.reason
    assert "HTTP API" in result.reason


@pytest.mark.asyncio
async def test_query_metrics_fails_without_registry(
    prometheus_registry: CollectorRegistry,
) -> None:
    """Query metrics without register_metrics() returns failure."""
    collector = PrometheusMetricsCollector(registry=prometheus_registry)

    result = await collector.query_metrics(
        metric_name=None,
        labels=None,
    )

    assert isinstance(result, QueryFailure)
    assert "No metrics registered" in result.reason


# Reset Tests


@pytest.mark.asyncio
async def test_reset_metrics_not_supported(
    collector: PrometheusMetricsCollector,
) -> None:
    """Reset metrics returns failure for Prometheus (not supported)."""
    result = await collector.reset_metrics()

    assert isinstance(result, MetricRecordingFailed)
    assert result.reason == "collector_error"
    assert "not supported" in result.message
    assert "Prometheus server" in result.message
