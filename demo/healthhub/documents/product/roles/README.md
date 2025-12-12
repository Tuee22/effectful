# Role-Based Guides

**Status**: Authoritative source
**Supersedes**: none **📖 Base Standard**: [README.md](../../../../../documents/product/roles/README.md)
**Referenced by**: demo/healthhub/documents/readme.md, demo/healthhub/documents/tutorials/README.md, demo/healthhub/documents/product/README.md

> **Purpose**: HealthHub overlay deltas for Readme. **📖 Base Standard**: [README.md](../../../../../documents/product/roles/README.md)

______________________________________________________________________

## Overview

Role-based guides explain HealthHub from each user role's perspective. Each guide documents capabilities, restrictions, and typical workflows.

**Use Case**: Training new users on specific roles, understanding RBAC enforcement patterns.

______________________________________________________________________

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

**Prerequisites**: [Beginner Journey](../../tutorials/01_journeys/beginner_journey.md)

______________________________________________________________________

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

**Prerequisites**: [Beginner Journey](../../tutorials/01_journeys/beginner_journey.md)

______________________________________________________________________

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

**Prerequisites**: [Beginner Journey](../../tutorials/01_journeys/beginner_journey.md)

______________________________________________________________________

## RBAC Enforcement

All role restrictions enforced via AuthorizationState ADT:

```python
# snippet
type AuthorizationState = (
    PatientAuthorized    # user_id, patient_id, email, role="patient"
    | DoctorAuthorized   # user_id, doctor_id, email, specialization, can_prescribe
    | AdminAuthorized    # user_id, email, role="admin"
    | Unauthorized       # reason, detail
)
```

**Pattern Matching Example**:

```python
# snippet
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

**See**: [Authentication Feature Tutorial](../../engineering/features/authentication.md) for complete RBAC patterns.

______________________________________________________________________

## Role Comparison Matrix

| Feature                    | Patient | Doctor                | Admin |
| -------------------------- | ------- | --------------------- | ----- |
| **View own appointments**  | ✅      | ✅                    | ✅    |
| **View all appointments**  | ❌      | ✅                    | ✅    |
| **Request appointment**    | ✅      | ✅                    | ✅    |
| **Confirm appointment**    | ❌      | ✅                    | ✅    |
| **Complete appointment**   | ❌      | ✅                    | ✅    |
| **View own prescriptions** | ✅      | ✅                    | ✅    |
| **View all prescriptions** | ❌      | ✅                    | ✅    |
| **Create prescription**    | ❌      | ✅ (if can_prescribe) | ✅    |
| **View own lab results**   | ✅      | ✅                    | ✅    |
| **View all lab results**   | ❌      | ✅                    | ✅    |
| **Review lab results**     | ❌      | ✅                    | ✅    |
| **View own invoices**      | ✅      | ❌                    | ✅    |
| **Create invoices**        | ❌      | ❌                    | ✅    |
| **View audit logs**        | ❌      | ❌                    | ✅    |
| **Manage users**           | ❌      | ❌                    | ✅    |

______________________________________________________________________

## Workflow Examples

### Patient Typical Workflow

1. Login → Dashboard
1. View upcoming appointments
1. Request new appointment
1. View prescriptions and refills
1. View lab results
1. View invoices

### Doctor Typical Workflow

1. Login → Dashboard
1. View pending appointment confirmations
1. Confirm appointments
1. Conduct appointment (start → complete)
1. Create prescription (medication interaction check)
1. Review lab results (add notes)

### Admin Typical Workflow

1. Login → Admin dashboard
1. View system metrics
1. Review audit logs (HIPAA compliance)
1. Create invoices for completed appointments
1. Manage users (activate/deactivate)

______________________________________________________________________

## Related Tutorials

**For deeper feature understanding**:

- [Appointments Feature](../../engineering/features/appointments.md)
- [Prescriptions Feature](../../engineering/features/prescriptions.md)
- [Lab Results Feature](../../engineering/features/lab_results.md)
- [Authentication Feature](../../engineering/features/authentication.md)

**For complete workflows**:

- [Appointment Lifecycle](../../product/workflows/appointment_lifecycle.md)
- [Prescription Workflow](../../product/workflows/prescription_workflow.md)
- [Patient Onboarding](../../product/workflows/patient_onboarding.md)

______________________________________________________________________

## Cross-References

- [HealthHub Tutorial Hub](../README.md)
- [Feature Tutorials](../../engineering/features/README.md)
- [Journey Tutorials](../../tutorials/01_journeys/README.md)
- [Workflow Tutorials](../../product/workflows/README.md)
- [Authentication Documentation](../../engineering/authentication.md)
