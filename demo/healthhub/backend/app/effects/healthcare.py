"""Healthcare-specific effects.

All effects are immutable (frozen dataclasses) following Effectful patterns.
Effects are descriptions of operations, not execution.
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from app.domain.appointment import AppointmentStatus
from app.domain.invoice import LineItem


@dataclass(frozen=True)
class GetPatientById:
    """Effect: Fetch patient by ID.

    Returns: Patient | None
    """

    patient_id: UUID


@dataclass(frozen=True)
class GetDoctorById:
    """Effect: Fetch doctor by ID.

    Returns: Doctor | None
    """

    doctor_id: UUID


@dataclass(frozen=True)
class CreateAppointment:
    """Effect: Create new appointment request.

    Creates appointment in Requested status awaiting doctor confirmation.

    Returns: Appointment
    """

    patient_id: UUID
    doctor_id: UUID
    requested_time: datetime | None
    reason: str


@dataclass(frozen=True)
class GetAppointmentById:
    """Effect: Fetch appointment by ID.

    Returns: Appointment | None
    """

    appointment_id: UUID


@dataclass(frozen=True)
class TransitionAppointmentStatus:
    """Effect: Transition appointment to new status.

    Validates state machine transitions before updating.
    Uses validate_transition() from domain model.

    Returns: TransitionSuccess | TransitionInvalid
    """

    appointment_id: UUID
    new_status: AppointmentStatus
    actor_id: UUID  # User performing the transition


@dataclass(frozen=True)
class CreatePrescription:
    """Effect: Create prescription order.

    Only doctors with can_prescribe=True should be allowed.

    Returns: Prescription
    """

    patient_id: UUID
    doctor_id: UUID
    medication: str
    dosage: str
    frequency: str
    duration_days: int
    refills_remaining: int
    notes: str | None


@dataclass(frozen=True)
class CheckMedicationInteractions:
    """Effect: Check for drug interactions.

    Returns: NoInteractions | MedicationInteractionWarning
    """

    medications: list[str]


@dataclass(frozen=True)
class CreateLabResult:
    """Effect: Store lab result.

    Returns: LabResult
    """

    result_id: UUID
    patient_id: UUID
    doctor_id: UUID
    test_type: str
    result_data: dict[str, str]
    critical: bool


@dataclass(frozen=True)
class GetLabResultById:
    """Effect: Fetch lab result by ID.

    Returns: LabResult | None
    """

    result_id: UUID


@dataclass(frozen=True)
class CreateInvoice:
    """Effect: Generate invoice.

    Returns: Invoice
    """

    patient_id: UUID
    appointment_id: UUID | None
    line_items: list[LineItem]
    due_date: date | None


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
