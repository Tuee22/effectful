# Appointment Workflows

**Status**: Authoritative source
**Supersedes**: none
**Referenced by**: demo/healthhub/documents/readme.md

> **Purpose**: SSoT for HealthHub appointment lifecycle workflows (scheduling, rescheduling, cancellation, follow-up) using the medical state machine patterns.

## Canonical Guidance

- **Reuse core machine**: Build appointment flows on top of the [Medical State Machines](medical_state_machines.md) SSoT; apply the same transition validation and invariants.
- **Explicit states**: Model discrete states (requested, confirmed, rescheduled, completed, no-show) as a closed ADT; avoid optionals for missing data.
- **Auditability**: Record every transition with user identity and timestamp via yielded audit effects; avoid inline logging or hidden side effects.
- **Error handling**: Surface scheduling conflicts as domain errors through `Err` results; do not encode failures as terminal states unless they are part of the business process.

## Cross-References
- [Medical State Machines](medical_state_machines.md)
- [Effect Patterns — State Machines](../engineering/effect_patterns.md#state-machines)
- [Architecture](../engineering/architecture.md)
- [Code Quality](../engineering/code_quality.md)
