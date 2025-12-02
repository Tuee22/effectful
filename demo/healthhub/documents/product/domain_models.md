# HealthHub Domain Models

> Extends base [Documentation Standards](../../../../documents/documentation_standards.md) and [Architecture](../../../../documents/engineering/architecture.md); base rules apply. HealthHub-specific domain model deltas only.

---

## Overview

All domain models in HealthHub follow these principles:

1. **Immutability**: All dataclasses use `frozen=True`
2. **ADT Patterns**: Union types for mutually exclusive states
3. **Type Safety**: No `Any`, `cast()`, or `# type: ignore`
4. **Explicit Fields**: All fields have explicit types

---

## Core Entities

### Patient

Medical patient with demographics and health information.

**Location**: `backend/app/domain/patient.py`

```python
@dataclass(frozen=True)
class Patient:
    """Patient entity with medical demographics."""

    id: UUID
    user_id: UUID
    first_name: str
    last_name: str
    date_of_birth: date
    blood_type: str | None
    allergies: list[str]
    insurance_id: str | None
    emergency_contact: str
    phone: str | None
    address: str | None
    created_at: datetime
    updated_at: datetime
```

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| user_id | UUID | Associated user account |
| first_name | str | Patient first name |
| last_name | str | Patient last name |
| date_of_birth | date | DOB for age calculations |
| blood_type | str or None | Blood type (A+, B-, O+, etc.) |
| allergies | list[str] | Known allergies |
| insurance_id | str or None | Insurance policy ID |
| emergency_contact | str | Emergency contact info |
| phone | str or None | Phone number |
| address | str or None | Mailing address |
| created_at | datetime | Record creation timestamp |
| updated_at | datetime | Last update timestamp |

---

### Doctor

Medical professional with credentials and prescribing authority.

**Location**: `backend/app/domain/doctor.py`

```python
@dataclass(frozen=True)
class Doctor:
    """Doctor entity with credentials."""

    id: UUID
    user_id: UUID
    first_name: str
    last_name: str
    specialization: str
    license_number: str
    can_prescribe: bool
    phone: str | None
    created_at: datetime
    updated_at: datetime
```

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| user_id | UUID | Associated user account |
| first_name | str | Doctor first name |
| last_name | str | Doctor last name |
| specialization | str | Medical specialty |
| license_number | str | State medical license |
| can_prescribe | bool | Prescribing authority flag |
| phone | str or None | Contact number |
| created_at | datetime | Record creation timestamp |
| updated_at | datetime | Last update timestamp |

**Specializations**: Internal Medicine, Cardiology, Neurology, Orthopedics, etc.

---

### Appointment

Patient-doctor appointment with state machine status.

**Location**: `backend/app/domain/appointment.py`

```python
@dataclass(frozen=True)
class Appointment:
    """Appointment entity with state machine."""

    id: UUID
    patient_id: UUID
    doctor_id: UUID
    status: AppointmentStatus
    reason: str
    created_at: datetime
    updated_at: datetime
```

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| patient_id | UUID | Patient requesting appointment |
| doctor_id | UUID | Doctor being requested |
| status | AppointmentStatus | ADT status (see State Machine) |
| reason | str | Reason for visit |
| created_at | datetime | Record creation timestamp |
| updated_at | datetime | Last update timestamp |

See [Appointment State Machine](appointment_state_machine.md) for status details.

---

### Prescription

Medication order with dosage and refill tracking.

**Location**: `backend/app/domain/prescription.py`

```python
@dataclass(frozen=True)
class Prescription:
    """Prescription entity."""

    id: UUID
    patient_id: UUID
    doctor_id: UUID
    medication: str
    dosage: str
    frequency: str
    duration_days: int
    refills_remaining: int
    notes: str | None
    created_at: datetime
    expires_at: datetime
```

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| patient_id | UUID | Patient receiving medication |
| doctor_id | UUID | Prescribing physician |
| medication | str | Drug name |
| dosage | str | Dose (e.g., "500mg") |
| frequency | str | How often (e.g., "twice daily") |
| duration_days | int | Treatment duration |
| refills_remaining | int | Number of refills left |
| notes | str or None | Special instructions |
| created_at | datetime | Prescription date |
| expires_at | datetime | Expiration date |

See [Medication Interactions](medication_interactions.md) for drug interaction checking.

---

### LabResult

Laboratory test result with critical value flagging.

**Location**: `backend/app/domain/lab_result.py`

```python
@dataclass(frozen=True)
class LabResult:
    """Lab test result entity."""

    id: UUID
    patient_id: UUID
    doctor_id: UUID
    test_type: str
    result_data: dict[str, str]
    critical: bool
    reviewed_by_doctor: bool
    doctor_notes: str | None
    created_at: datetime
```

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| patient_id | UUID | Patient tested |
| doctor_id | UUID | Ordering physician |
| test_type | str | Test category (CBC, BMP, etc.) |
| result_data | dict[str, str] | Test-specific values |
| critical | bool | Requires immediate attention |
| reviewed_by_doctor | bool | Doctor has reviewed |
| doctor_notes | str or None | Doctor comments |
| created_at | datetime | Result timestamp |

