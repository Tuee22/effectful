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
    doctor_notes: str | None


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


@dataclass(frozen=True)
class AddInvoiceLineItem:
    """Effect: Add line item to existing invoice.

    Returns: LineItem
    """

    invoice_id: UUID
    description: str
    quantity: int
    unit_price: Decimal


@dataclass(frozen=True)
class UpdateInvoiceStatus:
    """Effect: Update invoice payment status.

    Returns: Invoice
    """

    invoice_id: UUID
    status: str  # "draft" | "sent" | "paid" | "overdue"


@dataclass(frozen=True)
class ListAppointments:
    """Effect: List appointments with optional filtering.

    Returns: list[Appointment]
    """

    patient_id: UUID | None = None
    doctor_id: UUID | None = None
    status: str | None = None


@dataclass(frozen=True)
class GetPrescriptionById:
    """Effect: Fetch prescription by ID.

    Returns: Prescription | None
    """

    prescription_id: UUID


@dataclass(frozen=True)
class ListPrescriptions:
    """Effect: List prescriptions with optional filtering.

    Returns: list[Prescription]
    """

    patient_id: UUID | None = None
    doctor_id: UUID | None = None


@dataclass(frozen=True)
class ListLabResults:
    """Effect: List lab results with optional filtering.

    Returns: list[LabResult]
    """

    patient_id: UUID | None = None
    doctor_id: UUID | None = None


@dataclass(frozen=True)
class ReviewLabResult:
    """Effect: Mark lab result as reviewed by doctor.

    Returns: LabResult
    """

    result_id: UUID
    doctor_notes: str | None


@dataclass(frozen=True)
class GetInvoiceById:
    """Effect: Fetch invoice by ID.

    Returns: Invoice | None
    """

    invoice_id: UUID


@dataclass(frozen=True)
class ListInvoices:
    """Effect: List invoices with optional filtering.

    Returns: list[Invoice]
    """

    patient_id: UUID | None = None


@dataclass(frozen=True)
class CreatePatient:
    """Effect: Create new patient record.

    Returns: Patient
    """

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


@dataclass(frozen=True)
class ListPatients:
    """Effect: List all patients (admin only).

    Returns: list[Patient]
    """

    pass


type HealthcareEffect = (
    GetPatientById
    | GetDoctorById
    | CreateAppointment
    | GetAppointmentById
    | ListAppointments
    | TransitionAppointmentStatus
    | CreatePrescription
    | GetPrescriptionById
    | ListPrescriptions
    | CheckMedicationInteractions
    | CreateLabResult
    | GetLabResultById
    | ListLabResults
    | ReviewLabResult
    | CreateInvoice
    | AddInvoiceLineItem
    | UpdateInvoiceStatus
    | GetInvoiceById
    | ListInvoices
    | CreatePatient
    | ListPatients
)
