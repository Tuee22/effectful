"""Appointment Management API endpoints.

Boundary: OUTSIDE_PROOF
Target-Language: N/A (assumed correct)

Provides appointment scheduling and state management.
HTTP layer - converts requests to effect programs and runs them.

Assumptions:
- [Framework] FastAPI correctly routes requests and validates payloads
- [Protocol] HTTP semantics are correctly implemented by uvicorn/starlette
"""

from collections.abc import Generator
from datetime import datetime, timezone
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.api.dependencies import (
    AdminAuthorized,
    DoctorAuthorized,
    PatientAuthorized,
    get_audited_composite_interpreter,
    require_authenticated,
)
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
from app.domain.lookup_result import (
    AppointmentFound,
    AppointmentMissing,
    is_appointment_lookup_result,
)
from app.effects.healthcare import GetAppointmentById
from app.infrastructure.rate_limiter import rate_limit
from app.interpreters.auditing_interpreter import AuditedCompositeInterpreter
from app.interpreters.composite_interpreter import AllEffects
from app.programs.appointment_programs import (
    AppointmentDoctorMissing,
    AppointmentPatientMissing,
    AppointmentScheduled,
    ScheduleAppointmentResult,
    schedule_appointment_program,
    transition_appointment_program,
)
from app.programs.runner import run_program, unwrap_program_result
from effectful.domain.optional_value import Absent, OptionalValue, Provided, to_optional_value

router = APIRouter()
StatusFilter = Literal["requested", "confirmed", "in_progress", "completed", "cancelled"]


class AppointmentResponse(BaseModel):
    """Appointment response model."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str
    patient_id: str
    doctor_id: str
    status: str
    reason: str
    created_at: datetime
    updated_at: datetime


class CreateAppointmentRequest(BaseModel):
    """Create appointment request."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    patient_id: str
    doctor_id: str
    requested_time: OptionalValue[datetime] = Field(default_factory=lambda: Absent("not_requested"))
    reason: str

    @field_validator("requested_time", mode="before")
    @classmethod
    def normalize_requested_time(cls, value: object) -> OptionalValue[datetime]:
        if isinstance(value, (Provided, Absent)):
            return value
        if isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value)
            except Exception as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="requested_time must be ISO-8601 datetime when provided",
                ) from exc
            return to_optional_value(parsed, reason="not_requested")
        return to_optional_value(
            value if isinstance(value, datetime) else None, reason="not_requested"
        )


class TransitionStatusRequest(BaseModel):
    """Transition appointment status request."""

    new_status: str  # "requested", "confirmed", "in_progress", "completed", "cancelled"
    actor_id: str


def _parse_status_filter(raw_value: str | None) -> StatusFilter | None:
    """Validate and narrow status filter to the literal type.

    Args:
        raw_value: Raw status query parameter from request.

    Returns:
        A narrowed literal status filter or None when not provided.

    Raises:
        HTTPException: If the raw value is not a supported status.
    """
    match raw_value:
        case None:
            return None
        case "requested" | "confirmed" | "in_progress" | "completed" | "cancelled":
            return raw_value
        case _:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status filter: {raw_value}",
            )


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
    interpreter: Annotated[AuditedCompositeInterpreter, Depends(get_audited_composite_interpreter)],
    status_filter: str | None = None,
    _rate_limit: Annotated[None, Depends(rate_limit(100, 60))] = None,
) -> list[AppointmentResponse]:
    """List appointments with role-based filtering.

    Args:
        auth: Authorization state narrowed by dependency injection.
        interpreter: Injected audited composite interpreter.
        status_filter: Optional status filter string.
        _rate_limit: Rate limit guard (FastAPI dependency).

    Returns:
        List of appointments visible to the actor.

    Raises:
        HTTPException: If status_filter is invalid.

    Effects:
        ListAppointments
        LogAuditEvent (via AuditedCompositeInterpreter)
    """
    from collections.abc import Generator
    from app.effects.healthcare import ListAppointments

    # Extract patient/doctor IDs from auth state for filtering
    patient_id: UUID | None
    doctor_id: UUID | None
    match auth:
        case PatientAuthorized(patient_id=pid):
            patient_id = pid
            doctor_id = None
        case DoctorAuthorized(doctor_id=did):
            patient_id = None
            doctor_id = did
        case AdminAuthorized():
            patient_id = None
            doctor_id = None

    status_value = _parse_status_filter(status_filter)

    # Create effect program with audit logging
    def list_program() -> Generator[AllEffects, object, list[Appointment]]:
        appointments = yield ListAppointments(
            patient_id=to_optional_value(patient_id, reason="role_scope"),
            doctor_id=to_optional_value(doctor_id, reason="role_scope"),
            status=to_optional_value(status_value, reason="not_filtered"),
        )
        assert isinstance(appointments, list)

        return appointments

    # Run effect program
    appointments = unwrap_program_result(await run_program(list_program(), interpreter))

    return [appointment_to_response(a) for a in appointments]


