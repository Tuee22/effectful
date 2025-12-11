# Workflow-Based Tutorials

**Status**: Authoritative source
**Supersedes**: none
**Referenced by**: demo/healthhub/documents/readme.md, demo/healthhub/documents/tutorials/README.md, demo/healthhub/documents/product/README.md

> **Purpose**: Multi-feature integration tutorials demonstrating complete healthcare workflows from start to finish.

> **Recommended for**: Understanding end-to-end data flow, testing multi-feature integration, learning complete user journeys.

---

## Overview

Workflow tutorials demonstrate how multiple HealthHub features work together in real healthcare scenarios. Each workflow traces data flow from initial request through completion, showing feature integration points.

**Pattern**: Start with user action → Follow data through multiple features → End with completed workflow

**Difference from Feature Tutorials**: Feature tutorials deep-dive into one feature. Workflow tutorials show how features integrate.

---

## Workflows

### 1. Patient Onboarding

**Tutorial**: [patient_onboarding.md](patient_onboarding.md)

**Workflow**: Registration → First Appointment → Prescription → Invoice

**Features Involved**:
- Authentication (registration, login)
- Appointments (request, doctor confirms, complete)
- Prescriptions (doctor creates after appointment)
- Invoices (generated from completed appointment)

**Demo User**: emily.patient@example.com (new patient)

**Duration**: ~1.5 hours

**Learning Outcomes**:
- Complete patient journey from registration to billing
- Data flow across authentication → appointments → prescriptions → invoices
- Patient perspective throughout entire process

**E2E Tests**: test_complete_care_episode.py (patient onboarding scenario)

**Prerequisites**: [Intermediate Journey](../../tutorials/01_journeys/intermediate_journey.md)

---

### 2. Appointment Lifecycle

**Tutorial**: [appointment_lifecycle.md](appointment_lifecycle.md)

**Workflow**: Request → Confirm → Start → Complete → Invoice → Patient Views

**Features Involved**:
- Appointments (state machine: Requested → Confirmed → InProgress → Completed)
- Notifications (state transition alerts)
- Invoices (generation from completed appointment)

**Demo Users**: david.patient@example.com, dr.williams@healthhub.com

**Duration**: ~1 hour

**Learning Outcomes**:
- Complete appointment state machine progression
- Notification triggers at each state transition
- Invoice generation workflow
- Both patient and doctor perspectives

**E2E Tests**: test_complete_care_episode.py (appointment→invoice)

**Prerequisites**: [Intermediate Journey](../../tutorials/01_journeys/intermediate_journey.md)

---

### 3. Prescription Workflow

**Tutorial**: [prescription_workflow.md](prescription_workflow.md)

**Workflow**: Diagnosis → Patient Lookup → Medication Interaction Check → Create Prescription → Patient Views

**Features Involved**:
- Appointments (context: doctor appointment with patient)
- Patient Management (doctor searches/views patient history)
- Prescriptions (creation with interaction checking)
- Notifications (prescription ready notification)

**Demo Users**: alice.patient@example.com (allergies: Penicillin, Shellfish), dr.smith@healthhub.com

**Duration**: ~1 hour

**Learning Outcomes**:
- Complete prescription creation workflow
- Medication interaction checking against allergies and existing prescriptions
- Doctor-patient data flow
- Notification system integration

**E2E Tests**: test_prescriptions.py (enhanced with workflow), test_patient_management.py

**Prerequisites**: [Intermediate Journey](../../tutorials/01_journeys/intermediate_journey.md)

---

### 4. Lab Result Workflow

**Tutorial**: [lab_result_workflow.md](lab_result_workflow.md)

**Workflow**: Order → Lab Submits → Critical Alert → Doctor Review → Patient Notification → Patient Views

**Features Involved**:
- Lab Results (submission, critical flag detection)
- Notifications (critical value alerts to doctor and patient)
- Doctor Review (add notes, mark as reviewed)

**Demo Users**: david.patient@example.com, dr.brown@healthhub.com

**Duration**: ~1 hour

**Learning Outcomes**:
- Complete lab result processing workflow
- Critical value alert system
- Doctor review and annotation workflow
- Notification cascade (doctor → patient)

**E2E Tests**: test_lab_results.py (enhanced with critical alert workflow)

**Prerequisites**: [Intermediate Journey](../../tutorials/01_journeys/intermediate_journey.md)

---

## Workflow Comparison

| Workflow | Features | Roles | Duration | Complexity |
|----------|----------|-------|----------|------------|
| **Patient Onboarding** | Auth, Appointments, Prescriptions, Invoices | Patient, Doctor, Admin | 1.5h | High |
| **Appointment Lifecycle** | Appointments, Notifications, Invoices | Patient, Doctor | 1h | Medium |
| **Prescription Workflow** | Appointments, Patients, Prescriptions, Notifications | Doctor, Patient | 1h | Medium |
| **Lab Result Workflow** | Labs, Notifications, Doctor Review | Doctor, Patient | 1h | Medium |

---

## Integration Points

### Feature-to-Feature Data Flow

**Appointments → Invoices**:
- Completed appointment triggers invoice generation
- Appointment details populate invoice line items
- Invoice references appointment ID

**Prescriptions → Notifications**:
- New prescription triggers patient notification
- Medication interactions trigger warnings
- Refill reminders trigger scheduled notifications

**Lab Results → Notifications → Doctor Review**:
- Critical lab result triggers immediate doctor notification
- Doctor review triggers patient notification
- Review notes visible to patient

**Authentication → All Features**:
- AuthorizationState ADT used by all features for RBAC
- User ID links all patient/doctor data
- Role determines feature access

---

## Workflow Tutorial Structure

Each workflow tutorial follows this pattern:

1. **Workflow Overview**: Complete flow diagram with feature touchpoints
2. **Step-by-Step Execution**: Detailed instructions with demo data
3. **Integration Points**: Where features connect and data flows
4. **Code Tracing**: Follow data through effect programs across features
5. **State Transitions**: Track state changes across workflow
6. **Verification**: Expected outcomes at each step
7. **E2E Test References**: Corresponding test scenarios

---

## Related Content

**For feature deep dives**:
- [Authentication](../../engineering/features/authentication.md)
- [Appointments](../../engineering/features/appointments.md)
- [Prescriptions](../../engineering/features/prescriptions.md)
- [Lab Results](../../engineering/features/lab_results.md)
- [Invoices](../../engineering/features/invoices.md)

**For role perspectives**:
- [Patient Guide](../roles/patient_guide.md)
- [Doctor Guide](../roles/doctor_guide.md)
- [Admin Guide](../roles/admin_guide.md)

**For progressive learning**:
- [Beginner Journey](../../tutorials/01_journeys/beginner_journey.md)
- [Intermediate Journey](../../tutorials/01_journeys/intermediate_journey.md)
- [Advanced Journey](../../tutorials/01_journeys/advanced_journey.md)

---

## Cross-References

- [HealthHub Tutorial Hub](../README.md)
- [Feature Tutorials](../../engineering/features/README.md)
- [HealthHub Engineering Patterns](../../engineering/effect_patterns.md)
- [HealthHub Domain Documentation](../../domain/)
