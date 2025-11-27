# Healthcare Effects Reference

> Complete API reference for all healthcare and notification effects.

---

## Overview

Effects are immutable dataclasses that describe operations without executing them. This separation enables:

- **Testability**: Step through programs without real infrastructure
- **Composability**: Chain effects in generator-based programs
- **Type Safety**: Explicit types for all parameters and results

**Locations**:
- `backend/app/effects/healthcare.py` - Healthcare operations
- `backend/app/effects/notification.py` - Notifications and audit

---

## Effect Categories

| Category | Effects | Interpreter |
|----------|---------|-------------|
| Healthcare | Patient, Doctor, Appointment, Prescription, Lab, Invoice | HealthcareInterpreter |
| Notification | WebSocket publish, Audit logging | NotificationInterpreter |

---

## Healthcare Effects

### GetPatientById

Fetch a patient by their unique identifier.

```python
@dataclass(frozen=True)
class GetPatientById:
    """Effect: Fetch patient by ID."""
    patient_id: UUID
```

**Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| patient_id | UUID | Patient unique identifier |

**Returns**: `Patient | None`

**Usage**:
```python
patient = yield GetPatientById(patient_id=patient_id)
if isinstance(patient, Patient):
    # Use patient
```

---

### GetDoctorById

Fetch a doctor by their unique identifier.

```python
@dataclass(frozen=True)
class GetDoctorById:
    """Effect: Fetch doctor by ID."""
    doctor_id: UUID
```

**Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| doctor_id | UUID | Doctor unique identifier |

**Returns**: `Doctor | None`

**Usage**:
```python
doctor = yield GetDoctorById(doctor_id=doctor_id)
if isinstance(doctor, Doctor):
    # Check prescribing authority
    if doctor.can_prescribe:
        ...
```

---

### CreateAppointment

Create a new appointment request.

```python
@dataclass(frozen=True)
class CreateAppointment:
    """Effect: Create new appointment request."""
    patient_id: UUID
    doctor_id: UUID
    requested_time: datetime | None
    reason: str
```

**Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| patient_id | UUID | Patient requesting appointment |
| doctor_id | UUID | Doctor being requested |
| requested_time | datetime or None | Preferred time (optional) |
| reason | str | Reason for visit |

**Returns**: `Appointment` (in Requested status)

**Usage**:
```python
appointment = yield CreateAppointment(
    patient_id=patient_id,
    doctor_id=doctor_id,
    requested_time=datetime.now(UTC) + timedelta(days=7),
    reason="Annual checkup",
)
```

---

### GetAppointmentById

Fetch an appointment by its unique identifier.

```python
@dataclass(frozen=True)
class GetAppointmentById:
    """Effect: Fetch appointment by ID."""
    appointment_id: UUID
```

**Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| appointment_id | UUID | Appointment unique identifier |

**Returns**: `Appointment | None`

---

### TransitionAppointmentStatus

Transition an appointment to a new status with validation.

```python
@dataclass(frozen=True)
class TransitionAppointmentStatus:
    """Effect: Transition appointment to new status."""
    appointment_id: UUID
    new_status: AppointmentStatus
    actor_id: UUID
```

**Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| appointment_id | UUID | Appointment to transition |
| new_status | AppointmentStatus | Target status |
| actor_id | UUID | User performing transition |

**Returns**: `TransitionSuccess | TransitionInvalid`

**Usage**:
```python
result = yield TransitionAppointmentStatus(
    appointment_id=appointment_id,
    new_status=Confirmed(
        confirmed_at=datetime.now(UTC),
        scheduled_time=scheduled_time,
    ),
    actor_id=doctor_id,
)

match result:
    case TransitionSuccess(new_status=status):
        # Transition succeeded
    case TransitionInvalid(reason=reason):
        # Transition blocked
```

---

### CreatePrescription

Create a new prescription order.

```python
@dataclass(frozen=True)
class CreatePrescription:
    """Effect: Create prescription order."""
    patient_id: UUID
    doctor_id: UUID
    medication: str
    dosage: str
    frequency: str
    duration_days: int
    refills_remaining: int
    notes: str | None
```

**Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| patient_id | UUID | Patient receiving medication |
| doctor_id | UUID | Prescribing physician |
| medication | str | Drug name |
| dosage | str | Dose (e.g., "500mg") |
| frequency | str | How often (e.g., "twice daily") |
| duration_days | int | Treatment duration |
| refills_remaining | int | Number of refills |
| notes | str or None | Special instructions |

**Returns**: `Prescription`

**Note**: Only doctors with `can_prescribe=True` should use this effect.

---

### CheckMedicationInteractions

Check for drug interactions between medications.

```python
@dataclass(frozen=True)
class CheckMedicationInteractions:
    """Effect: Check for drug interactions."""
    medications: list[str]
```

**Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| medications | list[str] | List of drug names to check |

**Returns**: `NoInteractions | MedicationInteractionWarning`

