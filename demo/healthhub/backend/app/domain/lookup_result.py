"""Lookup result ADTs to avoid Optional sentinels."""

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
    """Patient lookup succeeded."""

    patient: Patient


@dataclass(frozen=True)
class PatientMissingById:
    """Patient lookup failed for a patient_id."""

    patient_id: UUID


@dataclass(frozen=True)
class PatientMissingByUserId:
    """Patient lookup failed for a user_id."""

    user_id: UUID


type PatientLookupResult = PatientFound | PatientMissingById | PatientMissingByUserId


@dataclass(frozen=True)
class DoctorFound:
    """Doctor lookup succeeded."""

    doctor: Doctor


@dataclass(frozen=True)
class DoctorMissingById:
    """Doctor lookup failed for a doctor_id."""

    doctor_id: UUID


@dataclass(frozen=True)
class DoctorMissingByUserId:
    """Doctor lookup failed for a user_id."""

    user_id: UUID


type DoctorLookupResult = DoctorFound | DoctorMissingById | DoctorMissingByUserId


@dataclass(frozen=True)
class UserFound:
    """User lookup succeeded."""

    user: User


@dataclass(frozen=True)
class UserMissingByEmail:
    """User lookup failed for an email."""

    email: str


type UserLookupResult = UserFound | UserMissingByEmail


@dataclass(frozen=True)
class AppointmentFound:
    """Appointment lookup succeeded."""

    appointment: Appointment


@dataclass(frozen=True)
class AppointmentMissing:
    """Appointment lookup failed for an appointment_id."""

    appointment_id: UUID


type AppointmentLookupResult = AppointmentFound | AppointmentMissing


@dataclass(frozen=True)
class PrescriptionFound:
    """Prescription lookup succeeded."""

    prescription: Prescription


@dataclass(frozen=True)
class PrescriptionMissing:
    """Prescription lookup failed for a prescription_id."""

    prescription_id: UUID


type PrescriptionLookupResult = PrescriptionFound | PrescriptionMissing


@dataclass(frozen=True)
class LabResultFound:
    """Lab result lookup succeeded."""

    lab_result: LabResult


@dataclass(frozen=True)
class LabResultMissing:
    """Lab result lookup failed for a result_id."""

    result_id: UUID


type LabResultLookupResult = LabResultFound | LabResultMissing


@dataclass(frozen=True)
class InvoiceFound:
    """Invoice lookup succeeded."""

    invoice: Invoice


@dataclass(frozen=True)
class InvoiceMissing:
    """Invoice lookup failed for an invoice_id."""

    invoice_id: UUID


type InvoiceLookupResult = InvoiceFound | InvoiceMissing


@dataclass(frozen=True)
class PatientUpdated:
    """Patient update succeeded."""

    patient: Patient


@dataclass(frozen=True)
class PatientUpdateMissing:
    """Patient update failed because the patient was not found."""

    patient_id: UUID


type PatientUpdateResult = PatientUpdated | PatientUpdateMissing


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
