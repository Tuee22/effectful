"""Appointment workflow programs.

Boundary: PURITY
Target-Language: Haskell

Effect programs for appointment scheduling and management.
These are pure generators that yield effect descriptions - no side effects.
The runner (proof boundary) executes these programs.
"""

from collections.abc import Generator
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.appointment import (
    Appointment,
    AppointmentStatus,
    TransitionInvalid,
    TransitionResult,
    TransitionSuccess,
)
from app.domain.doctor import Doctor
from app.domain.lookup_result import (
    AppointmentFound,
    AppointmentMissing,
    AppointmentLookupResult,
    DoctorFound,
    DoctorMissingById,
    DoctorMissingByUserId,
    DoctorLookupResult,
    PatientFound,
    PatientLookupResult,
    PatientMissingById,
    PatientMissingByUserId,
    is_appointment_lookup_result,
    is_doctor_lookup_result,
    is_patient_lookup_result,
)
from app.domain.patient import Patient
from effectful.domain.optional_value import OptionalValue, to_optional_value
from app.effects.healthcare import (
    CreateAppointment,
    GetAppointmentById,
    GetDoctorById,
    GetPatientById,
    TransitionAppointmentStatus,
)
from app.effects.notification import LogAuditEvent, NotificationValue, PublishWebSocketNotification
from app.effects.observability import IncrementCounter, ObserveHistogram
from app.interpreters.composite_interpreter import AllEffects


@dataclass(frozen=True)
class AppointmentScheduled:
    """Appointment created successfully.

    Attributes:
        appointment: The created appointment entity
    """

    appointment: Appointment


@dataclass(frozen=True)
class AppointmentPatientMissing:
    """Patient not found when scheduling.

    Attributes:
        patient_id: UUID of patient that was not found
    """

    patient_id: UUID


@dataclass(frozen=True)
class AppointmentDoctorMissing:
    """Doctor not found when scheduling.

    Attributes:
        doctor_id: UUID of doctor that was not found
    """

    doctor_id: UUID


type ScheduleAppointmentResult = (
    AppointmentScheduled | AppointmentPatientMissing | AppointmentDoctorMissing
)
"""Appointment scheduling result ADT.

Variants:
    AppointmentScheduled: Appointment created successfully
    AppointmentPatientMissing: Patient not found
    AppointmentDoctorMissing: Doctor not found
"""


def schedule_appointment_program(
    patient_id: UUID,
    doctor_id: UUID,
    requested_time: OptionalValue[datetime],
    reason: str,
    actor_id: UUID,
) -> Generator[AllEffects, object, ScheduleAppointmentResult]:
    """Schedule appointment workflow with notifications.

    Steps:
    1. Verify patient exists
    2. Verify doctor exists
    3. Create appointment in Requested status
    4. Send WebSocket notification to doctor
    5. Log audit event

    Args:
        patient_id: Patient requesting appointment
        doctor_id: Doctor being requested
        requested_time: Preferred appointment time
        reason: Reason for visit
        actor_id: User performing the action (for audit)

    Returns:
        Created appointment or None if validation fails

    Effects:
        GetPatientById: Verify patient exists
        GetDoctorById: Verify doctor exists
        CreateAppointment: Create appointment in Requested status
        IncrementCounter: Track appointment creation metric
        PublishWebSocketNotification: Notify doctor of new appointment request
        LogAuditEvent: Log appointment creation for HIPAA compliance
    """
    # Step 1: Verify patient exists
    patient_result = yield GetPatientById(patient_id=patient_id)
    assert is_patient_lookup_result(patient_result)
    match patient_result:
        case PatientFound():
            pass
        case PatientMissingById(patient_id=missing_id):
            return AppointmentPatientMissing(patient_id=missing_id)
        case PatientMissingByUserId():
            return AppointmentPatientMissing(patient_id=patient_id)
        # MyPy enforces exhaustiveness - no fallback needed

    # Step 2: Verify doctor exists
    doctor_result = yield GetDoctorById(doctor_id=doctor_id)
    assert is_doctor_lookup_result(doctor_result)
    match doctor_result:
        case DoctorFound(doctor=doctor):
            doctor_specialization = doctor.specialization
        case DoctorMissingById(doctor_id=missing_id):
            return AppointmentDoctorMissing(doctor_id=missing_id)
        case DoctorMissingByUserId():
            return AppointmentDoctorMissing(doctor_id=doctor_id)
        # MyPy enforces exhaustiveness - no fallback needed

    # Step 3: Create appointment
    appointment = yield CreateAppointment(
        patient_id=patient_id,
        doctor_id=doctor_id,
        requested_time=requested_time,
        reason=reason,
    )
    assert isinstance(appointment, Appointment)

    yield IncrementCounter(
        metric_name="healthhub_appointments_created_total",
        labels={"doctor_specialization": doctor_specialization},
    )

    # Step 4: Notify doctor via WebSocket
    notification_channel = f"doctor:{doctor_id}:notifications"
    notification_message: dict[str, NotificationValue] = {
        "type": "appointment_requested",
        "appointment_id": str(appointment.id),
    }

    yield PublishWebSocketNotification(
        channel=notification_channel,
        message=notification_message,
        recipient_id=to_optional_value(doctor_id, reason="doctor_recipient"),
    )

    yield LogAuditEvent(
        user_id=actor_id,
        action="create_appointment",
        resource_type="appointment",
        resource_id=appointment.id,
        ip_address=to_optional_value(None, reason="not_provided"),
        user_agent=to_optional_value(None, reason="not_provided"),
        metadata=to_optional_value({"reason_present": "true"}),
    )

    return AppointmentScheduled(appointment=appointment)


