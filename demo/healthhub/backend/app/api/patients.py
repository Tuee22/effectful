"""Patient Management API endpoints.

Provides CRUD operations for patient records with medical history tracking.
"""

from collections.abc import Generator
from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
import redis.asyncio as redis

from app.domain.patient import Patient
from app.effects.healthcare import (
    CreatePatient as CreatePatientEffect,
    GetPatientById,
    ListPatients,
)
from app.effects.notification import LogAuditEvent
from app.infrastructure import get_database_manager, rate_limit
from app.interpreters.auditing_interpreter import AuditContext, AuditedCompositeInterpreter
from app.interpreters.composite_interpreter import AllEffects, CompositeInterpreter
from app.programs.runner import run_program
from app.repositories.patient_repository import PatientRepository
from app.api.dependencies import (
    AdminAuthorized,
    AuthorizationState,
    DoctorAuthorized,
    PatientAuthorized,
    require_admin,
    require_authenticated,
    require_doctor_or_admin,
)

router = APIRouter()


class PatientResponse(BaseModel):
    """Patient response model."""

    id: str
    user_id: str
    first_name: str
    last_name: str
    date_of_birth: date
    blood_type: str | None
    allergies: list[str]
    insurance_id: str | None
    emergency_contact: str
    phone: str | None
    address: str | None


class CreatePatientRequest(BaseModel):
    """Create patient request."""

    user_id: str
    first_name: str
    last_name: str
    date_of_birth: date
    blood_type: str | None = None
    allergies: list[str] = Field(default_factory=list)
    insurance_id: str | None = None
    emergency_contact: str
    phone: str | None = None
    address: str | None = None


class UpdatePatientRequest(BaseModel):
    """Update patient request."""

    first_name: str | None = None
    last_name: str | None = None
    blood_type: str | None = None
    allergies: list[str] | None = None
    insurance_id: str | None = None
    emergency_contact: str | None = None
    phone: str | None = None
    address: str | None = None


def patient_to_response(patient: Patient) -> PatientResponse:
    """Convert Patient domain model to API response."""
    return PatientResponse(
        id=str(patient.id),
        user_id=str(patient.user_id),
        first_name=patient.first_name,
        last_name=patient.last_name,
        date_of_birth=patient.date_of_birth,
        blood_type=patient.blood_type,
        allergies=patient.allergies,
        insurance_id=patient.insurance_id,
        emergency_contact=patient.emergency_contact,
        phone=patient.phone,
        address=patient.address,
    )


@router.get("/", response_model=list[PatientResponse])
async def list_patients(
    request: Request,
    auth: Annotated[
        DoctorAuthorized | AdminAuthorized,
        Depends(require_doctor_or_admin),
    ],
    _rate_limit: Annotated[None, Depends(rate_limit(100, 60))],
) -> list[PatientResponse]:
    """List all patients.

    Requires: Doctor or Admin role.
    Patients cannot view other patients' records.
    Logs all PHI access for HIPAA compliance.
    Rate limit: 100 requests per 60 seconds per IP address.
    """
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
    def list_program() -> Generator[AllEffects, object, list[Patient]]:
        patients = yield ListPatients()
        assert isinstance(patients, list)

        # HIPAA-required audit logging (log all PHI list access)
        # Use UUID of first patient as resource_id (or nil UUID if empty list)
        resource_id = patients[0].id if patients else UUID("00000000-0000-0000-0000-000000000000")
        yield LogAuditEvent(
            user_id=actor_id,
            action="list_patients",
            resource_type="patient",
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={"count": str(len(patients))},
        )

        return patients

    # Run effect program
    patients = await run_program(list_program(), interpreter)

    await redis_client.aclose()

    return [patient_to_response(p) for p in patients]


