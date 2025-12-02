"""Tests for InMemoryMetricsCollector adapter.

Tests verify in-memory metrics collection for testing and development.
Not using pytest-mock since this is a pure in-memory implementation.
"""

import pytest

from effectful.adapters.in_memory_metrics import InMemoryMetricsCollector
from effectful.domain.metrics_result import (
    MetricRecorded,
    MetricRecordingFailed,
    QueryFailure,
    QuerySuccess,
)
from effectful.observability import (
    CounterDefinition,
    GaugeDefinition,
    HistogramDefinition,
    MetricsRegistry,
    SummaryDefinition,
)


# Test fixtures
@pytest.fixture
def sample_registry() -> MetricsRegistry:
    """Sample metrics registry for testing."""
    return MetricsRegistry(
        counters=(
            CounterDefinition(
                name="requests_total",
                help_text="Total requests",
                label_names=("method", "status"),
            ),
            CounterDefinition(
                name="errors_total",
                help_text="Total errors",
                label_names=("type",),
            ),
        ),
        gauges=(
            GaugeDefinition(
                name="active_connections",
                help_text="Active connections",
                label_names=("protocol",),
            ),
            GaugeDefinition(
                name="memory_bytes",
                help_text="Memory usage",
                label_names=(),
            ),
        ),
        histograms=(
            HistogramDefinition(
                name="request_duration_seconds",
                help_text="Request duration",
                label_names=("endpoint",),
                buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.5, 1.0),
            ),
        ),
        summaries=(
            SummaryDefinition(
                name="response_size_bytes",
                help_text="Response size",
                label_names=("content_type",),
                quantiles=(0.5, 0.9, 0.95, 0.99),
            ),
        ),
    )


@pytest.fixture
async def collector(sample_registry: MetricsRegistry) -> InMemoryMetricsCollector:
    """Collector with registered metrics."""
    c = InMemoryMetricsCollector()
    await c.register_metrics(sample_registry)
    return c


# Registry tests
@pytest.mark.asyncio
async def test_register_metrics_stores_registry() -> None:
    """Registering metrics stores the registry."""
    collector = InMemoryMetricsCollector()
    registry = MetricsRegistry(counters=(), gauges=(), histograms=(), summaries=())

    await collector.register_metrics(registry)

    assert collector.registry == registry


@pytest.mark.asyncio
async def test_register_metrics_is_idempotent(sample_registry: MetricsRegistry) -> None:
    """Calling register_metrics multiple times is safe."""
    collector = InMemoryMetricsCollector()

    await collector.register_metrics(sample_registry)
    await collector.register_metrics(sample_registry)

    assert collector.registry == sample_registry


# Counter increment tests
@pytest.mark.asyncio
async def test_increment_counter_success(collector: InMemoryMetricsCollector) -> None:
    """Incrementing counter succeeds with valid input."""
    result = await collector.increment_counter(
        metric_name="requests_total",
        labels={"method": "GET", "status": "200"},
        value=1.0,
    )

    assert isinstance(result, MetricRecorded)
    assert result.timestamp > 0


@pytest.mark.asyncio
async def test_increment_counter_accumulates_value(
    collector: InMemoryMetricsCollector,
) -> None:
    """Counter values accumulate across increments."""
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

    # Query to verify accumulated value
    query_result = await collector.query_metrics(
        metric_name="requests_total",
        labels={"method": "GET", "status": "200"},
    )
    assert isinstance(query_result, QuerySuccess)
    assert query_result.metrics["requests_total{method=GET,status=200}"] == 8.0


@pytest.mark.asyncio
async def test_increment_counter_different_labels_separate(
    collector: InMemoryMetricsCollector,
) -> None:
    """Different label combinations are tracked separately."""
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

    query_result = await collector.query_metrics(metric_name="requests_total", labels=None)
    assert isinstance(query_result, QuerySuccess)
    assert query_result.metrics["requests_total{method=GET,status=200}"] == 5.0
    assert query_result.metrics["requests_total{method=POST,status=201}"] == 3.0


