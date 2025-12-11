# Intermediate Journey (HealthHub Delta)

**Status**: Reference only
**Supersedes**: none
**Referenced by**: demo/healthhub/documents/tutorials/README.md

> **Purpose**: HealthHub delta for intermediate learning path.
> **📖 Authoritative Reference**: [Effectful Effect Types](../../../../../documents/tutorials/effect_types.md), [ADTs and Results](../../../../../documents/tutorials/adts_and_results.md)

## Base Tutorials

Follow the base Effectful tutorials for canonical patterns and concepts:
- [Effect Types](../../../../../documents/tutorials/effect_types.md) - Effect programs and composition
- [ADTs and Results](../../../../../documents/tutorials/adts_and_results.md) - Type-safe error handling

## HealthHub-Specific Patterns

The HealthHub demo demonstrates healthcare-specific applications of these patterns:

**Healthcare State Machines**:
- AppointmentStatus ADT: Requested → Confirmed → InProgress → Completed (or Cancelled)
- See [Medical State Machines](../../domain/medical_state_machines.md) for complete state transitions

**Healthcare Effect Programs**:
- `schedule_appointment_program`: Multi-step workflow with validation and audit logging
- `create_prescription_program`: Medication interaction checking with doctor authorization
- `process_lab_result_program`: Critical value detection with notification cascades

**HealthHub-Specific ADTs**:
- AuthorizationState: PatientAuthorized | DoctorAuthorized | AdminAuthorized | Unauthorized
- AppointmentStatus: Complete state machine with validation rules
- See [HealthHub Domain Patterns](../../domain/) for complete ADT definitions

**Testing Patterns**:
- Generator stepping for effect programs (same as base patterns)
- Integration tests with real PostgreSQL, Redis, and Pulsar
- See [HealthHub Testing](../../engineering/testing.md) for healthcare-specific test examples

## Cross-References

- [HealthHub Documentation Hub](../../readme.md)
- [Base Effect Types Tutorial](../../../../../documents/tutorials/effect_types.md)
- [Base ADTs Tutorial](../../../../../documents/tutorials/adts_and_results.md)
- [HealthHub Medical State Machines](../../domain/medical_state_machines.md)
- [HealthHub Effect Patterns](../../engineering/effect_patterns.md)
