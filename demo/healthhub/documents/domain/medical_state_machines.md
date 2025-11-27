# Medical State Machines

> General state machine patterns for healthcare workflows.

---

## Overview

Healthcare applications require robust state machines to manage complex medical workflows. This domain knowledge applies to any healthcare system managing patient care, prescriptions, lab results, or billing.

**Why This Matters**: Proper state machine design ensures:
- **Patient Safety**: Only valid state transitions occur (e.g., can't complete appointment before confirming)
- **Legal Compliance**: Complete audit trail for HIPAA and billing regulations
- **Data Integrity**: State-specific context captured (prescription dosage, lab results, billing amounts)
- **Business Rules**: Medical domain constraints enforced (e.g., doctor-only transitions)

---

## Healthcare State Machine Principles

### 1. Terminal State Immutability

Medical records in terminal states must never change once reached.

**Rationale**: Legal requirements for audit trails, billing disputes, malpractice protection.

**Examples**:
- Completed appointments (medical notes are permanent records)
- Paid invoices (financial records for tax compliance)
- Reviewed lab results (medical decisions based on results)

```python
def is_terminal(status: MedicalStatus) -> bool:
    """Terminal states allow no further transitions."""
    match status:
        case AppointmentCompleted() | AppointmentCancelled():
            return True
        case PrescriptionExpired() | PrescriptionCancelled():
            return True
        case LabResultReviewed():
            return True
        case InvoicePaid() | InvoiceVoided():
            return True
        case _:
            return False
```

---

### 2. State-Specific Context

Each state variant carries only the data relevant to that state.

**Medical Rationale**: Prevents invalid data combinations (e.g., completed_at timestamp when state is Requested).

```python
# GOOD - Each state has its own context
@dataclass(frozen=True)
class PrescriptionPending:
    """Awaiting pharmacy approval."""
    prescribed_at: datetime
    prescribed_by: UUID  # doctor_id

@dataclass(frozen=True)
class PrescriptionActive:
    """Patient can fill prescription."""
    prescribed_at: datetime
    prescribed_by: UUID
    approved_at: datetime  # Only active has approval
    approved_by: UUID      # pharmacist_id
    expiry_date: datetime  # Prescriptions expire

@dataclass(frozen=True)
class PrescriptionCompleted:
    """Patient filled prescription."""
    prescribed_at: datetime
    prescribed_by: UUID
    approved_at: datetime
    filled_at: datetime    # Only completed has fill timestamp
    filled_by: UUID        # pharmacist_id
    pharmacy_id: UUID

type PrescriptionStatus = (
    PrescriptionPending
    | PrescriptionActive
    | PrescriptionCompleted
    | PrescriptionExpired
    | PrescriptionCancelled
)
```

---

### 3. Transition Validation

All state transitions must be explicitly validated against medical domain rules.

**Medical Rationale**: Prevents dangerous scenarios (e.g., dispensing medication before doctor approval).

```python
@dataclass(frozen=True)
class TransitionSuccess:
    """Valid transition."""
    new_status: PrescriptionStatus

@dataclass(frozen=True)
class TransitionInvalid:
    """Invalid transition with reason."""
    current_status: str
    attempted_status: str
    reason: str

type TransitionResult = TransitionSuccess | TransitionInvalid

def validate_prescription_transition(
    current: PrescriptionStatus,
    new: PrescriptionStatus,
) -> TransitionResult:
    """Validate prescription state transitions."""
    match (current, new):
        # Pending → Active (pharmacist approval)
        case (PrescriptionPending(), PrescriptionActive()):
            return TransitionSuccess(new_status=new)

        # Pending → Cancelled (doctor cancels before approval)
        case (PrescriptionPending(), PrescriptionCancelled()):
            return TransitionSuccess(new_status=new)

        # Active → Completed (patient fills)
        case (PrescriptionActive(), PrescriptionCompleted()):
            return TransitionSuccess(new_status=new)

        # Active → Expired (time-based transition)
        case (PrescriptionActive(), PrescriptionExpired()):
            return TransitionSuccess(new_status=new)

        # Active → Cancelled (doctor recalls prescription)
        case (PrescriptionActive(), PrescriptionCancelled()):
            return TransitionSuccess(new_status=new)

        # Invalid - all other transitions
        case _:
            return TransitionInvalid(
                current_status=type(current).__name__,
                attempted_status=type(new).__name__,
                reason=f"Invalid prescription transition from {type(current).__name__} to {type(new).__name__}",
            )
```

---

### 4. Role-Based Transition Authority

Different healthcare roles have different transition permissions.

**Medical Rationale**: Only licensed professionals can perform certain actions (prescribing, diagnosing, billing).

```python
def can_perform_transition(
    current: PrescriptionStatus,
    new: PrescriptionStatus,
    user_role: Literal["doctor", "pharmacist", "patient"],
) -> bool:
    """Check if user role can perform transition."""
    match (current, new, user_role):
        # Only doctors can cancel prescriptions
        case (_, PrescriptionCancelled(), "doctor"):
            return True

        # Only pharmacists can approve (Pending → Active)
        case (PrescriptionPending(), PrescriptionActive(), "pharmacist"):
            return True

        # Only pharmacists can dispense (Active → Completed)
        case (PrescriptionActive(), PrescriptionCompleted(), "pharmacist"):
            return True

        # System (automated) can expire prescriptions
        case (PrescriptionActive(), PrescriptionExpired(), "system"):
            return True

        case _:
            return False
```

---

## Common Medical Workflows

Healthcare applications typically manage 4-6 core state machines:

### Appointment Lifecycle

```
Requested → Confirmed → InProgress → Completed
    ↓           ↓           ↓
 Cancelled  Cancelled   Cancelled
```

**Domain Knowledge**: See [Appointment Workflows](appointment_workflows.md) for complete medical context, validation rules, and HIPAA requirements.

**Key States**:
- **Requested**: Patient request awaiting doctor confirmation
- **Confirmed**: Doctor committed time slot (scheduled_time set)
- **InProgress**: Visit currently happening (billing started)
- **Completed**: Visit finished with doctor notes (generates billable event)
- **Cancelled**: Cancelled by patient/doctor/system (may incur fees)

**Medical Implications**: Affects resource allocation (doctor schedules, exam rooms), billing (only completed appointments generate charges), legal compliance (audit trails required).

---

### Prescription Lifecycle

```
Pending → Active → Completed
           ↓
        Expired
    ↓           ↓
 Cancelled  Cancelled
```

**Key States**:
- **Pending**: Doctor prescribed, awaiting pharmacist approval
- **Active**: Approved by pharmacist, patient can fill
- **Completed**: Patient filled prescription at pharmacy
- **Expired**: Active prescription passed expiry date
- **Cancelled**: Recalled by doctor or cancelled by pharmacist

**Medical Implications**:
- **Drug Safety**: Pharmacist reviews drug interactions before approving
- **Legal**: DEA regulations for controlled substances (expiry after 90 days)
- **Billing**: Insurance claims only for completed prescriptions
- **Audit**: Every state transition logged for controlled substance tracking

**Time-Based Transition**: Active → Expired triggered by background job (not user action).

---

### Lab Result Workflow

```
Ordered → InProgress → Completed → Reviewed
    ↓          ↓
 Cancelled  Cancelled
```

**Key States**:
- **Ordered**: Doctor ordered lab test
- **InProgress**: Lab technician processing sample
- **Completed**: Results available, awaiting doctor review
- **Reviewed**: Doctor reviewed and acknowledged results
- **Cancelled**: Test cancelled before completion

**Medical Implications**:
- **Critical Value Alerts**: Completed → Reviewed requires immediate doctor notification for critical values (e.g., glucose > 400 mg/dL)
- **Patient Safety**: Patients cannot see results until Reviewed (doctor must interpret first)
- **Billing**: Only completed tests generate charges
- **Audit**: Review timestamps required for malpractice defense

**Critical Value Handling**:
```python
@dataclass(frozen=True)
class LabResultCompleted:
    """Lab results available."""
    completed_at: datetime
    results: dict[str, float]
    is_critical: bool  # Triggers urgent doctor notification

    def requires_urgent_review(self) -> bool:
        """Critical values require immediate doctor review."""
        return self.is_critical
```

---

### Invoice Workflow

```
Draft → Sent → Paid
          ↓      ↓
       Overdue  Voided
```

**Key States**:
- **Draft**: Invoice being created from completed appointments/prescriptions
- **Sent**: Invoice delivered to patient
- **Paid**: Payment received (terminal state)
- **Overdue**: Sent invoice past due date
- **Voided**: Invoice cancelled (refund, billing error)

**Medical Implications**:
- **Billing Accuracy**: Only services in terminal states (Completed appointments, filled prescriptions) can be billed
- **Insurance**: Draft → Sent triggers insurance claim submission
- **Collections**: Overdue triggers reminder notifications, potential collections
- **Audit**: Paid/Voided invoices are permanent records for tax compliance

**Time-Based Transition**: Sent → Overdue triggered by background job checking due_date.

---

## ADT Design Patterns

### Pattern 1: State-Specific Fields

Each state variant should only include fields relevant to that state.

```python
# GOOD - Only Active has expiry_date
@dataclass(frozen=True)
class PrescriptionActive:
    prescribed_at: datetime
    approved_at: datetime
    expiry_date: datetime  # Only relevant when active

# BAD - All states have expiry_date even when meaningless
@dataclass
class Prescription:
    status: str
    expiry_date: datetime | None  # None for most states
```

**Healthcare Benefit**: Impossible to access expiry_date when prescription is Pending (type error).

---

### Pattern 2: Transition Result ADT

Never raise exceptions for invalid transitions. Return explicit result type.

```python
@dataclass(frozen=True)
class TransitionSuccess:
    new_status: MedicalStatus

@dataclass(frozen=True)
class TransitionInvalid:
    current_status: str
    attempted_status: str
    reason: str

type TransitionResult = TransitionSuccess | TransitionInvalid

# GOOD - Caller handles invalid transitions
result = validate_transition(current, new)
match result:
    case TransitionSuccess(new_status=status):
        # Update entity
        ...
    case TransitionInvalid(reason=reason):
        # Log error, notify user
        ...
```

**Healthcare Benefit**: Invalid transitions logged for audit without crashing critical systems.

---

### Pattern 3: Terminal State Detection

Provide utility to detect terminal states across all workflows.

```python
def is_terminal(status: MedicalStatus) -> bool:
    """Check if status allows no further transitions."""
    match status:
        # Appointments
        case AppointmentCompleted() | AppointmentCancelled():
            return True

        # Prescriptions
        case PrescriptionCompleted() | PrescriptionExpired() | PrescriptionCancelled():
            return True

        # Lab Results
        case LabResultReviewed() | LabResultCancelled():
            return True

        # Invoices
        case InvoicePaid() | InvoiceVoided():
            return True

        case _:
            return False
```

**Healthcare Benefit**: Prevents accidental modifications to permanent medical/financial records.

---

## Transition Validation

### Medical Domain Rules

State transitions must enforce healthcare-specific constraints:

**1. Sequential State Progression**
- Cannot skip required intermediate states
- Example: Cannot go Requested → Completed (must go through Confirmed → InProgress)

**2. Role-Based Authority**
- Only doctors can transition Requested → Confirmed (appointments)
- Only pharmacists can transition Pending → Active (prescriptions)
- Only doctors can transition Completed → Reviewed (lab results)

**3. Time-Based Constraints**
- Cannot mark appointment InProgress before scheduled_time
- Cannot fill prescription after expiry_date
- Cannot mark invoice Overdue before due_date

**4. Terminal State Protection**
- Completed, Cancelled, Paid, Voided states cannot transition to anything
- Enforced at type level: validate_transition returns TransitionInvalid

### Validation Function Template

```python
def validate_medical_transition(
    current: MedicalStatus,
    new: MedicalStatus,
    user_role: str,
    current_time: datetime,
) -> TransitionResult:
    """Validate state transition with medical domain rules."""

    # Rule 1: Terminal state check
    if is_terminal(current):
        return TransitionInvalid(
            current_status=type(current).__name__,
            attempted_status=type(new).__name__,
            reason="Cannot transition from terminal state",
        )

    # Rule 2: Role-based authority
    if not can_perform_transition(current, new, user_role):
        return TransitionInvalid(
            current_status=type(current).__name__,
            attempted_status=type(new).__name__,
            reason=f"Role '{user_role}' cannot perform this transition",
        )

    # Rule 3: Time-based constraints
    match (current, new):
        case (AppointmentConfirmed(scheduled_time=st), AppointmentInProgress()):
            if current_time < st:
                return TransitionInvalid(
                    current_status="Confirmed",
                    attempted_status="InProgress",
                    reason=f"Cannot start appointment before scheduled time {st}",
                )

    # Rule 4: Valid state machine transitions
    return validate_transition(current, new)
```

---

## Audit Logging Integration

Every state transition in a healthcare application must be logged for HIPAA compliance.

### Required Audit Fields

```python
@dataclass(frozen=True)
class StateTransitionAudit:
    """Audit log entry for state transition."""
    entity_type: Literal["appointment", "prescription", "lab_result", "invoice"]
    entity_id: UUID
    user_id: UUID
    user_role: str
    previous_status: str
    new_status: str
    transition_timestamp: datetime
    reason: str | None  # For cancellations
    ip_address: str
    user_agent: str
```

**HIPAA Requirement**: All state transitions involving Protected Health Information (PHI) must be logged with:
- Who performed the transition (user_id, user_role)
- When it occurred (transition_timestamp)
- What changed (previous_status → new_status)
- Why (reason, especially for cancellations)

See [HIPAA Compliance](hipaa_compliance.md) for complete audit logging requirements.

---

### Audit Logging Pattern

```python
def transition_with_audit(
    entity_id: UUID,
    entity_type: str,
    current_status: MedicalStatus,
    new_status: MedicalStatus,
    user_id: UUID,
    user_role: str,
    reason: str | None = None,
) -> Generator[AllEffects, EffectResult, TransitionResult]:
    """Perform state transition with audit logging."""

    # Validate transition
    result = validate_medical_transition(
        current=current_status,
        new=new_status,
        user_role=user_role,
        current_time=datetime.now(UTC),
    )

    # Log both successful and failed transitions
    audit_entry = StateTransitionAudit(
        entity_type=entity_type,
        entity_id=entity_id,
        user_id=user_id,
        user_role=user_role,
        previous_status=type(current_status).__name__,
        new_status=type(new_status).__name__,
        transition_timestamp=datetime.now(UTC),
        reason=reason,
        ip_address="...",
        user_agent="...",
    )

    # Log the audit entry (always, even for invalid transitions)
    yield LogAuditEntry(entry=audit_entry)

    # Return validation result
    return result
```

**Key Principle**: Log BOTH successful AND failed transitions. Failed transitions may indicate:
- Security issues (unauthorized access attempts)
- Training needs (users trying invalid workflows)
- System bugs (incorrect state machine implementation)

---

## Testing State Machines

### Complete Transition Matrix Testing

Test every valid and invalid transition for each workflow.

```python
def test_prescription_valid_transitions() -> None:
    """Test all valid prescription transitions."""
    valid_transitions = [
        (PrescriptionPending(...), PrescriptionActive(...)),
        (PrescriptionPending(...), PrescriptionCancelled(...)),
        (PrescriptionActive(...), PrescriptionCompleted(...)),
        (PrescriptionActive(...), PrescriptionExpired(...)),
        (PrescriptionActive(...), PrescriptionCancelled(...)),
    ]

    for current, new in valid_transitions:
        result = validate_prescription_transition(current, new)
        assert isinstance(result, TransitionSuccess), \
            f"Expected {current} → {new} to be valid"

def test_prescription_invalid_transitions() -> None:
    """Test all invalid prescription transitions."""
    invalid_transitions = [
        (PrescriptionPending(...), PrescriptionCompleted(...)),  # Skip approval
        (PrescriptionCompleted(...), PrescriptionCancelled(...)),  # Terminal
        (PrescriptionExpired(...), PrescriptionActive(...)),  # Terminal
    ]

    for current, new in invalid_transitions:
        result = validate_prescription_transition(current, new)
        assert isinstance(result, TransitionInvalid), \
            f"Expected {current} → {new} to be invalid"
```

---

### Role-Based Authority Testing

```python
def test_pharmacist_cannot_cancel_prescriptions() -> None:
    """Only doctors can cancel prescriptions."""
    current = PrescriptionActive(...)
    new = PrescriptionCancelled(...)

    # Pharmacist attempt
    assert not can_perform_transition(current, new, user_role="pharmacist")

    # Doctor attempt
    assert can_perform_transition(current, new, user_role="doctor")
```

---

### Time-Based Constraint Testing

```python
def test_cannot_start_appointment_before_scheduled_time() -> None:
    """Appointments cannot start before scheduled_time."""
    scheduled_time = datetime(2025, 1, 15, 10, 0, tzinfo=UTC)
    current = AppointmentConfirmed(
        confirmed_at=datetime(2025, 1, 14, 9, 0, tzinfo=UTC),
        scheduled_time=scheduled_time,
    )
    new = AppointmentInProgress(
        started_at=datetime(2025, 1, 15, 9, 0, tzinfo=UTC),  # 1 hour early
    )

    result = validate_medical_transition(
        current=current,
        new=new,
        user_role="doctor",
        current_time=datetime(2025, 1, 15, 9, 0, tzinfo=UTC),
    )

    assert isinstance(result, TransitionInvalid)
    assert "before scheduled time" in result.reason
```

---

## Related Documentation

### Domain Knowledge
- [Appointment Workflows](appointment_workflows.md) - Complete appointment lifecycle with medical context
- [HIPAA Compliance](hipaa_compliance.md) - Audit logging requirements for state transitions

### HealthHub Implementation
- [Appointment State Machine](../product/appointment_state_machine.md) - HealthHub appointment implementation
- [Domain Models](../product/domain_models.md) - Prescription, LabResult, Invoice models

### Best Practices
- [State Machine Patterns](../best_practices/state_machine_patterns.md) - Implementation patterns and anti-patterns
- [Effect Program Patterns](../best_practices/effect_program_patterns.md) - Using state machines in effect programs

---

**Last Updated**: 2025-11-26
**Maintainer**: HealthHub Team
