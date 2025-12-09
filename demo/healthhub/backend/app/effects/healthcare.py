"""Healthcare-specific effects.

All effects are immutable (frozen dataclasses) following Effectful patterns.
Effects are descriptions of operations, not execution.
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Literal, TypeVar
from uuid import UUID

from app.domain.appointment import AppointmentStatus
from app.domain.invoice import LineItem
from effectful.domain.optional_value import Absent, OptionalValue, Provided, to_optional_value

T_co = TypeVar("T_co")


def _normalize_optional_value(
    value: T_co | OptionalValue[T_co] | None,
) -> OptionalValue[T_co]:
    """Normalize value to OptionalValue for effect parameters.

    Args:
        value: Value to normalize (can be T, OptionalValue[T], or None)

    Returns:
        OptionalValue[T] (either Provided[T] or Absent)
    """
    if isinstance(value, (Provided, Absent)):
        return value
    return to_optional_value(value)


@dataclass(frozen=True)
class GetPatientById:
    """Effect: Fetch patient by ID.

    Attributes:
        patient_id: Patient identifier.

    Returns:
        PatientLookupResult
    """

    patient_id: UUID


@dataclass(frozen=True)
class GetDoctorById:
    """Effect: Fetch doctor by ID.

    Attributes:
        doctor_id: Doctor identifier.

    Returns:
        DoctorLookupResult
    """

    doctor_id: UUID


@dataclass(frozen=True)
class GetDoctorByUserId:
    """Effect: Fetch doctor by user ID.

    Attributes:
        user_id: User identifier.

    Returns:
        DoctorLookupResult
    """

    user_id: UUID


@dataclass(frozen=True)
class GetUserByEmail:
    """Effect: Fetch user by email.

    Attributes:
        email: User email address.

    Returns:
        UserLookupResult
    """

    email: str


@dataclass(frozen=True)
class CreateUser:
    """Effect: Create user with hashed password.

    Attributes:
        email: User email address.
        password_hash: Hashed password value.
        role: Role string to assign.

    Returns:
        User
    """

    email: str
    password_hash: str
    role: str


@dataclass(frozen=True)
class UpdateUserLastLogin:
    """Effect: Update user's last login timestamp.

    Attributes:
        user_id: User identifier.

    Returns:
        None
    """

    user_id: UUID


@dataclass(frozen=True)
class GetPatientByUserId:
    """Effect: Fetch patient by user ID.

    Attributes:
        user_id: User identifier.

    Returns:
        PatientLookupResult
    """

    user_id: UUID


@dataclass(frozen=True)
class CreateAppointment:
    """Effect: Create new appointment request.

    Creates appointment in Requested status awaiting doctor confirmation.

    Attributes:
        patient_id: Patient identifier.
        doctor_id: Doctor identifier.
        requested_time: Optional requested start time.
        reason: Appointment reason.

    Returns:
        Appointment
    """

    patient_id: UUID
    doctor_id: UUID
    requested_time: OptionalValue[datetime]
    reason: str


@dataclass(frozen=True)
class GetAppointmentById:
    """Effect: Fetch appointment by ID.

    Attributes:
        appointment_id: Appointment identifier.

    Returns:
        AppointmentLookupResult
    """

    appointment_id: UUID


@dataclass(frozen=True)
class TransitionAppointmentStatus:
    """Effect: Transition appointment to new status.

    Validates state machine transitions before updating.
    Uses validate_transition() from domain model.

    Attributes:
        appointment_id: Appointment identifier.
        new_status: Target status ADT value.
        actor_id: User performing the transition.

    Returns:
        TransitionResult
    """

    appointment_id: UUID
    new_status: AppointmentStatus
    actor_id: UUID  # User performing the transition


@dataclass(frozen=True)
class CreatePrescription:
    """Effect: Create prescription order.

    Only doctors with can_prescribe=True should be allowed.

    Attributes:
        patient_id: Patient identifier.
        doctor_id: Doctor identifier.
        medication: Medication name.
        dosage: Dosage instructions.
        frequency: Frequency text.
        duration_days: Duration in days.
        refills_remaining: Remaining refill count.
        notes: Optional notes.

    Returns:
        Prescription
    """

    patient_id: UUID
    doctor_id: UUID
    medication: str
    dosage: str
    frequency: str
    duration_days: int
    refills_remaining: int
    notes: OptionalValue[str]


@dataclass(frozen=True)
class CheckMedicationInteractions:
    """Effect: Check for drug interactions.

    Attributes:
        medications: Medication names to check.

    Returns:
        NoInteractions | MedicationInteractionWarning
    """

    medications: list[str]


@dataclass(frozen=True)
class CreateLabResult:
    """Effect: Store lab result.

    Attributes:
        result_id: Lab result identifier.
        patient_id: Patient identifier.
        doctor_id: Doctor identifier.
        test_type: Test type name.
        result_data: Result payload.
        critical: Whether the result is critical.
        doctor_notes: Optional notes from doctor.

    Returns:
        LabResult
    """

    result_id: UUID
    patient_id: UUID
    doctor_id: UUID
    test_type: str
    result_data: dict[str, str]
    critical: bool
    doctor_notes: OptionalValue[str]


@dataclass(frozen=True)
class GetLabResultById:
    """Effect: Fetch lab result by ID.

    Attributes:
        result_id: Lab result identifier.

    Returns:
        LabResultLookupResult
    """

    result_id: UUID


@dataclass(frozen=True)
class CreateInvoice:
    """Effect: Generate invoice.

    Attributes:
        patient_id: Patient identifier.
        appointment_id: Optional appointment identifier.
        line_items: Line items to include.
        due_date: Optional due date.

    Returns:
        Invoice
    """

    patient_id: UUID
    appointment_id: OptionalValue[UUID]
    line_items: list[LineItem]
    due_date: OptionalValue[date]


@dataclass(frozen=True)
class AddInvoiceLineItem:
    """Effect: Add line item to existing invoice.

    Attributes:
        invoice_id: Invoice identifier.
        description: Description of the line item.
        quantity: Item quantity.
        unit_price: Price per unit.

    Returns:
        LineItem
    """

    invoice_id: UUID
    description: str
    quantity: int
    unit_price: Decimal


@dataclass(frozen=True)
class UpdateInvoiceStatus:
    """Effect: Update invoice payment status.

    Attributes:
        invoice_id: Invoice identifier.
        status: New invoice status literal value.

    Returns:
        Invoice
    """

    invoice_id: UUID
    status: Literal["draft", "sent", "paid", "overdue"]


@dataclass(frozen=True, init=False)
class ListAppointments:
    """Effect: List appointments with optional filtering.

    Attributes:
        patient_id: Optional patient filter.
        doctor_id: Optional doctor filter.
        status: Optional status filter.

    Returns:
        list[Appointment]
    """

    patient_id: OptionalValue[UUID]
    doctor_id: OptionalValue[UUID]
    status: OptionalValue[
        Literal["requested", "confirmed", "in_progress", "completed", "cancelled"]
    ]

    def __init__(
        self,
        patient_id: UUID | OptionalValue[UUID] | None = None,
        doctor_id: UUID | OptionalValue[UUID] | None = None,
        status: (
            Literal["requested", "confirmed", "in_progress", "completed", "cancelled"]
            | OptionalValue[
                Literal["requested", "confirmed", "in_progress", "completed", "cancelled"]
            ]
            | None
        ) = None,
    ) -> None:
        object.__setattr__(self, "patient_id", _normalize_optional_value(patient_id))
        object.__setattr__(self, "doctor_id", _normalize_optional_value(doctor_id))
        object.__setattr__(self, "status", _normalize_optional_value(status))


@dataclass(frozen=True)
class GetPrescriptionById:
    """Effect: Fetch prescription by ID.

    Attributes:
        prescription_id: Prescription identifier.

    Returns:
        PrescriptionLookupResult
    """

    prescription_id: UUID


@dataclass(frozen=True, init=False)
class ListPrescriptions:
    """Effect: List prescriptions with optional filtering.

    Attributes:
        patient_id: Optional patient filter.
        doctor_id: Optional doctor filter.

    Returns:
        list[Prescription]
    """

    patient_id: OptionalValue[UUID]
    doctor_id: OptionalValue[UUID]

    def __init__(
        self,
        patient_id: UUID | OptionalValue[UUID] | None = None,
        doctor_id: UUID | OptionalValue[UUID] | None = None,
    ) -> None:
        object.__setattr__(self, "patient_id", _normalize_optional_value(patient_id))
        object.__setattr__(self, "doctor_id", _normalize_optional_value(doctor_id))


@dataclass(frozen=True, init=False)
class ListLabResults:
    """Effect: List lab results with optional filtering.

    Attributes:
        patient_id: Optional patient filter.
        doctor_id: Optional doctor filter.

    Returns:
        list[LabResult]
    """

    patient_id: OptionalValue[UUID]
    doctor_id: OptionalValue[UUID]

    def __init__(
        self,
        patient_id: UUID | OptionalValue[UUID] | None = None,
        doctor_id: UUID | OptionalValue[UUID] | None = None,
    ) -> None:
        object.__setattr__(self, "patient_id", _normalize_optional_value(patient_id))
        object.__setattr__(self, "doctor_id", _normalize_optional_value(doctor_id))


@dataclass(frozen=True, init=False)
class ReviewLabResult:
    """Effect: Mark lab result as reviewed by doctor.

    Attributes:
        result_id: Lab result identifier.
        doctor_notes: Optional notes to attach.

    Returns:
        LabResult
    """

    result_id: UUID
    doctor_notes: OptionalValue[str]

    def __init__(
        self,
        result_id: UUID,
        doctor_notes: str | OptionalValue[str] | None = None,
    ) -> None:
        object.__setattr__(self, "result_id", result_id)
        object.__setattr__(self, "doctor_notes", _normalize_optional_value(doctor_notes))


@dataclass(frozen=True)
class GetInvoiceById:
    """Effect: Fetch invoice by ID.

    Attributes:
        invoice_id: Invoice identifier.

    Returns:
        InvoiceLookupResult
    """

    invoice_id: UUID


@dataclass(frozen=True, init=False)
class ListInvoices:
    """Effect: List invoices with optional filtering.

    Attributes:
        patient_id: Optional patient filter.

    Returns:
        list[Invoice]
    """

    patient_id: OptionalValue[UUID]

    def __init__(
        self,
        patient_id: UUID | OptionalValue[UUID] | None = None,
    ) -> None:
        object.__setattr__(self, "patient_id", _normalize_optional_value(patient_id))


@dataclass(frozen=True)
class CreatePatient:
    """Effect: Create new patient record.

    Attributes:
        user_id: Associated user identifier.
        first_name: First name.
        last_name: Last name.
        date_of_birth: Date of birth.
        blood_type: Blood type (optional).
        allergies: Recorded allergies.
        insurance_id: Insurance identifier (optional).
        emergency_contact: Emergency contact details.
        phone: Phone number (optional).
        address: Address (optional).

    Returns:
        Patient
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
class UpdatePatient:
    """Effect: Update patient record.

    Attributes:
        patient_id: Patient identifier.
        first_name: Optional updated first name.
        last_name: Optional updated last name.
        blood_type: Optional blood type update.
        allergies: Optional allergy updates.
        insurance_id: Optional insurance identifier update.
        emergency_contact: Optional emergency contact update.
        phone: Optional phone update.
        address: Optional address update.

    Returns:
        Patient | None
    """

    patient_id: UUID
    first_name: str | None
    last_name: str | None
    blood_type: str | None
    allergies: list[str] | None
    insurance_id: str | None
    emergency_contact: str | None
    phone: str | None
    address: str | None


@dataclass(frozen=True)
class DeletePatient:
    """Effect: Delete patient record.

    Attributes:
        patient_id: Patient identifier.

    Returns:
        bool (True if deleted)
    """

    patient_id: UUID


@dataclass(frozen=True)
class ListPatients:
    """Effect: List all patients (admin only).

    Returns:
        list[Patient]
    """

    pass


@dataclass(frozen=True)
class ListInvoiceLineItems:
    """Effect: List line items for an invoice.

    Attributes:
        invoice_id: Invoice identifier.

    Returns:
        list[LineItem]
    """

    invoice_id: UUID


@dataclass(frozen=True)
class CheckDatabaseHealth:
    """Effect: Verify database connectivity.

    Returns:
        None
    """

    pass


type HealthcareEffect = (
    GetPatientById
    | GetDoctorById
    | GetDoctorByUserId
    | GetUserByEmail
    | CreateUser
    | UpdateUserLastLogin
    | GetPatientByUserId
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
    | UpdatePatient
    | DeletePatient
    | ListPatients
    | ListInvoiceLineItems
    | CheckDatabaseHealth
)
