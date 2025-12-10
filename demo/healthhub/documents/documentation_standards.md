# Documentation Standards (HealthHub Delta)

**Status**: Reference only
**Supersedes**: none
**Referenced by**: demo/healthhub/documents/readme.md

> **Purpose**: Explain how HealthHub documentation follows the delta/SSoT pattern and what belongs where, with compliance-focused engineering alignment.  
> **📖 Authoritative Reference**: ../../../documents/documentation_standards.md

---

## Base SSoT

- Follow `documents/documentation_standards.md` for all documentation rules (SSoT-first, DRY + linking, naming, header metadata, Mermaid standards, docstring/code example rigor, maintenance checklist).  
- Hierarchical structure is unchanged: framework standards → core SSoTs → patterns/how-tos → generated reference.

## Refactor Intent (must-keep outcomes)

- **Delta-first everywhere**: All demo docs stay delta-only; start with a link to the base SSoT section they extend and avoid duplicating canonical content.
- **Engineering folder focus**: `engineering/` documents capture HealthHub-specific engineering concerns, especially compliance implementations (audit, authZ, state machines, data handling). Move any such material out of `product/` into the matching `engineering/` delta doc, deduping against the base SSoT.
- **Tutorial alignment**: `tutorials/` must teach the delta flow—how to apply engineering compliance patterns with HealthHub examples—without restating SSoT content.
- **Product stays product**: `product/` holds product choices and surface behaviors, not reusable engineering patterns. If it reads like a reusable pattern or control, it belongs in `engineering/`.
- **Documentation integrity**: Every doc should declare what it extends, what it adds, and link back to the SSoT and sibling deltas; redundancy is a defect to remove.

## HealthHub Deltas

- Demo docs must stay delta-only: same filenames as base docs, start with a link to the base SSoT, and avoid copying procedures, examples, or diagrams. Add future deltas here with deep links to the overridden base sections.
- When migrating content from `product/` to `engineering/`, consolidate into the relevant delta doc and remove redundant wording; keep `product/` focused on HealthHub-specific product decisions and user-facing behaviors.
- Tutorials should reference engineering deltas for compliance patterns and avoid re-teaching the SSoT—link instead.

### File Type Policy

HealthHub follows the base [File Type Policy](../../../documents/documentation_standards.md#2a-file-type-policy) with no exceptions:
- No backup files (`.bak`, `.bak2`, `.backup`, `.old`, `~`)
- No temporary files (`.tmp`, `.temp`, `.swp`, `.swo`)
- No `.txt` files (use `.md` for all documentation)
