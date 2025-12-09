# Role-Based Guides

**Status**: Reference only
**Supersedes**: none
**Referenced by**: demo/healthhub/documents/tutorials/README.md

> **Purpose**: Learn HealthHub from patient, doctor, or admin perspective. Role-specific capabilities, RBAC restrictions, and operational workflows.

> **Recommended for**: Role-specific training, understanding RBAC enforcement, operational user guides.

---

## Overview

Role-based guides explain HealthHub from each user role's perspective. Each guide documents capabilities, restrictions, and typical workflows.

**Use Case**: Training new users on specific roles, understanding RBAC enforcement patterns.

---

## Roles

### Patient Role

**Guide**: [patient_guide.md](patient_guide.md)

**Capabilities**:
- ✅ View own appointments
- ✅ Request new appointments
- ✅ Cancel own appointments
- ✅ View own prescriptions
- ✅ View own lab results
- ✅ View own invoices

**Restrictions**:
- ❌ Cannot create prescriptions
- ❌ Cannot view other patients' data
- ❌ Cannot access admin features
- ❌ Cannot access audit logs

**Demo User**: alice.patient@example.com (allergies: Penicillin, Shellfish)

**E2E Tests**: test_rbac.py (patient access), test_patient_workflows.py

**Prerequisites**: [Beginner Journey](../01_journeys/beginner_journey.md)

---

### Doctor Role

**Guide**: [doctor_guide.md](doctor_guide.md)

**Capabilities**:
- ✅ View all patients
- ✅ Confirm/start/complete appointments
- ✅ Create prescriptions (if `can_prescribe=true`)
- ✅ Review lab results
- ✅ Add doctor notes
- ✅ Transition appointment state machine

**Restrictions**:
- ❌ Cannot create invoices
- ❌ Cannot access audit logs
- ❌ Cannot manage users
- ❌ Cannot modify system configuration

**Demo User**: dr.smith@healthhub.com (Cardiology, can_prescribe=true)

**E2E Tests**: test_rbac.py (doctor access), test_prescriptions.py (creation), test_patient_management.py

**Prerequisites**: [Beginner Journey](../01_journeys/beginner_journey.md)

---

### Admin Role

**Guide**: [admin_guide.md](admin_guide.md)

**Capabilities**:
- ✅ Full access to all features
- ✅ View HIPAA audit logs
- ✅ Create invoices
- ✅ Manage users
- ✅ View system metrics
- ✅ Access all patient data
- ✅ System administration

**Restrictions**:
- None (full system access)

**Demo User**: admin@healthhub.com

**E2E Tests**: test_rbac.py (admin access), test_admin_workflows.py

**Prerequisites**: [Beginner Journey](../01_journeys/beginner_journey.md)

---

## RBAC Enforcement

All role restrictions enforced via AuthorizationState ADT:

```python
type AuthorizationState = (
    PatientAuthorized    # user_id, patient_id, email, role="patient"
    | DoctorAuthorized   # user_id, doctor_id, email, specialization, can_prescribe
    | AdminAuthorized    # user_id, email, role="admin"
    | Unauthorized       # reason, detail
)
```

**Pattern Matching Example**:
```python
match auth_state:
    case PatientAuthorized(patient_id=pid):
        # Patient can only view own data
        return get_patient_appointments(pid)
    case DoctorAuthorized(can_prescribe=True):
        # Doctor can create prescriptions
        return create_prescription_form()
    case AdminAuthorized():
        # Admin has full access
        return admin_dashboard()
    case Unauthorized(reason=reason):
        # Redirect to login
        return redirect("/login")
```

**See**: [Authentication Feature Tutorial](../03_features/authentication.md) for complete RBAC patterns.

---

## Role Comparison Matrix

| Feature | Patient | Doctor | Admin |
|---------|---------|--------|-------|
| **View own appointments** | ✅ | ✅ | ✅ |
| **View all appointments** | ❌ | ✅ | ✅ |
| **Request appointment** | ✅ | ✅ | ✅ |
| **Confirm appointment** | ❌ | ✅ | ✅ |
| **Complete appointment** | ❌ | ✅ | ✅ |
| **View own prescriptions** | ✅ | ✅ | ✅ |
| **View all prescriptions** | ❌ | ✅ | ✅ |
| **Create prescription** | ❌ | ✅ (if can_prescribe) | ✅ |
| **View own lab results** | ✅ | ✅ | ✅ |
| **View all lab results** | ❌ | ✅ | ✅ |
| **Review lab results** | ❌ | ✅ | ✅ |
| **View own invoices** | ✅ | ❌ | ✅ |
| **Create invoices** | ❌ | ❌ | ✅ |
| **View audit logs** | ❌ | ❌ | ✅ |
| **Manage users** | ❌ | ❌ | ✅ |

---

## Workflow Examples

### Patient Typical Workflow
1. Login → Dashboard
2. View upcoming appointments
3. Request new appointment
4. View prescriptions and refills
5. View lab results
6. View invoices

### Doctor Typical Workflow
1. Login → Dashboard
2. View pending appointment confirmations
3. Confirm appointments
4. Conduct appointment (start → complete)
5. Create prescription (medication interaction check)
6. Review lab results (add notes)

### Admin Typical Workflow
1. Login → Admin dashboard
2. View system metrics
3. Review audit logs (HIPAA compliance)
4. Create invoices for completed appointments
5. Manage users (activate/deactivate)

---

## Related Tutorials

**For deeper feature understanding**:
- [Appointments Feature](../03_features/appointments.md)
- [Prescriptions Feature](../03_features/prescriptions.md)
- [Lab Results Feature](../03_features/lab_results.md)
- [Authentication Feature](../03_features/authentication.md)

**For complete workflows**:
- [Appointment Lifecycle](../04_workflows/appointment_lifecycle.md)
- [Prescription Workflow](../04_workflows/prescription_workflow.md)
- [Patient Onboarding](../04_workflows/patient_onboarding.md)

---

## Cross-References

- [HealthHub Tutorial Hub](../README.md)
- [Feature Tutorials](../03_features/README.md)
- [Journey Tutorials](../01_journeys/README.md)
- [Workflow Tutorials](../04_workflows/README.md)
- [Authentication Documentation](../../engineering/authentication.md)
