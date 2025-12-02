# Security Hardening (HealthHub supplement)

> Supplements base [Architecture](../../../../documents/engineering/architecture.md) and [Observability](../../../../documents/engineering/observability.md). Base rules apply; this overlay lists only HealthHub-specific deltas for PHI.

---

## Scope
- Applies to HealthHub production-like deployments handling PHI.
- Extends base security posture with HIPAA-focused controls and audit guarantees.

## HealthHub-specific deltas
- **Dual-token auth**: Keep base JWT model; HealthHub enforces short-lived access tokens, refresh in HttpOnly cookie, and rotation on every use. Link audit events to token `jti`.
- **Transport**: TLS required on all public edges; WebSocket upgrades limited to `wss://` with origin allowlist from environment. Internal service mesh may use mTLS when available.
- **Audit-first**: Every PHI read/write emits audit effects from interpreters (never from programs); audit payloads exclude PHI values and include opaque correlation IDs.
- **Rate limits**: Per-user and per-route rate limits enforced at ingress; burst limits tuned for appointment and notification endpoints to prevent PHI scraping.
- **Secrets**: All credentials loaded from environment/secret store; no defaults in code or docs. Rotate JWT signing keys and Redis/Pulsar credentials quarterly.
- **Data minimization**: Responses redact PHI in error bodies; logs/metrics use opaque IDs only. Sample data in docs stays anonymized per demo standards.

## Forbidden (demo overlay)
- Exposing PHI in logs, metrics, errors, or WebSocket messages.
- Skipping audit events for PHI access/mutation.
- Allowing WebSocket upgrades from non-allowlisted origins or plaintext.
- Embedding default credentials in code, docs, or samples.

## See also
- Base: [Architecture](../../../../documents/engineering/architecture.md), [Observability](../../../../documents/engineering/observability.md), [Monitoring & Alerting](../../../../documents/engineering/monitoring_and_alerting.md)
- Overlays: [WebSocket Security](websocket_security.md), [Authorization Patterns](authorization_patterns.md), [Documentation Standards](documentation_standards.md)

---

**Last Updated**: 2025-12-01  
**Supersedes**: none  
**Referenced by**: websocket_security.md, authorization_patterns.md, architecture.md