@pytest.mark.asyncio
async def test_increment_counter_fails_without_registry() -> None:
    """Incrementing counter fails if no registry registered."""
    collector = InMemoryMetricsCollector()

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
    collector: InMemoryMetricsCollector,
) -> None:
    """Incrementing counter fails with negative value."""
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
    collector: InMemoryMetricsCollector,
) -> None:
    """Incrementing unregistered counter fails."""
    result = await collector.increment_counter(
        metric_name="unknown_total",
        labels={"key": "value"},
        value=1.0,
    )

    assert isinstance(result, MetricRecordingFailed)
    assert result.reason == "metric_not_registered"
    assert "not registered" in result.message


@pytest.mark.asyncio
async def test_increment_counter_fails_with_wrong_labels(
    collector: InMemoryMetricsCollector,
) -> None:
    """Incrementing counter with wrong labels fails."""
    result = await collector.increment_counter(
        metric_name="requests_total",
        labels={"wrong": "label"},  # Should be method and status
        value=1.0,
    )

    assert isinstance(result, MetricRecordingFailed)
    assert result.reason == "invalid_labels"
    assert "don't match" in result.message


@pytest.mark.asyncio
async def test_increment_counter_fails_with_missing_labels(
    collector: InMemoryMetricsCollector,
) -> None:
    """Incrementing counter with missing labels fails."""
    result = await collector.increment_counter(
        metric_name="requests_total",
        labels={"method": "GET"},  # Missing status
        value=1.0,
    )

    assert isinstance(result, MetricRecordingFailed)
    assert result.reason == "invalid_labels"
    assert "don't match" in result.message


# Gauge tests
@pytest.mark.asyncio
async def test_record_gauge_success(collector: InMemoryMetricsCollector) -> None:
    """Recording gauge succeeds with valid input."""
    result = await collector.record_gauge(
        metric_name="active_connections",
        labels={"protocol": "http"},
        value=42.0,
    )

    assert isinstance(result, MetricRecorded)
    assert result.timestamp > 0


@pytest.mark.asyncio
async def test_record_gauge_overwrites_value(collector: InMemoryMetricsCollector) -> None:
    """Gauge value is overwritten on each record."""
    await collector.record_gauge(
        metric_name="active_connections",
        labels={"protocol": "http"},
        value=42.0,
    )
    await collector.record_gauge(
        metric_name="active_connections",
        labels={"protocol": "http"},
        value=100.0,
    )

    query_result = await collector.query_metrics(
        metric_name="active_connections",
        labels={"protocol": "http"},
    )
    assert isinstance(query_result, QuerySuccess)
    assert query_result.metrics["active_connections{protocol=http}"] == 100.0


@pytest.mark.asyncio
async def test_record_gauge_accepts_negative_value(
    collector: InMemoryMetricsCollector,
) -> None:
    """Gauge can accept negative values."""
    result = await collector.record_gauge(
        metric_name="memory_bytes",
        labels={},
        value=-10.5,
    )

    assert isinstance(result, MetricRecorded)

    query_result = await collector.query_metrics(metric_name="memory_bytes", labels={})
    assert isinstance(query_result, QuerySuccess)
    assert query_result.metrics["memory_bytes{}"] == -10.5


@pytest.mark.asyncio
async def test_record_gauge_accepts_zero(collector: InMemoryMetricsCollector) -> None:
    """Gauge can accept zero value."""
    result = await collector.record_gauge(
        metric_name="memory_bytes",
        labels={},
        value=0.0,
    )

    assert isinstance(result, MetricRecorded)


@pytest.mark.asyncio
async def test_record_gauge_fails_without_registry() -> None:
    """Recording gauge fails if no registry registered."""
    collector = InMemoryMetricsCollector()

    result = await collector.record_gauge(
        metric_name="active_connections",
        labels={"protocol": "http"},
        value=42.0,
    )

    assert isinstance(result, MetricRecordingFailed)
    assert result.reason == "collector_error"
    assert "No metrics registered" in result.message


@pytest.mark.asyncio
async def test_record_gauge_fails_with_unregistered_metric(
    collector: InMemoryMetricsCollector,
) -> None:
    """Recording unregistered gauge fails."""
    result = await collector.record_gauge(
        metric_name="unknown_gauge",
        labels={},
        value=1.0,
    )

    assert isinstance(result, MetricRecordingFailed)
    assert result.reason == "metric_not_registered"
    assert "not registered" in result.message