def transition_appointment_program(
    appointment_id: UUID,
    new_status: AppointmentStatus,
    actor_id: UUID,
    transition_time: datetime,
) -> Generator[AllEffects, object, TransitionResult]:
    """Transition appointment status with validation and notifications.

    Steps:
    1. Get current appointment
    2. Transition status (validates state machine)
    3. Send notifications to patient and doctor
    4. Log audit event

    Args:
        appointment_id: Appointment to transition
        new_status: New status to transition to
        actor_id: User performing the transition
        transition_time: Timestamp of the transition

    Returns:
        TransitionResult (Success or Invalid)

    Effects:
        GetAppointmentById: Retrieve current appointment
        TransitionAppointmentStatus: Validate and execute state transition
        PublishWebSocketNotification: Notify patient and doctor of status change
        LogAuditEvent: Log status transition for HIPAA compliance
    """
    # Step 1: Get current appointment
    appointment_result = yield GetAppointmentById(appointment_id=appointment_id)
    assert is_appointment_lookup_result(appointment_result)
    match appointment_result:
        case AppointmentFound(appointment=appointment):
            current_appointment = appointment
        case AppointmentMissing():
            return TransitionInvalid(
                current_status="none",
                attempted_status=type(new_status).__name__,
                reason=f"Appointment {appointment_id} not found",
            )
        # MyPy enforces exhaustiveness - no fallback needed

    # Step 2: Attempt transition
    result = yield TransitionAppointmentStatus(
        appointment_id=appointment_id,
        new_status=new_status,
        actor_id=actor_id,
    )
    assert isinstance(result, (TransitionSuccess, TransitionInvalid))

    # Step 3: If successful, send notifications
    if isinstance(result, TransitionSuccess):
        transition_latency_seconds = (
            transition_time - current_appointment.created_at
        ).total_seconds()

        yield ObserveHistogram(
            metric_name="healthhub_appointment_transition_latency_seconds",
            labels={"new_status": type(new_status).__name__},
            value=transition_latency_seconds,
        )

        # Notify patient
        patient_channel = f"patient:{current_appointment.patient_id}:notifications"
        patient_message: dict[str, NotificationValue] = {
            "type": "appointment_status_changed",
            "appointment_id": str(appointment_id),
            "new_status": type(new_status).__name__,
        }

        yield PublishWebSocketNotification(
            channel=patient_channel,
            message=patient_message,
            recipient_id=to_optional_value(
                current_appointment.patient_id, reason="patient_recipient"
            ),
        )

        # Notify doctor
        doctor_channel = f"doctor:{current_appointment.doctor_id}:notifications"
        doctor_message: dict[str, NotificationValue] = {
            "type": "appointment_status_changed",
            "appointment_id": str(appointment_id),
            "new_status": type(new_status).__name__,
        }

        yield PublishWebSocketNotification(
            channel=doctor_channel,
            message=doctor_message,
            recipient_id=to_optional_value(
                current_appointment.doctor_id, reason="doctor_recipient"
            ),
        )

        yield LogAuditEvent(
            user_id=actor_id,
            action="transition_appointment_status",
            resource_type="appointment",
            resource_id=appointment_id,
            ip_address=to_optional_value(None, reason="not_provided"),
            user_agent=to_optional_value(None, reason="not_provided"),
            metadata=to_optional_value({"new_status": type(new_status).__name__}),
        )

    return result
