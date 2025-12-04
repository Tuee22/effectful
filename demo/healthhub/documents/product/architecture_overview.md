# HealthHub Architecture Overview

> Extends base [Architecture](../../../../documents/engineering/architecture.md) and [Documentation Standards](../../../../documents/documentation_standards.md). Base rules apply; this file lists HealthHub-specific deltas only.

---

## What differs from the base SSoT
- **Single server/port**: FastAPI serves API + React on port `8851` (StaticFiles + catch-all). See [Frontend Architecture](../engineering/architecture.md) for serving details.
- **Interpreter split**: Composite interpreter routes two categories here—`HealthcareInterpreter` (PostgreSQL) and `NotificationInterpreter` (Redis pub/sub + audit logging). Effect catalog lives in [Effects Reference](effects_reference.md).
- **Infrastructure bindings**: Ports are pinned for local stack parity—PostgreSQL `5433`, Redis `6380`, Pulsar `6651`, MinIO `9001`. Values are set in `demo/healthhub/docker/docker-compose.yml`.
- **Audit-first paths**: Every PHI read/write emits audit effects from interpreters (never from programs). See [Code Quality overlay](../engineering/code_quality.md) and [Monitoring & Alerting overlay](../engineering/monitoring_and_alerting.md).
- **Authorization flow**: Routes enforce ADT-based authorization before invoking programs; no direct repository access from routes. See [Authorization Patterns](../engineering/authorization.md).

## Quick pointers (keep DRY)
- Layer responsibilities, runner loop, and effect unions remain unchanged—see base [Architecture SSoT](../../../../documents/engineering/architecture.md#5-layer-architecture).
- Program/interpreter shapes follow base [Effect Patterns](../../../../documents/engineering/effect_patterns.md).
- FastAPI wiring and error mapping live in [FastAPI Integration Patterns](../engineering/architecture.md).
- State-machine orchestration for medical workflows is in [State Machine Patterns](../engineering/effect_patterns.md#state-machines) and [Appointment State Machine](appointment_state_machine.md).

---

**Last Updated**: 2025-11-26  
**Supersedes**: none  
**Maintainer**: HealthHub Team  
**Referenced by**: ../README.md, ../engineering/README.md
