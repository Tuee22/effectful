# HIPAA Compliance

> Extends base [Documentation Standards](../../../../documents/documentation_standards.md); base rules apply. HealthHub-specific HIPAA compliance deltas only.

---

## Overview

HIPAA (Health Insurance Portability and Accountability Act) requires comprehensive audit logging for all access to Protected Health Information (PHI).

**Scope**: This document captures HIPAA-specific requirements plus common adjacent obligations (21st Century Cures/Information Blocking, 42 CFR Part 2 where applicable) that apply to any healthcare system.

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
| reason / purpose_of_use | Why access occurred | "treatment", "payment", "operations", "break_glass" |
| patient_id | Patient record the access relates to | UUID |
| org_id / tenant_id | Organization/clinic context | UUID |
| correlation_id | Ties together multi-entity operations | ULID/UUID |

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
- **Destruction**: After retention window, destroy via defensible process and log destruction events

**Clock Discipline**:
- Enforce UTC timestamps everywhere
- Sync all systems with NTP (multiple stratum-1/2 servers); alert on drift > 1s

**Tamper Resistance**:
- Write-once or append-only storage (e.g., WORM/S3 Object Lock, pg\_wal + hash chain)
- Sign/chain logs (hash of previous record) to detect modification
- Restrict UPDATE/DELETE; use partition drop + archival instead

**Access Controls**:
- Least privilege to read logs; separate roles for writers vs reviewers
- MFA required for log access; all log access is itself audited

**Review & Monitoring**:
- Daily alerting: anomalous access, mass export, excessive failures, break-glass use
- Weekly sampling of audit logs by compliance
- Quarterly access reviews for audit-log readers
- Annual (or after material change) tamper-evidence validation test

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

-- Optional: hash chain for tamper evidence
ALTER TABLE audit_events ADD COLUMN prev_hash BYTEA;
ALTER TABLE audit_events ADD COLUMN curr_hash BYTEA;
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

## Security Rule Safeguards (Operational Must-Haves)

**Administrative**:
- Risk analysis + risk management documented and refreshed at least annually
- Workforce training with sanctions policy; break-glass usage reviewed within 24 hours
- Role-based access control mapped to job duties; quarterly access reviews
- Contingency plan: backups, disaster recovery (RPO/RTO defined), emergency mode operation

**Physical**:
- Facility/workstation security (screen locks, device inventory, secure disposal)
- Device encryption for all PHI-capable endpoints (laptops/tablets/phones)

**Technical**:
- Unique user IDs; MFA for privileged and remote access
- Automatic logoff/session timeout (e.g., 15 minutes interactive, shorter for kiosks)
- Encryption in transit (TLS 1.2+; HSTS) and at rest (FIPS-validated crypto where possible; KMS-backed keys; rotation)
- Integrity controls: checksums/hash-chains on logs; backups validated with restore tests
- Transmission security: mTLS or signed URLs for service-to-service; no plaintext channels

---

## Breach Response & Notification

- **Detect**: Monitor for anomalous access, mass export, or tamper signals; alert to on-call
- **Contain**: Disable affected accounts/tokens, rotate keys, snapshot evidence, preserve logs
- **Assess**: Determine PHI scope, likelihood of compromise, and whether a breach occurred
- **Notify**:
  - Affected individuals without unreasonable delay, no later than 60 days from discovery
  - OCR if >500 individuals in a state/jurisdiction without unreasonable delay; otherwise log for annual submission
  - Media notice if >500 in a single state/jurisdiction
  - Follow stricter state deadlines where applicable (some are <30–45 days)
- **Document**: Incident report, timeline, remediation, and sanctions if applicable

---

## Adjacent Regulations & Interop

- **21st Century Cures / Information Blocking**: Support patient access/export; log all export/download events with purpose and actor; implement export throttling/anomaly alerting
- **HIPAA Right of Access**: Fulfill access within required timelines; log request, fulfillment timestamp, and data delivered
- **42 CFR Part 2 (SUD data)**: If applicable, stricter consent/redisclosure limits; tag data sets and enforce consent-aware access; audit redisclosure prevention
- **EPCS / DEA**: Two-factor auth with identity proofing for controlled substances; keep audit trail of identity proofing events and device bindings
- **PCI DSS adjacency**: Segregate payment flows/systems; never co-mingle cardholder data with PHI systems or audit stores

---

## Compliance Checklist

- [ ] All PHI access logged (view, create, update, delete)
- [ ] Failed access attempts logged
- [ ] Authentication events logged
- [ ] IP address captured when available
- [ ] User agent captured when available
- [ ] Purpose-of-use and patient_id captured for PHI access
- [ ] Timestamps in UTC
- [ ] Clocks NTP-synced with drift alerting
- [ ] 6+ year retention configured
- [ ] Retention + destruction policy implemented and logged
- [ ] Audit log immutability enforced
- [ ] Break-glass usage reviewed within 24 hours
- [ ] Regular compliance audits scheduled
- [ ] Breach response playbook tested (tabletop/annual)
- [ ] Export/Info Blocking events monitored with anomaly alerts

---

## Related Documentation

- [Audit Logging](../product/audit_logging.md)
- [Authorization System](../product/authorization_system.md)
- [Authentication](../product/authentication.md)

---

**Last Updated**: 2025-12-01  
**Supersedes**: none  
**Referenced by**: ../README.md, ../product/audit_logging.md
