# HealthHub Engineering Best Practices

> Extends base [Engineering Standards](../../../../documents/engineering/README.md). Base rules apply; this doc indexes HealthHub-specific overlays only.

---

## Purpose

The **engineering/** tier contains **HealthHub-specific implementation patterns** for applying domain knowledge in code. These documents focus on **HOW to implement** features using HealthHub's tech stack and architecture.

**Key Principle**: If a pattern describes HealthHub's specific implementation choices (ADT-based authorization, effect programs, generator testing), it belongs in this tier.

---

## Document Organization

All overlays in this folder inherit the base engineering SSoTs by filename; each doc links to the base and only lists HealthHub-specific deltas.

### Core overlays

- **[Architecture](architecture.md)**: Single-origin FastAPI + React serving, route/program wiring, security/transport controls, WebSocket gating, rate limits, and correlation/audit expectations.
- **[Authentication](authentication.md)**: HealthHub deltas on top of the base authentication SSoT (dual-token flow, audit tagging, break-glass requirements).
- **[Authorization](authorization.md)**: HealthHub ADT authorization application and integration with guards; extends base authentication/authz model.
- **[Effect Patterns](effect_patterns.md)**: HealthHub deltas (PHI-safe auditing, fire-and-forget notifications, medical ADT narrowing, state-machine composition). Includes the state machine section used for all workflows.
- **[Code Quality](code_quality.md)**: HIPAA-focused lint bans, purity/I/O isolation overlays, idempotent effects, PHI scrubbing, and notification discipline.
- **[Monitoring & Alerting](monitoring_and_alerting.md)**: PHI-safe metrics/logging, audit observability, notification alerting, and NTP/audit integrity checks.
- **[Testing](testing.md)**: Layout, generator stepping, PHI-safe fixtures, and commands for running tests in the HealthHub stack.

### No additional deltas (stubs)

- [build_artifact_management.md](build_artifact_management.md), [command_reference.md](command_reference.md), [configuration.md](configuration.md), [development_workflow.md](development_workflow.md), [docker.md](docker.md), [docker_workflow.md](docker_workflow.md), [observability.md](observability.md), [total_pure_modelling.md](total_pure_modelling.md) currently have no HealthHub-specific deltas and defer entirely to the base SSoTs.
- Native WebSocket architecture with Redis Pub/Sub
- One-time ticket authentication (60s expiry, Redis GETDEL)
- Channel isolation for patient PHI (server-side authorization)
- Connection state machine (Idle → Connecting → Authenticating → Active → Reconnecting → Terminated)
- Medical event protocol (appointment_updated, lab_result_ready, prescription_created, billing_invoice_ready)
- Priority levels (normal, urgent, critical) with acknowledgments
- Security controls (CSP, origin validation, rate limiting, TLS requirement)
- Resilience patterns (heartbeat, exponential backoff, subscription recovery)

**Use this when**: Implementing real-time notifications, WebSocket connections, or critical medical alerts.

---

### Integration

**[FastAPI Integration Patterns](architecture.md)** (390 lines)
- Route handler → effect program conversion (HTTP → Program → HTTP)
- Request/response lifecycle (Pydantic validation, program execution, DTO conversion)
- Error handling (domain errors → HTTP status codes)
- Dependency injection for interpreters (get_interpreter factory pattern)
- Authorization dependencies (ADT-based access control with Depends())
- Role-based filtering (pattern matching for query construction)
- Common pitfalls (direct infrastructure calls, mixing exceptions, resource leaks)

**Use this when**: Creating new FastAPI routes, integrating with effectful programs, or bridging HTTP and effect systems.

---

**[Frontend Architecture](architecture.md)** (355 lines)
- FastAPI StaticFiles mount + catch-all route pattern (ShipNorth reference)
- Single-server architecture (backend + frontend on port 8851)
- Build process (Vite → build/ directory → Docker image)
- Three development workflows (backend only, frontend dev with HMR, full stack rebuild)
- Route registration order (API → StaticFiles → catch-all)
- React Router client-side routing integration
- Troubleshooting guide (503 errors, 404s, static asset issues)

**Use this when**: Setting up frontend serving, debugging frontend access issues, or understanding the frontend build process.

---

### Documentation Standards

**[Documentation Standards](documentation_standards.md)** (HealthHub deltas)
- Extends base [documentation_standards.md](../../../../documents/documentation_standards.md) — base rules apply; this doc adds accessibility/alt-text reminders and PHI-free diagrams.
- Use this when documenting HealthHub and needing demo-specific reminders on top of the base standards.

**Build Artifact Management** (base SSoT)
- Read [../../../../documents/engineering/build_artifact_management.md](../../../../documents/engineering/build_artifact_management.md) for artifact/versioning rules (lockfiles treated as artifacts, container-only `/opt/**` outputs).
- HealthHub follows the same doctrine: lockfiles are ignored, and build outputs stay inside containers.

### Authentication State Machine Overlay

- Access token lives **only in memory**; refresh token is **HttpOnly cookie** managed by the backend.
- Missing or expired access tokens trigger a refresh attempt; only a confirmed refresh denial clears tokens and returns to the unauthenticated state.
- Refresh calls must include `credentials: include`; access tokens are short-lived (15 minutes) and renewed on refresh.
- Frontend states include `Hydrating → (Authenticated | Unauthenticated)`, with a `Refreshing` hop for refresh attempts and `RefreshDenied` prior to returning to `Unauthenticated`.

---

## Relationship to Other Tiers

### Domain → Best Practices

The **domain/** tier provides **healthcare domain knowledge** that best_practices implements:

- [Appointment Workflows](../domain/appointment_workflows.md) → Implemented using effect_patterns.md#state-machines
- [Medical State Machines](../domain/medical_state_machines.md) → General patterns implemented in effect_patterns.md#state-machines
- [HIPAA Compliance](../domain/hipaa_compliance.md) → Audit logging implemented in effect_patterns.md

**Flow**: Healthcare requirements → HealthHub implementation patterns

---

### Best Practices → Product

The **product/** tier contains **HealthHub-specific implementations** that use these patterns:

- authorization.md → [Authorization System](../product/authorization_system.md)
- effect_patterns.md#state-machines → [Appointment State Machine](../product/appointment_state_machine.md)
- effect_patterns.md → [Effects Reference](../product/effects_reference.md)
- testing.md → All product testing

**Flow**: Implementation patterns → Actual HealthHub code

---

### Best Practices → Tutorials

The **tutorials/** tier provides **step-by-step guides** that teach these patterns:

- authorization.md → [Tutorial 05: Authorization](../tutorials/05_authorization.md)
- effect_patterns.md#state-machines → [Tutorial 07: State Machines](../tutorials/07_state_machines.md)
- effect_patterns.md → [Tutorial 03: Effect Programs](../tutorials/03_effect_programs.md)

**Flow**: Patterns reference → Guided implementation

---

## Cross-Tier Navigation

**Starting Point**: If you're new to HealthHub development, start here:
1. Read [Effect Patterns](effect_patterns.md) to understand program structure
2. Read [State Machine Patterns](effect_patterns.md#state-machines) to understand workflow implementation
3. Read [Authorization Patterns](authorization.md) to understand access control
4. Read [Testing](testing.md) to understand testing philosophy

**Reference Material**: If you're implementing a specific feature:
- **Authorization**: authorization.md → ../product/authorization_system.md
- **State Machine**: effect_patterns.md#state-machines → ../product/appointment_state_machine.md
- **Effect Program**: effect_patterns.md → ../product/effects_reference.md
- **Testing**: testing.md → tests/pytest/*

**Architectural Context**: For healthcare domain understanding:
1. Read [domain/medical_state_machines.md](../domain/medical_state_machines.md) for healthcare requirements
2. Then read effect_patterns.md#state-machines for HealthHub implementation
3. Then check [product/appointment_state_machine.md](../product/appointment_state_machine.md) for actual code

---

## Document Dependencies

```mermaid
graph TB
    D1[domain/appointment_workflows.md]
    D2[domain/medical_state_machines.md]
    D3[domain/hipaa_compliance.md]

    BP1[engineering/authorization.md]
    BP2[engineering/effect_patterns.md#state-machines]
    BP3[engineering/effect_patterns.md]
    BP4[engineering/testing.md]

    P1[product/authorization_system.md]
    P2[product/appointment_state_machine.md]
    P3[product/effects_reference.md]

    T1[tutorials/05_authorization.md]
    T2[tutorials/07_state_machines.md]
    T3[tutorials/03_effect_programs.md]

    D1 -->|implements| BP2
    D2 -->|implements| BP2
    D3 -->|implements| BP3

    BP1 -->|implements| P1
    BP2 -->|implements| P2
    BP3 -->|implements| P3

    BP1 -->|teaches| T1
    BP2 -->|teaches| T2
    BP3 -->|teaches| T3

    BP4 -->|tests| BP1
    BP4 -->|tests| BP2
    BP4 -->|tests| BP3
```

**Legend**:
- **implements**: Best practice implements domain knowledge OR product implements best practice
- **teaches**: Tutorial teaches best practice
- **tests**: Testing doctrine covers testing strategy

---

## Maintenance Guidelines

### When to Add New Documents

Add a new document to **engineering/** if:
- ✅ The content describes HealthHub-specific implementation patterns
- ✅ It provides HOW-TO guidance for developers
- ✅ It's reusable across multiple HealthHub features

Do NOT add to **engineering/** if:
- ❌ The content is general healthcare domain knowledge (use domain/)
- ❌ It describes a specific HealthHub feature implementation (use product/)
- ❌ It's a step-by-step tutorial (use tutorials/)

### When to Update Existing Documents

Update **engineering/** documents when:
- New implementation patterns emerge from code reviews
- Anti-patterns are discovered in production
- HealthHub architecture evolves (new effect types, new interpreters)
- Testing strategies change (new test infrastructure, new patterns)

---

## Pattern Hierarchy

**Best Practices follow this hierarchy**:

1. **Domain Knowledge** (from domain/ tier)
   - Medical workflows, HIPAA requirements, healthcare constraints

2. **Implementation Patterns** (this tier)
   - ADT-based authorization, state machines, effect programs, testing

3. **Product Implementation** (product/ tier)
   - Actual HealthHub code using these patterns

4. **Tutorials** (tutorials/ tier)
   - Step-by-step guides for learning patterns

---

## Quick Reference

| What do you need? | Document to read |
|-------------------|------------------|
| Implement authorization | [Authorization Patterns](authorization.md) |
| Implement state machine | [State Machine Patterns](effect_patterns.md#state-machines) |
| Write effect program | [Effect Patterns](effect_patterns.md) |
| **Review code purity** | **[Purity Standards](code_quality.md)** |
| Write tests | [Testing](testing.md) |
| Implement security | [Security Hardening](architecture.md) |
| Add monitoring | [Monitoring & Alerting](monitoring_and_alerting.md) |
| Enforce code quality | [Code Quality](code_quality.md) |
| Implement WebSockets | [WebSocket Security](architecture.md) |
| Integrate FastAPI | [FastAPI Integration Patterns](architecture.md) |
| Serve frontend | [Frontend Architecture](architecture.md) |
| Create diagrams | [Documentation Standards](documentation_standards.md) |
| Understand domain | [../domain/](../domain/) |
| See actual code | [../product/](../product/) |
| Learn step-by-step | [../tutorials/](../tutorials/) |

---

**Last Updated**: 2025-11-28
**Supersedes**: none
**Maintainer**: HealthHub Team
**Document Count**: 13 engineering documents  
**Referenced by**: ../README.md, product/architecture_overview.md
