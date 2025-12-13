# Effect Patterns

**Status**: reference only
**Supersedes**: none
**Referenced by**: | **📖 Base Standard**: [effect_patterns.md](../../../../documents/engineering/effect_patterns.md)

> **Purpose**: HealthHub overlay deltas for Effect Patterns. See base SSoT for canonical guidance.
> **📖 Authoritative Reference**: [effect_patterns.md](../../../../documents/engineering/effect_patterns.md)

## Deltas

- HealthHub follows the base guidance; no additional deltas beyond using the HealthHub compose stack and service name (`healthhub`).
- State machine implementations (e.g., appointments) and effect program references defer to the base patterns doc; apply HealthHub-specific ports, credentials, and service names where applicable.

## State Machines

- Use the base [Effect Pattern State Machine guidance](../../../../documents/engineering/effect_patterns.md#state-machines) with HealthHub-specific ADTs.
- Appointment and lab result state machines live in the HealthHub domain docs; behaviors match the base SSoT.

## Cross-References

- [HealthHub Documentation Guide](../documentation_standards.md)
- [HealthHub Documentation Hub](../readme.md)
- [Effectful Effect Patterns](../../../../documents/engineering/effect_patterns.md)
