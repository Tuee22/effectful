# HealthHub Documentation

> Extends base [Effectful Documentation](../../documents/README.md) and [Documentation Standards](documentation_standards.md). Base standards apply; this hub lists HealthHub-specific deltas.

---

## Quick Navigation

### By Role

| Role | Start Here |
|------|-----------|
| **New Developer** | [tutorials/01_quickstart.md](tutorials/01_quickstart.md) |
| **Healthcare Context** | [domain/README.md](domain/README.md) |
| **Backend Engineer** | [product/architecture_overview.md](product/architecture_overview.md) |
| **Implementation Patterns & Compliance** | [engineering/README.md](engineering/README.md) |

### By Topic

| Topic | Document |
|-------|----------|
| **Healthcare Domain** | |
| Medical Workflows | [domain/appointment_workflows.md](domain/appointment_workflows.md) |
| State Machine Patterns | [domain/medical_state_machines.md](domain/medical_state_machines.md) |
| HIPAA Compliance | [domain/hipaa_compliance.md](domain/hipaa_compliance.md) |
| **Implementation** | |
| System Architecture | [product/architecture_overview.md](product/architecture_overview.md) |
| Domain Models | [product/domain_models.md](product/domain_models.md) |
| Effects Reference | [product/effects_reference.md](product/effects_reference.md) |
| Authorization | [product/authorization_system.md](product/authorization_system.md) |
| Audit Surfacing | [product/audit_logging.md](product/audit_logging.md) |
| **Patterns & Testing** | |
| Authorization Patterns | [engineering/authorization.md](engineering/authorization.md) |
| State Machine Implementation | [engineering/effect_patterns.md#state-machines](engineering/effect_patterns.md#state-machines) |
| Effect Programs | [engineering/effect_patterns.md](engineering/effect_patterns.md) |
| Audit Logging Implementation | [engineering/monitoring_and_alerting.md#audit-logging-observability](engineering/monitoring_and_alerting.md#audit-logging-observability) |
| Testing | [engineering/testing.md](engineering/testing.md) |

---

## 4-Tier Documentation Architecture

HealthHub documentation follows a strict **Single Source of Truth (SSoT)** hierarchy:

```
┌─────────────────────────────────────────┐
│  domain/  (Healthcare Domain Knowledge) │ ← Healthcare requirements
├─────────────────────────────────────────┤
│  engineering/  (Implementation)      │ ← HOW to implement in HealthHub
├─────────────────────────────────────────┤
│  product/  (HealthHub Features)         │ ← WHAT HealthHub implements
├─────────────────────────────────────────┤
│  tutorials/  (Step-by-Step Guides)      │ ← Learning path
└─────────────────────────────────────────┘
```

### Tier 1: domain/ (Healthcare Domain Knowledge)

**Purpose**: Medical workflows, compliance, and domain patterns that apply to ANY healthcare application.

| Document | Lines | Description |
|----------|-------|-------------|
| [appointment_workflows.md](domain/appointment_workflows.md) | 279 | Medical appointment lifecycle (Requested → Confirmed → InProgress → Completed) |
| [medical_state_machines.md](domain/medical_state_machines.md) | 567 | General medical workflow patterns (appointments, prescriptions, lab results, invoices) |
| [hipaa_compliance.md](domain/hipaa_compliance.md) | 253 | HIPAA audit logging requirements for PHI access |
| [README.md](domain/README.md) | 203 | Domain tier overview and navigation |

**Total**: 4 documents (1,302 lines)

**Use this tier when**: Understanding healthcare requirements, designing new medical workflows, verifying compliance.

---

### Tier 2: engineering/ (HealthHub Implementation Patterns)

**Purpose**: HOW to implement features using HealthHub's ADTs, effect programs, and pure functional architecture.

| Document | Lines | Description |
|----------|-------|-------------|
| [authorization.md](engineering/authorization.md) | 244 | ADT-based authorization patterns (PatientAuthorized, DoctorAuthorized) |
| [effect_patterns.md#state-machines](engineering/effect_patterns.md#state-machines) | 456 | ADT state machine implementation (frozen dataclasses, TransitionResult ADT) |
| [effect_patterns.md](engineering/effect_patterns.md) | 318 | Pure effect programs (generators, type narrowing, fire-and-forget notifications) |
| [testing.md](engineering/testing.md) | 1,345 | Comprehensive testing philosophy (22 anti-patterns, generator testing) |
| [README.md](engineering/README.md) | 240 | Engineering tier overview and navigation |

**Total**: 5+ documents (2,603+ lines)

**Use this tier when**: Implementing authorization checks, writing effect programs, creating state machines, writing tests.

---

### Tier 3: product/ (HealthHub System Implementation)

**Purpose**: WHAT HealthHub implements - specific features, APIs, and system architecture.

| Document | Lines | Description |
|----------|-------|-------------|
| [architecture_overview.md](product/architecture_overview.md) | 404 | 5-layer architecture (Application → Runner → Composite → Interpreters → Infrastructure) |
| [domain_models.md](product/domain_models.md) | 437 | Healthcare entities (Patient, Doctor, Appointment, Prescription, LabResult, Invoice) |
| [effects_reference.md](product/effects_reference.md) | 480 | Complete effect catalog (GetPatientById, CreateAppointment, CheckMedicationInteractions) |
| [authorization_system.md](product/authorization_system.md) | 378 | AuthorizationState ADT system implementation |
| [appointment_state_machine.md](product/appointment_state_machine.md) | 443 | Appointment lifecycle implementation with validation |
| [medication_interactions.md](product/medication_interactions.md) | 345 | Drug interaction checking system |
| [notification_system.md](product/notification_system.md) | 381 | WebSocket + Redis pub/sub notifications |
| [audit_logging.md](product/audit_logging.md) | 392 | HIPAA-compliant audit logging implementation |
| [authentication.md](product/authentication.md) | 351 | JWT dual-token authentication system |
| [api_reference.md](product/api_reference.md) | 492 | REST API endpoint reference (patients, appointments, prescriptions) |

**Total**: 10 documents (4,103 lines)

**Use this tier when**: Understanding HealthHub's specific features, API contracts, database schema, or system architecture.

---

### Tier 4: tutorials/ (Step-by-Step Guides)

**Purpose**: Learning path for new developers building with HealthHub patterns.

| Document | Description |
|----------|-------------|
| [01_quickstart.md](tutorials/01_quickstart.md) | Getting started with HealthHub |
| [02_scheduling_appointments.md](tutorials/02_scheduling_appointments.md) | Appointment workflow tutorial |
| [03_prescriptions.md](tutorials/03_prescriptions.md) | Prescription creation tutorial |
| [04_lab_results.md](tutorials/04_lab_results.md) | Lab result workflows |
| [05_billing_invoices.md](tutorials/05_billing_invoices.md) | Invoice generation tutorial |
| [06_authorization.md](tutorials/06_authorization.md) | Role-based access tutorial |
| [07_notifications.md](tutorials/07_notifications.md) | Real-time notification tutorial |
| [08_testing_healthhub.md](tutorials/08_testing_healthhub.md) | Testing effect programs |

**Total**: 8 documents

**Use this tier when**: Learning HealthHub development, following guided implementations, understanding workflow construction.

---

## Document Inventory

**Total**: 27+ documents
- **Domain Knowledge**: 4 documents (1,302 lines)
- **Engineering Patterns**: 5+ documents (2,603+ lines)
- **Product Documentation**: 10 documents (4,103 lines)
- **Tutorials**: 8 documents

**Documentation Coverage**: ~8,000 lines of comprehensive healthcare application documentation.

---

## Cross-Tier Navigation Patterns

### Pattern 1: Top-Down (Domain → Implementation)

**Use case**: Implementing a new medical workflow

1. Read [domain/medical_state_machines.md](domain/medical_state_machines.md) for healthcare requirements
2. Read [engineering/effect_patterns.md#state-machines](engineering/effect_patterns.md#state-machines) for ADT patterns
3. Reference [product/appointment_state_machine.md](product/appointment_state_machine.md) for concrete example
4. Follow [tutorials/02_scheduling_appointments.md](tutorials/02_scheduling_appointments.md) for step-by-step guide

---

### Pattern 2: Bottom-Up (Product → Domain)

**Use case**: Understanding why a feature works a certain way

1. See implementation in [product/appointment_state_machine.md](product/appointment_state_machine.md)
2. Understand patterns in [engineering/effect_patterns.md#state-machines](engineering/effect_patterns.md#state-machines)
3. Learn healthcare requirements in [domain/appointment_workflows.md](domain/appointment_workflows.md)

---

### Pattern 3: Horizontal (Same Tier)

**Use case**: Understanding related concepts at the same level

- **Domain tier**: [appointment_workflows.md](domain/appointment_workflows.md) references [medical_state_machines.md](domain/medical_state_machines.md) and [hipaa_compliance.md](domain/hipaa_compliance.md)
- **Engineering tier**: [effect_patterns.md](engineering/effect_patterns.md) references [effect_patterns.md#state-machines](engineering/effect_patterns.md#state-machines)
- **Product tier**: [api_reference.md](product/api_reference.md) references [authorization_system.md](product/authorization_system.md), [authentication.md](product/authentication.md), [audit_logging.md](product/audit_logging.md)

---

## Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Language | Python 3.12 | Backend implementation |
| Web Framework | FastAPI | REST API + async support |
| Effect System | Effectful | Pure functional effects |
| Database | PostgreSQL 15 | Patient/appointment data |
| Cache/Pub-Sub | Redis 7 | Notifications, caching |
| Messaging | Apache Pulsar 3.0 | Durable message queue |
| Storage | MinIO | S3-compatible document storage |
| Authentication | JWT + bcrypt | Dual-token authentication |
| Type Checking | MyPy (strict) | Zero escape hatches (no Any, cast, type:ignore) |

---

## Key Architectural Principles

### 1. Single Source of Truth (SSoT)

Each piece of information exists in exactly one authoritative location:

- **Healthcare requirements**: domain/ tier
- **Implementation patterns**: engineering/ tier
- **Feature specifications**: product/ tier
- **Learning guides**: tutorials/ tier

**Anti-pattern**: Duplicating content across tiers (creates inconsistency).

---

### 2. Bidirectional Cross-References

All documents include "Related Documentation" sections with three subsections:

```markdown
## Related Documentation

### Domain Knowledge
- Links to domain/ tier

### Engineering Patterns
- Links to engineering/ tier

### Product Documentation
- Links to product/ tier
```

This ensures clear navigation between tiers while maintaining SSoT.

---

### 3. Make Invalid States Unrepresentable

HealthHub demonstrates type-driven design:

**Authorization**:
```python
type AuthorizationState = (
    PatientAuthorized    # user_id, patient_id, email
    | DoctorAuthorized   # user_id, doctor_id, specialization, can_prescribe
    | AdminAuthorized    # user_id, email
    | Unauthorized       # reason, detail
)
```

**Appointment Status**:
```python
type AppointmentStatus = (
    Requested    # requested_at
    | Confirmed  # confirmed_at, scheduled_time
    | InProgress # started_at
    | Completed  # completed_at, notes
    | Cancelled  # cancelled_at, cancelled_by, reason
)
```

---

## Healthcare Domain Coverage

HealthHub demonstrates comprehensive medical workflows:

- **Patient Management**: Demographics, medical history, PHI access logging
- **Appointment Scheduling**: 5-state machine with validation (Requested → Confirmed → InProgress → Completed/Cancelled)
- **Prescription Management**: Doctor prescribing with medication interaction checking
- **Lab Results**: Test ordering, result review, critical value alerts
- **Billing**: Invoice generation from completed appointments/prescriptions
- **HIPAA Compliance**: Complete audit trail for all PHI access

---

## Maintenance Guidelines

### When to Add New Documents

**Add to domain/** if:
- Content applies to ANY healthcare application (not HealthHub-specific)
- Describes medical domain requirements or compliance rules
- Example: "Prescription State Machines for DEA Controlled Substances"

**Add to engineering/** if:
- Content describes HealthHub-specific implementation patterns
- Provides HOW-TO guidance for developers
- Example: "Testing Prescription Programs with Generator Stepping"

**Add to product/** if:
- Content documents a specific HealthHub feature
- Describes API contracts, database schema, or system architecture
- Example: "Prescription API Endpoints Reference"

**Add to tutorials/** if:
- Content is a step-by-step learning guide
- Teaches how to build features from scratch
- Example: "Building Your First Prescription Workflow"

---

### When to Update Existing Documents

**Update domain/** when:
- Healthcare regulations change (new HIPAA requirements)
- Medical best practices evolve (new prescription safety guidelines)
- Industry standards update (ICD-11 adoption)

**Update engineering/** when:
- New implementation patterns emerge from code reviews
- Anti-patterns discovered in production
- HealthHub architecture evolves (new effect types, interpreters)

**Update product/** when:
- HealthHub features change (new API endpoints, schema updates)
- System architecture changes (new infrastructure layer)
- Breaking changes to public APIs

---

## Related Documentation

- **Parent Library**: [../../effectful/](../../) - Effectful effect system library
- **Effectful Docs**: [../../documents/](../../documents/) - Core effectful documentation
- **CLAUDE.md**: [../CLAUDE.md](../CLAUDE.md) - Claude Code patterns for HealthHub

---

**Last Updated**: 2025-11-26
**Supersedes**: none
**Maintainer**: HealthHub Team
**Documentation Version**: 2.0 (4-tier architecture with SSoT)
**Status**: All tiers complete with bidirectional cross-references  
**Referenced by**: engineering/README.md, product/architecture_overview.md, domain/README.md
