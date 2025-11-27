"""Appointment Management API endpoints.

Provides appointment scheduling and state management.
"""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
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
from app.infrastructure import get_database_manager
from app.interpreters.composite_interpreter import CompositeInterpreter
from app.interpreters.healthcare_interpreter import HealthcareInterpreter
from app.programs.appointment_programs import (
    schedule_appointment_program,
    transition_appointment_program,
)
from app.programs.runner import run_program
from app.api.dependencies import (
    AuthorizationState,
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
    auth: Annotated[
        PatientAuthorized | DoctorAuthorized | AdminAuthorized,
        Depends(require_authenticated),
    ],
    status_filter: str | None = None,
) -> list[AppointmentResponse]:
    """List appointments with role-based filtering.

    - Patient: sees only their own appointments
    - Doctor: sees only their own appointments
    - Admin: sees all appointments

    Optional status_filter to filter by status.
    """
    db_manager = get_database_manager()
    pool = db_manager.get_pool()
    interpreter = HealthcareInterpreter(pool)

    # Build query based on role
    match auth:
        case PatientAuthorized(patient_id=patient_id):
            base_query = """
                SELECT id, patient_id, doctor_id, status, requested_time,
                       reason, notes, created_at, updated_at
                FROM appointments
                WHERE patient_id = $1
            """
            params: list[UUID | str] = [patient_id]

        case DoctorAuthorized(doctor_id=doctor_id):
            base_query = """
                SELECT id, patient_id, doctor_id, status, requested_time,
                       reason, notes, created_at, updated_at
                FROM appointments
                WHERE doctor_id = $1
            """
            params = [doctor_id]

        case AdminAuthorized():
            base_query = """
                SELECT id, patient_id, doctor_id, status, requested_time,
                       reason, notes, created_at, updated_at
                FROM appointments
            """
            params = []

    # Add status filter if provided
    if status_filter:
        if params:
            base_query += f" AND status = ${len(params) + 1}"
            params.append(status_filter)
        else:
            base_query += " WHERE status = $1"
            params.append(status_filter)

    # Add ordering
    base_query += " ORDER BY created_at DESC"

    # Execute query
    rows = await pool.fetch(base_query, *params)

    # Convert rows to appointments
    appointments = [interpreter._row_to_appointment(row) for row in rows]

    return [appointment_to_response(a) for a in appointments]


@router.post("/", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
async def create_appointment(request: CreateAppointmentRequest) -> AppointmentResponse:
    """Create new appointment request.

    Uses effect program: schedule_appointment_program
    Sends notification to doctor via Redis pub/sub.

    Requires: Patient or Admin role (TODO: add authorization)
    """
    db_manager = get_database_manager()
    pool = db_manager.get_pool()

    # Create Redis client
    redis_client: redis.Redis[bytes] = redis.Redis(
        host="redis",
        port=6379,
        decode_responses=False,
    )

    # Create composite interpreter
    interpreter = CompositeInterpreter(pool, redis_client)

    # Run effect program
    program = schedule_appointment_program(
        patient_id=UUID(request.patient_id),
        doctor_id=UUID(request.doctor_id),
        requested_time=request.requested_time,
        reason=request.reason,
        actor_id=UUID(request.patient_id),  # TODO: Get from JWT
    )

    appointment = await run_program(program, interpreter)

    await redis_client.aclose()

    if appointment is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create appointment - patient or doctor not found",
        )

    return appointment_to_response(appointment)


@router.get("/{appointment_id}", response_model=AppointmentResponse)
async def get_appointment(appointment_id: str) -> AppointmentResponse:
    """Get appointment by ID.

    Requires: Patient (own appointment), Doctor (own appointment), or Admin (TODO: add authorization)
    """
    db_manager = get_database_manager()
    pool = db_manager.get_pool()

    row = await pool.fetchrow(
        """
        SELECT id, patient_id, doctor_id, status, requested_time,
               reason, notes, created_at, updated_at
        FROM appointments
        WHERE id = $1
        """,
        UUID(appointment_id),
    )

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment {appointment_id} not found",
        )

    # Convert row to Appointment
    interpreter = HealthcareInterpreter(pool)
    appointment = interpreter._row_to_appointment(row)

    return appointment_to_response(appointment)


@router.post("/{appointment_id}/transition", response_model=dict[str, str])
async def transition_status(
    appointment_id: str, request: TransitionStatusRequest
) -> dict[str, str]:
    """Transition appointment status.

    Uses effect program: transition_appointment_program
    Validates state machine transitions.

    Requires: Patient or Doctor (based on transition) or Admin (TODO: add authorization)
    """
    db_manager = get_database_manager()
    pool = db_manager.get_pool()

    # Create Redis client
    redis_client: redis.Redis[bytes] = redis.Redis(
        host="redis",
        port=6379,
        decode_responses=False,
    )

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

    # Create composite interpreter
    interpreter = CompositeInterpreter(pool, redis_client)

    # Run effect program
    program = transition_appointment_program(
        appointment_id=UUID(appointment_id),
        new_status=new_status,
        actor_id=UUID(request.actor_id),
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
