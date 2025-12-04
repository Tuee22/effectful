# Monitoring & Alerting (HealthHub Deltas)

> Extends base [Monitoring & Alerting](../../../../documents/engineering/monitoring_and_alerting.md) and [Observability](../../../../documents/engineering/observability.md). Base rules apply unless explicitly overridden here.

## Scope
- HealthHub-specific monitoring, metrics, and alert policies on top of base observability standards.
- Applies to API, background workers, notification pipelines, and data stores in the demo stack.
- Focused on PHI-safe telemetry and audit coverage.

## Base Inheritance (retain)
- Follow base metric names, label casing, and alert severities.
- Keep dashboards and alerts defined as code where possible.
- Use TB-oriented safe Mermaid patterns when diagramming observability pipelines.

## HealthHub-specific additions (HIPAA linkage)
- **PHI metrics catalog**: track PHI access (`phi_access_total`, `phi_access_denied_total`), appointment lifecycle, lab result delivery, prescriptions, and billing events; always aggregate—no PHI/PII in labels.
- **PHI/PII guardrails**: metrics/logs exclude PHI; labels are categorical only (e.g., `portal=patient`, `result_status=abnormal`).
- **Audit alignment**: page immediately on missing audit events, audit queue backlog, or interpreter failures to emit audit logs; maps to HIPAA §164.312(b) audit controls. Required fields: purpose_of_use, patient_id/org_id when applicable, correlation_id, outcome, UTC timestamp.
- **Audit effect shape**: Use the shared `LogAuditEvent` effect (see engineering delta) with append-only interpreter, hash chaining, and idempotency key `(correlation_id, resource_id, action, outcome)`. Reject non-UTC timestamps at the interpreter boundary.
- **Notification failure policy**: notification send failures (email/SMS/WebSocket) must alert via metrics but must not block business flows; treat as non-blocking with bounded retries.
- **HIPAA traceability**: include audit event IDs in logs/metrics (opaque identifiers, not patient data) to correlate PHI access; supports forensic requirements.
- **Data store visibility**: monitor Postgres/Redis/MinIO/Pulsar with health checks tied to interpreter success rates, not raw container liveness.
- **Rate limits**: alert on sustained rate-limit breaches to detect abuse without logging identifiers.
- **Commands**: run observability checks via demo service:  
  `docker compose -f docker/docker-compose.yml exec healthhub poetry run check-code` (includes doc link verification).

## Metric/alert checklist
- [ ] No PHI in labels; only categorical values.
- [ ] Audit pipeline availability (queue depth, consumer lag) alerted at severity-1.
- [ ] Notification failure metrics alert at warning; do not halt request/worker flows.
- [ ] Interpreter success/failure ratios tracked per effect type.
- [ ] HTTP route metrics scrub identifiers; path templated.
- [ ] Dashboards link to audit and incident runbooks.

## Anti-patterns (reject)
- Embedding patient IDs, names, or MRNs in logs/metrics.
- Alerts based solely on container liveness without interpreter success context.
- Using notification delivery failures to block or roll back business logic.
- Missing correlation between audit events and effect execution.

## SLO examples (HealthHub)
- Appointment booking success rate ≥ 99.5% over 30 minutes; alert at burn-rate 14/4.
- Lab result delivery latency p95 ≤ 2 minutes; alert on sustained breach for 15 minutes.
- Audit pipeline availability 100%; any drop pages immediately.
- Notification delivery success ≥ 99%; warn on retries >3 per message.

## Metric catalog (sample)
| Metric | Labels (categorical) | Purpose |
|--------|----------------------|---------|
| `phi_access_total` | `portal`, `resource` | Count PHI reads; correlate with audits |
| `phi_access_denied_total` | `portal`, `resource` | Detect unauthorized access attempts |
| `appointment_booking_success_total` | `portal` | Booking throughput |
| `lab_result_delivery_seconds` | `portal`, `status` | Delivery latency histogram |
| `notification_send_failure_total` | `channel` | Alert on notification reliability |
| `audit_queue_depth` | `queue` | Detect backlog for audit events |

## Runbook pointers
- Link alerts to runbooks stored in product docs; include steps for audit verification and PHI redaction checks.
- Capture Grafana dashboard IDs and Prometheus queries in runbooks for reproducibility.
- Include rollback and feature-flag guidance for notification systems to keep flows non-blocking.

## Dashboard expectations
- Panels for interpreter success/failure by effect type.
- PHI access over time with anomaly detection (labels are PHI-free).
- Notification reliability panels by channel with retry counts.
- Audit pipeline health (queue depth, consumer lag, dead-letter counts).

## Procedures
1. Define metric with categorical labels; confirm PHI-free.
2. Add alert with severity mapped to clinical impact; include runbook link.
3. Add dashboard panel and annotation for deployments affecting the metric.
4. Test in staging via `healthhub` service; verify alerts fire with anonymized data.
5. Capture screenshots with redaction and alt text per documentation overlay.
6. Review alert routing with on-call rotation; page only on clinical or audit impact.

## Alert routing (HealthHub)
- **Page**: audit pipeline gaps, PHI access anomalies, lab result delivery failures.
- **Warn**: notification retries, degraded interpreter success ratios.
- **Info**: planned maintenance, analytics-only metrics.

## Data retention
- Metrics/logs must follow data retention policies that avoid storing PHI; keep retention minimal and aligned with audit requirements.
- Redact request bodies before logging; keep only opaque IDs and correlation tokens.

## Tooling
- Use Prometheus + Grafana from the demo stack; define alerts as code where possible.
- Prefer exemplars and traces that carry audit correlation IDs without PHI payloads.

## Verification
- Exercise alert rules in staging using anonymized fixtures; validate firing and routing paths.
- Document verification steps in runbooks and link them from alert descriptions.
- Re-run verification after any infra change affecting observability stack.

## See also
- Base standards: [Monitoring & Alerting](../../../../documents/engineering/monitoring_and_alerting.md), [Observability](../../../../documents/engineering/observability.md)
- Related overlays: [Testing](testing.md), [Code Quality](code_quality.md), [Effect Patterns](effect_patterns.md), [Documentation Standards](documentation_standards.md)

---

**Last Updated**: 2025-12-01  
**Supersedes**: none  
**Referenced by**: code_quality.md, effect_patterns.md, documentation_standards.md, testing.md
