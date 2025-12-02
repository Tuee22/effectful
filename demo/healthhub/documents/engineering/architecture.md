# Architecture (HealthHub Deltas)

> Extends base [Architecture](../../../../documents/engineering/architecture.md). Base architecture rules apply; this doc lists HealthHub-specific deltas and points to supporting overlays.

## Scope
- Single-server FastAPI + React deployment (static assets served by FastAPI).
- Program runner + interpreter layering remains identical to base; adapters target HealthHub services.
- Uses Pulsar, Postgres, Redis, MinIO configured in `docker/docker-compose.yml` for the demo.

## HealthHub-specific deltas
- **Frontend serving**: See [Frontend Architecture](frontend_architecture.md) for FastAPI static serving and build pipeline.
- **Route integration**: See [FastAPI Integration Patterns](fastapi_integration_patterns.md) for route → program wiring and error conversion.
- **Security overlays**: See [Security Hardening](security_hardening.md) and [WebSocket Security](websocket_security.md) for HIPAA-focused controls.
- **Authorization**: See [Authorization Patterns](authorization_patterns.md) for ADT-based auth rules and result translation.
- **State machines**: See [State Machine Patterns](state_machine_patterns.md) for medical workflow orchestration.

## See also
- Base: [Architecture](../../../../documents/engineering/architecture.md)
- Base: [Effect Patterns](../../../../documents/engineering/effect_patterns.md)
- Base: [Code Quality](../../../../documents/engineering/code_quality.md)
- Overlay: [Documentation Standards](documentation_standards.md)

---

**Last Updated**: 2025-12-01  
**Supersedes**: none  
**Referenced by**: README.md, frontend_architecture.md, fastapi_integration_patterns.md, authorization_patterns.md, state_machine_patterns.md, security_hardening.md, websocket_security.md