**Usage**:
```python
result = yield CheckMedicationInteractions(
    medications=["Aspirin", "Warfarin"]
)

match result:
    case NoInteractions():
        # Safe to prescribe
    case MedicationInteractionWarning(severity="severe"):
        # Block prescription
    case MedicationInteractionWarning(severity="moderate"):
        # Allow with warning
```

---

### CreateLabResult

Store a new lab test result.

```python
@dataclass(frozen=True)
class CreateLabResult:
    """Effect: Store lab result."""
    result_id: UUID
    patient_id: UUID
    doctor_id: UUID
    test_type: str
    result_data: dict[str, str]
    critical: bool
```

**Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| result_id | UUID | Result unique identifier |
| patient_id | UUID | Patient tested |
| doctor_id | UUID | Ordering physician |
| test_type | str | Test category (CBC, BMP, etc.) |
| result_data | dict[str, str] | Test-specific values |
| critical | bool | Requires immediate attention |

**Returns**: `LabResult`

---

### GetLabResultById

Fetch a lab result by its unique identifier.

```python
@dataclass(frozen=True)
class GetLabResultById:
    """Effect: Fetch lab result by ID."""
    result_id: UUID
```

**Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| result_id | UUID | Lab result unique identifier |

**Returns**: `LabResult | None`

---

### CreateInvoice

Generate a healthcare invoice.

```python
@dataclass(frozen=True)
class CreateInvoice:
    """Effect: Generate invoice."""
    patient_id: UUID
    appointment_id: UUID | None
    line_items: list[LineItem]
    due_date: date | None
```

**Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| patient_id | UUID | Patient being billed |
| appointment_id | UUID or None | Related appointment |
| line_items | list[LineItem] | Billing line items |
| due_date | date or None | Payment due date |

**Returns**: `Invoice`

---

## Notification Effects

### PublishWebSocketNotification

Publish real-time notification via Redis pub/sub.

```python
@dataclass(frozen=True)
class PublishWebSocketNotification:
    """Effect: Publish ephemeral notification via Redis pub/sub."""
    channel: str
    message: dict[str, str | int | bool]
    recipient_id: UUID | None
```

**Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| channel | str | Redis pub/sub channel |
| message | dict | Notification payload |
| recipient_id | UUID or None | Target user (None = broadcast) |

**Returns**: `NotificationPublished | PublishFailed`

**Channel Patterns**:
- `doctor:{doctor_id}:notifications` - Doctor-specific
- `patient:{patient_id}:notifications` - Patient-specific
- `system:alerts` - System-wide broadcasts

---

### LogAuditEvent

Store HIPAA-compliant audit event.

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

**Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| user_id | UUID | User performing action |
| action | str | Action performed |
| resource_type | str | Resource category |
| resource_id | UUID | Affected resource |
| ip_address | str or None | Client IP |
| user_agent | str or None | Client browser/agent |
| metadata | dict or None | Additional context |

**Returns**: `AuditEventLogged`

**Common Actions**:
- `view_patient` - Viewing patient record
- `create_appointment` - Creating appointment
- `transition_appointment_status` - Status change
- `create_prescription` - Writing prescription
- `view_lab_result` - Accessing lab results

---

## Effect Union Types

### AllEffects

Complete union of all effects for program type signatures.

```python
type AllEffects = HealthcareEffect | NotificationEffect
```

### HealthcareEffect

Union of healthcare-specific effects.

```python
type HealthcareEffect = (
    GetPatientById
    | GetDoctorById
    | CreateAppointment
    | GetAppointmentById
    | TransitionAppointmentStatus
    | CreatePrescription
    | CheckMedicationInteractions
    | CreateLabResult
    | GetLabResultById
    | CreateInvoice
)
```

### NotificationEffect

Union of notification effects.

```python
type NotificationEffect = PublishWebSocketNotification | LogAuditEvent
```

---

## Result Types

### TransitionResult

```python
type TransitionResult = TransitionSuccess | TransitionInvalid
```

### MedicationCheckResult

```python
type MedicationCheckResult = NoInteractions | MedicationInteractionWarning
```

### PublishResult

```python
type PublishResult = NotificationPublished | PublishFailed
```

---

## Related Documentation

### Best Practices
- [Effect Program Patterns](../best_practices/effect_program_patterns.md) - How to use effects in programs (yield, type narrowing, composition)
- [Testing Doctrine](../best_practices/testing_doctrine.md) - Testing effect programs with generator stepping

### Product Documentation
- [Architecture Overview](architecture_overview.md) - How effects fit in the 5-layer architecture
- [Domain Models](domain_models.md) - Entity definitions returned by effects
- [Audit Logging](audit_logging.md) - LogAuditEvent effect for HIPAA compliance
- [Appointment State Machine](appointment_state_machine.md) - Appointment-related effects
- [Messaging Infrastructure](messaging_infrastructure.md) - PublishWebSocketNotification effect

---

**Last Updated**: 2025-11-26
**Maintainer**: HealthHub Team
