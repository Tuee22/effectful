# HIPAA Compliance

> Audit logging requirements for healthcare data protection.

---

## Overview

HIPAA (Health Insurance Portability and Accountability Act) requires comprehensive audit logging for all access to Protected Health Information (PHI).

---

## What Must Be Logged

### PHI Access Events

| Event Type | When to Log |
|------------|-------------|
| View Patient | Any access to patient demographics |
| View Appointment | Any access to appointment details |
| View Prescription | Any access to medication records |
| View Lab Result | Any access to test results |
| Create/Update | Any modification to PHI |
| Export/Download | Any bulk data access |

### Authentication Events

| Event Type | When to Log |
|------------|-------------|
| Login Success | Successful authentication |
| Login Failure | Failed authentication attempt |
| Logout | User session termination |
| Token Refresh | Access token renewal |
| Password Change | Password modification |

### Authorization Events

| Event Type | When to Log |
|------------|-------------|
| Permission Denied | Access attempt blocked |
| Role Change | User role modification |
| Account Lockout | Too many failed attempts |

---

## Required Fields

Every audit event must include:

| Field | Requirement | Example |
|-------|-------------|---------|
| user_id | Who performed action | UUID |
| timestamp | When action occurred | ISO 8601 datetime |
| action | What was done | "view_patient" |
| resource_type | Category of data | "patient", "appointment" |
| resource_id | Specific record | UUID |
| ip_address | Where request originated | "192.168.1.100" |
| outcome | Success or failure | "success", "denied" |

---

## Logging Pattern

### Success Logging

```python
def view_patient_program(
    patient_id: UUID,
    actor_id: UUID,
    ip_address: str | None,
    user_agent: str | None,
) -> Generator[AllEffects, object, Patient | None]:
    patient = yield GetPatientById(patient_id=patient_id)

    # Log successful access
    if isinstance(patient, Patient):
        yield LogAuditEvent(
            user_id=actor_id,
            action="view_patient",
            resource_type="patient",
            resource_id=patient_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={"status": "success"},
        )
        return patient

    # Log failed access (not found)
    yield LogAuditEvent(
        user_id=actor_id,
        action="view_patient",
        resource_type="patient",
        resource_id=patient_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={"status": "not_found"},
    )
    return None
```

### Failure Logging

```python
def view_patient_unauthorized(
    patient_id: UUID,
    actor_id: UUID,
    auth: AuthorizationState,
    ip_address: str | None,
) -> Generator[AllEffects, object, None]:
    # Log unauthorized access attempt
    yield LogAuditEvent(
        user_id=actor_id,
        action="view_patient",
        resource_type="patient",
        resource_id=patient_id,
        ip_address=ip_address,
        user_agent=None,
        metadata={
            "status": "unauthorized",
            "reason": auth.reason if isinstance(auth, Unauthorized) else "unknown",
        },
    )
    return None
```

---

## Retention Requirements

- **Minimum**: 6 years (HIPAA requirement)
- **Recommendation**: 7 years (safe margin)
- **Storage**: Immutable, tamper-evident

### Database Partitioning

For high-volume systems:

```sql
-- Partition by month for efficient archival
CREATE TABLE audit_events (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id UUID NOT NULL,
    ip_address INET,
    user_agent TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
) PARTITION BY RANGE (created_at);

-- Create monthly partitions
CREATE TABLE audit_events_2025_01 PARTITION OF audit_events
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
```

---

## Anti-Patterns

### Anti-Pattern 1: Log Only Success

```python
# BAD - Doesn't log failures
patient = yield GetPatientById(patient_id=patient_id)
if isinstance(patient, Patient):
    yield LogAuditEvent(...)  # Only logs success

# GOOD - Log all access attempts
patient = yield GetPatientById(patient_id=patient_id)
yield LogAuditEvent(
    metadata={"status": "success" if patient else "not_found"},
    ...
)
```

### Anti-Pattern 2: Missing IP Address

```python
# BAD - No source information
yield LogAuditEvent(
    ip_address=None,  # Always None
    ...
)

# GOOD - Capture from request
yield LogAuditEvent(
    ip_address=request.client.host,
    user_agent=request.headers.get("User-Agent"),
    ...
)
```

### Anti-Pattern 3: Mutable Audit Logs

```python
# BAD - Allow updates/deletes
UPDATE audit_events SET action = 'view_patient' WHERE ...
DELETE FROM audit_events WHERE created_at < ...

# GOOD - Immutable storage
-- No UPDATE or DELETE permissions on audit_events table
-- Use partitioning and archival for retention management
```

### Anti-Pattern 4: Insufficient Detail

```python
# BAD - Vague logging
yield LogAuditEvent(
    action="access",  # What kind of access?
    resource_type="data",  # What data?
    metadata=None,
)

# GOOD - Detailed logging
yield LogAuditEvent(
    action="view_prescription",
    resource_type="prescription",
    resource_id=prescription.id,
    metadata={
        "patient_id": str(patient_id),
        "medication": prescription.medication,
    },
)
```

---

## Compliance Checklist

- [ ] All PHI access logged (view, create, update, delete)
- [ ] Failed access attempts logged
- [ ] Authentication events logged
- [ ] IP address captured when available
- [ ] User agent captured when available
- [ ] Timestamps in UTC
- [ ] 6+ year retention configured
- [ ] Audit log immutability enforced
- [ ] Regular compliance audits scheduled

---

## Related Documentation

- [Audit Logging](../product/audit_logging.md)
- [Authorization System](../product/authorization_system.md)
- [Authentication](../product/authentication.md)

---

**Last Updated**: 2025-11-25