@pytest.mark.asyncio
async def test_record_gauge_fails_with_wrong_labels(
    collector: InMemoryMetricsCollector,
) -> None:
    """Recording gauge with wrong labels fails."""
    result = await collector.record_gauge(
        metric_name="active_connections",
        labels={"wrong": "label"},
        value=42.0,
    )

    assert isinstance(result, MetricRecordingFailed)
    assert result.reason == "invalid_labels"
    assert "don't match" in result.message


# Histogram tests
@pytest.mark.asyncio
async def test_observe_histogram_success(collector: InMemoryMetricsCollector) -> None:
    """Observing histogram succeeds with valid input."""
    result = await collector.observe_histogram(
        metric_name="request_duration_seconds",
        labels={"endpoint": "/api/users"},
        value=0.123,
    )

    assert isinstance(result, MetricRecorded)
    assert result.timestamp > 0


@pytest.mark.asyncio
async def test_observe_histogram_accumulates_observations(
    collector: InMemoryMetricsCollector,
) -> None:
    """Histogram observations accumulate in list."""
    await collector.observe_histogram(
        metric_name="request_duration_seconds",
        labels={"endpoint": "/api/users"},
        value=0.1,
    )
    await collector.observe_histogram(
        metric_name="request_duration_seconds",
        labels={"endpoint": "/api/users"},
        value=0.2,
    )
    await collector.observe_histogram(
        metric_name="request_duration_seconds",
        labels={"endpoint": "/api/users"},
        value=0.3,
    )

    query_result = await collector.query_metrics(
        metric_name="request_duration_seconds",
        labels={"endpoint": "/api/users"},
    )
    assert isinstance(query_result, QuerySuccess)
    assert query_result.metrics["request_duration_seconds_count{endpoint=/api/users}"] == 3.0


@pytest.mark.asyncio
async def test_observe_histogram_different_labels_separate(
    collector: InMemoryMetricsCollector,
) -> None:
    """Different label combinations tracked separately for histograms."""
    await collector.observe_histogram(
        metric_name="request_duration_seconds",
        labels={"endpoint": "/api/users"},
        value=0.1,
    )
    await collector.observe_histogram(
        metric_name="request_duration_seconds",
        labels={"endpoint": "/api/posts"},
        value=0.2,
    )

    query_result = await collector.query_metrics(
        metric_name="request_duration_seconds", labels=None
    )
    assert isinstance(query_result, QuerySuccess)
    assert query_result.metrics["request_duration_seconds_count{endpoint=/api/users}"] == 1.0
    assert query_result.metrics["request_duration_seconds_count{endpoint=/api/posts}"] == 1.0


@pytest.mark.asyncio
async def test_observe_histogram_fails_without_registry() -> None:
    """Observing histogram fails if no registry registered."""
    collector = InMemoryMetricsCollector()

    result = await collector.observe_histogram(
        metric_name="request_duration_seconds",
        labels={"endpoint": "/api/users"},
        value=0.123,
    )

    assert isinstance(result, MetricRecordingFailed)
    assert result.reason == "collector_error"
    assert "No metrics registered" in result.message


@pytest.mark.asyncio
async def test_observe_histogram_fails_with_unregistered_metric(
    collector: InMemoryMetricsCollector,
) -> None:
    """Observing unregistered histogram fails."""
    result = await collector.observe_histogram(
        metric_name="unknown_histogram",
        labels={},
        value=1.0,
    )

    assert isinstance(result, MetricRecordingFailed)
    assert result.reason == "metric_not_registered"
    assert "not registered" in result.message


@pytest.mark.asyncio
async def test_observe_histogram_fails_with_wrong_labels(
    collector: InMemoryMetricsCollector,
) -> None:
    """Observing histogram with wrong labels fails."""
    result = await collector.observe_histogram(
        metric_name="request_duration_seconds",
        labels={"wrong": "label"},
        value=0.123,
    )

    assert isinstance(result, MetricRecordingFailed)
    assert result.reason == "invalid_labels"
    assert "don't match" in result.message


# Summary tests
@pytest.mark.asyncio
async def test_record_summary_success(collector: InMemoryMetricsCollector) -> None:
    """Recording summary succeeds with valid input."""
    result = await collector.record_summary(
        metric_name="response_size_bytes",
        labels={"content_type": "application/json"},
        value=1024.0,
    )

    assert isinstance(result, MetricRecorded)
    assert result.timestamp > 0


