"""Appointment Management API endpoints.

Provides appointment scheduling and state management.
"""

from collections.abc import Generator
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
import redis.asyncio as redis

from app.domain.appointment import (
    Appointment,
    AppointmentStatus,
    Cancelled,
    Completed,
    Confirmed,
    InProgress,
    Requested,
    TransitionInvalid,
    TransitionSuccess,
)
from app.effects.notification import LogAuditEvent
from app.infrastructure import get_database_manager, rate_limit
from app.interpreters.auditing_interpreter import AuditContext, AuditedCompositeInterpreter
from app.interpreters.composite_interpreter import AllEffects, CompositeInterpreter
from app.programs.appointment_programs import (
    AppointmentDoctorMissing,
    AppointmentPatientMissing,
    AppointmentScheduled,
    ScheduleAppointmentResult,
    schedule_appointment_program,
    transition_appointment_program,
)
from app.programs.runner import run_program
from app.api.dependencies import (
    PatientAuthorized,
    DoctorAuthorized,
    AdminAuthorized,
    require_authenticated,
)

router = APIRouter()


class AppointmentResponse(BaseModel):
    """Appointment response model."""

    id: str
    patient_id: str
    doctor_id: str
    status: str
    reason: str
    created_at: datetime
    updated_at: datetime


class CreateAppointmentRequest(BaseModel):
    """Create appointment request."""

    patient_id: str
    doctor_id: str
    requested_time: datetime | None = None
    reason: str


class TransitionStatusRequest(BaseModel):
    """Transition appointment status request."""

    new_status: str  # "requested", "confirmed", "in_progress", "completed", "cancelled"
    actor_id: str


def status_to_string(status: AppointmentStatus) -> str:
    """Convert AppointmentStatus ADT to string."""
    match status:
        case Requested():
            return "requested"
        case Confirmed():
            return "confirmed"
        case InProgress():
            return "in_progress"
        case Completed():
            return "completed"
        case Cancelled():
            return "cancelled"


def appointment_to_response(appointment: Appointment) -> AppointmentResponse:
    """Convert Appointment domain model to API response."""
    return AppointmentResponse(
        id=str(appointment.id),
        patient_id=str(appointment.patient_id),
        doctor_id=str(appointment.doctor_id),
        status=status_to_string(appointment.status),
        reason=appointment.reason,
        created_at=appointment.created_at,
        updated_at=appointment.updated_at,
    )


@router.get("/", response_model=list[AppointmentResponse])
async def list_appointments(
    request: Request,
    auth: Annotated[
        PatientAuthorized | DoctorAuthorized | AdminAuthorized,
        Depends(require_authenticated),
    ],
    status_filter: str | None = None,
    _rate_limit: Annotated[None, Depends(rate_limit(100, 60))] = None,
) -> list[AppointmentResponse]:
    """List appointments with role-based filtering.

    - Patient: sees only their own appointments
    - Doctor: sees only their own appointments
    - Admin: sees all appointments

    Optional status_filter to filter by status.
    Logs all PHI access for HIPAA compliance.
    Rate limit: 100 requests per 60 seconds per IP address.
    """
    from collections.abc import Generator
    from app.effects.healthcare import ListAppointments
    from app.interpreters.composite_interpreter import AllEffects

    db_manager = get_database_manager()
    pool = db_manager.get_pool()

    # Create Redis client
    redis_client: redis.Redis[bytes] = redis.Redis(
        host="redis",
        port=6379,
        decode_responses=False,
    )

    # Extract actor ID from auth state
    actor_id: UUID
    match auth:
        case PatientAuthorized(user_id=uid, patient_id=pid):
            actor_id = uid
            patient_id: UUID | None = pid
            doctor_id: UUID | None = None
        case DoctorAuthorized(user_id=uid, doctor_id=did):
            actor_id = uid
            patient_id = None
            doctor_id = did
        case AdminAuthorized(user_id=uid):
            actor_id = uid
            patient_id = None
            doctor_id = None

    # Extract IP and user agent from request
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    # Create composite interpreter with audit wrapper
    base_interpreter = CompositeInterpreter(pool, redis_client)
    interpreter: AuditedCompositeInterpreter = AuditedCompositeInterpreter(
        base_interpreter,
        AuditContext(user_id=actor_id, ip_address=ip_address, user_agent=user_agent),
    )

    # Create effect program with audit logging
    def list_program() -> Generator[AllEffects, object, list[Appointment]]:
        appointments = yield ListAppointments(
            patient_id=patient_id, doctor_id=doctor_id, status=status_filter
        )
        assert isinstance(appointments, list)

        # HIPAA-required audit logging (log all PHI list access)
        resource_id = (
            appointments[0].id if appointments else UUID("00000000-0000-0000-0000-000000000000")
        )
        yield LogAuditEvent(
            user_id=actor_id,
            action="list_appointments",
            resource_type="appointment",
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={"count": str(len(appointments))},
        )

        return appointments

    # Run effect program
    appointments = await run_program(list_program(), interpreter)

    await redis_client.aclose()

    return [appointment_to_response(a) for a in appointments]


