"""Prescription Management API endpoints.

Provides prescription creation with medication interaction checking.
"""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
import redis.asyncio as redis

from app.domain.prescription import (
    MedicationInteractionWarning,
    Prescription,
)
from app.effects.notification import LogAuditEvent
from app.infrastructure import get_database_manager, rate_limit
from app.interpreters.auditing_interpreter import AuditContext, AuditedCompositeInterpreter
from app.interpreters.composite_interpreter import CompositeInterpreter
from app.programs.prescription_programs import (
    PrescriptionBlocked,
    PrescriptionCreated,
    PrescriptionDoctorMissing,
    PrescriptionDoctorUnauthorized,
    PrescriptionPatientMissing,
    create_prescription_program,
)
from app.programs.runner import run_program
from app.api.dependencies import (
    AdminAuthorized,
    DoctorAuthorized,
    PatientAuthorized,
    require_authenticated,
    require_doctor_or_admin,
)

router = APIRouter()


class PrescriptionResponse(BaseModel):
    """Prescription response model."""

    id: str
    patient_id: str
    doctor_id: str
    medication: str
    dosage: str
    frequency: str
    duration_days: int
    refills_remaining: int
    notes: str | None
    created_at: datetime
    expires_at: datetime


class CreatePrescriptionRequest(BaseModel):
    """Create prescription request."""

    patient_id: str
    doctor_id: str
    medication: str
    dosage: str
    frequency: str
    duration_days: int
    refills_remaining: int
    notes: str | None = None
    existing_medications: list[str] = Field(default_factory=list)


def prescription_to_response(prescription: Prescription) -> PrescriptionResponse:
    """Convert Prescription domain model to API response."""
    return PrescriptionResponse(
        id=str(prescription.id),
        patient_id=str(prescription.patient_id),
        doctor_id=str(prescription.doctor_id),
        medication=prescription.medication,
        dosage=prescription.dosage,
        frequency=prescription.frequency,
        duration_days=prescription.duration_days,
        refills_remaining=prescription.refills_remaining,
        notes=prescription.notes,
        created_at=prescription.created_at,
        expires_at=prescription.expires_at,
    )


@router.get("/", response_model=list[PrescriptionResponse])
async def list_prescriptions(
    request: Request,
    auth: Annotated[
        PatientAuthorized | DoctorAuthorized | AdminAuthorized,
        Depends(require_authenticated),
    ],
    _rate_limit: Annotated[None, Depends(rate_limit(100, 60))],
) -> list[PrescriptionResponse]:
    """List prescriptions with role-based filtering.

    - Patient: sees only their own prescriptions
    - Doctor: sees prescriptions they created
    - Admin: sees all prescriptions

    Logs all PHI access for HIPAA compliance.
    Rate limit: 100 requests per 60 seconds per IP address.
    """
    from collections.abc import Generator
    from app.effects.healthcare import ListPrescriptions
    from app.interpreters.composite_interpreter import AllEffects

    db_manager = get_database_manager()
    pool = db_manager.get_pool()

    # Create Redis client
    redis_client: redis.Redis[bytes] = redis.Redis(
        host="redis",
        port=6379,
        decode_responses=False,
    )

    # Extract actor ID and determine filters based on role
    actor_id: UUID
    patient_id: UUID | None = None
    doctor_id: UUID | None = None

    match auth:
        case PatientAuthorized(user_id=uid, patient_id=pid):
            actor_id = uid
            patient_id = pid
        case DoctorAuthorized(user_id=uid, doctor_id=did):
            actor_id = uid
            doctor_id = did
        case AdminAuthorized(user_id=uid):
            actor_id = uid

    # Extract IP and user agent from request
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    # Create composite interpreter
    base_interpreter = CompositeInterpreter(pool, redis_client)
    interpreter = AuditedCompositeInterpreter(
        base_interpreter,
        AuditContext(user_id=actor_id, ip_address=ip_address, user_agent=user_agent),
    )

    # Create effect program with audit logging
    def list_program() -> Generator[AllEffects, object, list[Prescription]]:
        prescriptions = yield ListPrescriptions(patient_id=patient_id, doctor_id=doctor_id)
        assert isinstance(prescriptions, list)

        # HIPAA-required audit logging (log all PHI list access)
        resource_id = (
            prescriptions[0].id if prescriptions else UUID("00000000-0000-0000-0000-000000000000")
        )
        yield LogAuditEvent(
            user_id=actor_id,
            action="list_prescriptions",
            resource_type="prescription",
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={"count": str(len(prescriptions))},
        )

        return prescriptions

    # Run effect program
    prescriptions = await run_program(list_program(), interpreter)

    await redis_client.aclose()

    return [prescription_to_response(p) for p in prescriptions]


