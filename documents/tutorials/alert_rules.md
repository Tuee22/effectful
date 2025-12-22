# Alert Rules Tutorial

**Status**: Authoritative source
**Supersedes**: none
**Referenced by**: readme.md, tutorials/prometheus_setup.md, tutorials/metrics_quickstart.md, tutorials/metric_types_guide.md, tutorials/grafana_dashboards.md

> **Purpose**: Tutorial for writing actionable Prometheus alert rules for effectful applications.

**Write actionable Prometheus alert rules for effectful applications.**

> **Core Doctrine**: For alerting philosophy, see [monitoring_and_alerting.md](../engineering/monitoring_and_alerting.md#alerting-policy)

> **Tutorial**: For Prometheus setup, see [prometheus_setup.md](./prometheus_setup.md)

## SSoT Link Map

| Need                | Link                                                                               |
| ------------------- | ---------------------------------------------------------------------------------- |
| Alerting philosophy | [Monitoring & Alerting](../engineering/monitoring_and_alerting.md#alerting-policy) |
| Prometheus setup    | [Prometheus Setup](./prometheus_setup.md)                                          |
| Metrics quickstart  | [Metrics Quickstart](./metrics_quickstart.md)                                      |
| Grafana dashboards  | [Grafana Dashboards](./grafana_dashboards.md)                                      |

______________________________________________________________________

## Prerequisites

- Prometheus and Grafana running from [prometheus_setup.md](./prometheus_setup.md).
- Metrics emitted from your application per [metrics_quickstart.md](./metrics_quickstart.md).
- Familiar with alerting philosophy and severity taxonomy in [monitoring_and_alerting.md](../engineering/monitoring_and_alerting.md#alerting-policy).

## Learning Objectives

By the end of this tutorial, you will:

1. ✅ Write alert rules with PromQL expressions
1. ✅ Understand severity levels (critical, warning, info)
1. ✅ Configure alert thresholds and durations
1. ✅ Test alerts before deploying
1. ✅ Integrate with Alertmanager for notifications

**Time**: 25 minutes

**Prerequisites**: Prometheus setup complete (see previous tutorial).

______________________________________________________________________

## Alert Anatomy

```yaml
# file: configs/14_alert_rules.yaml
- alert: HighEffectErrorRate              # Alert name (PascalCase)
  expr: |                                  # PromQL expression (when to fire)
    sum(rate(effectful_effects_total{result="error"}[5m]))
    /
    sum(rate(effectful_effects_total[5m]))
    > 0.05                                 # Threshold: 5% error rate
  for: 5m                                  # Must be true for 5 minutes
  labels:                                  # Metadata for routing
    severity: critical
    component: effect_system
  annotations:                             # Human-readable context
    summary: "High effect error rate detected"
    description: "Effect error rate is {{ $value | humanizePercentage }}"
    runbook_url: "https://docs.example.com/runbooks/high-error-rate"
```

**Components**:

- **alert**: Unique alert name (shows in Alertmanager, Grafana)
- **expr**: PromQL expression (when true, alert fires)
- **for**: Duration expression must be true before firing (prevents flapping)
- **labels**: Metadata for routing and filtering
- **annotations**: Human-readable descriptions (use templates)

______________________________________________________________________

## Step 1: Create Alert Rules File

Create `docker/prometheus/alerts.yml`:

```yaml
# file: configs/14_alert_rules.yaml
# Prometheus alert rules for effectful
groups:
  # Effect system alerts
  - name: effectful_slo_alerts
    interval: 30s                # Evaluate every 30 seconds
    rules:
      # Alert 1: High error rate
      - alert: HighEffectErrorRate
        expr: |
          sum(rate(effectful_effects_total{result="error"}[5m]))
          /
          sum(rate(effectful_effects_total[5m]))
          > 0.05
        for: 5m
        labels:
          severity: critical
          component: effect_system
        annotations:
          summary: "High effect error rate detected"
          description: "Effect error rate is {{ $value | humanizePercentage }} (threshold: 5%)"
          runbook_url: "https://docs.effectful.dev/runbooks/high-error-rate"

      # Alert 2: Slow effect execution
      - alert: SlowEffectExecution
        expr: |
          histogram_quantile(0.95,
            sum by (effect_type, le) (
              rate(effectful_effect_duration_seconds_bucket[5m])
            )
          ) > 5.0
        for: 10m
        labels:
          severity: warning
          component: effect_system
        annotations:
          summary: "Slow effect execution detected"
          description: "P95 duration is {{ $value }}s for {{ $labels.effect_type }} (threshold: 5s)"

      # Alert 3: No metrics received
      - alert: NoMetricsReceived
        expr: |
          absent(effectful_effects_total)
        for: 2m
        labels:
          severity: critical
          component: monitoring
        annotations:
          summary: "No metrics received from effectful"
          description: "Prometheus has not received any effectful metrics for 2+ minutes"
```

______________________________________________________________________

## Step 2: Configure Prometheus to Load Alerts

Update `docker/prometheus/prometheus.yml`:

```yaml
# file: configs/14_alert_rules.yaml
global:
  scrape_interval: 15s
  evaluation_interval: 30s      # How often to evaluate alert rules

# Load alert rules
rule_files:
  - '/etc/prometheus/alerts.yml'

# Alertmanager configuration (optional, for notifications)
alerting:
  alertmanagers:
    - static_configs:
        - targets:
            - 'alertmanager:9093'

scrape_configs:
  # ... existing scrape configs
```

Mount alerts file in `docker-compose.yml`:

```yaml
# file: configs/14_alert_rules.yaml
services:
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - ./prometheus/alerts.yml:/etc/prometheus/alerts.yml:ro  # Add this
      - prometheusdata:/prometheus
```

______________________________________________________________________

## Step 3: Restart Prometheus and Verify

```bash
# Restart Prometheus to load alert rules
docker compose -f docker/docker-compose.yml restart prometheus

# Check Prometheus logs for errors
docker compose -f docker/docker-compose.yml logs prometheus | grep -i error

# Expected output: (no errors)
```

**Verify in UI**:

1. Open http://localhost:9090
1. Navigate to **Status → Rules**
1. Verify alert groups appear (e.g., `effectful_slo_alerts`)
1. Check "State" column (should be "inactive" or "pending")

______________________________________________________________________

## Step 4: Understand Alert States

Alerts transition through 3 states:

```text
# file: diagrams/alert_state_flow.txt
┌─────────┐  expr=true   ┌─────────┐  for duration   ┌────────┐
│ INACTIVE├─────────────►│ PENDING ├────────────────►│ FIRING │
└─────────┘              └────┬────┘                 └───┬────┘
                              │                          │
                              │ expr=false               │ expr=false
                              │                          │
                              └──────────────────────────┘
```

**States**:

- **INACTIVE**: Expression is false, no alert
- **PENDING**: Expression is true, waiting for `for` duration
- **FIRING**: Expression true for `for` duration, alert active

**Example Timeline**:

```text
# file: diagrams/alert_state_timeline.txt
00:00 - Error rate: 3% → INACTIVE
00:01 - Error rate: 6% → PENDING (for: 5m)
00:02 - Error rate: 7% → PENDING (3m remaining)
00:06 - Error rate: 6% → FIRING (notification sent)
00:10 - Error rate: 2% → INACTIVE (resolved notification)
```

______________________________________________________________________

## Step 5: Write Effective Alert Expressions

### Pattern 1: Error Rate Alert

```yaml
# file: configs/14_alert_rules.yaml
- alert: HighAPIErrorRate
  expr: |
    sum(rate(http_requests_total{status=~"5.."}[5m]))
    /
    sum(rate(http_requests_total[5m]))
    > 0.01                          # 1% error threshold
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "API error rate above 1%"
    description: "{{ $value | humanizePercentage }} of requests failing"
```

**Key Points**:

- Use `rate()` for counter metrics (per-second rate)
- 5m window balances responsiveness vs noise
- `for: 5m` prevents alerting on transient spikes
- Divide error count by total count for percentage

### Pattern 2: Latency Alert (Histogram)

```yaml
# file: configs/14_alert_rules.yaml
- alert: HighP95Latency
  expr: |
    histogram_quantile(0.95,
      sum by (endpoint, le) (
        rate(http_request_duration_seconds_bucket[5m])
      )
    ) > 1.0                         # 1 second threshold
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "High P95 latency for {{ $labels.endpoint }}"
    description: "P95 latency is {{ $value }}s (threshold: 1.0s)"
```

**Key Points**:

- `histogram_quantile()` computes percentiles from histogram buckets
- `sum by (endpoint, le)` aggregates across labels while preserving buckets
- `le` (less-than-or-equal) label is required for histogram quantiles

### Pattern 3: Resource Exhaustion

```yaml
# file: configs/14_alert_rules.yaml
- alert: DatabaseConnectionPoolExhaustion
  expr: |
    database_connections_active
    /
    database_connections_max
    > 0.90                          # 90% utilization
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "Database connection pool nearly exhausted"
    description: "{{ $value | humanizePercentage }} of connections in use"
```

**Key Points**:

- Gauge metrics don't need `rate()` (already current values)
- Alert before 100% to allow time for intervention
- 90% is typical threshold (adjust based on traffic patterns)

### Pattern 4: Absence Detection

```yaml
# file: configs/14_alert_rules.yaml
- alert: ServiceDown
  expr: |
    up{job="effectful"} == 0
  for: 1m
  labels:
    severity: critical
  annotations:
    summary: "Effectful service is down"
    description: "Prometheus cannot scrape {{ $labels.job }}"

- alert: NoMetricsReceived
  expr: |
    absent(effectful_effects_total)
  for: 2m
  labels:
    severity: critical
  annotations:
    summary: "No metrics received"
    description: "effectful_effects_total metric is missing"
```

**Key Points**:

- `up` metric (auto-generated by Prometheus) tracks scrape health
- `absent()` function detects missing metrics
- Short `for` duration (1-2m) for critical service outages

______________________________________________________________________

## Step 6: Configure Severity Levels

Use severity labels for routing and prioritization:

```yaml
# file: configs/14_alert_rules.yaml
groups:
  - name: effectful_alerts
    rules:
      # CRITICAL - Page on-call engineer
      - alert: EffectSystemDown
        expr: absent(effectful_effects_total)
        for: 2m
        labels:
          severity: critical        # Pages on-call
          component: effect_system
        annotations:
          summary: "Effect system is down"

      # WARNING - Slack notification
      - alert: HighCacheEvictionRate
        expr: rate(cache_evictions_total[5m]) > 100
        for: 10m
        labels:
          severity: warning         # Slack only
          component: cache
        annotations:
          summary: "High cache eviction rate"

      # INFO - Email notification
      - alert: NewDeploymentDetected
        expr: changes(app_version_info[5m]) > 0
        for: 1m
        labels:
          severity: info            # Email only
          component: deployment
        annotations:
          summary: "New version deployed"
```

**Routing Configuration** (in Alertmanager):

```yaml
# file: configs/14_alert_rules.yaml
# alertmanager.yml
route:
  receiver: 'default'
  routes:
    - match:
        severity: critical
      receiver: 'pagerduty'
    - match:
        severity: warning
      receiver: 'slack'
    - match:
        severity: info
      receiver: 'email'
```

______________________________________________________________________

## Step 7: Test Alerts Before Deploying

### Method 1: Manual Threshold Trigger

Lower threshold temporarily to force alert:

```yaml
# file: configs/14_alert_rules.yaml
# Original (production threshold)
expr: rate(errors_total[5m]) > 100

# Test (lower threshold)
expr: rate(errors_total[5m]) > 0.01
```

Generate some errors, wait for `for` duration, verify alert fires.

**Restore production threshold** after testing!

### Method 2: PromQL Validation

Test PromQL expression before adding to alert rules:

```bash
# In Prometheus UI (Graph tab)
# Paste expression and click Execute

sum(rate(effectful_effects_total{result="error"}[5m]))
/
sum(rate(effectful_effects_total[5m]))

# Verify output makes sense (0.0 - 1.0 range for error rate)
```

### Method 3: Unit Testing with promtool

```bash
# Install promtool (included with Prometheus)
docker compose -f docker/docker-compose.yml exec prometheus promtool --version

# Validate alert rules syntax
docker compose -f docker/docker-compose.yml exec prometheus \
  promtool check rules /etc/prometheus/alerts.yml

# Expected output:
# Checking /etc/prometheus/alerts.yml
#  SUCCESS: 3 rules found
```

### Method 4: Integration Test with Test Data

```yaml
# file: configs/14_alert_rules.yaml
# test_alerts.yml - Mock test data
evaluation_interval: 1m

tests:
  - interval: 1m
    input_series:
      - series: 'effectful_effects_total{result="error"}'
        values: '0 0 10 20 30 40'  # Simulates increasing errors
      - series: 'effectful_effects_total{result="ok"}'
        values: '100 100 100 100 100 100'

    alert_rule_test:
      - eval_time: 5m
        alertname: HighEffectErrorRate
        exp_alerts:
          - exp_labels:
              severity: critical
              component: effect_system
            exp_annotations:
              summary: "High effect error rate detected"
```

```bash
# Run test
promtool test rules test_alerts.yml
```

______________________________________________________________________

## Step 8: Add Alertmanager (Optional)

Alertmanager handles alert routing, grouping, and notifications.

### Add Alertmanager Service

```yaml
# file: configs/14_alert_rules.yaml
# docker-compose.yml
services:
  alertmanager:
    image: prom/alertmanager:latest
    container_name: alertmanager
    ports:
      - "9093:9093"
    volumes:
      - ./alertmanager/config.yml:/etc/alertmanager/config.yml:ro
      - alertmanagerdata:/alertmanager
    command:
      - '--config.file=/etc/alertmanager/config.yml'
      - '--storage.path=/alertmanager'
    restart: unless-stopped

volumes:
  alertmanagerdata:
```

### Configure Alertmanager

Create `docker/alertmanager/config.yml`:

```yaml
# file: configs/14_alert_rules.yaml
# Alertmanager configuration
global:
  slack_api_url: 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL'

route:
  receiver: 'default'
  group_by: ['alertname', 'severity']
  group_wait: 30s          # Wait 30s before sending first notification
  group_interval: 5m       # Send updates every 5m
  repeat_interval: 4h      # Re-notify every 4h if still firing

  routes:
    # Critical alerts → PagerDuty
    - match:
        severity: critical
      receiver: 'pagerduty'
      group_wait: 10s       # Faster for critical

    # Warning alerts → Slack
    - match:
        severity: warning
      receiver: 'slack'

    # Info alerts → Email
    - match:
        severity: info
      receiver: 'email'

receivers:
  - name: 'default'
    slack_configs:
      - channel: '#alerts'
        title: 'Alert: {{ .GroupLabels.alertname }}'
        text: '{{ .CommonAnnotations.description }}'

  - name: 'pagerduty'
    pagerduty_configs:
      - service_key: 'YOUR_PAGERDUTY_SERVICE_KEY'
        description: '{{ .GroupLabels.alertname }}: {{ .CommonAnnotations.summary }}'

  - name: 'slack'
    slack_configs:
      - channel: '#alerts-warnings'
        title: '⚠️  {{ .GroupLabels.alertname }}'
        text: '{{ .CommonAnnotations.description }}'
        color: 'warning'

  - name: 'email'
    email_configs:
      - to: 'team@example.com'
        from: 'alerts@example.com'
        smarthost: 'smtp.gmail.com:587'
        auth_username: 'alerts@example.com'
        auth_password: 'password'
        headers:
          Subject: '{{ .GroupLabels.alertname }}'
```

### Test Alertmanager

```bash
# Start Alertmanager
docker compose -f docker/docker-compose.yml up -d alertmanager

# Access UI
open http://localhost:9093

# Send test alert
curl -X POST http://localhost:9093/api/v1/alerts \
  -H 'Content-Type: application/json' \
  -d '[{
    "labels": {
      "alertname": "TestAlert",
      "severity": "critical"
    },
    "annotations": {
      "summary": "This is a test alert"
    }
  }]'
```

______________________________________________________________________

## Real-World Alert Examples

### HealthHub Application

```yaml
# file: configs/14_alert_rules.yaml
# docker/prometheus/alerts_healthhub.yml
groups:
  - name: healthhub_clinical_alerts
    interval: 30s
    rules:
      # HIPAA violation detection
      - alert: UnauthorizedPatientDataAccess
        expr: |
          sum(increase(healthhub_audit_events_total{
            event_type="patient_data_accessed",
            authorization_result="unauthorized"
          }[5m])) > 0
        for: 1m
        labels:
          severity: critical
          component: security
          compliance: hipaa
        annotations:
          summary: "Unauthorized patient data access detected"
          description: "{{ $value }} unauthorized access attempts in last 5 minutes"
          runbook_url: "https://healthhub.internal/runbooks/hipaa-violation"

      # Critical lab results unreviewed
      - alert: CriticalLabResultsUnreviewed
        expr: |
          sum(healthhub_unreviewed_critical_results_current{age_bucket=~"6_24h|24h_plus"}) > 0
        for: 30m
        labels:
          severity: critical
          component: clinical
        annotations:
          summary: "Critical lab results unreviewed for >6 hours"
          description: "{{ $value }} critical lab results awaiting review"

      # Medication interaction detected
      - alert: HighSeverityMedicationInteraction
        expr: |
          sum(increase(healthhub_medication_interactions_detected_total{
            severity="high"
          }[5m])) > 0
        for: 1m
        labels:
          severity: warning
          component: clinical
        annotations:
          summary: "High-severity medication interaction detected"
          description: "{{ $value }} high-severity interactions in last 5 minutes"
```

### E-Commerce Application

```yaml
# file: configs/14_alert_rules.yaml
groups:
  - name: ecommerce_business_alerts
    rules:
      # Payment failures spike
      - alert: HighPaymentFailureRate
        expr: |
          sum(rate(payments_total{status="failed"}[5m]))
          /
          sum(rate(payments_total[5m]))
          > 0.10
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Payment failure rate above 10%"
          description: "{{ $value | humanizePercentage }} of payments failing"

      # Low inventory warning
      - alert: LowInventory
        expr: inventory_items_available < 10
        for: 1h
        labels:
          severity: warning
        annotations:
          summary: "Low inventory for {{ $labels.product_id }}"
          description: "Only {{ $value }} items remaining"
```

______________________________________________________________________

## Best Practices

### DO

**✅ Write Actionable Alerts**

```yaml
# file: configs/14_alert_rules.yaml
# Good: Includes specific threshold and action
annotations:
  summary: "High error rate (>5%) detected"
  description: "Error rate is {{ $value | humanizePercentage }}. Check recent deployments."
  runbook_url: "https://docs.example.com/runbooks/high-error-rate"
```

**✅ Use `for` Duration**

```yaml
# file: configs/14_alert_rules.yaml
# Good: Waits 5m to avoid transient spikes
for: 5m
```

**✅ Add Runbook URLs**

```yaml
# file: configs/14_alert_rules.yaml
annotations:
  runbook_url: "https://docs.example.com/runbooks/slow-database"
```

**✅ Group Related Alerts**

```yaml
# file: configs/14_alert_rules.yaml
groups:
  - name: database_alerts      # Group by subsystem
  - name: api_alerts
  - name: cache_alerts
```

### DON'T

**❌ Alert on Everything**

```yaml
# file: configs/14_alert_rules.yaml
# Bad: Noisy, not actionable
- alert: AnyError
  expr: rate(errors_total[5m]) > 0  # Fires on single error!
```

**❌ Forget `for` Duration**

```yaml
# file: configs/14_alert_rules.yaml
# Bad: Fires immediately on transient spike
- alert: HighLatency
  expr: latency_seconds > 1.0
  # Missing: for: 5m
```

**❌ Use Vague Descriptions**

```yaml
# file: configs/14_alert_rules.yaml
# Bad: No context or action
annotations:
  summary: "Something is wrong"
```

**❌ Too Many Severity Levels**

```yaml
# file: configs/14_alert_rules.yaml
# Bad: Too granular
labels:
  severity: p0  # Use: critical
  severity: p1  # Use: warning
  severity: p2  # Use: warning
  severity: p3  # Use: info
  severity: p4  # Don't alert
```

______________________________________________________________________

## Troubleshooting

### Alert Not Firing

**Check**:

1. PromQL expression returns data: Query in Graph tab
1. Expression evaluates to true: Check value > threshold
1. `for` duration passed: Wait full duration
1. Alert rules loaded: Status → Rules

**Debug**:

```bash
# Check alert state
curl http://localhost:9090/api/v1/alerts | jq

# Expected output includes alert with state="pending" or "firing"
```

### Alert Fires Too Often

**Solutions**:

- Increase threshold (e.g., `> 0.05` → `> 0.10`)
- Increase `for` duration (e.g., `for: 5m` → `for: 10m`)
- Use longer rate window (e.g., `[5m]` → `[10m]`)

### Alert Never Resolves

**Check**:

- Expression still true? (Query in Graph tab)
- Metric labels changed? (Label mismatch prevents resolution)

______________________________________________________________________

## Summary

- Authored Prometheus alert rules with clear severity, duration, and annotations.
- Loaded and tested rules in Prometheus, then routed notifications via Alertmanager.
- Captured troubleshooting steps to reduce noise, flapping, and misconfigured expressions.

## Next Steps

- Pair alerts with dashboards in [grafana_dashboards.md](./grafana_dashboards.md).
- Define runbooks and SLOs aligned to alerts using [Monitoring & Alerting](../engineering/monitoring_and_alerting.md).
- Refine metric selection using [Metric Types Guide](metric_types_guide.md) for better alert signals.

______________________________________________________________________

## See Also

- [Monitoring & Alerting](../engineering/monitoring_and_alerting.md#alerting-policy) - Alert philosophy and severity levels
- [Prometheus Setup](./prometheus_setup.md) - Docker integration
- [Grafana Dashboards](./grafana_dashboards.md) - Visualize metrics
- [Metrics Quickstart](./metrics_quickstart.md) - Getting started

______________________________________________________________________

## Cross-References

- [Documentation Standards](../documentation_standards.md)
- [Engineering Standards](../engineering/README.md)
