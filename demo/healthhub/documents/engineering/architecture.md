# Architecture (HealthHub Deltas)

> Extends base [Architecture](../../../../documents/engineering/architecture.md). Base architecture rules apply; this doc lists HealthHub-specific deltas and points to supporting overlays.

## Scope
- Single-server FastAPI + React deployment (static assets served by FastAPI).
- Program runner + interpreter layering remains identical to base; adapters target HealthHub services.
- Uses Pulsar, Postgres, Redis, MinIO configured in `docker/docker-compose.yml` for the demo.

## HealthHub-specific deltas (HIPAA rationale)

### Frontend serving (FastAPI + React)
- FastAPI serves static assets and a catch-all route to keep PHI under a single origin (simpler CSP and cookie scope).
- Build via `docker compose -f demo/healthhub/docker/docker-compose.yml exec healthhub npm run build` and serve from `StaticFiles` mount.
- Cache bust with hashed assets; disable directory listings; set HSTS on the single origin.

### FastAPI route integration
- Routes are thin adapters: DTO ↔ program; no business logic in handlers.
- Use a single `run_program` + composite interpreter per request; infra handles come from shared helpers (no new clients in programs).
- Centralized ADT→HTTP mapping: validation → 400, auth failures → 401/403, unexpected → 500 with PHI stripped from responses.
- Require ADT-based auth (`PatientAuthorized`/`DoctorAuthorized`) via FastAPI `Depends` before invoking programs; programs never bypass auth.

### Security & transport
- Dual-token auth: short-lived access token + refresh in HttpOnly cookie; rotate on use and tie audit events to token `jti`.
- TLS everywhere (`https://` / `wss://`), origin allowlist, and optional mTLS inside the mesh when available.
- Rate limits per user and per route, tuned for appointment/notification endpoints to deter PHI scraping.
- Audit-first: every PHI read/write emits audit effects from interpreters; payloads exclude PHI values and include correlation IDs.

### WebSocket controls
- One-time JWT tickets (`aud=ws`, ~60s TTL) consumed with Redis `GETDEL`; ticket `jti` is auditable.
- Enforce origin allowlist and `wss://` only; restrict `connect-src` to configured endpoints.
- Channel auth after ticket validation using ADT-based authorization per channel (patient vs doctor); default deny.
- Rate limiting per connection and per user for subscribe/publish; alerts on abuse without leaking PHI identifiers.

### State machines
- Use ADT-based state machines for appointments/prescriptions/labs/invoices; transitions validated before side effects.
- Correlate cascades (appointment → invoice → notification) with a single `correlation_id`; log both success and failure transitions for HIPAA audit.

**Why HIPAA-relevant**: Single-server static serving reduces multi-origin PHI exposure; tight route/program boundaries enable exhaustive auditing and access control; security overlays and ADT auth are explicitly mapped to HIPAA §164.312 (Access Control, Audit Controls, Integrity, Transmission Security).

## See also
- Base: [Architecture](../../../../documents/engineering/architecture.md)
- Base: [Effect Patterns](../../../../documents/engineering/effect_patterns.md)
- Base: [Code Quality](../../../../documents/engineering/code_quality.md)
- Overlay: [Documentation Standards](documentation_standards.md)

---

**Last Updated**: 2025-12-02  
**Supersedes**: none  
**Referenced by**: README.md, authorization.md
