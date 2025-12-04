# Audit Logging (product surface)

> Extends base [Documentation Standards](../../../../documents/documentation_standards.md). Product-facing description only; engineering implementation lives in [engineering/monitoring_and_alerting.md#audit-logging-observability](../engineering/monitoring_and_alerting.md#audit-logging-observability). Regulatory SSoT is [domain/hipaa_compliance.md](../domain/hipaa_compliance.md).

---

## Purpose

Describe how HealthHub product surfaces expose audit logs and how feature teams should consume the engineering SSoT without redefining schemas or controls.

---

## Product Responsibilities

- **Surfacing**: Admin/support UI can filter and export audit events; no schema edits allowed.
- **Routing**: All PHI-touching routes must call the shared `LogAuditEvent` effect; no per-feature variants.
- **Configuration**: Product teams may tune views/filters; retention, required fields, and tamper controls are fixed in engineering.
- **Correlation**: Product flows must pass `correlation_id`, `purpose_of_use`, `patient_id` (when applicable), and `org_id` to enable end-to-end traceability.
- **Resilience**: Do not block patient workflows on audit sink issues; rely on the shared interpreter buffering/alerting.

---

## Source of Truth

- Engineering SSoT: [engineering/monitoring_and_alerting.md#audit-logging-observability](../engineering/monitoring_and_alerting.md#audit-logging-observability) (effect shape, interpreter, schema, monitoring, anti-patterns)
- Regulatory SSoT: [domain/hipaa_compliance.md](../domain/hipaa_compliance.md) (what must be logged and why)
- Architecture context: [architecture_overview.md](architecture_overview.md)

---

## Rollout Checklist for New Product Flows

- [ ] Identify PHI resources touched; ensure each call logs `purpose_of_use`, `patient_id`, `org_id`, `correlation_id`, and `outcome`.
- [ ] Wire to shared `LogAuditEvent`; no bespoke audit structs.
- [ ] Validate UI/export paths use the centralized audit store only.
- [ ] Confirm alerts/ownership in compliance review before launch.

---

## Related Documentation

- Domain: [HIPAA Compliance](../domain/hipaa_compliance.md)
- Engineering: [Audit Logging](../engineering/monitoring_and_alerting.md#audit-logging-observability), [Monitoring & Alerting](../engineering/monitoring_and_alerting.md), [Authorization Patterns](../engineering/authorization.md)
- Product: [Architecture Overview](architecture_overview.md)