**Test Types**: Complete Blood Count (CBC), Basic Metabolic Panel (BMP), Lipid Panel, Hemoglobin A1C, Urinalysis, etc.

---

### Invoice

Healthcare billing with line items.

**Location**: `backend/app/domain/invoice.py`

```python
@dataclass(frozen=True)
class Invoice:
    """Healthcare invoice entity."""

    id: UUID
    patient_id: UUID
    appointment_id: UUID | None
    status: Literal["draft", "sent", "paid", "overdue"]
    subtotal: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    due_date: date | None
    paid_at: datetime | None
    created_at: datetime
    updated_at: datetime

@dataclass(frozen=True)
class LineItem:
    """Invoice line item."""

    id: UUID
    invoice_id: UUID
    description: str
    quantity: int
    unit_price: Decimal
    total: Decimal
    created_at: datetime
```

| Invoice Field | Type | Description |
|---------------|------|-------------|
| status | Literal | draft, sent, paid, overdue |
| subtotal | Decimal | Sum of line items |
| tax_amount | Decimal | Applied taxes |
| total_amount | Decimal | Final amount due |
| due_date | date or None | Payment due date |
| paid_at | datetime or None | Payment timestamp |

---

## ADT Types

### AppointmentStatus

State machine for appointment lifecycle.

```python
type AppointmentStatus = (
    Requested
    | Confirmed
    | InProgress
    | Completed
    | Cancelled
)
```

Each variant carries context-specific data:

```python
@dataclass(frozen=True)
class Requested:
    requested_at: datetime

@dataclass(frozen=True)
class Confirmed:
    confirmed_at: datetime
    scheduled_time: datetime

@dataclass(frozen=True)
class InProgress:
    started_at: datetime

@dataclass(frozen=True)
class Completed:
    completed_at: datetime
    notes: str

@dataclass(frozen=True)
class Cancelled:
    cancelled_at: datetime
    cancelled_by: Literal["patient", "doctor", "system"]
    reason: str
```

---

### MedicationCheckResult

Result of drug interaction check.

```python
type MedicationCheckResult = NoInteractions | MedicationInteractionWarning
```

```python
@dataclass(frozen=True)
class NoInteractions:
    """No medication interactions detected."""
    medications_checked: list[str]

@dataclass(frozen=True)
class MedicationInteractionWarning:
    """Warning about drug interactions."""
    medications: list[str]
    severity: Literal["minor", "moderate", "severe"]
    description: str
```

---

### TransitionResult

Result of appointment status transition.

```python
type TransitionResult = TransitionSuccess | TransitionInvalid
```

```python
@dataclass(frozen=True)
class TransitionSuccess:
    """Valid state transition."""
    new_status: AppointmentStatus

@dataclass(frozen=True)
class TransitionInvalid:
    """Invalid state transition."""
    current_status: str
    attempted_status: str
    reason: str
```

---

### LabResultLookupResult

Result of lab result lookup.

```python
type LabResultLookupResult = LabResultFound | LabResultNotFound
```

```python
@dataclass(frozen=True)
class LabResultFound:
    lab_result: LabResult

@dataclass(frozen=True)
class LabResultNotFound:
    result_id: UUID
    reason: str
```

---

## Pattern Matching Examples

### Handling AppointmentStatus

```python
def get_status_display(status: AppointmentStatus) -> str:
    match status:
        case Requested(requested_at=ts):
            return f"Requested at {ts.isoformat()}"

        case Confirmed(scheduled_time=ts):
            return f"Confirmed for {ts.isoformat()}"

        case InProgress(started_at=ts):
            return f"Started at {ts.isoformat()}"

        case Completed(notes=notes):
            return f"Completed: {notes}"

        case Cancelled(reason=reason, cancelled_by=by):
            return f"Cancelled by {by}: {reason}"
```

### Handling MedicationCheckResult

```python
def process_interaction_check(result: MedicationCheckResult) -> bool:
    match result:
        case NoInteractions():
            return True  # Safe to prescribe

        case MedicationInteractionWarning(severity="severe"):
            return False  # Block prescription

        case MedicationInteractionWarning(severity="moderate" | "minor"):
            return True  # Allow with warning
```

---

## Related Documentation

### Domain Knowledge
- [Medical State Machines](../domain/medical_state_machines.md) - Healthcare state machine patterns for all workflows

### Best Practices
- [State Machine Patterns](../engineering/state_machine_patterns.md) - ADT-based state machine implementation

### Product Documentation
- [Appointment State Machine](appointment_state_machine.md) - Appointment status transitions and validation
- [Authorization System](authorization_system.md) - User roles and access control ADTs
- [Effects Reference](effects_reference.md) - Effects that operate on domain models
- [Database Schema](database_schema.md) - How models map to database tables

---

**Last Updated**: 2025-11-26  
**Supersedes**: none  
**Referenced by**: ../README.md, ../engineering/code_quality.md
**Maintainer**: HealthHub Team
