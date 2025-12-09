"""Appointment domain model with state machine ADT.

The AppointmentStatus ADT makes illegal state transitions unrepresentable.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

from typing_extensions import assert_never


# Appointment Status ADT - makes illegal states unrepresentable
@dataclass(frozen=True)
class Requested:
    """Patient requested appointment, awaiting doctor confirmation.

    Attributes:
        requested_at: Timestamp when appointment was requested
    """

    requested_at: datetime


@dataclass(frozen=True)
class Confirmed:
    """Doctor confirmed appointment with scheduled time.

    Attributes:
        confirmed_at: Timestamp when doctor confirmed the appointment
        scheduled_time: Scheduled appointment start time
    """

    confirmed_at: datetime
    scheduled_time: datetime


@dataclass(frozen=True)
class InProgress:
    """Appointment currently happening.

    Attributes:
        started_at: Timestamp when appointment began
    """

    started_at: datetime


@dataclass(frozen=True)
class Completed:
    """Appointment finished with notes.

    Attributes:
        completed_at: Timestamp when appointment was completed
        notes: Doctor's notes from the completed appointment
    """

    completed_at: datetime
    notes: str


@dataclass(frozen=True)
class Cancelled:
    """Appointment cancelled by patient, doctor, or system.

    Attributes:
        cancelled_at: Timestamp when appointment was cancelled
        cancelled_by: Actor who cancelled the appointment
        reason: Cancellation reason text
    """

    cancelled_at: datetime
    cancelled_by: Literal["patient", "doctor", "system"]
    reason: str


type AppointmentStatus = Requested | Confirmed | InProgress | Completed | Cancelled
"""Appointment status ADT with state machine transitions.

Variants:
    Requested: Initial state, awaiting doctor confirmation
    Confirmed: Doctor confirmed with scheduled time
    InProgress: Appointment currently happening
    Completed: Appointment finished (terminal state)
    Cancelled: Appointment cancelled (terminal state)
"""


@dataclass(frozen=True)
class Appointment:
    """Appointment entity with state machine.

    Immutable domain model following Effectful patterns.
    Status field uses ADT to ensure valid state transitions.

    Attributes:
        id: Unique appointment identifier
        patient_id: Patient UUID reference
        doctor_id: Doctor UUID reference
        status: Current status ADT variant
        reason: Patient's stated reason for appointment
        created_at: Timestamp when appointment was created
        updated_at: Timestamp of last status change
    """

    id: UUID
    patient_id: UUID
    doctor_id: UUID
    status: AppointmentStatus
    reason: str
    created_at: datetime
    updated_at: datetime


# State transition validation
@dataclass(frozen=True)
class TransitionSuccess:
    """Valid state transition.

    Attributes:
        new_status: The new status that was successfully transitioned to
    """

    new_status: AppointmentStatus


@dataclass(frozen=True)
class TransitionInvalid:
    """Invalid state transition.

    Attributes:
        current_status: String name of current status
        attempted_status: String name of attempted new status
        reason: Human-readable explanation of why transition is invalid
    """

    current_status: str
    attempted_status: str
    reason: str


type TransitionResult = TransitionSuccess | TransitionInvalid
"""State transition validation result ADT.

Variants:
    TransitionSuccess: Transition is valid, contains new status
    TransitionInvalid: Transition is invalid, contains error details
"""


def validate_transition(current: AppointmentStatus, new: AppointmentStatus) -> TransitionResult:
    """Validate appointment state transition.

    Valid transitions:
    - Requested → Confirmed
    - Requested → Cancelled
    - Confirmed → InProgress
    - Confirmed → Cancelled
    - InProgress → Completed
    - InProgress → Cancelled

    Args:
        current: Current appointment status
        new: Attempted new status

    Returns:
        TransitionSuccess if valid, TransitionInvalid if not
    """
    match current:
        case Requested():
            match new:
                case Confirmed() | Cancelled():
                    return TransitionSuccess(new_status=new)
                case Requested() | InProgress() | Completed():
                    current_name = type(current).__name__
                    new_name = type(new).__name__
                    return TransitionInvalid(
                        current_status=current_name,
                        attempted_status=new_name,
                        reason=f"Cannot transition from {current_name} to {new_name}",
                    )
                case _:
                    assert_never(new)

        case Confirmed():
            match new:
                case InProgress() | Cancelled():
                    return TransitionSuccess(new_status=new)
                case Requested() | Confirmed() | Completed():
                    current_name = type(current).__name__
                    new_name = type(new).__name__
                    return TransitionInvalid(
                        current_status=current_name,
                        attempted_status=new_name,
                        reason=f"Cannot transition from {current_name} to {new_name}",
                    )
                case _:
                    assert_never(new)

        case InProgress():
            match new:
                case Completed() | Cancelled():
                    return TransitionSuccess(new_status=new)
                case Requested() | Confirmed() | InProgress():
                    current_name = type(current).__name__
                    new_name = type(new).__name__
                    return TransitionInvalid(
                        current_status=current_name,
                        attempted_status=new_name,
                        reason=f"Cannot transition from {current_name} to {new_name}",
                    )
                case _:
                    assert_never(new)

        case Completed() | Cancelled():
            current_name = type(current).__name__
            new_name = type(new).__name__
            return TransitionInvalid(
                current_status=current_name,
                attempted_status=new_name,
                reason=f"Cannot transition from {current_name} to {new_name}",
            )

        case _:
            assert_never(current)
