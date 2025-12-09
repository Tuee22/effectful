# HealthHub Tutorials

**Status**: Reference only
**Supersedes**: none
**Referenced by**: demo/healthhub/documents/readme.md

> **Purpose**: Navigation hub for HealthHub tutorials demonstrating real-world healthcare workflows using the Effectful library.

> **📖 Base Tutorials**: [Effectful Tutorials](../../../../documents/tutorials/) - Learn core Effectful patterns first, then apply them to HealthHub healthcare domain.

---

## Overview

HealthHub tutorials demonstrate pure functional effect systems applied to healthcare management. Three learning paths support different goals:

1. **Journey-Based** (Beginner → Intermediate → Advanced) - Progressive learning
2. **Role-Based** (Patient, Doctor, Admin) - Learn by user perspective
3. **Feature-Based** (Appointments, Prescriptions, Labs, Invoices) - Deep dive into specific features

**Plus**: Multi-feature workflow tutorials showing complete healthcare scenarios.

---

## Quick Start

**New to HealthHub?** Start here:
1. [Beginner Journey](01_journeys/beginner_journey.md) - Login, navigation, viewing data (1 hour)
2. [Intermediate Journey](01_journeys/intermediate_journey.md) - Appointments, prescriptions, state machines (2 hours)
3. [Advanced Journey](01_journeys/advanced_journey.md) - Custom effects, performance, production (3 hours)

**Need role-specific training?** See [Role Guides](02_roles/README.md)

**Need feature documentation?** See [Feature Tutorials](03_features/README.md)

---

## Learning Paths

### Path 1: Journey-Based (Recommended for New Users)

Progressive learning from basics to production deployment.

| Tutorial | Duration | Topics | Prerequisites |
|----------|----------|--------|---------------|
| [Beginner Journey](01_journeys/beginner_journey.md) | 1 hour | Login, RBAC, viewing data, ADTs | Base effectful quickstart |
| [Intermediate Journey](01_journeys/intermediate_journey.md) | 2 hours | State machines, effect programs, workflows | Beginner journey |
| [Advanced Journey](01_journeys/advanced_journey.md) | 3 hours | Custom effects, performance, production | Intermediate journey |

**Total Time**: ~6 hours
**Outcome**: Complete understanding of HealthHub architecture and patterns

---

### Path 2: Role-Based (Recommended for Role Training)

Learn HealthHub from patient, doctor, or admin perspective.

| Role | Tutorial | Capabilities | RBAC Restrictions |
|------|----------|--------------|-------------------|
| **Patient** | [Patient Guide](02_roles/patient_guide.md) | View/request appointments, view prescriptions/labs/invoices | Cannot create prescriptions, view other patients, access admin features |
| **Doctor** | [Doctor Guide](02_roles/doctor_guide.md) | View all patients, manage appointments, create prescriptions, review labs | Cannot create invoices, access audit logs, manage users |
| **Admin** | [Admin Guide](02_roles/admin_guide.md) | Full access, audit logs, user management, system metrics | Full system access |

**Use Case**: Training new users on specific roles
**Outcome**: Role-specific operational knowledge

---

### Path 3: Feature-Based (Recommended for Development)

Deep dive into specific HealthHub features.

| Feature | Tutorial | Key Concepts | E2E Tests |
|---------|----------|--------------|-----------|
| **Authentication** | [Authentication](03_features/authentication.md) | JWT, RBAC, auth state ADT | test_login_flow.py |
| **Appointments** | [Appointments](03_features/appointments.md) | State machine, transitions, scheduling | test_appointments.py |
| **Prescriptions** | [Prescriptions](03_features/prescriptions.md) | RBAC, medication interactions, doctor-only | test_prescriptions.py |
| **Lab Results** | [Lab Results](03_features/lab_results.md) | Critical alerts, doctor review, notifications | test_lab_results.py |
| **Invoices** | [Invoices](03_features/invoices.md) | Billing, payment status, line items | test_invoices.py |

**Use Case**: Developers working on specific features
**Outcome**: Deep technical understanding of feature implementation

---

