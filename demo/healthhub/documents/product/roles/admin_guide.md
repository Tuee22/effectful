# Admin Guide

**Status**: Authoritative source
**Supersedes**: none **📖 Base Standard**: [admin_guide.md](../../../../../documents/product/roles/admin_guide.md)
**Referenced by**: demo/healthhub/documents/tutorials/README.md

> **Purpose**: HealthHub overlay deltas for Admin Guide. **📖 Base Standard**: [admin_guide.md](../../../../../documents/product/roles/admin_guide.md)

## Prerequisites

- Docker workflow running; commands executed via `docker compose -f docker/docker-compose.yml`.
- Completed [Beginner Journey](../../tutorials/01_journeys/beginner_journey.md).
- Access to HealthHub at `http://localhost:8851`.
- Understanding of HIPAA compliance and audit logging.

## Learning Objectives

- Understand complete admin capabilities (full system access)
- Navigate admin dashboard and features
- Generate invoices from completed appointments
- View and analyze HIPAA audit logs
- Manage users (activate, deactivate, update roles)
- Mark invoices as paid and manage payment status
- Understand audit trail and compliance requirements

## Overview

**Admin Role**: Admins have full system access for administrative, financial, and compliance operations. Admins can perform all operations that doctors can, plus additional administrative functions.

**Authorization**: AdminAuthorized ADT variant

```python
# snippet
@dataclass(frozen=True)
class AdminAuthorized:
    user_id: UUID
    email: str
    role: Literal["admin"] = "admin"
```

**Key Characteristic**: No additional context fields needed - admins have unrestricted access to all features.

## Admin Capabilities

### ✅ What Admins CAN Do

**All Doctor Capabilities**:

- View all patients and patient details
- View all appointments, prescriptions, lab results
- Confirm, start, complete, and cancel appointments
- Create prescriptions (with `can_prescribe=true` in doctor table)
- Review lab results

**Admin-Only Capabilities**:

