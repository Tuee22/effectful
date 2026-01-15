"""Lookup result ADTs to avoid Optional sentinels.

Boundary: PURITY
Target-Language: Haskell

Typed lookup results that make None/missing explicit via ADT variants.
This pattern eliminates null-related bugs at the type level.
"""

from dataclasses import dataclass
from typing import TypeGuard
from uuid import UUID

from app.domain.appointment import Appointment
from app.domain.doctor import Doctor
from app.domain.invoice import Invoice
from app.domain.lab_result import LabResult
from app.domain.patient import Patient
from app.domain.prescription import Prescription
from app.domain.user import User


@dataclass(frozen=True)
class PatientFound:
    """Patient lookup succeeded.

    Attributes:
        patient: The found patient entity
    """

    patient: Patient


@dataclass(frozen=True)
class PatientMissingById:
    """Patient lookup failed for a patient_id.

    Attributes:
        patient_id: UUID of patient that was not found
    """

    patient_id: UUID


@dataclass(frozen=True)
class PatientMissingByUserId:
    """Patient lookup failed for a user_id.

    Attributes:
        user_id: UUID of user whose patient record was not found
    """

    user_id: UUID


type PatientLookupResult = PatientFound | PatientMissingById | PatientMissingByUserId
"""Patient lookup result ADT.

Variants:
    PatientFound: Patient found successfully
    PatientMissingById: Patient not found by patient_id
    PatientMissingByUserId: Patient not found by user_id
"""


@dataclass(frozen=True)
class DoctorFound:
    """Doctor lookup succeeded.

    Attributes:
        doctor: The found doctor entity
    """

    doctor: Doctor


@dataclass(frozen=True)
class DoctorMissingById:
    """Doctor lookup failed for a doctor_id.

    Attributes:
        doctor_id: UUID of doctor that was not found
    """

    doctor_id: UUID


@dataclass(frozen=True)
class DoctorMissingByUserId:
    """Doctor lookup failed for a user_id.

    Attributes:
        user_id: UUID of user whose doctor record was not found
    """

    user_id: UUID


type DoctorLookupResult = DoctorFound | DoctorMissingById | DoctorMissingByUserId
"""Doctor lookup result ADT.

Variants:
    DoctorFound: Doctor found successfully
    DoctorMissingById: Doctor not found by doctor_id
    DoctorMissingByUserId: Doctor not found by user_id
"""


@dataclass(frozen=True)
class UserFound:
    """User lookup succeeded.

    Attributes:
        user: The found user entity
    """

    user: User


@dataclass(frozen=True)
class UserMissingByEmail:
    """User lookup failed for an email.

    Attributes:
        email: Email address that was not found
    """

    email: str


type UserLookupResult = UserFound | UserMissingByEmail
"""User lookup result ADT.

Variants:
    UserFound: User found successfully
    UserMissingByEmail: User not found by email address
"""


@dataclass(frozen=True)
class AppointmentFound:
    """Appointment lookup succeeded.

    Attributes:
        appointment: The found appointment entity
    """

    appointment: Appointment


@dataclass(frozen=True)
class AppointmentMissing:
    """Appointment lookup failed for an appointment_id.

    Attributes:
        appointment_id: UUID of appointment that was not found
    """

    appointment_id: UUID


type AppointmentLookupResult = AppointmentFound | AppointmentMissing
"""Appointment lookup result ADT.

Variants:
    AppointmentFound: Appointment found successfully
    AppointmentMissing: Appointment not found by appointment_id
"""


@dataclass(frozen=True)
class PrescriptionFound:
    """Prescription lookup succeeded.

    Attributes:
        prescription: The found prescription entity
    """

    prescription: Prescription


@dataclass(frozen=True)
class PrescriptionMissing:
    """Prescription lookup failed for a prescription_id.

    Attributes:
        prescription_id: UUID of prescription that was not found
    """

    prescription_id: UUID


type PrescriptionLookupResult = PrescriptionFound | PrescriptionMissing
"""Prescription lookup result ADT.

Variants:
    PrescriptionFound: Prescription found successfully
    PrescriptionMissing: Prescription not found by prescription_id
"""


@dataclass(frozen=True)
class LabResultFound:
    """Lab result lookup succeeded.

    Attributes:
        lab_result: The found lab result entity
    """

    lab_result: LabResult


@dataclass(frozen=True)
class LabResultMissing:
    """Lab result lookup failed for a result_id.

    Attributes:
        result_id: UUID of lab result that was not found
    """

    result_id: UUID


type LabResultLookupResult = LabResultFound | LabResultMissing
"""Lab result lookup result ADT.

Variants:
    LabResultFound: Lab result found successfully
    LabResultMissing: Lab result not found by result_id
"""


@dataclass(frozen=True)
class InvoiceFound:
    """Invoice lookup succeeded.

    Attributes:
        invoice: The found invoice entity
    """

    invoice: Invoice


@dataclass(frozen=True)
class InvoiceMissing:
    """Invoice lookup failed for an invoice_id.

    Attributes:
        invoice_id: UUID of invoice that was not found
    """

    invoice_id: UUID


type InvoiceLookupResult = InvoiceFound | InvoiceMissing
"""Invoice lookup result ADT.

Variants:
    InvoiceFound: Invoice found successfully
    InvoiceMissing: Invoice not found by invoice_id
"""


@dataclass(frozen=True)
class PatientUpdated:
    """Patient update succeeded.

    Attributes:
        patient: The updated patient entity
    """

    patient: Patient


@dataclass(frozen=True)
class PatientUpdateMissing:
    """Patient update failed because the patient was not found.

    Attributes:
        patient_id: UUID of patient that was not found for update
    """

    patient_id: UUID


type PatientUpdateResult = PatientUpdated | PatientUpdateMissing
"""Patient update result ADT.

Variants:
    PatientUpdated: Patient updated successfully
    PatientUpdateMissing: Patient not found for update
"""


def is_patient_lookup_result(value: object) -> TypeGuard[PatientLookupResult]:
    """Type guard for patient lookup results."""
    return isinstance(value, (PatientFound, PatientMissingById, PatientMissingByUserId))


def is_doctor_lookup_result(value: object) -> TypeGuard[DoctorLookupResult]:
    """Type guard for doctor lookup results."""
    return isinstance(value, (DoctorFound, DoctorMissingById, DoctorMissingByUserId))


def is_user_lookup_result(value: object) -> TypeGuard[UserLookupResult]:
    """Type guard for user lookup results."""
    return isinstance(value, (UserFound, UserMissingByEmail))


def is_appointment_lookup_result(value: object) -> TypeGuard[AppointmentLookupResult]:
    """Type guard for appointment lookup results."""
    return isinstance(value, (AppointmentFound, AppointmentMissing))


def is_prescription_lookup_result(value: object) -> TypeGuard[PrescriptionLookupResult]:
    """Type guard for prescription lookup results."""
    return isinstance(value, (PrescriptionFound, PrescriptionMissing))


def is_lab_result_lookup_result(value: object) -> TypeGuard[LabResultLookupResult]:
    """Type guard for lab result lookup results."""
    return isinstance(value, (LabResultFound, LabResultMissing))


def is_invoice_lookup_result(value: object) -> TypeGuard[InvoiceLookupResult]:
    """Type guard for invoice lookup results."""
    return isinstance(value, (InvoiceFound, InvoiceMissing))


def is_patient_update_result(value: object) -> TypeGuard[PatientUpdateResult]:
    """Type guard for patient update results."""
    return isinstance(value, (PatientUpdated, PatientUpdateMissing))
