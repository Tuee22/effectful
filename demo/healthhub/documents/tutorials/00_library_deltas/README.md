# Library Delta Tutorials

**Status**: reference only
**Supersedes**: none
**Referenced by**: | **📖 Base Standard**: [README.md](../../../../../documents/tutorials/00_library_deltas/README.md)

> **Purpose**: HealthHub overlay deltas for library delta tutorials. See base SSoT for canonical guidance.
> **📖 Authoritative Reference**: [README.md](../../../../../documents/tutorials/00_library_deltas/README.md)

______________________________________________________________________

## Delta Pattern

Each file in this directory:

- **Links to base tutorial** as authoritative source
- **Documents ONLY HealthHub-specific deltas**: compose file path, service name, ports, credentials
- **Avoids duplication** of base content (procedures, examples, diagrams)
- **~17 lines per file** (minimal reference documents)

**Example Delta Structure**:

```markdown
# Tutorial Title



## Deltas
- Use `docker/docker-compose.yml` (not `docker-compose.yml`)
- Service name: `healthhub` (not `effectful`)
- Port: 8851 (not 8080)
- Apply HealthHub-specific credentials where applicable

## Cross-References
- [HealthHub Documentation Guide](../../../../../documents/readme.md)
- [Base Tutorials](../../../../../documents/tutorials/)
```

______________________________________________________________________

## Library Delta Tutorials

| Delta File                                           | Base Tutorial                                                                                  | Key Deltas                                                    |
| ---------------------------------------------------- | ---------------------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| [quickstart.md](quickstart.md)                       | [Effectful Quickstart](../../../../../documents/tutorials/quickstart.md)                       | Compose stack, service name `healthhub`                       |
| [adts_and_results.md](adts_and_results.md)           | [Effectful ADTs and Results](../../../../../documents/tutorials/adts_and_results.md)           | HealthHub domain ADTs (AppointmentStatus, AuthorizationState) |
| [effect_types.md](effect_types.md)                   | [Effectful Effect Types](../../../../../documents/tutorials/effect_types.md)                   | HealthcareEffect, NotificationEffect                          |
| [testing_guide.md](testing_guide.md)                 | [Effectful Testing Guide](../../../../../documents/tutorials/testing_guide.md)                 | HealthHub test fixtures, e2e patterns                         |
| [production_deployment.md](production_deployment.md) | [Effectful Production Deployment](../../../../../documents/tutorials/production_deployment.md) | HealthHub-specific deployment                                 |
| [advanced_composition.md](advanced_composition.md)   | [Effectful Advanced Composition](../../../../../documents/tutorials/advanced_composition.md)   | AuditedCompositeInterpreter                                   |
| [messaging_effects.md](messaging_effects.md)         | [Effectful Messaging Effects](../../../../../documents/tutorials/messaging_effects.md)         | HealthHub Pulsar configuration                                |
| [migration_guide.md](migration_guide.md)             | [Effectful Migration Guide](../../../../../documents/tutorials/migration_guide.md)             | Migrating to HealthHub patterns                               |

______________________________________________________________________

## When to Use Delta Tutorials

**Use delta tutorials when**:

- Following base Effectful tutorial but working in HealthHub codebase
- Need HealthHub-specific configuration (compose file, service name, ports)
- Looking for HealthHub domain examples of base patterns

**Don't use delta tutorials for**:

- Learning HealthHub features → Use [Feature Tutorials](../../engineering/features/README.md)
- Learning by role → Use [Role Guides](../../product/roles/README.md)
- Progressive learning → Use [Journey Tutorials](../../tutorials/01_journeys/README.md)

______________________________________________________________________

## Cross-References

- [HealthHub Tutorial Hub](../README.md)
- [Effectful Base Tutorials](../../../../../documents/tutorials/)
- [HealthHub Documentation Standards](../../../../../documents/readme.md)
