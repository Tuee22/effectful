# Architecture

**Status**: reference only
**Supersedes**: none
**Referenced by**: | **📖 Base Standard**: [architecture.md](../../../../documents/engineering/architecture.md)

> **Purpose**: HealthHub overlay deltas for Architecture. See base SSoT for canonical guidance.
> **📖 Authoritative Reference**: [architecture.md](../../../../documents/engineering/architecture.md)

## Deltas

This follows base with no changes beyond service name (`healthhub`) and compose location.

Domain modelling, architecture overview, and medication interaction handling all defer to the base architecture doc; apply HealthHub-specific ports, credentials, and service names where applicable.
Startup/config assembly follows the base **Pure Interpreter Assembly Doctrine** (`../../../../documents/engineering/architecture.md#pure-interpreter-assembly-doctrine`); no HealthHub-specific deviations beyond settings values/paths.

## Cross-References

- [HealthHub Documentation Guide](../documentation_standards.md)
- [HealthHub Documentation Hub](../readme.md)
- [Effectful Architecture](../../../../documents/engineering/architecture.md)