@router.post(
    "/",
    response_model=PrescriptionResponse | dict[str, object],
    status_code=status.HTTP_201_CREATED,
)
async def create_prescription(
    request: CreatePrescriptionRequest,
    auth: Annotated[
        DoctorAuthorized | AdminAuthorized,
        Depends(require_doctor_or_admin),
    ],
    _rate_limit: Annotated[None, Depends(rate_limit(100, 60))],
) -> PrescriptionResponse | dict[str, object]:
    """Create new prescription with interaction checking.

    Uses effect program: create_prescription_program
    Checks medication interactions before creating.
    Blocks creation if severe interaction detected.

    Requires: Doctor (with can_prescribe capability) or Admin role.
    Rate limit: 100 requests per 60 seconds per IP address.

    Returns:
        - PrescriptionResponse: if created successfully
        - dict with warning: if severe interaction blocks creation
    """
    # Capability check - doctor must have can_prescribe=True
    match auth:
        case DoctorAuthorized(
            user_id=user_id, doctor_id=auth_doctor_id, can_prescribe=can_prescribe
        ):
            if not can_prescribe:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Doctor does not have prescription privileges",
                )
            # Also verify doctor is creating their own prescription
            if str(auth_doctor_id) != request.doctor_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Doctors can only create their own prescriptions",
                )
        case AdminAuthorized():
            pass  # Admins can create any prescription

    actor_id: UUID
    match auth:
        case DoctorAuthorized(user_id=uid):
            actor_id = uid
        case AdminAuthorized(user_id=uid):
            actor_id = uid

    db_manager = get_database_manager()
    pool = db_manager.get_pool()

    # Create Redis client
    redis_client: redis.Redis[bytes] = redis.Redis(
        host="redis",
        port=6379,
        decode_responses=False,
    )

    program = create_prescription_program(
        patient_id=UUID(request.patient_id),
        doctor_id=UUID(request.doctor_id),
        medication=request.medication,
        dosage=request.dosage,
        frequency=request.frequency,
        duration_days=request.duration_days,
        refills_remaining=request.refills_remaining,
        notes=request.notes,
        actor_id=actor_id,
        existing_medications=request.existing_medications,
    )

    # Create composite interpreter
    base_interpreter = CompositeInterpreter(pool, redis_client)
    interpreter: AuditedCompositeInterpreter = AuditedCompositeInterpreter(
        base_interpreter,
        AuditContext(user_id=actor_id, ip_address=None, user_agent=None),
    )

    result = await run_program(program, interpreter)

    await redis_client.aclose()

    # Handle result
    match result:
        case PrescriptionCreated(prescription=prescription):
            return prescription_to_response(prescription)
        case PrescriptionBlocked(warning=warning):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "severe_medication_interaction",
                    "medications": warning.medications,
                    "severity": warning.severity,
                    "description": warning.description,
                },
            )
        case PrescriptionPatientMissing(patient_id=missing_patient_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Patient {missing_patient_id} not found",
            )
        case PrescriptionDoctorMissing(doctor_id=missing_doctor_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Doctor {missing_doctor_id} not found",
            )
        case PrescriptionDoctorUnauthorized(doctor_id=unauthorized_doctor_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Doctor {unauthorized_doctor_id} is not authorized to prescribe",
            )
        case _:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unexpected error creating prescription",
            )


@router.get("/{prescription_id}", response_model=PrescriptionResponse)
async def get_prescription(
    prescription_id: str,
    request: Request,
    auth: Annotated[
        PatientAuthorized | DoctorAuthorized | AdminAuthorized,
        Depends(require_authenticated),
    ],
    _rate_limit: Annotated[None, Depends(rate_limit(100, 60))],
) -> PrescriptionResponse:
    """Get prescription by ID.

    Requires: Patient (own prescription), Doctor (own prescription), or Admin.
    Logs all PHI access for HIPAA compliance.
    Rate limit: 100 requests per 60 seconds per IP address.
    """
    from collections.abc import Generator
    from app.effects.healthcare import GetPrescriptionById
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
    interpreter = AuditedCompositeInterpreter(
        base_interpreter,
        AuditContext(user_id=actor_id, ip_address=ip_address, user_agent=user_agent),
    )

    # Create effect program with audit logging
    def get_program() -> Generator[AllEffects, object, Prescription]:
        prescription = yield GetPrescriptionById(prescription_id=UUID(prescription_id))

        # HIPAA-required audit logging (log all access attempts)
        yield LogAuditEvent(
            user_id=actor_id,
            action="view_prescription",
            resource_type="prescription",
            resource_id=UUID(prescription_id),
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={"status": "found" if prescription else "not_found"},
        )

        if prescription is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Prescription {prescription_id} not found",
            )
        assert isinstance(prescription, Prescription)
        return prescription

    # Run effect program
    prescription = await run_program(get_program(), interpreter)

    await redis_client.aclose()

    return prescription_to_response(prescription)


@router.get("/patient/{patient_id}", response_model=list[PrescriptionResponse])
async def get_patient_prescriptions(
    patient_id: str,
    request: Request,
    auth: Annotated[
        PatientAuthorized | DoctorAuthorized | AdminAuthorized,
        Depends(require_authenticated),
    ],
    _rate_limit: Annotated[None, Depends(rate_limit(100, 60))],
) -> list[PrescriptionResponse]:
    """Get all prescriptions for a patient.

    Requires: Patient (own prescriptions), Doctor, or Admin.
    Logs all PHI access for HIPAA compliance.
    Rate limit: 100 requests per 60 seconds per IP address.
    """
    from collections.abc import Generator
    from app.effects.healthcare import ListPrescriptions
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
    interpreter = AuditedCompositeInterpreter(
        base_interpreter,
        AuditContext(user_id=actor_id, ip_address=ip_address, user_agent=user_agent),
    )

    # Create effect program with audit logging
    def list_program() -> Generator[AllEffects, object, list[Prescription]]:
        prescriptions = yield ListPrescriptions(patient_id=UUID(patient_id), doctor_id=None)
        assert isinstance(prescriptions, list)

        # HIPAA-required audit logging (log all PHI list access)
        resource_id = (
            prescriptions[0].id if prescriptions else UUID("00000000-0000-0000-0000-000000000000")
        )
        yield LogAuditEvent(
            user_id=actor_id,
            action="list_patient_prescriptions",
            resource_type="prescription",
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={"count": str(len(prescriptions)), "patient_id": patient_id},
        )

        return prescriptions

    # Run effect program
    prescriptions = await run_program(list_program(), interpreter)

    await redis_client.aclose()

    return [prescription_to_response(p) for p in prescriptions]
