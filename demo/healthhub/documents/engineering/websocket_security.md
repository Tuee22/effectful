# WebSocket Security for HealthHub (HealthHub supplement)

> Supplements base [Architecture](../../../../documents/engineering/architecture.md) and [Observability](../../../../documents/engineering/observability.md). Base rules apply; this overlay lists only HealthHub-specific deltas for real-time PHI notifications.

---

## Scope
- Applies to WebSocket endpoints delivering appointment/notification updates.
- Extends base WebSocket guidance with PHI-safe controls and audit hooks.

## HealthHub-specific deltas
- **One-time tickets**: Issue short-lived JWT tickets (`aud=ws`, 60s TTL) and consume with Redis `GETDEL` to enforce single use; tie ticket `jti` to audit events.
- **Origin + protocol**: Allowlist origins from config; require `wss://` only; deny upgrades without matching origin header. CSP `connect-src` restricted to configured endpoints.
- **Channel authorization**: After ticket validation, enforce ADT-based authorization per channel (patient vs doctor) before subscribing; deny by default.
- **Rate limiting**: Per-connection + per-user limits for subscribe/publish to prevent PHI scraping; limits configured in environment.
- **Error handling**: Convert interpreter errors to close codes/messages without PHI. Delivery failures trigger audit + metrics; programs remain pure and non-blocking.
- **Fanout**: Redis pub/sub for horizontal scale; messages include opaque IDs only (no PHI payloads). Clients fetch PHI over authenticated REST when needed.

## Forbidden (demo overlay)
- Accepting non-allowlisted origins or plaintext WebSockets.
- Including PHI in WebSocket payloads, logs, or close reasons.
- Reusing tickets (missing `GETDEL`) or skipping channel-level authorization.
- Blocking program flow on notification delivery failures.

## See also
- Base: [Architecture](../../../../documents/engineering/architecture.md), [Observability](../../../../documents/engineering/observability.md), [Monitoring & Alerting](../../../../documents/engineering/monitoring_and_alerting.md)
- Overlays: [Security Hardening](security_hardening.md), [Authorization Patterns](authorization_patterns.md), [Documentation Standards](documentation_standards.md)

---

**Last Updated**: 2025-12-01  
**Supersedes**: none  
**Referenced by**: architecture.md, security_hardening.md
