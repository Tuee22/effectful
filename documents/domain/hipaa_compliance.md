# HIPAA Compliance

**Status**: Authoritative source  
**Supersedes**: none  
**Referenced by**: demo/healthhub/documents/domain/hipaa_compliance.md

> **Purpose**: SSoT for HIPAA-aligned documentation and controls across domain workflows; ties code quality standards to PHI/PII handling requirements.

## Canonical Guidance

- **Data handling**: Apply [Code Quality](../engineering/code_quality.md) purity and PHI handling rules; all PHI access and mutation go through typed effects with explicit audit trails.
- **Minimum necessary**: Model domain types to carry only required identifiers; prefer opaque identifiers over raw PHI in logs, metrics, and messages.
- **Storage + transport**: Enforce encryption-at-rest and in-transit via configuration SSoTs; never embed secrets or PHI in URLs or logs.
- **Auditing**: Emit structured audit events for all PHI access paths; route to observability pipelines defined in the observability SSoT.

## Cross-References
- [Code Quality](../engineering/code_quality.md)
- [Configuration](../engineering/configuration.md)
- [Observability](../engineering/observability.md)
- [Monitoring & Alerting](../engineering/monitoring_and_alerting.md)