@router.post("/", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
async def create_appointment(
    request: CreateAppointmentRequest,
    auth: Annotated[
        PatientAuthorized | AdminAuthorized,
        Depends(require_authenticated),
    ],
    interpreter: Annotated[
        AuditedCompositeInterpreter,
        Depends(get_audited_composite_interpreter),
    ],
    _rate_limit: Annotated[None, Depends(rate_limit(100, 60))],
) -> AppointmentResponse:
    """Create new appointment request.

    Args:
        request: Appointment creation payload.
        auth: Authorization state (patient for self, or admin).
        interpreter: Audited composite interpreter (injected).
        _rate_limit: Rate limit guard (FastAPI dependency).

    Returns:
        Created appointment in response format.

    Raises:
        HTTPException: If caller is not authorized or dependencies fail.

    Effects:
        schedule_appointment_program (CreateAppointment, LogAuditEvent, notifications)
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

    # Extract actor_id from auth state
    actor_id: UUID
    match auth:
        case PatientAuthorized(user_id=uid):
            actor_id = uid
        case AdminAuthorized(user_id=uid):
            actor_id = uid

    # Run effect program
    program = schedule_appointment_program(
        patient_id=UUID(request.patient_id),
        doctor_id=UUID(request.doctor_id),
        requested_time=request.requested_time,
        reason=request.reason,
        actor_id=actor_id,
    )

    result: ScheduleAppointmentResult = unwrap_program_result(
        await run_program(program, interpreter)
    )

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
    auth: Annotated[
        PatientAuthorized | DoctorAuthorized | AdminAuthorized,
        Depends(require_authenticated),
    ],
    interpreter: Annotated[
        AuditedCompositeInterpreter,
        Depends(get_audited_composite_interpreter),
    ],
    _rate_limit: Annotated[None, Depends(rate_limit(100, 60))],
) -> AppointmentResponse:
    """Get appointment by ID.

    Args:
        appointment_id: Appointment UUID string.
        auth: Authorization state (patient, doctor, or admin).
        interpreter: Audited composite interpreter (injected).
        _rate_limit: Rate limit guard (FastAPI dependency).

    Returns:
        Appointment response for the requested appointment.

    Raises:
        HTTPException: When not found or caller is unauthorized.

    Effects:
        GetAppointmentById
        LogAuditEvent (via AuditedCompositeInterpreter)
    """
    from collections.abc import Generator
    from app.effects.healthcare import GetAppointmentById
    from app.interpreters.composite_interpreter import AllEffects

    # Create effect program with audit logging
    def get_program() -> Generator[AllEffects, object, AppointmentFound | AppointmentMissing]:
        result = yield GetAppointmentById(appointment_id=UUID(appointment_id))
        assert is_appointment_lookup_result(result)
        return result

    # Run effect program
    appointment_result = unwrap_program_result(await run_program(get_program(), interpreter))

    match appointment_result:
        case AppointmentFound(appointment=appointment):
            return appointment_to_response(appointment)
        case AppointmentMissing():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Appointment {appointment_id} not found",
            )
        # MyPy enforces exhaustiveness - no fallback needed


@router.post("/{appointment_id}/transition", response_model=dict[str, str])
async def transition_status(
    appointment_id: str,
    request: TransitionStatusRequest,
    auth: Annotated[
        PatientAuthorized | DoctorAuthorized | AdminAuthorized,
        Depends(require_authenticated),
    ],
    interpreter: Annotated[
        AuditedCompositeInterpreter,
        Depends(get_audited_composite_interpreter),
    ],
    _rate_limit: Annotated[None, Depends(rate_limit(100, 60))],
) -> dict[str, str]:
    """Transition appointment status.

    Args:
        appointment_id: Appointment UUID string.
        request: New status payload and actor identifier.
        auth: Authorization state (patient, doctor, or admin).
        interpreter: Audited composite interpreter (injected).
        _rate_limit: Rate limit guard (FastAPI dependency).

    Returns:
        Success message when transition succeeds.

    Raises:
        HTTPException: If unauthorized, appointment missing, invalid status, or transition invalid.

    Effects:
        GetAppointmentById
        transition_appointment_program (TransitionAppointmentStatus, LogAuditEvent)
    """

    def get_program() -> Generator[AllEffects, object, AppointmentFound | AppointmentMissing]:
        result = yield GetAppointmentById(appointment_id=UUID(appointment_id))
        assert is_appointment_lookup_result(result)
        return result

    appointment_result = unwrap_program_result(await run_program(get_program(), interpreter))

    match appointment_result:
        case AppointmentFound(appointment=appointment):
            current_appointment = appointment
        case AppointmentMissing():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Appointment {appointment_id} not found",
            )
        # MyPy enforces exhaustiveness - no fallback needed

    match auth:
        case PatientAuthorized(patient_id=auth_patient_id):
            if current_appointment.patient_id != auth_patient_id:
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
            if current_appointment.doctor_id != auth_doctor_id:
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
            new_status = Requested(requested_at=datetime.now(timezone.utc))
        case "confirmed":
            new_status = Confirmed(
                confirmed_at=datetime.now(timezone.utc),
                scheduled_time=datetime.now(timezone.utc),
            )
        case "in_progress":
            new_status = InProgress(started_at=datetime.now(timezone.utc))
        case "completed":
            new_status = Completed(
                completed_at=datetime.now(timezone.utc), notes="Appointment completed"
            )
        case "cancelled":
            new_status = Cancelled(
                cancelled_at=datetime.now(timezone.utc),
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
        transition_time=datetime.now(timezone.utc),
    )

    result = unwrap_program_result(await run_program(program, interpreter))

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
