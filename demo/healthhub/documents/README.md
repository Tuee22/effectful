# HealthHub Documentation

**Status**: Reference only  
**Supersedes**: none  
**Referenced by**: demo/healthhub/documents/documentation_standards.md

> **Purpose**: Navigation hub for HealthHub documentation deltas extending the base Effectful docs. Base standards apply; this file lists where overlays live.
> **📖 Authoritative Reference**: [Effectful Documentation](../../../documents/readme.md)

## Scope

- HealthHub inherits all Effectful standards. Only deltas/overrides live under this directory.
- Overlay docs mirror base filenames (e.g., `engineering/docker_workflow.md` overrides `documents/engineering/docker_workflow.md`).

## Navigation

- **Engineering Overlays**: [engineering/](engineering/README.md) — HealthHub-specific overrides for architecture, authentication, observability, operations, and feature engineering patterns.
- **Product Documentation**: [product/roles/](product/roles/README.md) — User-facing operational guides (role guides, workflows).
- **Domain Documentation**: [domain/](domain/hipaa_compliance.md) — HealthHub-specific domain models: HIPAA compliance, appointment workflows, and medical state machines.
- **Tutorials**: [tutorials/](tutorials/README.md) — Journey-based progressive learning paths, plus library deltas for base Effectful tutorials.
- **API Overlays**: [api/](api/README.md) — API notes tailored for HealthHub services.

## Obligations

- Link back to the base SSoT before listing deltas in any overlay doc.
- Do not duplicate base procedures or examples; describe only HealthHub-specific differences and link to the base doc for rationale.
