# Advanced Journey (HealthHub Delta)

**Status**: Reference only
**Supersedes**: none
**Referenced by**: demo/healthhub/documents/tutorials/README.md

> **Purpose**: HealthHub overlay deltas for Advanced Journey. See base SSoT for canonical flow.
> **📖 Base Standard**: [advanced_journey.md](../../../../../documents/tutorials/01_journeys/advanced_journey.md)
> **📖 Authoritative Reference**: [advanced_journey.md](../../../../../documents/tutorials/01_journeys/advanced_journey.md)

## Deltas

- No additional deltas; inherits base standard.

## Base Tutorials

Follow the base Effectful tutorials for canonical patterns:

- [Advanced Composition](../../../../../documents/tutorials/advanced_composition.md) - Custom effects and composite interpreters
- [Production Deployment](../../../../../documents/tutorials/production_deployment.md) - Production patterns and monitoring

## HealthHub-Specific Advanced Patterns

The HealthHub demo demonstrates healthcare-specific applications:

**Custom Healthcare Effects**:

- HealthcareEffect: Patient/Doctor/Appointment/Prescription operations
- NotificationEffect: HIPAA-compliant audit logging
- See [HealthHub Effects API](../../api/effects.md) for complete effect definitions

**Composite Interpreter Pattern**:

- AuditedCompositeInterpreter: Wraps all healthcare operations with audit logging
- Automatic PHI access logging for HIPAA compliance
- See [HealthHub Effect Patterns](../../engineering/effect_patterns.md) for implementation

**Infrastructure Configuration**:

- PostgreSQL (port 5433), Redis (port 6380), Pulsar (port 6651), MinIO (port 9001)
- Settings injected at infrastructure layer (see Configuration Doctrine 7)
- See [HealthHub Docker Workflow](../../engineering/docker_workflow.md)

**Integration Testing**:

- Real infrastructure services (PostgreSQL, Redis, Pulsar, MinIO)
- Complete E2E care episode tests (patient onboarding through discharge)
- See [HealthHub Testing](../../engineering/testing.md) for integration test patterns

**Production Patterns**:

- Observability with Prometheus metrics
- HIPAA-compliant audit logging for all PHI access
- See [HealthHub Monitoring](../../engineering/monitoring_and_alerting.md)

## Cross-References

- [HealthHub Documentation Hub](../../readme.md)
- [Base Advanced Composition](../../../../../documents/tutorials/advanced_composition.md)
- [Base Production Deployment](../../../../../documents/tutorials/production_deployment.md)
- [HealthHub Custom Effects](../../api/effects.md)
- [HealthHub Effect Patterns](../../engineering/effect_patterns.md)
- [HealthHub HIPAA Compliance](../../domain/hipaa_compliance.md)