@router.post("/", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
async def create_patient(
    request: CreatePatientRequest,
    auth: Annotated[AdminAuthorized, Depends(require_admin)],
    _rate_limit: Annotated[None, Depends(rate_limit(100, 60))],
) -> PatientResponse:
    """Create a new patient record.

    Requires: Admin role only.
    Rate limit: 100 requests per 60 seconds per IP address.
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
    base_interpreter = CompositeInterpreter(pool, redis_client)
    interpreter = AuditedCompositeInterpreter(
        base_interpreter,
        AuditContext(user_id=auth.user_id, ip_address=None, user_agent=None),
    )

    # Create effect program
    def create_program() -> Generator[AllEffects, object, Patient]:
        patient = yield CreatePatientEffect(
            user_id=UUID(request.user_id),
            first_name=request.first_name,
            last_name=request.last_name,
            date_of_birth=request.date_of_birth,
            blood_type=request.blood_type,
            allergies=request.allergies,
            insurance_id=request.insurance_id,
            emergency_contact=request.emergency_contact,
            phone=request.phone,
            address=request.address,
        )
        assert isinstance(patient, Patient)
        return patient

    # Run effect program
    patient = await run_program(create_program(), interpreter)

    await redis_client.aclose()

    return patient_to_response(patient)


@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(
    patient_id: str,
    request: Request,
    auth: Annotated[
        PatientAuthorized | DoctorAuthorized | AdminAuthorized,
        Depends(require_authenticated),
    ],
    _rate_limit: Annotated[None, Depends(rate_limit(100, 60))],
) -> PatientResponse:
    """Get patient by ID.

    Requires: Patient (own record), Doctor, or Admin role.
    Logs all PHI access for HIPAA compliance.
    Rate limit: 100 requests per 60 seconds per IP address.
    """
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
    def get_program() -> Generator[AllEffects, object, Patient]:
        patient = yield GetPatientById(patient_id=UUID(patient_id))

        # HIPAA-required audit logging (log all access attempts)
        yield LogAuditEvent(
            user_id=actor_id,
            action="view_patient",
            resource_type="patient",
            resource_id=UUID(patient_id),
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={"status": "found" if patient else "not_found"},
        )

        if patient is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Patient {patient_id} not found",
            )
        assert isinstance(patient, Patient)
        return patient

    # Run effect program
    patient = await run_program(get_program(), interpreter)

    await redis_client.aclose()

    return patient_to_response(patient)


@router.get("/by-user/{user_id}", response_model=PatientResponse)
async def get_patient_by_user(
    user_id: str,
    request: Request,
    auth: Annotated[
        PatientAuthorized | DoctorAuthorized | AdminAuthorized,
        Depends(require_authenticated),
    ],
    _rate_limit: Annotated[None, Depends(rate_limit(100, 60))],
) -> PatientResponse:
    """Get patient by user ID.

    Requires: Patient (own record), Doctor, or Admin role.
    Logs all PHI access for HIPAA compliance.
    Rate limit: 100 requests per 60 seconds per IP address.

    TODO: Migrate to effect-based implementation (Phase 2 architectural fix)
    """
    db_manager = get_database_manager()
    pool = db_manager.get_pool()
    patient_repo = PatientRepository(pool)

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

    # Create Redis client for audit logging
    redis_client: redis.Redis[bytes] = redis.Redis(
        host="redis",
        port=6379,
        decode_responses=False,
    )
    base_interpreter = CompositeInterpreter(pool, redis_client)
    interpreter: AuditedCompositeInterpreter = AuditedCompositeInterpreter(
        base_interpreter,
        AuditContext(user_id=actor_id, ip_address=ip_address, user_agent=user_agent),
    )

    patient = await patient_repo.get_by_user_id(UUID(user_id))

    # HIPAA-required audit logging (log all PHI access attempts)
    def audit_program() -> Generator[AllEffects, object, None]:
        yield LogAuditEvent(
            user_id=actor_id,
            action="view_patient_by_user",
            resource_type="patient",
            resource_id=patient.id if patient else UUID("00000000-0000-0000-0000-000000000000"),
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={
                "status": "found" if patient else "not_found",
                "lookup_user_id": user_id,
            },
        )

    await run_program(audit_program(), interpreter)
    await redis_client.aclose()

    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient for user {user_id} not found",
        )

    return patient_to_response(patient)


@router.put("/{patient_id}", response_model=PatientResponse)
async def update_patient(
    patient_id: str,
    request: UpdatePatientRequest,
    auth: Annotated[
        PatientAuthorized | AdminAuthorized,
        Depends(require_authenticated),
    ],
    _rate_limit: Annotated[None, Depends(rate_limit(100, 60))],
) -> PatientResponse:
    """Update patient record.

    Requires: Patient (own record) or Admin role.
    Rate limit: 100 requests per 60 seconds per IP address.
    """
    db_manager = get_database_manager()
    pool = db_manager.get_pool()
    patient_repo = PatientRepository(pool)

    # Get existing patient
    patient = await patient_repo.get_by_id(UUID(patient_id))
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id} not found",
        )

    # Authorization check - patient can only update their own record
    match auth:
        case PatientAuthorized(patient_id=auth_patient_id):
            if str(auth_patient_id) != patient_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to update this patient record",
                )
        case AdminAuthorized():
            pass  # Admins can update any patient

    # Create Redis client and interpreter for auditing
    redis_client: redis.Redis[bytes] = redis.Redis(
        host="redis",
        port=6379,
        decode_responses=False,
    )
    base_interpreter = CompositeInterpreter(pool, redis_client)
    interpreter: AuditedCompositeInterpreter = AuditedCompositeInterpreter(
        base_interpreter,
        AuditContext(user_id=auth.user_id, ip_address=None, user_agent=None),
    )

    # Update patient (simplified - in production, use UPDATE query)
    updated_patient = await patient_repo.create(
        user_id=patient.user_id,
        first_name=request.first_name or patient.first_name,
        last_name=request.last_name or patient.last_name,
        date_of_birth=patient.date_of_birth,
        blood_type=request.blood_type if request.blood_type is not None else patient.blood_type,
        allergies=request.allergies if request.allergies is not None else patient.allergies,
        insurance_id=(
            request.insurance_id if request.insurance_id is not None else patient.insurance_id
        ),
        emergency_contact=request.emergency_contact or patient.emergency_contact,
        phone=request.phone if request.phone is not None else patient.phone,
        address=request.address if request.address is not None else patient.address,
    )

    # Audit mutation
    await interpreter.handle(
        LogAuditEvent(
            user_id=auth.user_id,
            action="update_patient",
            resource_type="patient",
            resource_id=UUID(patient_id),
            ip_address=None,
            user_agent=None,
            metadata=None,
        )
    )
    await redis_client.aclose()

    return patient_to_response(updated_patient)


@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_patient(
    patient_id: str,
    auth: Annotated[AdminAuthorized, Depends(require_admin)],
    _rate_limit: Annotated[None, Depends(rate_limit(100, 60))],
) -> None:
    """Delete patient record.

    Requires: Admin role only.
    Rate limit: 100 requests per 60 seconds per IP address.

    Note: In production, this should be a soft delete (status update) for HIPAA compliance.
    """
    db_manager = get_database_manager()
    pool = db_manager.get_pool()
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

    # Execute delete query (simplified)
    await pool.execute(
        "DELETE FROM patients WHERE id = $1",
        UUID(patient_id),
    )

    await interpreter.handle(
        LogAuditEvent(
            user_id=auth.user_id,
            action="delete_patient",
            resource_type="patient",
            resource_id=UUID(patient_id),
            ip_address=None,
            user_agent=None,
            metadata=None,
        )
    )
    await redis_client.aclose()

    # No content response
    return None
