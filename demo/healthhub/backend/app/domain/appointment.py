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
    """Patient requested appointment, awaiting doctor confirmation."""

    requested_at: datetime


@dataclass(frozen=True)
class Confirmed:
    """Doctor confirmed appointment with scheduled time."""

    confirmed_at: datetime
    scheduled_time: datetime


@dataclass(frozen=True)
class InProgress:
    """Appointment currently happening."""

    started_at: datetime


@dataclass(frozen=True)
class Completed:
    """Appointment finished with notes."""

    completed_at: datetime
    notes: str


@dataclass(frozen=True)
class Cancelled:
    """Appointment cancelled by patient, doctor, or system."""

    cancelled_at: datetime
    cancelled_by: Literal["patient", "doctor", "system"]
    reason: str


type AppointmentStatus = Requested | Confirmed | InProgress | Completed | Cancelled


@dataclass(frozen=True)
class Appointment:
    """Appointment entity with state machine.

    Immutable domain model following Effectful patterns.
    Status field uses ADT to ensure valid state transitions.
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
    """Valid state transition."""

    new_status: AppointmentStatus


@dataclass(frozen=True)
class TransitionInvalid:
    """Invalid state transition."""

    current_status: str
    attempted_status: str
    reason: str


type TransitionResult = TransitionSuccess | TransitionInvalid


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