### Path 4: Workflow-Based (Multi-Feature Integration)

Complete healthcare scenarios demonstrating feature integration.

| Workflow | Tutorial | Features Involved | Duration |
|----------|----------|-------------------|----------|
| **Patient Onboarding** | [Patient Onboarding](04_workflows/patient_onboarding.md) | Auth, Appointments, Prescriptions, Invoices | 1.5 hours |
| **Appointment Lifecycle** | [Appointment Lifecycle](04_workflows/appointment_lifecycle.md) | Appointments, Notifications, Invoices | 1 hour |
| **Prescription Workflow** | [Prescription Workflow](04_workflows/prescription_workflow.md) | Prescriptions, Patient lookup, Notifications | 1 hour |
| **Lab Result Workflow** | [Lab Result Workflow](04_workflows/lab_result_workflow.md) | Labs, Critical alerts, Doctor review | 1 hour |

**Use Case**: Understanding end-to-end data flow
**Outcome**: Complete workflow comprehension

---

## Library Delta Tutorials

HealthHub-specific deltas for base Effectful tutorials. These are minimal reference documents (~17 lines each) that document only HealthHub-specific differences (compose stack, service name, ports, credentials).

See [00_library_deltas/README.md](00_library_deltas/README.md) for the complete list.

**When to use**: Reference when following base Effectful tutorials but need HealthHub-specific configuration.

---

## Demo Data

All tutorials use seeded demo data from `backend/scripts/seed_data.sql`:

**Credentials** (all users: password `password123`):
- **Admins**: admin@healthhub.com, superadmin@healthhub.com
- **Doctors**: dr.smith@healthhub.com (Cardiology), dr.johnson@healthhub.com (Orthopedics), dr.williams@healthhub.com (Dermatology), dr.brown@healthhub.com (Neurology)
- **Patients**: alice.patient@example.com, bob.patient@example.com, carol.patient@example.com, david.patient@example.com, emily.patient@example.com

**Sample Data**: 3 appointments, 2 prescriptions, 2 lab results, 1 invoice

**Reset Demo Data**:
```bash
docker compose -f docker/docker-compose.yml down -v
docker compose -f docker/docker-compose.yml up -d
```

---

## Prerequisites

**All tutorials require**:
1. Docker running with HealthHub stack: `docker compose -f docker/docker-compose.yml up -d`
2. Completed [Effectful Quickstart](../../../../documents/tutorials/quickstart.md)
3. Familiarity with Python generators and type hints

**Recommended background**:
- Understanding of ADTs and Result types from [ADTs and Results](../../../../documents/tutorials/adts_and_results.md)
- Basic knowledge of effect systems from [Effect Types](../../../../documents/tutorials/effect_types.md)

---

## Tutorial Structure

Every tutorial follows this pattern:

1. **Header Metadata**: Status, purpose, cross-references
2. **Prerequisites**: Required prior knowledge and tutorials
3. **Learning Objectives**: 3-5 measurable outcomes
4. **Step-by-Step Instructions**: Executable with demo data
5. **Code Deep Dive**: Effect programs, domain models, interpreters
6. **Summary**: Achievements and key takeaways
7. **Next Steps**: Related tutorials and documentation
8. **Cross-References**: Links to SSoT documents

---

## E2E Test Coverage

Every tutorial workflow has corresponding e2e tests verifying correctness:

- Tutorial steps → Test cases (conceptual feature coverage, not metric-driven)
- Code examples → Verified in integration tests
- State machines → All transitions tested
- RBAC → All role restrictions enforced

**See**: Tutorial-to-test mapping in [Phase 6 Implementation Plan](/Users/matthewnowak/.claude/plans/hazy-frolicking-engelbart.md#tutorial-to-test-mapping-matrix)

---

## Cross-References

- [HealthHub Documentation Hub](../readme.md)
- [Effectful Base Tutorials](../../../../documents/tutorials/)
- [HealthHub Engineering Standards](../engineering/README.md)
- [HealthHub Domain Documentation](../domain/)
- [Documentation Standards](../documentation_standards.md)
