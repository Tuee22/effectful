# Audit Logging

> HIPAA-compliant audit logging for healthcare data access.

---

## Overview

HealthHub implements comprehensive audit logging for HIPAA compliance. Every access to Protected Health Information (PHI) is logged with full context.

**Requirement**: All operations involving patient data must be logged, including:
- Successful access
- Failed access attempts
- Modifications to records

---

## LogAuditEvent Effect

```python
@dataclass(frozen=True)
class LogAuditEvent:
    """Effect: Store audit event for HIPAA compliance."""
    user_id: UUID
    action: str
    resource_type: str
    resource_id: UUID
    ip_address: str | None
    user_agent: str | None
    metadata: dict[str, str] | None
```

| Field | Type | Description |
|-------|------|-------------|
| user_id | UUID | User performing the action |
| action | str | Action performed |
| resource_type | str | Type of resource accessed |
| resource_id | UUID | Specific resource ID |
| ip_address | str or None | Client IP address |
| user_agent | str or None | Client browser/application |
| metadata | dict or None | Additional context |

### Result Type

```python
@dataclass(frozen=True)
class AuditEventLogged:
    """Audit event successfully stored."""
    event_id: UUID
    logged_at: datetime
```

---

## Audit Actions

### Patient Access

| Action | Description |
|--------|-------------|
| `view_patient` | Viewing patient demographics |
| `create_patient` | Creating new patient record |
| `update_patient` | Modifying patient information |

### Appointment Actions

| Action | Description |
|--------|-------------|
| `create_appointment` | Scheduling new appointment |
| `view_appointment` | Viewing appointment details |
| `transition_appointment_status` | Changing appointment status |
| `cancel_appointment` | Cancelling appointment |

### Prescription Actions

| Action | Description |
|--------|-------------|
| `create_prescription` | Writing new prescription |
| `view_prescription` | Viewing prescription details |
| `refill_prescription` | Processing refill request |

### Lab Result Actions

| Action | Description |
|--------|-------------|
| `create_lab_result` | Recording new lab result |
| `view_lab_result` | Viewing lab result |
| `review_lab_result` | Doctor reviewing result |
| `acknowledge_critical` | Acknowledging critical value |

### Authentication Actions

| Action | Description |
|--------|-------------|
| `login_success` | Successful authentication |
| `login_failure` | Failed authentication attempt |
| `logout` | User logout |
| `token_refresh` | Token renewal |
| `password_change` | Password modification |

---

## Usage in Effect Programs

### Standard Audit Pattern

```python
def view_patient_record_program(
    patient_id: UUID,
    actor_id: UUID,
    ip_address: str | None,
    user_agent: str | None,
) -> Generator[AllEffects, object, Patient | None]:
    # Fetch the patient
    patient = yield GetPatientById(patient_id=patient_id)

    if not isinstance(patient, Patient):
        # Log failed access attempt
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

    # Log successful access
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
```

### Appointment Status Change

```python
def transition_appointment_program(
    appointment_id: UUID,
    new_status: AppointmentStatus,
    actor_id: UUID,
) -> Generator[AllEffects, object, TransitionResult]:
    appointment = yield GetAppointmentById(appointment_id=appointment_id)

    if not isinstance(appointment, Appointment):
        return TransitionInvalid(...)

    result = yield TransitionAppointmentStatus(
        appointment_id=appointment_id,
        new_status=new_status,
        actor_id=actor_id,
    )

    # Log the transition attempt
    yield LogAuditEvent(
        user_id=actor_id,
        action="transition_appointment_status",
        resource_type="appointment",
        resource_id=appointment_id,
        ip_address=None,
        user_agent=None,
        metadata={
            "old_status": type(appointment.status).__name__,
            "new_status": type(new_status).__name__,
            "result": "success" if isinstance(result, TransitionSuccess) else "invalid",
        },
    )

    return result
```

---

## Database Schema

```sql
CREATE TABLE audit_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id UUID NOT NULL,
    ip_address INET,
    user_agent TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX idx_audit_events_user_id ON audit_events(user_id);
CREATE INDEX idx_audit_events_resource ON audit_events(resource_type, resource_id);
CREATE INDEX idx_audit_events_action ON audit_events(action);
CREATE INDEX idx_audit_events_created_at ON audit_events(created_at);
```

