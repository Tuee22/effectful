# Shipnorth Prometheus Analysis

**Reference document analyzing shipnorth's Prometheus/Grafana implementation and how it influenced effectful's observability design.**

> **Note**: This is a reference document for understanding design decisions. It is not a tutorial.

---

## Purpose

This document analyzes how **shipnorth** (a production Flask application) implements Prometheus metrics and Grafana dashboards, and documents the key patterns and lessons learned that were applied to effectful's observability system.

**Key Questions Answered**:
- How does shipnorth structure its Prometheus Docker services?
- What naming conventions does shipnorth use?
- How does shipnorth handle metrics cardinality?
- What patterns from shipnorth were adapted (or avoided) in effectful?

---

## Shipnorth Architecture Overview

**Shipnorth** is a shipping logistics management system built with Flask, using:
- **Backend**: Flask + SQLAlchemy + Celery
- **Infrastructure**: PostgreSQL, Redis, RabbitMQ
- **Observability**: Prometheus + Grafana + prometheus_client library

**Metrics Philosophy**:
- Explicit metrics over automatic instrumentation
- Low cardinality by design (strict label discipline)
- Business metrics (shipments, routes) alongside infrastructure metrics (database, cache)

---

## Docker Compose Configuration

### Shipnorth's Prometheus Service

```yaml
# shipnorth/docker/docker-compose.yml (excerpt)
services:
  prometheus:
    image: prom/prometheus:v2.42.0
    container_name: shipnorth-prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - ./prometheus/alerts.yml:/etc/prometheus/alerts.yml:ro
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=60d'
      - '--web.console.libraries=/usr/share/prometheus/console_libraries'
      - '--web.console.templates=/usr/share/prometheus/consoles'
      - '--web.enable-lifecycle'
    networks:
      - shipnorth-network
    restart: unless-stopped

  grafana:
    image: grafana/grafana:9.3.6
    container_name: shipnorth-grafana
    ports:
      - "3000:3000"
    volumes:
      - ./grafana/provisioning:/etc/grafana/provisioning:ro
      - ./grafana/dashboards:/var/lib/grafana/dashboards:ro
      - grafana_data:/var/lib/grafana
    environment:
      GF_SECURITY_ADMIN_USER: admin
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_ADMIN_PASSWORD}
      GF_INSTALL_PLUGINS: ""
      GF_SERVER_ROOT_URL: https://metrics.shipnorth.com
    depends_on:
      - prometheus
    networks:
      - shipnorth-network
    restart: unless-stopped

volumes:
  prometheus_data:
  grafana_data:

networks:
  shipnorth-network:
    driver: bridge
```

**Key Learnings**:
1. ✅ **Named volumes** (`prometheus_data`, `grafana_data`) - Prevents permission issues
2. ✅ **Explicit retention** (`60d`) - Longer retention for production (effectful uses 30d for dev)
3. ✅ **Web lifecycle enabled** (`--web.enable-lifecycle`) - Allows config reload via API
4. ✅ **Read-only config mounts** (`:ro`) - Prevents accidental modification
5. ✅ **Separate network** - Isolates monitoring stack from application
6. ⚠️  **Environment variable for password** - Good for production, effectful uses hardcoded `admin/admin` for dev

**Applied to Effectful**:
- Adopted named volumes pattern
- Adopted read-only config mounts
- Used shorter retention (30d vs 60d) for dev environment
- Kept simpler network config for dev environment

---

## Prometheus Configuration

### Shipnorth's prometheus.yml

```yaml
# shipnorth/docker/prometheus/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    cluster: 'production'
    environment: 'prod'
    region: 'us-east-1'

rule_files:
  - '/etc/prometheus/alerts.yml'

alerting:
  alertmanagers:
    - static_configs:
        - targets:
            - 'alertmanager:9093'

scrape_configs:
  # Prometheus self-monitoring
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  # Shipnorth backend (Flask app)
  - job_name: 'shipnorth-backend'
    static_configs:
      - targets: ['backend:5000']
    metrics_path: '/metrics'
    scrape_interval: 15s
    scrape_timeout: 10s
    relabel_configs:
      - source_labels: [__address__]
        target_label: instance
        replacement: 'shipnorth-backend'

  # Celery workers
  - job_name: 'shipnorth-celery'
    static_configs:
      - targets: ['celery:9091']
    metrics_path: '/metrics'

  # PostgreSQL exporter
  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']

  # Redis exporter
  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']
```

