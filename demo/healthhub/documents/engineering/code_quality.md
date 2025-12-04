# Code Quality (HealthHub Deltas)

> Extends base [Code Quality](../../../../documents/engineering/code_quality.md). Base rules apply unless explicitly overridden here.

## Scope
- Enforces HIPAA-safe coding practices layered on the base type-safety and purity doctrine.
- Applies to all HealthHub services, tools, and scripts; no exceptions for “temporary” code.
- Treats demo code as production-grade—PHI safety, deterministic behavior, and auditability are mandatory.

## Base Inheritance (do not repeat)
- Keep generators pure and synchronous; yield effects only (no direct I/O).
- Use frozen dataclasses for effects and domain models; ban `Any`, `cast()`, and `# type: ignore`.
- Keep loops out of programs; prefer combinators and state machines from base effect patterns.

## HealthHub-specific additions
- **HIPAA-focused lint bans**: retain Ruff banned APIs to block direct infra imports (asyncpg, Redis, Pulsar) from programs and domain modules.
- **PHI safety**: never log or label metrics with PHI/PII; prefer categorical tags (e.g., `portal="patient"` not patient names/ids).
- **Audit-first logging**: route sensitive events through audit log effects; avoid ad-hoc `logger.info` for PHI.
- **I/O isolation**: Routes call `run_program` only; no direct DB/Redis/Pulsar/HTTP clients in programs or domain modules. Audit emitted from interpreters, never programs.
- **Idempotent effects**: Effects carry opaque identifiers (`appointment_id`, `lab_order_id`) so retries do not duplicate PHI side effects.
- **Notification discipline**: Patient-facing notifications are fire-and-forget and PHI-free; pair with audit + metric recording in interpreters.
- **Check wrapper**: run quality gates through the demo service name:  
  `docker compose -f docker/docker-compose.yml exec healthhub poetry run check-code`
- **Outbound notifications**: ensure notification effects are non-blocking and redact PHI payloads before queuing.
- **Secrets discipline**: forbid inline secrets in tests or fixtures; use environment bindings documented in base configuration.
- **Repo hygiene**: no generated PHI data in repo history; use anonymized fixtures from `tests/pytest/fixtures/`.

## Review checklist (HealthHub)
- Programs yield effects only; zero direct DB/Redis/Pulsar/HTTP calls.
- Audit log effects emitted for PHI access, mutation, or transmission.
- Metrics/logs scrub PHI; labels are categorical; message bodies sanitized.
- Effects and domain types are frozen; constructors validate invariants.
- Exhaustive ADT matching for medical states (appointments, prescriptions, labs).
- Generators remain synchronous; interpreters own async I/O.
- Idempotency keys present for retryable effects; no unbounded retries.
- Notifications are PHI-free and non-blocking with audit/metrics on failure.
- No silent error handling; use Result/ADT error shapes per base code quality.

## Anti-patterns (blockers)
- Using patient identifiers in log/metric labels.
- Calling repositories or HTTP clients from FastAPI routes without `run_program`.
- Creating optional domain fields instead of ADT variants (e.g., `Optional[Prescription]`).
- Returning raw exceptions from interpreters instead of Result-based errors.
- Using notification failures to block business flows (violates non-blocking rule).

## Procedures
1. Author change with base standards open; map each health-related path to audit/metrics hooks.
2. Run `check-code` via the healthhub service (command above).
3. Review audit coverage: every PHI read/write must emit an audit effect.
4. Validate metric/log labels are categorical and PHI-free.
5. Ensure tests step generators to assert audit and notification effects.
6. Escalate any required exception as an ADR; no inline suppressions.

## Interpreter boundary guide
- **Routes layer**: HTTP ↔ domain conversion, `run_program` calls, Result/ADT → HTTP response translation. No infra calls.
- **Program layer**: yields effects, pattern-matches on ADTs, no `await`, no loops, no logging, no metrics.
- **Interpreter layer**: owns all I/O, emits audit events, metrics, logging, and retries.
- **Adapter layer**: typed clients for Postgres/Redis/Pulsar; keep PHI redaction here.

## Banned patterns and rewrites
- **Found**: direct DB call in program → **Rewrite**: create effect + interpreter.
- **Found**: `Optional[Patient]` → **Rewrite**: ADT capturing presence/absence (`PatientFound | PatientNotFound`).
- **Found**: logging PHI → **Rewrite**: audit effect + PHI-free metric.
- **Found**: async program → **Rewrite**: sync generator yielding effects; move async to interpreter.

## PR checklist (must be in description)
- [ ] `check-code` via `healthhub` service passed
- [ ] Audit coverage verified for PHI access/mutation paths
- [ ] Metrics/log labels PHI-free and categorical
- [ ] Generator tests cover effect order and ADT narrowing
- [ ] No banned imports in programs/domain

## Examples (PHI-safe logging)
```python
# ✅ CORRECT: audit + metric, no PHI in labels
effects = [
    RecordAuditLog(
        actor=actor_id,
        action="read_lab_result",
        resource="lab_result",
        resource_id=lab_result_id,
    ),
    IncrementMetric(name="lab_result_read_total", labels={"portal": "patient"}),
]
```

## CI expectations
- `check-code` must pass with Ruff + Black + MyPy strict + doc link checks.
- CI runs under `healthhub` container; mirror local command to avoid drift.
- Reject merges with lint suppressions for banned APIs or type ignores.

## Tooling tips
- Add Ruff bans for new infra imports as soon as they appear.
- Use MyPy plugins already configured in base; do not disable strictness.
- Run `pytest -q --maxfail=1` locally before CI to surface generator contract failures.
- Use `rg` searches for `await .*repo` and `logger.info` with PHI keywords during reviews.

## See also
- Base standards: [Code Quality](../../../../documents/engineering/code_quality.md), [Documentation Standards](../../../../documents/documentation_standards.md)
- Related overlays: [Effect Patterns](effect_patterns.md), [Testing](testing.md), [Monitoring & Alerting](monitoring_and_alerting.md)

---

**Last Updated**: 2025-12-01  
**Supersedes**: none  
**Referenced by**: effect_patterns.md, testing.md, monitoring_and_alerting.md, documentation_standards.md
