# Observability

**Status**: Reference only
**Supersedes**: none
**Referenced by**: none

> **Purpose**: HealthHub overlay deltas for Observability. See base SSoT for canonical telemetry guidance.
> **📖 Authoritative Reference**: [observability.md](../../../../documents/engineering/observability.md)
> **📖 Base Standard**: [observability.md](../../../../documents/engineering/observability.md)

## SSoT Link Map

| Need                          | Link                                                                          |
| ----------------------------- | ----------------------------------------------------------------------------- |
| Base observability standards  | [Effectful Observability](../../../../documents/engineering/observability.md) |
| HealthHub documentation guide | [Documentation Standards](../documentation_standards.md)                      |
| HealthHub documentation hub   | [Documentation Hub](../readme.md)                                             |

## Deltas

- HealthHub follows the base guidance; no additional deltas beyond using the HealthHub compose stack and service name (`healthhub`).
- Audit logging posture defers to the base observability SSoT; apply HealthHub-specific ports, credentials, and service names where applicable.

## Cross-References

- [HealthHub Documentation Guide](../documentation_standards.md)
- [HealthHub Documentation Hub](../readme.md)
- [Effectful Observability](../../../../documents/engineering/observability.md)
