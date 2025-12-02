# Documentation Standards (HealthHub Deltas)

> Extends base [Documentation Standards](../../../../documents/documentation_standards.md). Base rules apply unless explicitly overridden here.

## Scope
- Applies to all HealthHub documentation (engineering, tutorials, domain, product) hosted in this demo tree.
- Keeps demo docs as deltas only—link back to base SSoTs for canonical definitions.
- Enforces PHI-safe writing, diagrams, and screenshots.

## Base Inheritance (keep)
- Follow SSoT/DRY: link to base standards instead of restating them.
- Use the safe Mermaid subset (TB orientation; no subgraphs, dotted lines, or `Note over`).
- Include required headers and metadata (`Last Updated`, `Referenced by`).
- Use imperative mood and active voice.

## HealthHub-specific additions
- **Accessibility**: WCAG AA color contrast; alt text for all images and diagrams; avoid color-only encoding for medical states.
- **PHI redaction**: never include real patient data; use anonymized fixtures; strip IDs from diagrams and logs shown in docs.
- **Mermaid usage**: prefer `flowchart TB` for medical workflows; keep labels PHI-free and free of special characters.
- **Audit alignment**: when describing flows that touch PHI, link to audit logging rules in [Code Quality](code_quality.md) and [Monitoring & Alerting](monitoring_and_alerting.md).
- **Inheritance reminder**: every demo doc must start with a base link; add context on what is overridden, not the full content.

## Writing checklist (HealthHub)
- [ ] Title + base link present at top.
- [ ] States what differs from base; avoids copying base text.
- [ ] All diagrams use safe subset and PHI-free labels.
- [ ] Screenshots/samples anonymized; redact IDs, names, MRNs.
- [ ] Links point to base SSoTs for definitions/procedures.
- [ ] Metadata block added (`Last Updated`, `Referenced by`).

## Anti-patterns (reject)
- Rewriting base standards instead of linking.
- Using real patient data or screenshots from production systems.
- Mermaid diagrams with subgraphs, dotted lines, `Note over`, or LR orientation on long flows.
- Missing alt text or color-only state indicators.
- Demo docs that do not declare which base doc they extend.
- Standalone demo docs that replace base content instead of describing deltas.

## Content types
- **Engineering overlays**: deltas only; use same filename as base doc where applicable; link to base in first paragraph.
- **Product/domain notes**: reference base standards for terminology; flag any domain-specific exceptions clearly.
- **Tutorial overlays**: keep short summaries; link to base tutorials for steps; ensure PHI-free sample data.
- **Runbooks**: place in product domain tree; include links to monitoring and audit rules; redact identifiers in examples.

## Diagram and screenshot rules
- Use TB orientation for workflows; keep labels simple and PHI-free.
- Avoid timelines or swimlanes with real timestamps; use generic examples.
- Add alt text noting that data is anonymized; call out where audit events occur.
- For screenshots, blur/redact IDs, names, MRNs, and addresses; prefer seeded demo data.

## PHI scrub workflow
1. Replace names/IDs with anonymized placeholders (`Patient Alpha`, `lab_result_id=LR-001`).
2. Remove dates of birth, addresses, phone numbers; use generic ranges where needed.
3. Verify code snippets and shell output do not leak PHI.
4. Re-read diagrams for accidental PHI (node labels, tooltips).
5. Run link checks and commit only after verification.

## Demo doc template (overlay)
```markdown
# [Title] (HealthHub Deltas)
> Extends base [Title](../../../../documents/engineering/[file].md). Base rules apply unless explicitly overridden here.

## Scope
- [What differs]

## HealthHub-specific additions
- [Delta 1]
- [Delta 2]

## See also
- Base standards: [...]
- Related overlays: [...]

---
**Last Updated**: YYYY-MM-DD  
**Referenced by**: [...]
```

## Review workflow
- Author drafts with base doc open; confirm only deltas are described.
- Reviewer checks PHI scrub, accessibility, link completeness, and header metadata.
- Block merges if the doc restates base content instead of linking.
- Store screenshots and diagrams in repo under `demo/healthhub/documents/assets/` with redaction noted in alt text.
- File an ADR when deviating from base standards; include justification and link from the overlay.

## Procedures
1. Start from the base doc; list only HealthHub deltas.
2. Add accessibility and PHI-safety notes for every diagram or screenshot.
3. Cross-link to audit, monitoring, and testing overlays when flows involve PHI.
4. Run link verification as part of `check-code`.
5. Add metadata block and submit for review.

## See also
- Base standards: [Documentation Standards](../../../../documents/documentation_standards.md)
- Related overlays: [Monitoring & Alerting](monitoring_and_alerting.md), [Effect Patterns](effect_patterns.md), [Code Quality](code_quality.md)

---

**Last Updated**: 2025-12-01  
**Supersedes**: none  
**Referenced by**: monitoring_and_alerting.md, code_quality.md, effect_patterns.md, testing.md
