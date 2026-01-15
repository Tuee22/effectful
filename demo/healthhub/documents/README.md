# HealthHub Documentation

**Status**: reference only
**Supersedes**: none
**Referenced by**: | **📖 Base Standard**: [readme.md](../../../documents/readme.md)

> **Purpose**: HealthHub overlay deltas for Readme. See base SSoT for canonical navigation and guidance.
> **📖 Authoritative Reference**: [readme.md](../../../documents/readme.md)

## Deltas

- No additional deltas; inherits base standard.

## Scope

- HealthHub inherits all Effectful standards. Only deltas/overrides live under this directory.
- Overlay docs mirror base filenames (e.g., `engineering/docker_workflow.md` overrides `documents/engineering/docker_workflow.md`).

## Navigation

- **Engineering Overlays**: [engineering/](engineering/README.md) — HealthHub-specific overrides for architecture, authentication, observability, operations, and feature engineering patterns.
- **Boundary Model**: [engineering/boundary_map.md](engineering/boundary_map.md) — HealthHub as reference implementation for the Effectful boundary model.
- **Product Documentation**: [product/roles/](product/roles/README.md) — User-facing operational guides (role guides, workflows).
- **Domain Documentation**: [domain/](domain/hipaa_compliance.md) — HealthHub-specific domain models: HIPAA compliance, appointment workflows, and medical state machines.
- **Tutorials**: [tutorials/](tutorials/README.md) — Journey-based progressive learning paths, plus library deltas for base Effectful tutorials.
- **API Overlays**: [api/](api/README.md) — API notes tailored for HealthHub services.

## Obligations

- Link back to the base SSoT before listing deltas in any overlay doc.
- Do not duplicate base procedures or examples; describe only HealthHub-specific differences and link to the base doc for rationale.
