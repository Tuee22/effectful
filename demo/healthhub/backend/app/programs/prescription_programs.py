"""Prescription workflow programs.

Effect programs for prescription management.
"""

from collections.abc import Generator
from dataclasses import dataclass
from uuid import UUID

from app.domain.doctor import Doctor
from app.domain.lookup_result import (
    DoctorFound,
    DoctorLookupResult,
    DoctorMissingById,
    DoctorMissingByUserId,
    PatientFound,
    PatientLookupResult,
    PatientMissingById,
    PatientMissingByUserId,
    is_doctor_lookup_result,
    is_patient_lookup_result,
)
from app.domain.patient import Patient
from app.domain.prescription import (
    MedicationCheckResult,
    MedicationInteractionWarning,
    NoInteractions,
    Prescription,
)
from effectful.domain.optional_value import to_optional_value
from app.effects.healthcare import (
    CheckMedicationInteractions,
    CreatePrescription,
    GetDoctorById,
    GetPatientById,
)
from app.effects.notification import LogAuditEvent, NotificationValue, PublishWebSocketNotification
from app.effects.observability import IncrementCounter
from app.interpreters.composite_interpreter import AllEffects


@dataclass(frozen=True)
class PrescriptionCreated:
    """Prescription created successfully.

    Attributes:
        prescription: The created prescription entity
    """

    prescription: Prescription


@dataclass(frozen=True)
class PrescriptionPatientMissing:
    """Patient not found.

    Attributes:
        patient_id: UUID of patient that was not found
    """

    patient_id: UUID


@dataclass(frozen=True)
class PrescriptionDoctorMissing:
    """Doctor not found.

    Attributes:
        doctor_id: UUID of doctor that was not found
    """

    doctor_id: UUID


@dataclass(frozen=True)
class PrescriptionDoctorUnauthorized:
    """Doctor cannot prescribe.

    Attributes:
        doctor_id: UUID of doctor without prescribing authorization
    """

    doctor_id: UUID


@dataclass(frozen=True)
class PrescriptionBlocked:
    """Prescription blocked due to severe interaction.

    Attributes:
        warning: Medication interaction warning with severity details
    """

    warning: MedicationInteractionWarning


type PrescriptionCreationResult = (
    PrescriptionCreated
    | PrescriptionPatientMissing
    | PrescriptionDoctorMissing
    | PrescriptionDoctorUnauthorized
    | PrescriptionBlocked
)
"""Prescription creation result ADT.

Variants:
    PrescriptionCreated: Prescription created successfully
    PrescriptionPatientMissing: Patient not found
    PrescriptionDoctorMissing: Doctor not found
    PrescriptionDoctorUnauthorized: Doctor lacks prescribing authorization
    PrescriptionBlocked: Severe medication interaction detected
"""


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

    Effects:
        GetPatientById: Verify patient exists
        GetDoctorById: Verify doctor exists and retrieve prescribing authorization
        CheckMedicationInteractions: Check for drug interactions with existing medications
        CreatePrescription: Create prescription record if no severe interactions
        IncrementCounter: Track prescription creation metrics
        PublishWebSocketNotification: Notify patient of new prescription
        LogAuditEvent: Log prescription creation for HIPAA compliance
    """
    # Step 1: Verify patient exists
    patient_result = yield GetPatientById(patient_id=patient_id)
    assert is_patient_lookup_result(patient_result)
    match patient_result:
        case PatientFound():
            pass
        case PatientMissingById(patient_id=missing_id):
            return PrescriptionPatientMissing(patient_id=missing_id)
        case PatientMissingByUserId():
            return PrescriptionPatientMissing(patient_id=patient_id)
        # MyPy enforces exhaustiveness - no fallback needed

    # Step 2: Verify doctor exists and can prescribe
    doctor_result = yield GetDoctorById(doctor_id=doctor_id)
    assert is_doctor_lookup_result(doctor_result)
    match doctor_result:
        case DoctorFound(doctor=doctor):
            current_doctor = doctor
            doctor_specialization = doctor.specialization
        case DoctorMissingById(doctor_id=missing_id):
            return PrescriptionDoctorMissing(doctor_id=missing_id)
        case DoctorMissingByUserId():
            return PrescriptionDoctorMissing(doctor_id=doctor_id)
        # MyPy enforces exhaustiveness - no fallback needed

    if not current_doctor.can_prescribe:
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
                ip_address=to_optional_value(None, reason="not_provided"),
                user_agent=to_optional_value(None, reason="not_provided"),
                metadata=to_optional_value(
                    {
                        "medication_count": str(len(interaction_result.medications)),
                        "severity": interaction_result.severity,
                    }
                ),
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
        notes=to_optional_value(notes, reason="no_notes"),
    )
    assert isinstance(prescription, Prescription)

    yield IncrementCounter(
        metric_name="healthhub_prescriptions_created_total",
        labels={
            "doctor_specialization": doctor_specialization,
            "severity": (
                interaction_result.severity
                if isinstance(interaction_result, MedicationInteractionWarning)
                else "none"
            ),
        },
    )

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
        recipient_id=to_optional_value(patient_id, reason="patient_recipient"),
    )

    yield LogAuditEvent(
        user_id=actor_id,
        action="create_prescription",
        resource_type="prescription",
        resource_id=prescription.id,
        ip_address=to_optional_value(None, reason="not_provided"),
        user_agent=to_optional_value(None, reason="not_provided"),
        metadata=to_optional_value(None, reason="not_provided"),
    )

    return PrescriptionCreated(prescription=prescription)