| Capability                   | Description                                 | API Endpoint                                        | Tutorial Reference                                                                             |
| ---------------------------- | ------------------------------------------- | --------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| **Generate invoices**        | Create invoices from completed appointments | `POST /api/invoices/generate-from-appointment/{id}` | [Invoices Feature](../../engineering/features/invoices.md#invoice-generation-from-appointment) |
| **View all invoices**        | View all invoices for all patients          | `GET /api/invoices`                                 | [Invoices Feature](../../engineering/features/invoices.md)                                     |
| **Mark invoices paid**       | Update invoice status to Paid               | `POST /api/invoices/{id}/mark-paid`                 | [Invoices Feature](../../engineering/features/invoices.md#mark-invoice-as-paid)                |
| **View audit logs**          | View HIPAA audit trail (all PHI access)     | `GET /api/audit-logs`                               | -                                                                                              |
| **Manage users**             | Create, activate, deactivate users          | `POST /api/users`, `PUT /api/users/{id}`            | -                                                                                              |
| **Update user roles**        | Change user roles (patient, doctor, admin)  | `PUT /api/users/{id}/role`                          | -                                                                                              |
| **Update doctor privileges** | Toggle `can_prescribe` flag for doctors     | `PUT /api/doctors/{id}/can-prescribe`               | -                                                                                              |
| **View system metrics**      | View system usage, performance metrics      | `GET /api/metrics`                                  | -                                                                                              |
| **Manage data retention**    | Configure HIPAA-compliant data retention    | `PUT /api/settings/retention`                       | -                                                                                              |

### ❌ What Admins CANNOT Do (Intentional Restrictions)

| Restriction                | Reason               | Policy                                               |
| -------------------------- | -------------------- | ---------------------------------------------------- |
| **Delete patient records** | HIPAA compliance     | Data retention policy requires 7 years minimum       |
| **Modify audit logs**      | Compliance integrity | Audit logs are append-only, no modifications allowed |
| **Delete audit logs**      | Compliance integrity | Audit logs retained for 7 years per HIPAA            |
| **View passwords**         | Security             | Passwords stored as bcrypt hashes, not reversible    |

## Admin Dashboard

**Access**: `http://localhost:8851/dashboard` (after login as admin)

**Sections**:

1. **Welcome Banner**: "Welcome, Admin"
1. **System Overview**:
   - Total Patients
   - Total Doctors
   - Total Appointments (by status)
   - Total Prescriptions
1. **Pending Tasks**:
   - Appointments needing invoice generation
   - Unpaid invoices past due
   - New user registrations awaiting approval
1. **Recent Activity**:
   - Recent audit log entries
   - Recent invoices generated
   - Recent payments received
1. **System Alerts**:
   - Critical system errors
   - Security alerts (failed login attempts)
   - Compliance alerts (audit log gaps)

**Navigation Sidebar**:

- **Dashboard** (overview)
- **Patients** (all patients)
- **Doctors** (all doctors)
- **Appointments** (all appointments)
- **Prescriptions** (all prescriptions)
- **Lab Results** (all lab results)
- **Invoices** (all invoices) **[Admin-only]**
- **Audit Logs** (HIPAA audit trail) **[Admin-only]**
- **Users** (user management) **[Admin-only]**
- **System Metrics** (performance) **[Admin-only]**
- **Logout**

## Workflow 1: Generate Invoice from Completed Appointment

**Goal**: Create invoice for patient after appointment completed.

**Prerequisites**: Appointment must be in "Completed" status.

**Steps**:

1. **Navigate to Appointments**: Click "Appointments" in sidebar

1. **Filter to Completed**: Select "Completed" status filter

1. **Identify Unbilled Appointments**: Look for appointments without linked invoices

   - Badge: "Invoice Needed" displayed on unbilled completed appointments

1. **Click Appointment**: View appointment details

   - Patient: Name and demographics
   - Doctor: Name and specialization
   - Scheduled Time: Date and time
   - Status: Completed (with completion notes)

1. **Click "Generate Invoice"** button

1. **System Calculates Charges**:

   - **Office Visit**: Base charge based on specialization
     - Cardiology: $250.00
     - Pediatrics: $150.00
     - General Practice: $120.00
     - Orthopedics: $300.00
   - **Additional Services**: Based on appointment reason
     - Annual Physical: +$50.00
   - **Subtotal**: Sum of charges
   - **Tax**: 7% of subtotal
   - **Total**: Subtotal + Tax

1. **Review Invoice Preview**:

   ```
   Invoice Preview:

   Patient: Alice Anderson
   Appointment Date: 2025-11-15
   Doctor: Dr. Sarah Smith (Cardiology)

   Line Items:
   1. Office Visit - Cardiology (1 × $250.00) = $250.00
   2. Annual Physical Examination (1 × $50.00) = $50.00

   Subtotal: $300.00
   Tax (7%): $21.00
   Total: $321.00

   Due Date: 2025-12-20 (30 days from issue)
   ```

1. **Confirm Invoice Generation**: Click "Generate Invoice"

1. **Expected Result**:

   - Invoice created with status "Sent"
   - Patient notified via notification
   - Invoice visible to patient in "Invoices" section
   - Invoice appears in admin invoice list

**RBAC Enforcement**:

```python
# Backend validation
match auth_state:
    case AdminAuthorized():
        # Admin can generate invoices
        pass
    case DoctorAuthorized() | PatientAuthorized():
        raise HTTPException(403, "Only admins can generate invoices")
```

**Demo Data**: Generate invoice for Alice's completed appointment with Dr. Williams.

**Test Coverage**: `test_admin_workflows.py::test_admin_generate_invoice`

## Workflow 2: Mark Invoice as Paid

**Goal**: Update invoice status after payment received.

**Steps**:

1. **Navigate to Invoices**: Click "Invoices" in sidebar

1. **Filter to Unpaid**: Select "Sent" or "Overdue" status filter

1. **Click Invoice**: View invoice details

   - Patient: Name and contact info
   - Total: Amount due
   - Due Date: Payment deadline
   - Status: Sent or Overdue
   - Line Items: Itemized charges

1. **Receive Payment** (external process):

   - Patient pays via credit card, check, or online portal
   - Payment reference number obtained (e.g., "CH_abc123xyz")

1. **Click "Mark as Paid"** button

1. **Enter Payment Details**:

   - **Payment Method**: Credit Card, Check, Cash, Online Portal
   - **Payment Reference**: Transaction ID or check number
   - **Payment Date**: Date payment received (defaults to today)

1. **Confirm Payment**: Click "Mark as Paid"

1. **Expected Result**:

   - Invoice status updated: Sent/Overdue → Paid
   - Payment date recorded
   - Payment log entry created (for audit trail)
   - Invoice no longer appears in unpaid invoices list

**RBAC Enforcement**:

```python
# Backend validation
match auth_state:
    case AdminAuthorized():
        # Admin can mark invoices as paid
        pass
    case DoctorAuthorized() | PatientAuthorized():
        raise HTTPException(403, "Only admins can mark invoices as paid")
```

**Demo Data**: Mark test invoice as paid with payment method "Credit Card".

**Test Coverage**: `test_admin_workflows.py::test_admin_mark_invoice_paid`

## Workflow 3: View HIPAA Audit Logs

**Goal**: Review audit trail of all PHI (Protected Health Information) access.

**HIPAA Requirement**: All access to PHI must be logged for compliance.

**Steps**:

1. **Navigate to Audit Logs**: Click "Audit Logs" in sidebar **[Admin-only]**

1. **View Audit Log List**:

   - **Timestamp**: When action occurred
   - **User**: Who accessed PHI (email)
   - **Action**: Type of access (appointment_viewed, prescription_created, etc.)
   - **Resource**: What was accessed (patient_id, appointment_id, etc.)
   - **IP Address**: Source IP address
   - **User Agent**: Browser/device information

1. **Filter Options**:

   - **User**: Filter by specific user email
   - **Action Type**: Filter by action (appointment_created, prescription_viewed, etc.)
   - **Date Range**: Filter by date range
   - **Resource**: Filter by patient_id or specific resource

1. **Example Audit Log Entries**:

   ```
   2025-11-15 14:32:10 | alice.patient@example.com | appointment_created
   Resource: appointment_id=50000000-0000-0000-0000-000000000001
   IP: 192.168.1.100 | User Agent: Mozilla/5.0 (Macintosh...)

   2025-11-15 14:35:22 | dr.smith@healthhub.com | prescription_created
   Resource: prescription_id=60000000-0000-0000-0000-000000000001, patient_id=30000000-0000-0000-0000-000000000001
   IP: 192.168.1.101 | User Agent: Mozilla/5.0 (Macintosh...)

   2025-11-15 14:40:15 | dr.smith@healthhub.com | patient_viewed
   Resource: patient_id=30000000-0000-0000-0000-000000000001
   IP: 192.168.1.101 | User Agent: Mozilla/5.0 (Macintosh...)

   2025-11-15 15:00:00 | alice.patient@example.com | prescription_viewed
   Resource: prescription_id=60000000-0000-0000-0000-000000000001
   IP: 192.168.1.100 | User Agent: Mozilla/5.0 (Macintosh...)
   ```

1. **Audit Log Actions**:

   - `appointment_created` - New appointment created
   - `appointment_viewed` - Appointment details viewed
   - `appointment_updated` - Appointment status changed
   - `prescription_created` - New prescription created
   - `prescription_viewed` - Prescription details viewed
   - `lab_result_created` - New lab result submitted
   - `lab_result_viewed` - Lab result details viewed
   - `lab_result_reviewed` - Doctor added review notes
   - `patient_viewed` - Patient profile viewed
   - `patient_updated` - Patient profile updated
   - `invoice_generated` - Invoice created
   - `invoice_viewed` - Invoice details viewed

1. **Investigate Suspicious Activity**:

   - Multiple failed login attempts from same IP
   - PHI access outside business hours
   - Excessive PHI access by single user
   - Access to unrelated patients (no clinical justification)

1. **Export Audit Logs** (for compliance reporting):

   - Click "Export to CSV"
   - Select date range
   - Download CSV file for regulatory reporting

**RBAC Enforcement**:

```python
# Backend validation
match auth_state:
    case AdminAuthorized():
        # Admin can view audit logs
        pass
    case DoctorAuthorized() | PatientAuthorized():
        raise HTTPException(403, "Only admins can view audit logs")
```

**HIPAA Compliance**:

- **Retention**: Audit logs retained for 7 years
- **Immutability**: Audit logs cannot be modified or deleted
- **Completeness**: All PHI access logged (no gaps)
- **Availability**: Audit logs available for regulatory review within 24 hours

**Demo Data**: View audit logs for Alice Anderson's patient_id.

**Test Coverage**: `test_admin_workflows.py::test_admin_view_audit_logs`

## Workflow 4: Manage Users

**Goal**: Create, activate, or deactivate user accounts.

**Steps**:

### Create New User

1. **Navigate to Users**: Click "Users" in sidebar **[Admin-only]**

1. **Click "Create New User"** button

1. **Fill out User Form**:

   - **Email**: User's email address (username)
   - **Role**: Patient, Doctor, or Admin
   - **Temporary Password**: Initial password (user must change on first login)
   - **First Name**: User's first name
   - **Last Name**: User's last name

1. **Role-Specific Fields**:

   - **Patient**: Date of birth, blood type, allergies
   - **Doctor**: Specialization, can_prescribe flag
   - **Admin**: No additional fields

1. **Submit**: Click "Create User"

1. **Expected Result**:

   - User account created
   - User appears in user list
   - User can log in with temporary password

### Deactivate User

1. **Navigate to Users**: Click "Users" in sidebar

1. **Select User**: Click user email

1. **Click "Deactivate User"** button

1. **Confirm Deactivation**: Click "Confirm"

1. **Expected Result**:

   - User account deactivated (is_active=false)
   - User cannot log in
   - User data retained (HIPAA compliance)
   - Audit log entry created

### Reactivate User

1. **Navigate to Users**: Click "Users" in sidebar

1. **Filter to Inactive**: Select "Inactive" filter

1. **Select User**: Click user email

1. **Click "Reactivate User"** button

1. **Confirm Reactivation**: Click "Confirm"

1. **Expected Result**:

   - User account reactivated (is_active=true)
   - User can log in again
   - Audit log entry created

**RBAC Enforcement**:

```python
# Backend validation
match auth_state:
    case AdminAuthorized():
        # Admin can manage users
        pass
    case DoctorAuthorized() | PatientAuthorized():
        raise HTTPException(403, "Only admins can manage users")
```

**Demo Data**: Create test user, deactivate, then reactivate.

**Test Coverage**: `test_admin_workflows.py::test_admin_manage_users`

## Workflow 5: Update Doctor Prescription Privileges

**Goal**: Toggle `can_prescribe` flag for doctor.

**Use Case**: Grant prescription privileges to newly licensed doctor, or revoke privileges for doctor under investigation.

**Steps**:

1. **Navigate to Doctors**: Click "Doctors" in sidebar

1. **Select Doctor**: Click doctor name

1. **View Doctor Profile**:

   - **Name**: Doctor's full name
   - **Email**: Doctor's email
   - **Specialization**: Medical specialty
   - **can_prescribe**: Current flag value (true/false)
   - **License Number**: Medical license number (if available)

1. **Toggle Prescription Privileges**:

   - **If can_prescribe=false**: Click "Grant Prescription Privileges"
   - **If can_prescribe=true**: Click "Revoke Prescription Privileges"

1. **Confirm Change**: Enter reason for change (for audit trail)

   ```
   Example reasons:
   - "Doctor obtained DEA registration"
   - "Doctor's license renewed"
   - "Doctor under investigation, revoking privileges pending review"
   ```

1. **Submit**: Click "Confirm"

1. **Expected Result**:

   - `can_prescribe` flag updated in database
   - Doctor's next JWT token will reflect new flag value
   - Doctor can/cannot create prescriptions accordingly
   - Audit log entry created with reason

**RBAC Enforcement**:

```python
# Backend validation
match auth_state:
    case AdminAuthorized():
        # Admin can update doctor privileges
        pass
    case DoctorAuthorized() | PatientAuthorized():
        raise HTTPException(403, "Only admins can update doctor privileges")
```

**Demo Data**: Toggle `can_prescribe` for test doctor.

**Test Coverage**: `test_admin_workflows.py::test_admin_update_doctor_privileges`

## System Metrics

**Access**: Click "System Metrics" in sidebar **[Admin-only]**

**Metrics Displayed**:

- **User Metrics**:
  - Total users (by role)
  - Active users (logged in within 30 days)
  - New user registrations (last 7 days)
- **Appointment Metrics**:
  - Total appointments (by status)
  - Appointments per day (last 30 days)
  - Average appointment duration
  - Appointment confirmation rate
- **Prescription Metrics**:
  - Total prescriptions
  - Prescriptions per day (last 30 days)
  - Top prescribed medications
  - Prescription interaction warnings (count by severity)
- **Lab Result Metrics**:
  - Total lab results
  - Critical lab results (count)
  - Lab result review rate (% reviewed within 24 hours)
- **Invoice Metrics**:
  - Total invoices (by status)
  - Revenue (last 30 days)
  - Average invoice amount
  - Payment collection rate
  - Overdue invoices (count and total amount)
- **System Performance**:
  - API request count (last 24 hours)
  - API request latency (P50, P95, P99)
  - Database query latency
  - Error rate (4xx, 5xx responses)

**Use Cases**:

- Monitor system health
- Identify performance bottlenecks
- Track business metrics (revenue, appointments)
- Compliance reporting (audit log completeness)

## Security and Privacy

**Admin Access Scope**:

- **Full System Access**: Admins can perform all operations
- **HIPAA Audit Logging**: All admin actions logged for compliance
- **Separation of Duties**: Financial operations (invoices) restricted to admin role

**Best Practices**:

- Use admin access only when necessary
- Do not share admin credentials
- Log out when not actively using admin features
- Review audit logs regularly for suspicious activity

**Password Policy**:

- Minimum 12 characters
- Must include uppercase, lowercase, number, special character
- Cannot reuse last 5 passwords
- Expires every 90 days

## Demo Users

**Admin User** - Featured in tutorials

- Email: `admin@healthhub.com`
- Password: `password123`
- Full system access

## Troubleshooting

**Issue**: Cannot generate invoice

**Possible Causes**:

- Appointment not in "Completed" status
- Invoice already generated for appointment
- Network error

**Solution**: Verify appointment status is "Completed". Check if invoice already exists for appointment.

______________________________________________________________________

**Issue**: Cannot view audit logs

**Possible Causes**:

- Not logged in as admin
- Network error
- Audit log service unavailable

**Solution**: Verify admin role in JWT token. Check system status.

______________________________________________________________________

**Issue**: User deactivation fails

**Possible Causes**:

- User has active appointments or prescriptions
- Network error

**Solution**: Deactivation prevents new logins but does not affect existing data. Retry deactivation.

## Summary

**Admin role characteristics**:

- ✅ Full system access (all doctor capabilities + admin-only features)
- ✅ Generate and manage invoices
- ✅ View HIPAA audit logs for compliance
- ✅ Manage users (create, activate, deactivate)
- ✅ Update doctor prescription privileges
- ✅ View system metrics and performance
- ❌ Cannot delete patient records (HIPAA compliance)
- ❌ Cannot modify or delete audit logs (compliance integrity)

**RBAC enforcement**: AdminAuthorized ADT variant grants unrestricted access to all features.

**Key Takeaway**: Admin role has full system access for administrative, financial, and compliance operations, with audit logging for all actions.

## Cross-References

- [Beginner Journey - Admin Login](../../tutorials/01_journeys/beginner_journey.md#step-7-login-as-admin)
- [Authentication Feature](../../engineering/features/authentication.md)
- [Appointments Feature](../../engineering/features/appointments.md)
- [Prescriptions Feature](../../engineering/features/prescriptions.md)
- [Lab Results Feature](../../engineering/features/lab_results.md)
- [Invoices Feature](../../engineering/features/invoices.md)
- [Patient Guide](patient_guide.md)
- [Doctor Guide](doctor_guide.md)
