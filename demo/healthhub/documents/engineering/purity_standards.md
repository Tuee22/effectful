# Purity Standards for HealthHub (Deltas)

> Supplements base [Code Quality](../../../../documents/engineering/code_quality.md#purity-doctrines) and [Documentation Standards](../../../../documents/documentation_standards.md). Base purity rules apply; this file lists HIPAA-focused overlays only.

---

## Scope
- HealthHub-specific enforcement for purity as a HIPAA §164.312 control.
- Applies to routes, programs, interpreters, domain models, and tests inside `demo/healthhub/`.
- Use this doc alongside the base purity doctrines; do not restate them here.

## HealthHub-specific overlays
- **Audit coupling**: Every PHI read/write must emit an audit effect from interpreters; programs stay pure and must not log or audit directly. See [Code Quality overlay](code_quality.md#healthhub-specific-additions).
- **I/O isolation**: Routes call `run_program` only; no direct DB/Redis/Pulsar/HTTP clients in programs or domain modules. Violations map to HIPAA §164.312(b) (audit controls) and §164.312(c)(1) (integrity).
- **Idempotent effects**: Require opaque identifiers (`appointment_id`, `lab_order_id`) for retries; effects must be safe to re-run without duplicating PHI side effects.
- **Notification discipline**: Patient-facing notifications are fire-and-forget and PHI-free; pair with audit + metric recording in interpreters.
- **Redaction defaults**: Interpreters redact PHI from logs/metrics; programs may only pass opaque IDs and role context.
- **Banned imports**: Keep Ruff bans for direct infra clients in pure layers (asyncpg, redis, pulsar, boto3). Add bans for new infra before usage lands.

## Review checklist (delta-specific)
- [ ] Program generators are synchronous/pure; zero `await` and zero direct infra calls.
- [ ] Audit effect emitted for every PHI read/write path; notifications PHI-free and non-blocking.
- [ ] Effect payloads carry opaque IDs + tenant context; no names/addresses/SSN/MRN values.
- [ ] Interpreters return typed Result/ADT errors; no raw exceptions or silent failures.
- [ ] Retry logic uses bounded attempts and idempotency keys; no unbounded loops.
- [ ] Ruff bans present for new infra modules introduced in pure layers.

## ADR expectations
- Deviations from base purity doctrine require an ADR linked from this overlay and the relevant module. Include HIPAA rationale and sunset date.

## See also
- Base: [Code Quality](../../../../documents/engineering/code_quality.md#purity-doctrines)
- Overlay: [Code Quality (HealthHub)](code_quality.md)
- Overlay: [Effect Patterns](effect_patterns.md)
- Overlay: [Monitoring & Alerting](monitoring_and_alerting.md)
- Domain: [HIPAA Compliance](../domain/hipaa_compliance.md)

---

**Last Updated**: 2025-11-27  
**Supersedes**: none  
**Referenced by**: README.md, code_quality.md, effect_patterns.md, monitoring_and_alerting.md
