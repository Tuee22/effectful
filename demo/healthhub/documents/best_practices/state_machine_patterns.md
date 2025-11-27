# State Machine Patterns

> ADT-based state machine implementation patterns for HealthHub.

---

## Principle

State machines should make invalid transitions impossible through the type system.

**For healthcare domain context** (appointment workflows, medical requirements, HIPAA compliance), see [Medical State Machines](../domain/medical_state_machines.md).

This document focuses on **HOW to implement** state machines using ADTs in HealthHub.

---

## Patterns

### Pattern 1: ADT Status Types

Each state is a distinct type carrying state-specific data.

**Key Benefit**: Impossible to access fields that don't exist in current state (type error).

```python
# GOOD - Each state has its own context
@dataclass(frozen=True)
class EntityRequested:
    """Initial request state."""
    requested_at: datetime
    requested_by: UUID

@dataclass(frozen=True)
class EntityConfirmed:
    """Confirmed with scheduled time."""
    requested_at: datetime
    confirmed_at: datetime
    scheduled_time: datetime  # Only confirmed has scheduled time
    confirmed_by: UUID

@dataclass(frozen=True)
class EntityInProgress:
    """Currently being processed."""
    requested_at: datetime
    confirmed_at: datetime
    started_at: datetime

@dataclass(frozen=True)
class EntityCompleted:
    """Processing finished."""
    requested_at: datetime
    confirmed_at: datetime
    started_at: datetime
    completed_at: datetime
    notes: str  # Only completed has notes

@dataclass(frozen=True)
class EntityCancelled:
    """Cancelled before completion."""
    cancelled_at: datetime
    cancelled_by: UUID
    reason: str

type EntityStatus = (
    EntityRequested
    | EntityConfirmed
    | EntityInProgress
    | EntityCompleted
    | EntityCancelled
)
```

**Why `frozen=True`**: Immutability ensures states cannot be modified after creation (critical for audit trails).

---

### Pattern 2: Transition Result ADT

Return explicit success or failure instead of raising exceptions.

**Key Benefit**: Composable error handling, all paths visible to type checker.

```python
@dataclass(frozen=True)
class TransitionSuccess:
    """Valid transition occurred."""
    new_status: EntityStatus

@dataclass(frozen=True)
class TransitionInvalid:
    """Transition not allowed."""
    current_status: str
    attempted_status: str
    reason: str

type TransitionResult = TransitionSuccess | TransitionInvalid
```

**Usage**:
```python
result = validate_transition(current, new)
match result:
    case TransitionSuccess(new_status=status):
        # Update entity with new status
        updated_entity = replace(entity, status=status)
        yield UpdateEntity(entity=updated_entity)
        return updated_entity

    case TransitionInvalid(reason=reason):
        # Log error, return None
        yield LogError(message=f"Invalid transition: {reason}")
        return None
```

---

### Pattern 3: Validate Before Transition

Centralize transition validation in a single function using exhaustive pattern matching.

**Key Benefit**: All valid transitions visible in one place, easy to audit.

```python
def validate_transition(
    current: EntityStatus, new: EntityStatus
) -> TransitionResult:
    """Validate state transition using exhaustive pattern matching."""
    match (current, new):
        # From Requested
        case (EntityRequested(), EntityConfirmed()):
            return TransitionSuccess(new_status=new)
        case (EntityRequested(), EntityCancelled()):
            return TransitionSuccess(new_status=new)

        # From Confirmed
        case (EntityConfirmed(), EntityInProgress()):
            return TransitionSuccess(new_status=new)
        case (EntityConfirmed(), EntityCancelled()):
            return TransitionSuccess(new_status=new)

        # From InProgress
        case (EntityInProgress(), EntityCompleted()):
            return TransitionSuccess(new_status=new)
        case (EntityInProgress(), EntityCancelled()):
            return TransitionSuccess(new_status=new)

        # Invalid - all other transitions
        case _:
            return TransitionInvalid(
                current_status=type(current).__name__,
                attempted_status=type(new).__name__,
                reason=f"Cannot transition from {type(current).__name__} to {type(new).__name__}",
            )
```

**Testing Tip**: Create test cases for every `case` branch to ensure complete coverage.

