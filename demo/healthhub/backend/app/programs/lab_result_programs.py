"""Lab result workflow programs.

Effect programs for lab result processing and notifications.
"""

from collections.abc import Generator
from dataclasses import dataclass
from uuid import UUID
from typing_extensions import assert_never

from app.domain.doctor import Doctor
from app.domain.lookup_result import (
    DoctorFound,
    DoctorLookupResult,
    DoctorMissingById,
    DoctorMissingByUserId,
    LabResultFound,
    LabResultLookupResult,
    LabResultMissing as LabResultLookupMissing,
    PatientFound,
    PatientLookupResult,
    PatientMissingById,
    PatientMissingByUserId,
    is_doctor_lookup_result,
    is_lab_result_lookup_result,
    is_patient_lookup_result,
)
from app.domain.lab_result import LabResult
from app.domain.patient import Patient
from effectful.domain.optional_value import to_optional_value
from app.effects.healthcare import (
    CreateLabResult,
    GetDoctorById,
    GetLabResultById,
    GetPatientById,
)
from app.effects.notification import LogAuditEvent, NotificationValue, PublishWebSocketNotification
from app.effects.observability import IncrementCounter
from app.interpreters.composite_interpreter import AllEffects


@dataclass(frozen=True)
class LabResultProcessed:
    """Lab result stored successfully."""

    lab_result: LabResult


@dataclass(frozen=True)
class LabResultPatientMissing:
    """Patient not found for lab result."""

    patient_id: UUID


@dataclass(frozen=True)
class LabResultDoctorMissing:
    """Doctor not found for lab result."""

    doctor_id: UUID


type ProcessLabResultResult = (
    LabResultProcessed | LabResultPatientMissing | LabResultDoctorMissing
)


@dataclass(frozen=True)
class LabResultViewed:
    """Lab result fetched successfully."""

    lab_result: LabResult


@dataclass(frozen=True)
class LabResultMissing:
    """Lab result not found."""

    result_id: UUID


type ViewLabResultResult = LabResultViewed | LabResultMissing


def process_lab_result_program(
    result_id: UUID,
    patient_id: UUID,
    doctor_id: UUID,
    test_type: str,
    result_data: dict[str, str],
    critical: bool,
    actor_id: UUID,
) -> Generator[AllEffects, object, ProcessLabResultResult]:
    """Process lab result with notifications.

    Steps:
    1. Verify patient exists
    2. Verify doctor exists
    3. Store lab result in database
    4. Send notification to patient (always)
    5. Send urgent notification to doctor if critical
    6. Log audit event

    Args:
        result_id: Unique result ID
        patient_id: Patient for this result
        doctor_id: Ordering doctor
        test_type: Type of test (e.g., "CBC", "Lipid Panel")
        result_data: Test-specific key-value results
        critical: Whether result requires immediate attention
        actor_id: User performing action

    Returns:
        LabResult if successful, error string if validation fails
    """
    # Step 1: Verify patient exists
    patient_result = yield GetPatientById(patient_id=patient_id)
    assert is_patient_lookup_result(patient_result)
    match patient_result:
        case PatientFound():
            pass
        case PatientMissingById(patient_id=missing_id):
            return LabResultPatientMissing(patient_id=missing_id)
        case PatientMissingByUserId():
            return LabResultPatientMissing(patient_id=patient_id)
        case _:
            assert_never(patient_result)

    # Step 2: Verify doctor exists
    doctor_result = yield GetDoctorById(doctor_id=doctor_id)
    assert is_doctor_lookup_result(doctor_result)
    match doctor_result:
        case DoctorFound(doctor=doctor):
            doctor_specialization = doctor.specialization
        case DoctorMissingById(doctor_id=missing_id):
            return LabResultDoctorMissing(doctor_id=missing_id)
        case DoctorMissingByUserId():
            return LabResultDoctorMissing(doctor_id=doctor_id)
        case _:
            assert_never(doctor_result)

    # Step 3: Store lab result
    lab_result = yield CreateLabResult(
        result_id=result_id,
        patient_id=patient_id,
        doctor_id=doctor_id,
        test_type=test_type,
        result_data=result_data,
        critical=critical,
        doctor_notes=to_optional_value(None, reason="not_provided"),
    )
    assert isinstance(lab_result, LabResult)

    yield IncrementCounter(
        metric_name="healthhub_lab_results_created_total",
        labels={
            "doctor_specialization": doctor_specialization,
            "critical": "true" if critical else "false",
        },
    )

    # Step 4: Send notification to patient
    patient_message: dict[str, NotificationValue] = {
        "type": "lab_result_available",
        "result_id": str(result_id),
        "critical": critical,
    }

    patient_channel = f"patient:{patient_id}:notifications"
    yield PublishWebSocketNotification(
        channel=patient_channel,
        message=patient_message,
        recipient_id=to_optional_value(patient_id, reason="patient_recipient"),
    )

    # Step 5: If critical, send urgent notification to doctor
    if critical:
        doctor_message: dict[str, NotificationValue] = {
            "type": "critical_lab_result",
            "result_id": str(result_id),
            "urgency": "immediate_attention_required",
        }

        doctor_channel = f"doctor:{doctor_id}:notifications"
        yield PublishWebSocketNotification(
            channel=doctor_channel,
            message=doctor_message,
            recipient_id=to_optional_value(doctor_id, reason="doctor_recipient"),
        )

    yield LogAuditEvent(
        user_id=actor_id,
        action="create_lab_result",
        resource_type="lab_result",
        resource_id=result_id,
        ip_address=to_optional_value(None, reason="not_provided"),
        user_agent=to_optional_value(None, reason="not_provided"),
        metadata=to_optional_value({"critical": str(critical)}),
    )

    return LabResultProcessed(lab_result=lab_result)


def view_lab_result_program(
    result_id: UUID, actor_id: UUID
) -> Generator[AllEffects, object, ViewLabResultResult]:
    """View lab result with audit logging.

    Steps:
    1. Fetch lab result
    2. Log audit event (HIPAA compliance)

    Args:
        result_id: Lab result to view
        actor_id: User viewing the result

    Returns:
        LabResult if found, None otherwise
    """
    # Step 1: Fetch lab result
    lab_result_result = yield GetLabResultById(result_id=result_id)
    assert is_lab_result_lookup_result(lab_result_result)

    match lab_result_result:
        case LabResultFound(lab_result=lab_result):
            return LabResultViewed(lab_result=lab_result)
        case LabResultLookupMissing(result_id=missing_id):
            return LabResultMissing(result_id=missing_id)
        case _:
            assert_never(lab_result_result)
