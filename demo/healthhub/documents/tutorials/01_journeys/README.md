# Journey-Based Tutorials

**Status**: Reference only
**Supersedes**: none
**Referenced by**: demo/healthhub/documents/tutorials/README.md

> **Purpose**: Progressive learning path from beginner to advanced HealthHub development.

> **Recommended for**: New HealthHub users, developers onboarding to the project, anyone wanting systematic progression.

---

## Overview

Journey-based tutorials provide a structured learning path with increasing complexity. Complete all three journeys for comprehensive HealthHub mastery.

**Total Time**: ~6 hours
**Outcome**: Production-ready HealthHub development skills

---

## Learning Path

### 1. Beginner Journey (1 hour)

**Tutorial**: [beginner_journey.md](beginner_journey.md)

**Learning Objectives**:
- Log in as patient/doctor/admin using demo credentials
- Navigate HealthHub UI and understand role-based views
- View existing data (appointments, prescriptions, lab results)
- Understand ADTs and Result types in HealthHub domain

**Prerequisites**:
- Docker running
- Completed [Effectful Quickstart](../../../../../documents/tutorials/quickstart.md)

**Topics Covered**:
- Authentication flow (JWT, bcrypt)
- AuthorizationState ADT (PatientAuthorized | DoctorAuthorized | AdminAuthorized | Unauthorized)
- RBAC basics
- Dashboard navigation
- Viewing appointments, prescriptions, lab results, invoices

**Demo Users**: alice.patient@example.com, dr.smith@healthhub.com

**E2E Tests**: test_login_flow.py, test_rbac.py

---

### 2. Intermediate Journey (2 hours)

**Tutorial**: [intermediate_journey.md](intermediate_journey.md)

**Learning Objectives**:
- Schedule and manage appointments (state machine)
- Create prescriptions with medication interaction checking
- Process lab results with critical value alerts
- Understand effect programs and generators

**Prerequisites**:
- Completed [Beginner Journey](beginner_journey.md)
- Familiarity with [Effect Types](../../../../../documents/tutorials/effect_types.md)

**Topics Covered**:
- AppointmentStatus state machine (Requested → Confirmed → InProgress → Completed | Cancelled)
- State transition validation
- Effect programs (yield pattern, generator stepping)
- Medication interaction checking
- Critical value alerts and notifications
- Doctor and patient workflows

**Demo Users**: bob.patient@example.com, dr.johnson@healthhub.com

**E2E Tests**: test_appointments.py, test_prescriptions.py, test_lab_results.py

---

### 3. Advanced Journey (3 hours)

**Tutorial**: [advanced_journey.md](advanced_journey.md)

**Learning Objectives**:
- Build custom effects for HealthHub-specific operations
- Optimize performance with caching and batching
- Deploy to production with monitoring
- Write comprehensive tests (unit, integration, e2e)

**Prerequisites**:
- Completed [Intermediate Journey](intermediate_journey.md)
- Familiarity with [Advanced Composition](../../../../../documents/tutorials/advanced_composition.md)

**Topics Covered**:
- HealthcareEffect and NotificationEffect (custom effects)
- AuditedCompositeInterpreter composition
- Caching strategies (Redis)
- Generator-based unit testing
- Integration tests with real infrastructure
- Production deployment patterns
- Observability and monitoring

**Demo Users**: All roles

**E2E Tests**: All existing tests + extension patterns

---

## Progression Chart

```
Beginner Journey (1h)
├─ Login & Navigation
├─ View Data (Appointments/Prescriptions/Labs)
├─ Understand RBAC
└─ ADTs and Result Types
    ↓
Intermediate Journey (2h)
├─ Appointment State Machine
├─ Create Prescriptions
├─ Process Lab Results
└─ Effect Programs & Generators
    ↓
Advanced Journey (3h)
├─ Custom Effects
├─ Performance Optimization
├─ Testing Strategies
└─ Production Deployment
```

---

## Alternative Paths

After completing journeys, explore:

- **[Feature Tutorials](../03_features/README.md)** - Deep dive into specific features
- **[Workflow Tutorials](../04_workflows/README.md)** - Multi-feature integration scenarios
- **[Role Guides](../02_roles/README.md)** - Role-specific operational knowledge

---

## Success Criteria

### After Beginner Journey
- ✅ Can log in as any role
- ✅ Understand RBAC restrictions
- ✅ View and interpret all data types
- ✅ Understand AuthorizationState ADT

### After Intermediate Journey
- ✅ Can manage appointment lifecycle
- ✅ Create and validate prescriptions
- ✅ Process lab results with critical alerts
- ✅ Write effect programs using generators

### After Advanced Journey
- ✅ Build custom effects
- ✅ Optimize performance with caching
- ✅ Write comprehensive test suites
- ✅ Deploy to production with monitoring

---

## Cross-References

- [HealthHub Tutorial Hub](../README.md)
- [Feature Tutorials](../03_features/README.md)
- [Role Guides](../02_roles/README.md)
- [Workflow Tutorials](../04_workflows/README.md)
- [Effectful Base Tutorials](../../../../../documents/tutorials/)
