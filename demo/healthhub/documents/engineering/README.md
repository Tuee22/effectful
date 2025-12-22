# HealthHub Engineering Best Practices

**Status**: Reference only
**Supersedes**: none
**Referenced by**: demo/healthhub/documents/engineering/build_artifact_management.md, demo/healthhub/documents/engineering/docker.md

> **Purpose**: HealthHub overlay deltas for Engineering Standards. See base SSoT for canonical navigation and policies.
> **📖 Authoritative Reference**: [README.md](../../../../documents/engineering/README.md)
> **📖 Base Standard**: [README.md](../../../../documents/engineering/README.md)

## SSoT Link Map

| Need                           | Link                                                                           |
| ------------------------------ | ------------------------------------------------------------------------------ |
| Base engineering standards     | [Effectful Engineering Standards](../../../../documents/engineering/README.md) |
| HealthHub Docker configuration | [Docker & Environment Variables](docker.md)                                    |
| HealthHub build artifacts      | [Build Artifact Management](build_artifact_management.md)                      |
| HealthHub warnings policy      | [Warnings Policy](warnings_policy.md)                                          |
| Feature engineering patterns   | [Feature Engineering Patterns](features/README.md)                             |
| Documentation standards        | [Documentation Standards](../documentation_standards.md)                       |

______________________________________________________________________

## Deltas

- Base SSoT: [Effectful Engineering Standards](../../../../documents/engineering/README.md); use the base doc for all canonical guidance.
- HealthHub-specific adjustments are limited to service naming (`healthhub`) and compose location (`demo/healthhub/docker/docker-compose.yml`). Add future engineering deltas in the matching overlay file (same filename as the base) instead of copying procedures.
- Apply **Total Pure Modelling** to request DTOs: Pydantic/FastAPI models are boundaries and must normalize immediately to `OptionalValue`/ADT variants—no `None` gaps carried into domain logic (see [effect_patterns.md#pattern-6-boundary-normalization-for-optionalvalue](../../../../documents/engineering/effect_patterns.md#pattern-6-boundary-normalization-for-optionalvalue)).

## HealthHub-Specific Engineering Documentation

### Docker & Environment Variables

HealthHub-specific environment variables, cache directories, frontend build management, and pytest enforcement.

**Location**: [docker.md](docker.md)

**Content**:

- PYTHONPATH configuration for dual effectful/healthhub imports
- `/opt/healthhub/` cache namespace (separate from effectful)
- Frontend build management (vite build in Dockerfile)
- Pytest wrapper (4 test categories: test-all, test-backend, test-integration, test-e2e)

**Use Case**: Understanding HealthHub-specific Docker configuration and build artifacts

### Build Artifact Management

HealthHub-specific build artifacts including frontend build output, lock file patterns, and cache namespace.

**Location**: [build_artifact_management.md](build_artifact_management.md)

**Content**:

- Frontend build artifacts (`/opt/healthhub/frontend-build/build/`)
- Frontend lock file pattern (regenerated in-container)
- HealthHub cache namespace (prevents conflicts with effectful)
- Enhanced lock guard with pip fallback

**Use Case**: Understanding HealthHub build process and artifact lifecycle

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
- [HealthHub Docker & Environment Variables](docker.md)
- [HealthHub Build Artifact Management](build_artifact_management.md)
- [HealthHub Warnings Policy](warnings_policy.md)
- [HealthHub Feature Engineering Patterns](features/README.md)
