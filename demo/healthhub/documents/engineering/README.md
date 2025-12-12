# HealthHub Engineering Best Practices

**Status**: Reference only\\
**Supersedes**: none **📖 Base Standard**: [README.md](../../../../documents/engineering/README.md)
**Referenced by**: demo/healthhub/documents/readme.md

> **Purpose**: HealthHub overlay deltas for Readme. **📖 Base Standard**: [README.md](../../../../documents/engineering/README.md)
> **📖 Authoritative Reference**: [README.md](../../../../documents/engineering/README.md)

______________________________________________________________________

## Deltas

- Base SSoT: [Effectful Engineering Standards](../../../../documents/engineering/README.md); use the base doc for all canonical guidance.
- HealthHub-specific adjustments are limited to service naming (`healthhub`) and compose location (`demo/healthhub/docker/docker-compose.yml`). Add future engineering deltas in the matching overlay file (same filename as the base) instead of copying procedures.

## HealthHub-Specific Engineering Documentation

### Feature Engineering Patterns

HealthHub-specific feature implementation patterns documenting domain models, state machines, effect programs, and RBAC enforcement.

**Location**: [features/](features/README.md)

**Content**:

- Authentication - JWT, RBAC, auth state ADT
- Appointments - State machine, transitions, scheduling
- Prescriptions - RBAC, medication interactions, doctor-only
- Lab Results - Critical alerts, doctor review, notifications
- Invoices - Billing, payment status, line items

**Use Case**: Developers working on specific features need deep technical understanding of feature implementation

## Cross-References

- [HealthHub Documentation Guide](../documentation_standards.md)
- [Effectful Engineering Standards](../../../../documents/engineering/README.md)
- [HealthHub Feature Engineering Patterns](features/README.md)