@router.post("/", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
async def create_appointment(
    request: CreateAppointmentRequest,
    auth: Annotated[
        PatientAuthorized | AdminAuthorized,
        Depends(require_authenticated),
    ],
    _rate_limit: Annotated[None, Depends(rate_limit(100, 60))],
) -> AppointmentResponse:
    """Create new appointment request.

    Uses effect program: schedule_appointment_program
    Sends notification to doctor via Redis pub/sub.

    Requires: Patient (own appointment) or Admin role.
    Rate limit: 100 requests per 60 seconds per IP address.
    """
    # Authorization check - patient can only create for themselves
    match auth:
        case PatientAuthorized(user_id=user_id, patient_id=auth_patient_id):
            if str(auth_patient_id) != request.patient_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to create appointment for this patient",
                )
        case AdminAuthorized():
            pass  # Admins can create for any patient

    db_manager = get_database_manager()
    pool = db_manager.get_pool()

    actor_id: UUID
    match auth:
        case PatientAuthorized(user_id=uid):
            actor_id = uid
        case AdminAuthorized(user_id=uid):
            actor_id = uid

    # Create Redis client
    redis_client: redis.Redis[bytes] = redis.Redis(
        host="redis",
        port=6379,
        decode_responses=False,
    )

    # Create composite interpreter
    base_interpreter = CompositeInterpreter(pool, redis_client)
    interpreter: AuditedCompositeInterpreter = AuditedCompositeInterpreter(
        base_interpreter,
        AuditContext(user_id=actor_id, ip_address=None, user_agent=None),
    )

    # Run effect program
    program = schedule_appointment_program(
        patient_id=UUID(request.patient_id),
        doctor_id=UUID(request.doctor_id),
        requested_time=request.requested_time,
        reason=request.reason,
        actor_id=actor_id,
    )

    result: ScheduleAppointmentResult = await run_program(program, interpreter)

    await redis_client.aclose()

    match result:
        case AppointmentScheduled(appointment=appointment):
            return appointment_to_response(appointment)
        case AppointmentPatientMissing(patient_id=missing_patient_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Patient {missing_patient_id} not found",
            )
        case AppointmentDoctorMissing(doctor_id=missing_doctor_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Doctor {missing_doctor_id} not found",
            )
        case _:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create appointment",
            )


@router.get("/{appointment_id}", response_model=AppointmentResponse)
async def get_appointment(
    appointment_id: str,
    request: Request,
    auth: Annotated[
        PatientAuthorized | DoctorAuthorized | AdminAuthorized,
        Depends(require_authenticated),
    ],
    _rate_limit: Annotated[None, Depends(rate_limit(100, 60))],
) -> AppointmentResponse:
    """Get appointment by ID.

    Requires: Patient (own appointment), Doctor (own appointment), or Admin.
    Logs all PHI access for HIPAA compliance.
    Rate limit: 100 requests per 60 seconds per IP address.
    """
    from collections.abc import Generator
    from app.effects.healthcare import GetAppointmentById
    from app.interpreters.composite_interpreter import AllEffects

    db_manager = get_database_manager()
    pool = db_manager.get_pool()

    # Create Redis client
    redis_client: redis.Redis[bytes] = redis.Redis(
        host="redis",
        port=6379,
        decode_responses=False,
    )

    # Extract actor ID from auth state
    actor_id: UUID
    match auth:
        case PatientAuthorized(user_id=uid):
            actor_id = uid
        case DoctorAuthorized(user_id=uid):
            actor_id = uid
        case AdminAuthorized(user_id=uid):
            actor_id = uid

    # Extract IP and user agent from request
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    # Create composite interpreter
    base_interpreter = CompositeInterpreter(pool, redis_client)
    interpreter: AuditedCompositeInterpreter = AuditedCompositeInterpreter(
        base_interpreter,
        AuditContext(user_id=actor_id, ip_address=ip_address, user_agent=user_agent),
    )

    # Create effect program with audit logging
    def get_program() -> Generator[AllEffects, object, Appointment]:
        appointment = yield GetAppointmentById(appointment_id=UUID(appointment_id))

        # HIPAA-required audit logging (log all access attempts)
        yield LogAuditEvent(
            user_id=actor_id,
            action="view_appointment",
            resource_type="appointment",
            resource_id=UUID(appointment_id),
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={"status": "found" if appointment else "not_found"},
        )

        if appointment is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Appointment {appointment_id} not found",
            )
        assert isinstance(appointment, Appointment)
        return appointment

    # Run effect program
    appointment = await run_program(get_program(), interpreter)

    await redis_client.aclose()

    return appointment_to_response(appointment)


