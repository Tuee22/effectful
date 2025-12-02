"""Prescription workflow programs.

Effect programs for prescription management.
"""

from collections.abc import Generator
from dataclasses import dataclass
from uuid import UUID

from app.domain.doctor import Doctor
from app.domain.patient import Patient
from app.domain.prescription import (
    MedicationCheckResult,
    MedicationInteractionWarning,
    NoInteractions,
    Prescription,
)
from app.effects.healthcare import (
    CheckMedicationInteractions,
    CreatePrescription,
    GetDoctorById,
    GetPatientById,
)
from app.effects.notification import (
    LogAuditEvent,
    NotificationValue,
    PublishWebSocketNotification,
)
from app.interpreters.composite_interpreter import AllEffects


@dataclass(frozen=True)
class PrescriptionCreated:
    """Prescription created successfully."""

    prescription: Prescription


@dataclass(frozen=True)
class PrescriptionPatientMissing:
    """Patient not found."""

    patient_id: UUID


@dataclass(frozen=True)
class PrescriptionDoctorMissing:
    """Doctor not found."""

    doctor_id: UUID


@dataclass(frozen=True)
class PrescriptionDoctorUnauthorized:
    """Doctor cannot prescribe."""

    doctor_id: UUID


@dataclass(frozen=True)
class PrescriptionBlocked:
    """Prescription blocked due to severe interaction."""

    warning: MedicationInteractionWarning


type PrescriptionCreationResult = (
    PrescriptionCreated
    | PrescriptionPatientMissing
    | PrescriptionDoctorMissing
    | PrescriptionDoctorUnauthorized
    | PrescriptionBlocked
)


def create_prescription_program(
    patient_id: UUID,
    doctor_id: UUID,
    medication: str,
    dosage: str,
    frequency: str,
    duration_days: int,
    refills_remaining: int,
    notes: str | None,
    actor_id: UUID,
    existing_medications: list[str],
) -> Generator[AllEffects, object, PrescriptionCreationResult]:
    """Create prescription with interaction checking.

    Steps:
    1. Verify patient exists
    2. Verify doctor exists and can prescribe
    3. Check medication interactions
    4. If severe interaction, return warning (do not create)
    5. If moderate/minor interaction, create but notify
    6. Create prescription
    7. Send notification to patient
    8. Log audit event

    Args:
        patient_id: Patient receiving prescription
        doctor_id: Doctor prescribing
        medication: Medication name
        dosage: Dosage instructions
        frequency: Frequency of doses
        duration_days: Prescription duration
        refills_remaining: Number of refills
        notes: Additional notes
        actor_id: User performing action
        existing_medications: Patient's current medications

    Returns:
        Prescription if successful, MedicationInteractionWarning if severe interaction,
        or error string if validation fails
    """
    # Step 1: Verify patient exists
    patient = yield GetPatientById(patient_id=patient_id)
    if not isinstance(patient, Patient):
        return PrescriptionPatientMissing(patient_id=patient_id)

    # Step 2: Verify doctor exists and can prescribe
    doctor = yield GetDoctorById(doctor_id=doctor_id)
    if not isinstance(doctor, Doctor):
        return PrescriptionDoctorMissing(doctor_id=doctor_id)

    if not doctor.can_prescribe:
        return PrescriptionDoctorUnauthorized(doctor_id=doctor_id)

    # Step 3: Check medication interactions
    all_medications = [*existing_medications, medication]
    interaction_result = yield CheckMedicationInteractions(medications=all_medications)
    assert isinstance(interaction_result, (NoInteractions, MedicationInteractionWarning))

    # Step 4: Handle severe interactions (block prescription)
    if isinstance(interaction_result, MedicationInteractionWarning):
        if interaction_result.severity == "severe":
            # Log the blocked attempt
            yield LogAuditEvent(
                user_id=actor_id,
                action="prescription_blocked_severe_interaction",
                resource_type="prescription",
                resource_id=patient_id,
                ip_address=None,
                user_agent=None,
                metadata={
                    "severity": "severe",
                },
            )
            return PrescriptionBlocked(warning=interaction_result)

    # Step 5: Create prescription
    prescription = yield CreatePrescription(
        patient_id=patient_id,
        doctor_id=doctor_id,
        medication=medication,
        dosage=dosage,
        frequency=frequency,
        duration_days=duration_days,
        refills_remaining=refills_remaining,
        notes=notes,
    )
    assert isinstance(prescription, Prescription)

    # Step 6: Send notification to patient
    notification_message: dict[str, NotificationValue] = {
        "type": "prescription_created",
        "prescription_id": str(prescription.id),
    }

    # Add interaction warning to notification if moderate/minor
    if isinstance(interaction_result, MedicationInteractionWarning):
        notification_message["interaction_warning"] = {
            "severity": interaction_result.severity,
            "description": interaction_result.description,
        }

    patient_channel = f"patient:{patient_id}:notifications"
    yield PublishWebSocketNotification(
        channel=patient_channel,
        message=notification_message,
        recipient_id=patient_id,
    )

    # Step 7: Log audit event
    has_warning = isinstance(interaction_result, MedicationInteractionWarning)
    yield LogAuditEvent(
        user_id=actor_id,
        action="create_prescription",
        resource_type="prescription",
        resource_id=prescription.id,
        ip_address=None,
        user_agent=None,
        metadata={
            "patient_id": str(patient_id),
            "doctor_id": str(doctor_id),
            "has_interaction_warning": str(has_warning),
        },
    )

    return PrescriptionCreated(prescription=prescription)