---

## HIPAA Compliance Requirements

### What Must Be Logged

1. **PHI Access**: Any view, create, update, or delete of patient data
2. **Authentication**: Login attempts (success and failure)
3. **Authorization Changes**: Role modifications, permission grants
4. **Export/Download**: Any bulk data access or export
5. **System Access**: Administrative actions

### Required Fields

| Field | HIPAA Requirement |
|-------|-------------------|
| user_id | Identity of person accessing data |
| action | Type of activity performed |
| resource_id | Specific record accessed |
| timestamp | Date and time of access |
| ip_address | Source of access (when available) |

### Retention

- Minimum 6 years retention required by HIPAA
- Configure database backup and archival accordingly
- Consider partitioning by date for large-scale deployments

---

## Interpreter Implementation

```python
class NotificationInterpreter:
    async def handle(self, effect: NotificationEffect) -> object:
        match effect:
            case LogAuditEvent(
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata=metadata,
            ):
                event_id = uuid4()
                now = datetime.now(timezone.utc)

                await self.pool.execute(
                    """
                    INSERT INTO audit_events
                    (id, user_id, action, resource_type, resource_id,
                     ip_address, user_agent, metadata, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    """,
                    event_id,
                    user_id,
                    action,
                    resource_type,
                    resource_id,
                    ip_address,
                    user_agent,
                    json.dumps(metadata) if metadata else None,
                    now,
                )

                return AuditEventLogged(
                    event_id=event_id,
                    logged_at=now,
                )
```

---

## Querying Audit Logs

### By User

```sql
SELECT * FROM audit_events
WHERE user_id = $1
ORDER BY created_at DESC
LIMIT 100;
```

### By Resource

```sql
SELECT * FROM audit_events
WHERE resource_type = 'patient'
  AND resource_id = $1
ORDER BY created_at DESC;
```

### By Date Range

```sql
SELECT * FROM audit_events
WHERE created_at BETWEEN $1 AND $2
  AND action = 'view_patient'
ORDER BY created_at;
```

### Failed Access Attempts

```sql
SELECT * FROM audit_events
WHERE metadata->>'status' = 'not_found'
   OR metadata->>'status' = 'unauthorized'
ORDER BY created_at DESC;
```

---

## Anti-Patterns

### Log Only Success (Wrong)

```python
# WRONG - Doesn't log failed attempts
patient = yield GetPatientById(patient_id)
if isinstance(patient, Patient):
    yield LogAuditEvent(...)  # Only logs success
```

### Missing Context (Wrong)

```python
# WRONG - No IP address or user agent
yield LogAuditEvent(
    user_id=actor_id,
    action="view_patient",
    resource_type="patient",
    resource_id=patient_id,
    ip_address=None,  # Should capture from request
    user_agent=None,  # Should capture from request
    metadata=None,
)
```

### Blocking on Audit Failure (Wrong)

```python
# WRONG - Audit failure shouldn't block business logic
result = yield LogAuditEvent(...)
if not isinstance(result, AuditEventLogged):
    raise Exception("Audit failed")  # Don't do this
```

---

## Testing

```python
def test_audit_event_logged() -> None:
    gen = view_patient_program(patient_id, actor_id, "192.168.1.1", "Mozilla/5.0")

    # Step to GetPatientById
    effect = next(gen)
    assert isinstance(effect, GetPatientById)

    # Send patient, expect audit log
    effect = gen.send(mock_patient)
    assert isinstance(effect, LogAuditEvent)
    assert effect.action == "view_patient"
    assert effect.resource_id == patient_id
    assert effect.ip_address == "192.168.1.1"
```

---

## Related Documentation

### Domain Knowledge
- [HIPAA Compliance](../domain/hipaa_compliance.md) - Legal requirements for audit logging of PHI access

### Best Practices
- [Effect Program Patterns](../best_practices/effect_program_patterns.md) - Audit logging pattern for effect programs

### Product Documentation
- [Authorization System](authorization_system.md) - Access control and user identification
- [Effects Reference](effects_reference.md) - LogAuditEvent effect
- [Authentication](authentication.md) - Login/logout audit events

---

**Last Updated**: 2025-11-26
**Maintainer**: HealthHub Team
