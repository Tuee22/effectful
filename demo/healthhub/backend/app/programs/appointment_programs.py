"""Appointment workflow programs.

Effect programs for appointment scheduling and management.
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
from app.domain.patient import Patient
from app.effects.healthcare import (
    CreateAppointment,
    GetAppointmentById,
    GetDoctorById,
    GetPatientById,
    TransitionAppointmentStatus,
)
from app.effects.notification import (
    LogAuditEvent,
    NotificationValue,
    PublishWebSocketNotification,
)
from app.interpreters.composite_interpreter import AllEffects


@dataclass(frozen=True)
class AppointmentScheduled:
    """Appointment created successfully."""

    appointment: Appointment


@dataclass(frozen=True)
class AppointmentPatientMissing:
    """Patient not found when scheduling."""

    patient_id: UUID


@dataclass(frozen=True)
class AppointmentDoctorMissing:
    """Doctor not found when scheduling."""

    doctor_id: UUID


type ScheduleAppointmentResult = (
    AppointmentScheduled | AppointmentPatientMissing | AppointmentDoctorMissing
)


def schedule_appointment_program(
    patient_id: UUID,
    doctor_id: UUID,
    requested_time: datetime | None,
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
    """
    # Step 1: Verify patient exists
    patient = yield GetPatientById(patient_id=patient_id)
    if not isinstance(patient, Patient):
        return AppointmentPatientMissing(patient_id=patient_id)

    # Step 2: Verify doctor exists
    doctor = yield GetDoctorById(doctor_id=doctor_id)
    if not isinstance(doctor, Doctor):
        return AppointmentDoctorMissing(doctor_id=doctor_id)

    # Step 3: Create appointment
    appointment = yield CreateAppointment(
        patient_id=patient_id,
        doctor_id=doctor_id,
        requested_time=requested_time,
        reason=reason,
    )
    assert isinstance(appointment, Appointment)

    # Step 4: Notify doctor via WebSocket
    notification_channel = f"doctor:{doctor_id}:notifications"
    notification_message: dict[str, NotificationValue] = {
        "type": "appointment_requested",
        "appointment_id": str(appointment.id),
    }

    yield PublishWebSocketNotification(
        channel=notification_channel,
        message=notification_message,
        recipient_id=doctor_id,
    )

    # Step 5: Log audit event
    yield LogAuditEvent(
        user_id=actor_id,
        action="create_appointment",
        resource_type="appointment",
        resource_id=appointment.id,
        ip_address=None,
        user_agent=None,
        metadata={
            "patient_id": str(patient_id),
            "doctor_id": str(doctor_id),
        },
    )

    return AppointmentScheduled(appointment=appointment)


def transition_appointment_program(
    appointment_id: UUID,
    new_status: AppointmentStatus,
    actor_id: UUID,
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

    Returns:
        TransitionResult (Success or Invalid)
    """
    # Step 1: Get current appointment
    appointment = yield GetAppointmentById(appointment_id=appointment_id)
    if not isinstance(appointment, Appointment):
        return TransitionInvalid(
            current_status="none",
            attempted_status=type(new_status).__name__,
            reason=f"Appointment {appointment_id} not found",
        )

    # Step 2: Attempt transition
    result = yield TransitionAppointmentStatus(
        appointment_id=appointment_id,
        new_status=new_status,
        actor_id=actor_id,
    )
    assert isinstance(result, (TransitionSuccess, TransitionInvalid))

    # Step 3: If successful, send notifications
    if isinstance(result, TransitionSuccess):
        # Notify patient
        patient_channel = f"patient:{appointment.patient_id}:notifications"
        patient_message: dict[str, NotificationValue] = {
            "type": "appointment_status_changed",
            "appointment_id": str(appointment_id),
            "new_status": type(new_status).__name__,
        }

        yield PublishWebSocketNotification(
            channel=patient_channel,
            message=patient_message,
            recipient_id=appointment.patient_id,
        )

        # Notify doctor
        doctor_channel = f"doctor:{appointment.doctor_id}:notifications"
        doctor_message: dict[str, NotificationValue] = {
            "type": "appointment_status_changed",
            "appointment_id": str(appointment_id),
            "new_status": type(new_status).__name__,
        }

        yield PublishWebSocketNotification(
            channel=doctor_channel,
            message=doctor_message,
            recipient_id=appointment.doctor_id,
        )

        # Step 4: Log audit event
        yield LogAuditEvent(
            user_id=actor_id,
            action="transition_appointment_status",
            resource_type="appointment",
            resource_id=appointment_id,
            ip_address=None,
            user_agent=None,
            metadata={
                "old_status": type(appointment.status).__name__,
                "new_status": type(new_status).__name__,
            },
        )

    return result
