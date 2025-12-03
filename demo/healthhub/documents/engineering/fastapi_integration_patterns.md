# FastAPI Integration Patterns (HealthHub supplement)

> Supplements base [Architecture](../../../../documents/engineering/architecture.md) and [Effect Patterns](../../../../documents/engineering/effect_patterns.md); base rules apply. This overlay lists only HealthHub-specific deltas.

---

## Scope
- Applies to FastAPI routes in the HealthHub demo.
- Routes remain thin adapters: HTTP DTOs ↔ effect programs; no business logic in handlers.
- PHI-facing flows must reuse base authorization and error patterns.

## HealthHub-specific deltas
- **Route wiring**: Use a single runner (`run_program`) and composite interpreter per request; build infra handles via shared helpers (`app.infrastructure`) instead of in programs.
- **Error conversion**: Centralize ADT→HTTP mapping (domain validation → 400, auth failures → 401/403, unexpected → 500) and strip PHI from responses; audit events emitted from interpreters.
- **Authorization**: Require ADT-based auth (`PatientAuthorized`/`DoctorAuthorized`) via FastAPI `Depends` before invoking programs; programs never bypass auth.
- **Request models**: Pydantic DTOs validate only; coercion into domain types happens at the boundary before calling programs.
- **Notifications**: Delivery failures surface as Result ADTs and return 202/non-blocking responses while interpreters emit audit + metrics events.
- **SQL via repositories in interpreters**: Database access happens only in interpreters through repository helpers built on `asyncpg`; routes/programs never compose SQL. Rationale: keep impurity isolated while still letting interpreters use expressive SQL (CTEs, locking, projections) tailored to each effect without leaking DB concerns into pure layers.
- **SQL injection protections**:
  - Use `asyncpg` positional parameters (`$1`, `$2`, …) exclusively; never f-string or concatenate user input into SQL.
  - Centralize SQL in repositories/interpreters; programs/routes cannot build SQL strings.
  - Prefer typed converters (`safe_uuid`, `safe_int`, `safe_decimal`, etc.) on all DB outputs before building domain objects.
  - For dynamic filters, build parameterized fragments with positional binds; avoid interpolating identifiers unless whitelisted constants.

## Forbidden (demo overlay)
- Re-implementing base routing/program patterns in route bodies.
- Constructing infrastructure clients inside programs or handlers.
- Returning raw ADTs over HTTP without centralized converters.
- Exposing PHI or internal error details in HTTP responses.

## See also
- Base: [Architecture](../../../../documents/engineering/architecture.md), [Effect Patterns](../../../../documents/engineering/effect_patterns.md), [Documentation Standards](../../../../documents/documentation_standards.md)
- Overlays: [Authorization Patterns](authorization_patterns.md), [Security Hardening](security_hardening.md), [WebSocket Security](websocket_security.md)

---

**Last Updated**: 2025-12-01  
**Supersedes**: none  
**Referenced by**: frontend_architecture.md, architecture.md, security_hardening.md