@router.post("/{appointment_id}/transition", response_model=dict[str, str])
async def transition_status(
    appointment_id: str,
    request: TransitionStatusRequest,
    auth: Annotated[
        PatientAuthorized | DoctorAuthorized | AdminAuthorized,
        Depends(require_authenticated),
    ],
    _rate_limit: Annotated[None, Depends(rate_limit(100, 60))],
) -> dict[str, str]:
    """Transition appointment status.

    Uses effect program: transition_appointment_program
    Validates state machine transitions.

    Requires: Patient/Doctor (own appointment) or Admin role.
    Authorization validated based on transition type:
    - Patients can: cancel
    - Doctors can: confirm, start, complete, cancel
    - Admins can: all transitions
    Rate limit: 100 requests per 60 seconds per IP address.
    """
    db_manager = get_database_manager()
    pool = db_manager.get_pool()

    # Authorization check based on role and transition
    redis_client: redis.Redis[bytes] = redis.Redis(
        host="redis",
        port=6379,
        decode_responses=False,
    )

    base_interpreter = CompositeInterpreter(pool, redis_client)
    interpreter = AuditedCompositeInterpreter(
        base_interpreter,
        AuditContext(user_id=auth.user_id, ip_address=None, user_agent=None),
    )

    def get_program() -> Generator[AllEffects, object, Appointment | None]:
        appointment = yield GetAppointmentById(appointment_id=UUID(appointment_id))
        return appointment

    appointment = await run_program(get_program(), interpreter)

    if appointment is None:
        await redis_client.aclose()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment {appointment_id} not found",
        )

    match auth:
        case PatientAuthorized(patient_id=auth_patient_id):
            if appointment.patient_id != auth_patient_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to modify this appointment",
                )
            # Patients can only cancel
            if request.new_status != "cancelled":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Patients can only cancel appointments",
                )

        case DoctorAuthorized(doctor_id=auth_doctor_id):
            if appointment.doctor_id != auth_doctor_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to modify this appointment",
                )
            # Doctors can perform all transitions

        case AdminAuthorized():
            pass  # Admins can perform all transitions

    # Parse status string to ADT - declare with union type for proper narrowing
    new_status: AppointmentStatus
    match request.new_status:
        case "requested":
            new_status = Requested(requested_at=datetime.now())
        case "confirmed":
            new_status = Confirmed(confirmed_at=datetime.now(), scheduled_time=datetime.now())
        case "in_progress":
            new_status = InProgress(started_at=datetime.now())
        case "completed":
            new_status = Completed(completed_at=datetime.now(), notes="Appointment completed")
        case "cancelled":
            new_status = Cancelled(
                cancelled_at=datetime.now(),
                cancelled_by="patient",
                reason="User requested cancellation",
            )
        case _:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {request.new_status}",
            )

    # Run effect program
    program = transition_appointment_program(
        appointment_id=UUID(appointment_id),
        new_status=new_status,
        actor_id=auth.user_id,
    )

    result = await run_program(program, interpreter)

    await redis_client.aclose()

    # Handle result
    match result:
        case TransitionSuccess():
            return {
                "status": "success",
                "message": f"Transitioned to {request.new_status}",
            }
        case TransitionInvalid():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.reason,
            )
