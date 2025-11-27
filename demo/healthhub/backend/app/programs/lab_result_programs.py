"""Lab result workflow programs.

Effect programs for lab result processing and notifications.
"""

from collections.abc import Generator
from uuid import UUID

from app.domain.doctor import Doctor
from app.domain.lab_result import LabResult
from app.domain.patient import Patient
from app.effects.healthcare import (
    CreateLabResult,
    GetDoctorById,
    GetLabResultById,
    GetPatientById,
)
from app.effects.notification import (
    LogAuditEvent,
    NotificationValue,
    PublishWebSocketNotification,
)
from app.interpreters.composite_interpreter import AllEffects


def process_lab_result_program(
    result_id: UUID,
    patient_id: UUID,
    doctor_id: UUID,
    test_type: str,
    result_data: dict[str, str],
    critical: bool,
    actor_id: UUID,
) -> Generator[AllEffects, object, LabResult | str]:
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
    patient = yield GetPatientById(patient_id=patient_id)
    if not isinstance(patient, Patient):
        return f"Patient {patient_id} not found"

    # Step 2: Verify doctor exists
    doctor = yield GetDoctorById(doctor_id=doctor_id)
    if not isinstance(doctor, Doctor):
        return f"Doctor {doctor_id} not found"

    # Step 3: Store lab result
    lab_result = yield CreateLabResult(
        result_id=result_id,
        patient_id=patient_id,
        doctor_id=doctor_id,
        test_type=test_type,
        result_data=result_data,
        critical=critical,
    )
    assert isinstance(lab_result, LabResult)

    # Step 4: Send notification to patient
    patient_message: dict[str, NotificationValue] = {
        "type": "lab_result_available",
        "result_id": str(result_id),
        "test_type": test_type,
        "critical": critical,
        "doctor_name": f"{doctor.first_name} {doctor.last_name}",
    }

    patient_channel = f"patient:{patient_id}:notifications"
    yield PublishWebSocketNotification(
        channel=patient_channel,
        message=patient_message,
        recipient_id=patient_id,
    )

    # Step 5: If critical, send urgent notification to doctor
    if critical:
        doctor_message: dict[str, NotificationValue] = {
            "type": "critical_lab_result",
            "result_id": str(result_id),
            "patient_name": f"{patient.first_name} {patient.last_name}",
            "test_type": test_type,
            "urgency": "immediate_attention_required",
        }

        doctor_channel = f"doctor:{doctor_id}:notifications"
        yield PublishWebSocketNotification(
            channel=doctor_channel,
            message=doctor_message,
            recipient_id=doctor_id,
        )

    # Step 6: Log audit event
    yield LogAuditEvent(
        user_id=actor_id,
        action="create_lab_result",
        resource_type="lab_result",
        resource_id=result_id,
        ip_address=None,
        user_agent=None,
        metadata={
            "patient_id": str(patient_id),
            "doctor_id": str(doctor_id),
            "test_type": test_type,
            "critical": str(critical),
        },
    )

    return lab_result


def view_lab_result_program(
    result_id: UUID, actor_id: UUID
) -> Generator[AllEffects, object, LabResult | None]:
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
    lab_result = yield GetLabResultById(result_id=result_id)

    if isinstance(lab_result, LabResult):
        # Step 2: Log audit event (HIPAA requirement)
        yield LogAuditEvent(
            user_id=actor_id,
            action="view_lab_result",
            resource_type="lab_result",
            resource_id=result_id,
            ip_address=None,
            user_agent=None,
            metadata={
                "patient_id": str(lab_result.patient_id),
                "test_type": lab_result.test_type,
            },
        )

    return lab_result if isinstance(lab_result, LabResult) else None