@pytest.mark.asyncio
async def test_record_summary_accumulates_observations(
    collector: InMemoryMetricsCollector,
) -> None:
    """Summary observations accumulate in list."""
    await collector.record_summary(
        metric_name="response_size_bytes",
        labels={"content_type": "application/json"},
        value=1000.0,
    )
    await collector.record_summary(
        metric_name="response_size_bytes",
        labels={"content_type": "application/json"},
        value=2000.0,
    )
    await collector.record_summary(
        metric_name="response_size_bytes",
        labels={"content_type": "application/json"},
        value=3000.0,
    )

    query_result = await collector.query_metrics(
        metric_name="response_size_bytes",
        labels={"content_type": "application/json"},
    )
    assert isinstance(query_result, QuerySuccess)
    assert query_result.metrics["response_size_bytes_count{content_type=application/json}"] == 3.0


@pytest.mark.asyncio
async def test_record_summary_fails_without_registry() -> None:
    """Recording summary fails if no registry registered."""
    collector = InMemoryMetricsCollector()

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
    collector: InMemoryMetricsCollector,
) -> None:
    """Recording unregistered summary fails."""
    result = await collector.record_summary(
        metric_name="unknown_summary",
        labels={},
        value=1.0,
    )

    assert isinstance(result, MetricRecordingFailed)
    assert result.reason == "metric_not_registered"
    assert "not registered" in result.message


@pytest.mark.asyncio
async def test_record_summary_fails_with_wrong_labels(
    collector: InMemoryMetricsCollector,
) -> None:
    """Recording summary with wrong labels fails."""
    result = await collector.record_summary(
        metric_name="response_size_bytes",
        labels={"wrong": "label"},
        value=1024.0,
    )

    assert isinstance(result, MetricRecordingFailed)
    assert result.reason == "invalid_labels"
    assert "don't match" in result.message


# Query metrics tests
@pytest.mark.asyncio
async def test_query_metrics_all_returns_all_metrics(
    collector: InMemoryMetricsCollector,
) -> None:
    """Querying with None returns all metrics."""
    # Record some metrics
    await collector.increment_counter(
        metric_name="requests_total",
        labels={"method": "GET", "status": "200"},
        value=5.0,
    )
    await collector.record_gauge(
        metric_name="active_connections",
        labels={"protocol": "http"},
        value=42.0,
    )

    result = await collector.query_metrics(metric_name=None, labels=None)

    assert isinstance(result, QuerySuccess)
    assert "requests_total{method=GET,status=200}" in result.metrics
    assert "active_connections{protocol=http}" in result.metrics


@pytest.mark.asyncio
async def test_query_metrics_specific_counter(
    collector: InMemoryMetricsCollector,
) -> None:
    """Querying specific counter returns only that counter."""
    await collector.increment_counter(
        metric_name="requests_total",
        labels={"method": "GET", "status": "200"},
        value=5.0,
    )
    await collector.increment_counter(
        metric_name="errors_total",
        labels={"type": "timeout"},
        value=3.0,
    )

    result = await collector.query_metrics(metric_name="requests_total", labels=None)

    assert isinstance(result, QuerySuccess)
    assert "requests_total{method=GET,status=200}" in result.metrics
    assert "errors_total{type=timeout}" not in result.metrics


@pytest.mark.asyncio
async def test_query_metrics_with_label_filter(
    collector: InMemoryMetricsCollector,
) -> None:
    """Querying with label filter returns only matching labels."""
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

    result = await collector.query_metrics(
        metric_name="requests_total",
        labels={"method": "GET", "status": "200"},
    )

    assert isinstance(result, QuerySuccess)
    assert result.metrics["requests_total{method=GET,status=200}"] == 5.0
    assert "requests_total{method=POST,status=201}" not in result.metrics


@pytest.mark.asyncio
async def test_query_metrics_returns_timestamp(
    collector: InMemoryMetricsCollector,
) -> None:
    """Query result includes timestamp."""
    await collector.increment_counter(
        metric_name="requests_total",
        labels={"method": "GET", "status": "200"},
        value=1.0,
    )

    result = await collector.query_metrics(metric_name="requests_total", labels=None)

    assert isinstance(result, QuerySuccess)
    assert result.timestamp > 0


