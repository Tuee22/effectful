# Medical State Machines

**Status**: Authoritative source
**Supersedes**: none **📖 Base Standard**: [medical_state_machines.md](../../../../documents/domain/medical_state_machines.md)
**Referenced by**: demo/healthhub/documents/readme.md

> **Purpose**: HealthHub overlay deltas for Medical State Machines. **📖 Base Standard**: [medical_state_machines.md](../../../../documents/domain/medical_state_machines.md)

## Canonical Guidance

- **Base pattern**: Follow [Effect Patterns — State Machines](../engineering/effect_patterns.md#state-machines) for generator structure, discriminated unions, and transition validation.
- **Domain invariants first**: Encode patient-safety and compliance rules as state invariants; reject transitions that would violate HIPAA or clinical constraints.
- **Side effects stay explicit**: All external actions (notifications, storage, audit) remain yielded effects; state transitions are pure and testable.
- **Observability**: Emit domain metrics at transitions (e.g., escalation counts, triage throughput) using the observability SSoT; prefer counters/histograms with clear labels.

## Cross-References

- [Effect Patterns — State Machines](../engineering/effect_patterns.md#state-machines)
- [Architecture](../engineering/architecture.md)
- [Code Quality](../engineering/code_quality.md)
- [Observability](../engineering/observability.md)
