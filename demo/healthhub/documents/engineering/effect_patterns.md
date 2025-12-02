# Effect Patterns (HealthHub Deltas)

> Extends base [Effect Patterns](../../../../documents/engineering/effect_patterns.md). Base rules apply unless explicitly overridden here.

## Scope
- HealthHub-specific shape rules for effects, programs, and interpreters on top of the base patterns.
- Focused on PHI-safe auditability, non-blocking notifications, and medical ADT handling.
- Applies to new effects, refactors, and reviews inside the HealthHub demo.

## Base Inheritance (retain)
- Programs stay pure and synchronous; interpreters own all I/O.
- Effects use verb-noun naming and frozen dataclasses.
- Exhaustive matching on ADT results; use `assert_never` for unreachable states.
- Non-blocking notifications and Result-based error handling remain mandatory.

## HealthHub-specific additions
- **Audit logging**: every PHI access/mutation effect must be paired with an audit log effect; emit from interpreters, not programs.
- **Patient messaging**: SMS/email/WebSocket effects are fire-and-forget; failures log to audit/metrics but must not abort business flows.
- **Medical ADT narrowing**: after each yield, pattern-match appointment/prescription/lab ADTs; use dedicated error ADTs for invalid transitions.
- **State machines**: compose appointment/prescription/lab state machines via sub-programs; transitions validated before side effects.
- **Security context**: propagate authenticated principal through effects; forbid implicit globals for user identity.
- **Idempotency**: design effects with idempotent identifiers (appointment_id, prescription_id, lab_order_id) to support retries.
- **Notifications vs. audits**: audit logs capture PHI access; notifications redact PHI and avoid embedding identifiers.

## Effect design checklist
- [ ] Frozen dataclass with verb-noun name and explicit types.
- [ ] Identifiers include tenant/account context; no raw patient names.
- [ ] Result/ADT return type documents all outcomes, including PHI redaction errors.
- [ ] Audit effect emitted for PHI reads/writes.
- [ ] Notification effects marked non-blocking; interpreter swallows and reports failures via metrics/audit.
- [ ] State machine transitions validated before interpreter calls infra.

## Anti-patterns (reject)
- Effect interpreters that raise exceptions instead of returning Result/ADT errors.
- Programs that block on notification delivery or retry indefinitely.
- Mixing routing concerns (HTTP) into interpreters or programs.
- Carrying PII in effect payloads when an opaque identifier plus audit context suffices.
- Omitting exhaustiveness checks on medical ADTs.

## Example pattern: audit + notification split
1. Program yields `ReadLabResult` effect.
2. Interpreter fetches result, emits `RecordAuditLog` with PHI access context.
3. Interpreter emits `SendNotification` with PHI-free message body.
4. Program pattern-matches on `ReadLabResultResult` ADT; handles not-found and unauthorized cases explicitly.

## Effect categories (HealthHub)
- **Clinical reads**: `ReadLabResult`, `ReadPrescription`, `ReadAppointment`; must produce audit events and PHI-free metrics.
- **Clinical writes**: `UpdateLabResult`, `UpdatePrescription`, `ScheduleAppointment`; validate transitions via ADTs before touching infra.
- **Notifications**: `SendAppointmentReminder`, `SendLabResultNotification`; non-blocking, PHI-free payloads.
- **Security**: `AuthorizePrincipal`, `RecordAuditLog`; always emitted from interpreters, never from programs directly.

## Interpreter guidance
- Emit audit events adjacent to PHI access; include actor, action, resource, and opaque resource_id.
- Retry idempotent effects with bounded attempts; include idempotency keys per effect payload.
- Capture metrics for interpreter success/failure per effect type; avoid leaking identifiers.
- Translate infra errors into domain Result/ADT errors; never raise raw exceptions.

## State machine integration
- Delegate state validation to dedicated state machine modules; programs call state transitions before yielding effects.
- Use `assert_never` after matching transition results to ensure exhaustiveness.
- Keep terminal states explicit (`is_terminal(state)`) and avoid implicit `None` checks.

## Testing expectations
- Step generators to assert effect order (e.g., audit before notification).
- Validate interpreters emit audit + metric side effects and return Result/ADT errors.
- Use anonymized fixtures; never assert on PHI values in tests.

## Anti-pattern rewrites
- **Found**: notification effect contains PHI → **Rewrite**: send PHI-free message; include audit event for access.
- **Found**: interpreter raises `Exception` → **Rewrite**: return typed error ADT; emit metric/audit.
- **Found**: program awaits HTTP client → **Rewrite**: create effect + interpreter.

## Sample ADT (appointments)
```python
@dataclass(frozen=True)
class ConfirmAppointment:
    appointment_id: AppointmentId
    actor: ActorId

@dataclass(frozen=True)
class ConfirmAppointmentResult:
    result: AppointmentConfirmed | AppointmentNotFound | AppointmentAlreadyFinalized
```
Programs must pattern-match on `result` and use `assert_never` for exhaustiveness.

## Review steps
- Check effect payloads for opaque identifiers and missing audit context.
- Ensure interpreters emit audit + metric side effects before returning.
- Verify programs handle every ADT variant and keep notifications non-blocking.
- Align authorization decisions with dedicated authorization effects; avoid inline role checks inside programs.
- Record deviations in an ADR and link from this overlay when base patterns cannot be followed.

## See also
- Base standards: [Effect Patterns](../../../../documents/engineering/effect_patterns.md), [Architecture](../../../../documents/engineering/architecture.md)
- Related overlays: [Code Quality](code_quality.md), [Testing](testing.md), [Monitoring & Alerting](monitoring_and_alerting.md)

---

**Last Updated**: 2025-12-01  
**Supersedes**: none  
**Referenced by**: testing.md, monitoring_and_alerting.md, code_quality.md, documentation_standards.md