---

### Pattern 4: Terminal State Detection

Identify states that allow no further transitions.

**Key Benefit**: Prevents modifications to permanent records (audit trails, billing, medical notes).

```python
def is_terminal(status: EntityStatus) -> bool:
    """Check if status allows no further transitions."""
    match status:
        case EntityCompleted() | EntityCancelled():
            return True
        case EntityRequested() | EntityConfirmed() | EntityInProgress():
            return False
```

**Usage in validation**:
```python
def validate_transition(
    current: EntityStatus, new: EntityStatus
) -> TransitionResult:
    # Terminal states cannot transition
    if is_terminal(current):
        return TransitionInvalid(
            current_status=type(current).__name__,
            attempted_status=type(new).__name__,
            reason="Cannot transition from terminal state",
        )

    # ... rest of validation
```

---

### Pattern 5: Status-Specific Actions

Use pattern matching to determine available actions based on current state.

**Key Benefit**: UI can show only valid actions, reducing user errors.

```python
def get_available_actions(
    status: EntityStatus,
    user_role: Literal["requester", "approver", "processor"],
) -> list[str]:
    """Get list of actions available for current state and user role."""
    match status:
        case EntityRequested():
            actions = ["cancel"]
            if user_role == "approver":
                actions.append("confirm")
            return actions

        case EntityConfirmed():
            actions = ["cancel"]
            if user_role == "processor":
                actions.append("start")
            return actions

        case EntityInProgress():
            if user_role == "processor":
                return ["complete", "cancel"]
            return []

        case EntityCompleted() | EntityCancelled():
            return []  # Terminal states - no actions
```

**Frontend Integration**: API endpoint returns available actions, UI renders only those buttons.

---

## Anti-Patterns

### Anti-Pattern 1: String-Based Status

```python
# BAD - Typos, no compile-time checking
class Entity:
    status: str  # "requested", "confirmed", etc.

def confirm(entity: Entity) -> None:
    if entity.status == "reqested":  # Typo undetected by type checker
        entity.status = "confirmed"

# GOOD - ADT prevents typos
def confirm(entity: Entity) -> TransitionResult:
    match entity.status:
        case EntityRequested():
            new_status = EntityConfirmed(...)
            return validate_transition(entity.status, new_status)
        case _:
            return TransitionInvalid(...)
```

**Why Bad**: String typos cause runtime errors, not compile-time errors. Type checker can't help.

---

### Anti-Pattern 2: No Transition Validation

```python
# BAD - Allows invalid transitions
class Entity:
    def complete(self, notes: str) -> None:
        self.status = "completed"  # Can transition from ANY state!

# GOOD - Validate before transition
def complete_entity(entity: Entity, notes: str) -> TransitionResult:
    new_status = EntityCompleted(notes=notes, ...)
    result = validate_transition(entity.status, new_status)

    if isinstance(result, TransitionInvalid):
        return result

    # Update entity via effect
    # ...
```

**Why Bad**: Skipping validation allows dangerous transitions (e.g., Requested → Completed skips approval).

---

### Anti-Pattern 3: Stateless Status

```python
# BAD - No context in status
class Entity:
    status: str  # "completed" - but when? what notes?
    completed_at: datetime | None
    notes: str | None

# GOOD - Status carries context
class Entity:
    status: EntityStatus  # EntityCompleted(completed_at=..., notes=...)
```

**Why Bad**: Optional fields allow invalid combinations (status="requested" but completed_at is set).

---

### Anti-Pattern 4: Mutable Status

```python
# BAD - Direct mutation breaks audit trail
entity.status = "completed"
entity.completed_at = datetime.now()

# GOOD - Return new entity with new status (immutable update)
new_status = EntityCompleted(
    completed_at=datetime.now(UTC),
    notes=notes,
)
new_entity = replace(entity, status=new_status)
```

**Why Bad**: Mutation breaks referential transparency, makes testing harder, audit trail unclear.

---

### Anti-Pattern 5: Exception on Invalid Transition