**Key Learnings**:
1. ✅ **External labels** (`cluster`, `environment`, `region`) - Useful for multi-environment setups
2. ✅ **Scrape timeout < interval** (`timeout=10s`, `interval=15s`) - Prevents overlap
3. ✅ **Relabel configs** - Simplifies instance naming
4. ✅ **Dedicated exporters** - Uses official exporters for PostgreSQL/Redis instead of custom metrics
5. ✅ **Separate jobs per service** - Better organization and filtering

**Applied to Effectful**:
- Adopted 15s scrape interval as default
- Adopted external labels pattern (cluster, environment)
- Used separate jobs per service (effectful, healthhub)
- Simplified relabel configs for dev environment

**Differences**:
- Effectful: No dedicated database exporters (app metrics only)
- Effectful: Single application target (vs shipnorth's backend + celery)

---

## Metrics Naming Conventions

### Shipnorth's Naming Patterns

```python
# shipnorth/app/metrics.py
from prometheus_client import Counter, Histogram, Gauge

# Business metrics
SHIPMENTS_CREATED = Counter(
    'shipnorth_shipments_created_total',
    'Total shipments created',
    ['customer_tier', 'destination_country'],
)

SHIPMENTS_DELIVERED = Counter(
    'shipnorth_shipments_delivered_total',
    'Total shipments delivered',
    ['on_time', 'destination_country'],
)

ROUTE_CALCULATION_DURATION = Histogram(
    'shipnorth_route_calculation_duration_seconds',
    'Route calculation duration',
    ['optimization_level'],
    buckets=(0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0),
)

# Infrastructure metrics
ACTIVE_SHIPMENTS = Gauge(
    'shipnorth_active_shipments',
    'Current active shipments in system',
)

DATABASE_QUERY_DURATION = Histogram(
    'shipnorth_database_query_duration_seconds',
    'Database query duration',
    ['query_type', 'table'],
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0),
)

CACHE_OPERATIONS = Counter(
    'shipnorth_cache_operations_total',
    'Total cache operations',
    ['operation', 'cache_name', 'result'],
)
```

**Patterns Observed**:
1. ✅ **Namespace prefix** (`shipnorth_`) - Prevents collision with other metrics
2. ✅ **`_total` suffix for counters** - Prometheus convention
3. ✅ **`_seconds` suffix for duration** - Standard unit
4. ✅ **Business metrics separate from infrastructure** - Clear separation
5. ✅ **Low-cardinality labels** - Limited to 2-3 labels per metric
6. ✅ **Meaningful help text** - Clear descriptions

**Applied to Effectful**:
- Adopted `effectful_` namespace prefix
- Adopted `_total` suffix for counters
- Adopted `_seconds` for durations
- Adopted low-cardinality label discipline
- Separated business metrics (effects) from infrastructure metrics (database, cache)

**Enhanced in Effectful**:
- Added explicit MetricsRegistry to prevent runtime metric creation
- Added frozen dataclass pattern for type safety
- Documented cardinality explosion prevention in observability_doctrine.md

---

## Alert Rules Structure

### Shipnorth's Alert Rules

```yaml
# shipnorth/docker/prometheus/alerts.yml
groups:
  - name: shipnorth_slo_alerts
    interval: 30s
    rules:
      # High-level SLO: Error rate
      - alert: HighShipmentErrorRate
        expr: |
          sum(rate(shipnorth_shipments_created_total{status="error"}[5m]))
          /
          sum(rate(shipnorth_shipments_created_total[5m]))
          > 0.01
        for: 5m
        labels:
          severity: critical
          component: shipments
          team: logistics
        annotations:
          summary: "High shipment creation error rate"
          description: "Error rate is {{ $value | humanizePercentage }} (threshold: 1%)"
          runbook_url: "https://docs.shipnorth.com/runbooks/shipment-errors"
          dashboard_url: "https://metrics.shipnorth.com/d/shipments"

      # Performance SLO: P95 latency
      - alert: SlowRouteCalculation
        expr: |
          histogram_quantile(0.95,
            sum by (le) (
              rate(shipnorth_route_calculation_duration_seconds_bucket[5m])
            )
          ) > 10.0
        for: 10m
        labels:
          severity: warning
          component: routing
          team: logistics
        annotations:
          summary: "Slow route calculation (P95 > 10s)"
          description: "P95 duration is {{ $value }}s"
          runbook_url: "https://docs.shipnorth.com/runbooks/slow-routing"

  - name: shipnorth_infrastructure_alerts
    interval: 30s
    rules:
      # Database connection pool
      - alert: DatabaseConnectionPoolExhaustion
        expr: |
          shipnorth_database_connections_active
          /
          shipnorth_database_connections_max
          > 0.90
        for: 5m
        labels:
          severity: critical
          component: database
          team: platform
        annotations:
          summary: "Database connection pool near exhaustion"
          description: "{{ $value | humanizePercentage }} of connections in use"

      # Redis cache hit rate
      - alert: LowCacheHitRate
        expr: |
          sum(rate(shipnorth_cache_operations_total{result="hit"}[5m]))
          /
          sum(rate(shipnorth_cache_operations_total[5m]))
          < 0.80
        for: 30m
        labels:
          severity: warning
          component: cache
          team: platform
        annotations:
          summary: "Low cache hit rate (< 80%)"
          description: "Hit rate is {{ $value | humanizePercentage }}"
```

**Patterns Observed**:
1. ✅ **Grouped by domain** (`slo_alerts`, `infrastructure_alerts`) - Logical organization
2. ✅ **Runbook URLs** - Links to remediation steps
3. ✅ **Dashboard URLs** - Direct link to visualization
4. ✅ **Team labels** - Routes to responsible team
5. ✅ **Severity levels** (critical, warning) - Clear prioritization
6. ✅ **`for` duration** - Prevents alert flapping (5m for critical, 30m for warning)
7. ✅ **Humanized values** (`humanizePercentage`) - Readable alert messages

**Applied to Effectful**:
- Adopted grouped alert structure (slo_alerts, infrastructure_alerts)
- Adopted runbook_url pattern
- Adopted severity levels (critical, warning, info)
- Adopted `for` duration pattern
- Documented in alerting_policy.md

**Not Applied** (dev environment differences):
- Dashboard URLs (effectful docs focus on local dev)
- Team labels (effectful is a library, not a production service)

---

## Grafana Provisioning

### Shipnorth's Datasource Provisioning

```yaml
# shipnorth/docker/grafana/provisioning/datasources/prometheus.yml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: false
    jsonData:
      timeInterval: "15s"
      queryTimeout: "60s"
      httpMethod: "POST"
```

**Patterns Observed**:
1. ✅ **Editable: false** - Prevents UI changes in production
2. ✅ **HTTP POST method** - Better for large queries
3. ✅ **Query timeout** - Prevents hanging queries

**Applied to Effectful**:
- Adopted provisioning pattern
- Set `editable: true` (dev environment)
- Adopted 15s time interval

### Shipnorth's Dashboard Provisioning

```yaml
# shipnorth/docker/grafana/provisioning/dashboards/dashboard.yml
apiVersion: 1

providers:
  - name: 'Shipnorth Dashboards'
    orgId: 1
    folder: 'Shipnorth'
    type: file
    disableDeletion: false
    updateIntervalSeconds: 30
    allowUiUpdates: true
    options:
      path: /var/lib/grafana/dashboards
```

**Patterns Observed**:
1. ✅ **Folder organization** - Groups dashboards logically
2. ✅ **Update interval** - Auto-reloads dashboard changes
3. ✅ **Allow UI updates** - Enables iteration

**Applied to Effectful**:
- Adopted file-based dashboard provisioning
- Adopted allowUiUpdates for dev environment
- Used 10s update interval (faster iteration)

---

## Cardinality Management

### Shipnorth's Approach

**Problem Shipnorth Solved**: Early versions had cardinality explosion from:
- Using customer IDs as labels (100,000+ customers = 100,000+ timeseries)
- Using shipment IDs as labels (millions of shipments)
- Using full URLs as labels (infinite cardinality)

**Solution Applied**:
```python
# ❌ BAD - Infinite cardinality
REQUESTS_TOTAL = Counter(
    'http_requests_total',
    ['customer_id', 'full_url'],  # WRONG!
)

# ✅ GOOD - Bounded cardinality
REQUESTS_TOTAL = Counter(
    'http_requests_total',
    ['customer_tier', 'endpoint_category'],  # Bounded!
)

# Customer tiers: free, pro, enterprise (3 values)
# Endpoint categories: shipments, routes, tracking, admin (4 values)
# Total timeseries: 3 * 4 = 12 (manageable!)
```

**Enforcement Strategy**:
1. **Pre-registration**: All metrics defined at startup
2. **Code review**: Label additions require review
3. **Monitoring**: Alert on high cardinality (> 10,000 timeseries per metric)
4. **Documentation**: Internal guide on label design

**Applied to Effectful**:
- Created MetricsRegistry with frozen dataclass (pre-registration enforced by type system)
- Documented cardinality management in observability_doctrine.md
- Provided examples of good vs bad label choices
- Added validation in monitoring_standards.md

---

## Key Learnings Applied to Effectful

### 1. Docker Configuration

| Pattern | Shipnorth | Effectful |
|---------|-----------|-----------|
| Named volumes | ✅ Used | ✅ Applied |
| Retention period | 60d (prod) | 30d (dev) |
| Read-only configs | ✅ Used | ✅ Applied |
| Web lifecycle | ✅ Enabled | ⚠️  Not needed (dev) |
| Alertmanager | ✅ Integrated | ⚠️  Optional (tutorial) |

### 2. Metrics Naming

| Pattern | Shipnorth | Effectful |
|---------|-----------|-----------|
| Namespace prefix | `shipnorth_` | `effectful_` |
| Counter suffix | `_total` | `_total` |
| Duration suffix | `_seconds` | `_seconds` |
| Low cardinality | ✅ Enforced | ✅ Enforced |
| Help text | ✅ Required | ✅ Required |

### 3. Alert Structure

| Pattern | Shipnorth | Effectful |
|---------|-----------|-----------|
| Grouped alerts | ✅ Used | ✅ Applied |
| Runbook URLs | ✅ Required | ✅ Recommended |
| Severity levels | critical, warning | critical, warning, info |
| `for` duration | 5m-30m | 5m-10m |
| Team routing | ✅ Used | ⚠️  N/A (library) |

### 4. Cardinality Management

| Aspect | Shipnorth | Effectful |
|--------|-----------|-----------|
| Pre-registration | Manual code review | Frozen MetricsRegistry |
| Enforcement | Process-based | Type-system enforced |
| Documentation | Internal guide | observability_doctrine.md |
| Monitoring | Cardinality alerts | ⚠️  Tutorial topic |

---

## Patterns Avoided

### 1. Custom Database Exporters

**Shipnorth** uses dedicated prometheus exporters (`postgres-exporter`, `redis-exporter`) for infrastructure metrics.

**Effectful** focuses on application-level metrics only, leaving infrastructure monitoring to deployment teams.

**Rationale**: Effectful is a library, not a production service. Infrastructure monitoring is deployment-specific.

### 2. Team-Based Alert Routing

**Shipnorth** routes alerts by team (logistics, platform, security).

**Effectful** uses component-based routing (effect_system, database, cache).

**Rationale**: Effectful users will have their own team structures. Component-based labels are more universal.

### 3. Production-Specific Features

**Shipnorth** includes:
- External labels for multi-region federation
- HTTP basic auth for scrape targets
- TLS for Grafana
- LDAP integration

**Effectful** focuses on dev environment simplicity.

**Rationale**: Production hardening is deployment-specific. Effectful provides foundational patterns, not production-ready infrastructure.

---

## References

### Shipnorth Resources
- **Repository**: (internal, not public)
- **Metrics Philosophy**: Based on Google SRE book chapters on monitoring
- **Implementation**: prometheus_client library + Flask integration

### Effectful Documentation
- [Observability Doctrine](../core/observability_doctrine.md) - Metrics philosophy
- [Monitoring Standards](../core/monitoring_standards.md) - Naming conventions
- [Alerting Policy](../core/alerting_policy.md) - Alert rules
- [Prometheus Setup Tutorial](../tutorials/13_prometheus_setup.md) - Docker integration

---

## Conclusion

Shipnorth's Prometheus implementation provided valuable patterns for effectful:

1. ✅ **Named volumes** prevent permission issues
2. ✅ **Low-cardinality labels** prevent timeseries explosion
3. ✅ **Pre-registration** enforces discipline
4. ✅ **Runbook URLs** make alerts actionable
5. ✅ **Grouped alerts** organize by domain

Effectful enhanced these patterns with:

1. ✅ **Type-safe MetricsRegistry** (frozen dataclass)
2. ✅ **SSoT documentation** (core doctrines)
3. ✅ **Generator-based metrics effects** (consistent with effectful architecture)
4. ✅ **Explicit ADT result types** (MetricRecorded | MetricRecordingFailed)

The result: A robust, type-safe, well-documented observability system suitable for production Python applications.

---

**Last Updated**: 2025-01-28
**Author**: Effectful Documentation Team
**Review Status**: Initial version based on shipnorth production implementation
