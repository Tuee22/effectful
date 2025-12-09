# Feature-Based Tutorials

**Status**: Reference only
**Supersedes**: none
**Referenced by**: demo/healthhub/documents/tutorials/README.md

> **Purpose**: Deep dive into specific HealthHub features. These tutorials are the Single Source of Truth for HealthHub-specific feature documentation.

> **Recommended for**: Developers working on specific features, debugging, feature enhancement, API documentation reference.

---

## Overview

Feature tutorials provide comprehensive documentation for each HealthHub feature. These are SSoT (Single Source of Truth) for HealthHub-specific patterns, not covered in base Effectful tutorials.

**Pattern**: Each tutorial covers domain models, state machines, effect programs, RBAC enforcement, and e2e tests for one feature.

---

## Features

### 1. Authentication

**Tutorial**: [authentication.md](authentication.md)

**Topics**:
- JWT authentication flow (login → token issue → refresh)
- AuthorizationState ADT (PatientAuthorized | DoctorAuthorized | AdminAuthorized | Unauthorized)
- RBAC enforcement (route guards, API protection)
- Session management (logout, token refresh)
- Bcrypt password hashing

**Domain Models**: User, AuthorizationState ADT

**E2E Tests**: test_login_flow.py (all auth state transitions)

**Prerequisites**: [Beginner Journey](../01_journeys/beginner_journey.md)

**Use Cases**: Implementing protected routes, auth state management, role-based access

---

### 2. Appointments

**Tutorial**: [appointments.md](appointments.md)

**Topics**:
- AppointmentStatus state machine (6 variants)
- Valid state transitions (Requested → Confirmed → InProgress → Completed | Cancelled)
- Transition validation (prevent invalid state changes)
- Scheduling workflows (patient requests, doctor confirms)
- Execution workflows (start, complete with notes)
- Cancellation from non-terminal states

**Domain Models**: Appointment, AppointmentStatus ADT

**State Machine**:
```
Requested → Confirmed → InProgress → Completed
    ↓           ↓           ↓
Cancelled   Cancelled   Cancelled
```

**E2E Tests**: test_appointments.py (all transitions, terminal states)

**Prerequisites**: [Intermediate Journey](../01_journeys/intermediate_journey.md)

**Use Cases**: Appointment management, state machine implementation, workflow validation

---

### 3. Prescriptions

**Tutorial**: [prescriptions.md](prescriptions.md)

**Topics**:
- Prescription domain model (medication, dosage, frequency, duration, refills)
- Doctor-only creation (RBAC enforcement via can_prescribe flag)
- Medication interaction checking (simulate drug database lookup)
- Patient viewing (own prescriptions only)
- Doctor viewing (all prescriptions)
- Prescription expiration and refills

**Domain Models**: Prescription

**RBAC**: Only doctors with `can_prescribe=true` can create prescriptions

**E2E Tests**: test_prescriptions.py (creation, viewing, RBAC)

**Prerequisites**: [Intermediate Journey](../01_journeys/intermediate_journey.md)

**Use Cases**: Prescription management, medication safety, RBAC patterns

---

### 4. Lab Results

**Tutorial**: [lab_results.md](lab_results.md)

**Topics**:
- Lab result domain model (test_type, result_data, critical flag)
- Critical value alerts (automatic notification triggers)
- Doctor review workflow (reviewed_by_doctor flag + notes)
- Patient notifications (critical results)
- Patient viewing (own results with doctor annotations)

**Domain Models**: LabResult

**Notifications**: Critical results trigger immediate doctor notification

**E2E Tests**: test_lab_results.py (critical alerts, doctor review, patient viewing)

**Prerequisites**: [Intermediate Journey](../01_journeys/intermediate_journey.md)

**Use Cases**: Lab result processing, critical alerts, doctor-patient communication

---

### 5. Invoices

**Tutorial**: [invoices.md](invoices.md)

**Topics**:
- Invoice domain model (status, subtotal, tax, total, due_date)
- Invoice generation from completed appointments
- Line item management (description, quantity, unit price)
- Payment status tracking (Sent | Paid | Overdue)
- Patient viewing (own invoices)
- Admin creation and management

**Domain Models**: Invoice, InvoiceLineItem

**RBAC**: Only admins can create invoices

**E2E Tests**: test_invoices.py (creation, viewing, status)

**Prerequisites**: [Intermediate Journey](../01_journeys/intermediate_journey.md)

**Use Cases**: Billing workflows, invoice management, payment tracking

---

## Feature Comparison

| Feature | State Machine | RBAC | Notifications | Critical Alerts |
|---------|---------------|------|---------------|-----------------|
| **Authentication** | ❌ | ✅ (core) | ❌ | ❌ |
| **Appointments** | ✅ (6 states) | ✅ | ✅ | ❌ |
| **Prescriptions** | ❌ | ✅ (doctor-only) | ✅ | ❌ |
| **Lab Results** | ❌ | ✅ | ✅ | ✅ (critical flag) |
| **Invoices** | ❌ | ✅ (admin-only) | ❌ | ❌ |

---

## Tutorial Structure

Each feature tutorial follows this pattern:

1. **Domain Model Definition**: Dataclasses, ADTs, type definitions
2. **Effect Programs**: Generator-based programs using effects
3. **State Machines** (if applicable): Valid transitions, terminal states
4. **RBAC Enforcement**: Role restrictions, authorization checks
5. **Code Examples**: From backend/app/programs/, backend/app/domain/
6. **Test Examples**: From tests/pytest/e2e/
7. **Cross-References**: Links to role guides, workflows, engineering docs

---

## Related Content

**For role-specific usage**:
- [Patient Guide](../02_roles/patient_guide.md)
- [Doctor Guide](../02_roles/doctor_guide.md)
- [Admin Guide](../02_roles/admin_guide.md)

**For multi-feature integration**:
- [Appointment Lifecycle](../04_workflows/appointment_lifecycle.md)
- [Prescription Workflow](../04_workflows/prescription_workflow.md)
- [Lab Result Workflow](../04_workflows/lab_result_workflow.md)
- [Patient Onboarding](../04_workflows/patient_onboarding.md)

**For progressive learning**:
- [Beginner Journey](../01_journeys/beginner_journey.md)
- [Intermediate Journey](../01_journeys/intermediate_journey.md)
- [Advanced Journey](../01_journeys/advanced_journey.md)

---

## Cross-References

- [HealthHub Tutorial Hub](../README.md)
- [HealthHub Engineering Standards](../../engineering/README.md)
- [HealthHub Domain Documentation](../../domain/)
- [Effectful Effect Patterns](../../../../../documents/engineering/effect_patterns.md)