@pytest.mark.asyncio
async def test_query_metrics_fails_without_registry() -> None:
    """Querying fails if no registry registered."""
    collector = InMemoryMetricsCollector()

    result = await collector.query_metrics(metric_name=None, labels=None)

    assert isinstance(result, QueryFailure)
    assert "No metrics registered" in result.reason


@pytest.mark.asyncio
async def test_query_metrics_fails_for_unknown_metric(
    collector: InMemoryMetricsCollector,
) -> None:
    """Querying unknown metric returns failure."""
    result = await collector.query_metrics(metric_name="unknown_metric", labels=None)

    assert isinstance(result, QueryFailure)
    assert "not found" in result.reason


@pytest.mark.asyncio
async def test_query_metrics_counter_with_no_data_returns_empty(
    collector: InMemoryMetricsCollector,
) -> None:
    """Querying counter with specific labels that don't exist returns empty QuerySuccess."""
    # Don't record any data for these labels
    result = await collector.query_metrics(
        metric_name="requests_total",
        labels={"method": "DELETE", "status": "404"},
    )

    # Returns QuerySuccess but with empty metrics (no data recorded)
    assert isinstance(result, QuerySuccess)
    # When filtering by labels that haven't been recorded, defaultdict returns 0
    assert result.metrics.get("requests_total{method=DELETE,status=404}", 0.0) == 0.0


# Reset metrics tests
@pytest.mark.asyncio
async def test_reset_metrics_clears_all_data(
    collector: InMemoryMetricsCollector,
) -> None:
    """Resetting metrics clears all counters, gauges, histograms, summaries."""
    # Record various metrics
    await collector.increment_counter(
        metric_name="requests_total",
        labels={"method": "GET", "status": "200"},
        value=5.0,
    )
    await collector.record_gauge(
        metric_name="active_connections",
        labels={"protocol": "http"},
        value=42.0,
    )
    await collector.observe_histogram(
        metric_name="request_duration_seconds",
        labels={"endpoint": "/api/users"},
        value=0.123,
    )
    await collector.record_summary(
        metric_name="response_size_bytes",
        labels={"content_type": "application/json"},
        value=1024.0,
    )

    # Reset
    result = await collector.reset_metrics()

    assert isinstance(result, MetricRecorded)

    # Verify all data cleared
    query_result = await collector.query_metrics(metric_name=None, labels=None)
    assert isinstance(query_result, QuerySuccess)
    assert len(query_result.metrics) == 0


@pytest.mark.asyncio
async def test_reset_metrics_returns_timestamp() -> None:
    """Reset metrics returns MetricRecorded with timestamp."""
    collector = InMemoryMetricsCollector()

    result = await collector.reset_metrics()

    assert isinstance(result, MetricRecorded)
    assert result.timestamp > 0


# Label serialization tests
@pytest.mark.asyncio
async def test_label_serialization_is_deterministic(
    collector: InMemoryMetricsCollector,
) -> None:
    """Label serialization produces consistent ordering."""
    # Record with labels in different order
    await collector.increment_counter(
        metric_name="requests_total",
        labels={"status": "200", "method": "GET"},  # Reversed order
        value=3.0,
    )
    await collector.increment_counter(
        metric_name="requests_total",
        labels={"method": "GET", "status": "200"},  # Normal order
        value=2.0,
    )

    # Both should accumulate to same metric
    query_result = await collector.query_metrics(
        metric_name="requests_total",
        labels={"method": "GET", "status": "200"},
    )
    assert isinstance(query_result, QuerySuccess)
    assert query_result.metrics["requests_total{method=GET,status=200}"] == 5.0


@pytest.mark.asyncio
async def test_empty_labels_serialization(collector: InMemoryMetricsCollector) -> None:
    """Empty labels are serialized correctly."""
    await collector.record_gauge(
        metric_name="memory_bytes",
        labels={},
        value=1024.0,
    )

    query_result = await collector.query_metrics(metric_name="memory_bytes", labels={})
    assert isinstance(query_result, QuerySuccess)
    assert "memory_bytes{}" in query_result.metrics
    assert query_result.metrics["memory_bytes{}"] == 1024.0