```python
# BAD - Exception interrupts flow, not composable
def transition(entity: Entity, new_status: EntityStatus) -> Entity:
    if not is_valid_transition(entity.status, new_status):
        raise InvalidTransitionError()  # Caller must catch
    # ...

# GOOD - Return result type, composable
def transition(entity: Entity, new_status: EntityStatus) -> TransitionResult:
    return validate_transition(entity.status, new_status)
```

**Why Bad**: Exceptions don't compose well in effect programs, all paths not visible to type checker.

---

## Testing State Machines

### Test All Valid Transitions

```python
def test_all_valid_transitions() -> None:
    """Test every valid transition in the state machine."""
    valid_transitions: list[tuple[EntityStatus, EntityStatus]] = [
        (EntityRequested(...), EntityConfirmed(...)),
        (EntityRequested(...), EntityCancelled(...)),
        (EntityConfirmed(...), EntityInProgress(...)),
        (EntityConfirmed(...), EntityCancelled(...)),
        (EntityInProgress(...), EntityCompleted(...)),
        (EntityInProgress(...), EntityCancelled(...)),
    ]

    for current, new in valid_transitions:
        result = validate_transition(current, new)
        assert isinstance(result, TransitionSuccess), \
            f"Expected {type(current).__name__} → {type(new).__name__} to be valid"
```

---

### Test All Invalid Transitions

```python
def test_invalid_transitions() -> None:
    """Test common invalid transitions."""
    invalid_transitions: list[tuple[EntityStatus, EntityStatus]] = [
        (EntityRequested(...), EntityCompleted(...)),  # Skip confirmation
        (EntityRequested(...), EntityInProgress(...)),  # Skip confirmation
        (EntityCompleted(...), EntityCancelled(...)),  # Terminal state
        (EntityCancelled(...), EntityRequested(...)),  # Terminal state
        (EntityConfirmed(...), EntityCompleted(...)),  # Skip InProgress
    ]

    for current, new in invalid_transitions:
        result = validate_transition(current, new)
        assert isinstance(result, TransitionInvalid), \
            f"Expected {type(current).__name__} → {type(new).__name__} to be invalid"
        assert len(result.reason) > 0, "Invalid transition must have reason"
```

---

### Test Terminal State Detection

```python
def test_terminal_states() -> None:
    """Verify terminal states are correctly identified."""
    terminal_states = [
        EntityCompleted(...),
        EntityCancelled(...),
    ]

    for status in terminal_states:
        assert is_terminal(status), f"{type(status).__name__} should be terminal"

    non_terminal_states = [
        EntityRequested(...),
        EntityConfirmed(...),
        EntityInProgress(...),
    ]

    for status in non_terminal_states:
        assert not is_terminal(status), f"{type(status).__name__} should not be terminal"
```

---

### Test Available Actions

```python
def test_available_actions_by_role() -> None:
    """Test role-based action availability."""
    requested = EntityRequested(...)

    # Requester can only cancel
    assert get_available_actions(requested, "requester") == ["cancel"]

    # Approver can confirm or cancel
    assert set(get_available_actions(requested, "approver")) == {"confirm", "cancel"}

    # Processor cannot act on requested state
    assert get_available_actions(requested, "processor") == ["cancel"]


def test_terminal_states_have_no_actions() -> None:
    """Terminal states should have no available actions."""
    completed = EntityCompleted(...)
    cancelled = EntityCancelled(...)

    for role in ["requester", "approver", "processor"]:
        assert get_available_actions(completed, role) == []
        assert get_available_actions(cancelled, role) == []
```

---

## Related Documentation

### Domain Knowledge
- [Medical State Machines](../domain/medical_state_machines.md) - Healthcare domain requirements and medical workflow context
- [Appointment Workflows](../domain/appointment_workflows.md) - Complete appointment lifecycle with medical implications

### HealthHub Implementation
- [Appointment State Machine](../product/appointment_state_machine.md) - HealthHub's appointment state machine implementation
- [Domain Models](../product/domain_models.md) - Appointment, Prescription, LabResult, Invoice entities

### Best Practices
- [Effect Program Patterns](effect_program_patterns.md) - Using state machines in effect programs
- [Testing Doctrine](testing_doctrine.md) - Comprehensive testing patterns

---

**Last Updated**: 2025-11-26
**Maintainer**: HealthHub Team
