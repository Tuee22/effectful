"""Patient Management API endpoints.

Provides CRUD operations for patient records with medical history tracking.
"""

from collections.abc import Generator
from dataclasses import dataclass
from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.dependencies import (
    AdminAuthorized,
    DoctorAuthorized,
    PatientAuthorized,
    get_audited_composite_interpreter,
    require_admin,
    require_authenticated,
    require_doctor_or_admin,
)
from app.domain.lookup_result import (
    PatientFound,
    PatientLookupResult,
    PatientMissingById,
    PatientMissingByUserId,
    PatientUpdateMissing,
    PatientUpdateResult,
    PatientUpdated,
    is_patient_lookup_result,
    is_patient_update_result,
)
from effectful.domain.optional_value import from_optional_value
from app.domain.patient import Patient
from app.effects.healthcare import (
    CreatePatient as CreatePatientEffect,
    DeletePatient,
    GetPatientById,
    GetPatientByUserId,
    ListPatients,
    UpdatePatient,
)
from app.infrastructure.rate_limiter import rate_limit
from app.interpreters.auditing_interpreter import AuditedCompositeInterpreter
from app.interpreters.composite_interpreter import AllEffects
from app.programs.runner import run_program

router = APIRouter()


@dataclass(frozen=True)
class PatientDeleted:
    patient_id: UUID


@dataclass(frozen=True)
class PatientDeleteMissing:
    patient_id: UUID


type PatientDeleteResult = PatientDeleted | PatientDeleteMissing


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
        blood_type=from_optional_value(patient.blood_type),
        allergies=patient.allergies,
        insurance_id=from_optional_value(patient.insurance_id),
        emergency_contact=patient.emergency_contact,
        phone=from_optional_value(patient.phone),
        address=from_optional_value(patient.address),
    )


@router.get("/", response_model=list[PatientResponse])
async def list_patients(
    auth: Annotated[
        DoctorAuthorized | AdminAuthorized,
        Depends(require_doctor_or_admin),
    ],
    interpreter: Annotated[
        AuditedCompositeInterpreter,
        Depends(get_audited_composite_interpreter),
    ],
    _rate_limit: Annotated[None, Depends(rate_limit(100, 60))],
) -> list[PatientResponse]:
    """List all patients.

    Args:
        auth: Authorization state (doctor or admin).
        interpreter: Audited composite interpreter (injected).
        _rate_limit: Rate limit guard (FastAPI dependency).

    Returns:
        List of patient responses.

    Raises:
        HTTPException: If authorization fails (via dependency).

    Effects:
        ListPatients
        LogAuditEvent (via AuditedCompositeInterpreter)
    """

    # Create effect program with audit logging
    def list_program() -> Generator[AllEffects, object, list[Patient]]:
        patients = yield ListPatients()
        assert isinstance(patients, list)

        return patients

    # Run effect program
    patients = await run_program(list_program(), interpreter)

    return [patient_to_response(p) for p in patients]


@router.post("/", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
async def create_patient(
    request: CreatePatientRequest,
    auth: Annotated[AdminAuthorized, Depends(require_admin)],
    interpreter: Annotated[
        AuditedCompositeInterpreter,
        Depends(get_audited_composite_interpreter),
    ],
    _rate_limit: Annotated[None, Depends(rate_limit(100, 60))],
) -> PatientResponse:
    """Create a new patient record.

    Args:
        request: Patient creation payload.
        auth: Authorization state (admin).
        interpreter: Audited composite interpreter (injected).
        _rate_limit: Rate limit guard (FastAPI dependency).

    Returns:
        Created patient response.

    Raises:
        HTTPException: If authorization fails (via dependency).

    Effects:
        CreatePatient
        LogAuditEvent (via AuditedCompositeInterpreter)
    """

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

    return patient_to_response(patient)


@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(
    patient_id: str,
    auth: Annotated[
        PatientAuthorized | DoctorAuthorized | AdminAuthorized,
        Depends(require_authenticated),
    ],
    interpreter: Annotated[
        AuditedCompositeInterpreter,
        Depends(get_audited_composite_interpreter),
    ],
    _rate_limit: Annotated[None, Depends(rate_limit(100, 60))],
) -> PatientResponse:
    """Get patient by ID.

    Args:
        patient_id: Patient UUID string.
        auth: Authorization state (patient self, doctor, or admin).
        interpreter: Audited composite interpreter (injected).
        _rate_limit: Rate limit guard (FastAPI dependency).

    Returns:
        Patient response for the requested patient.

    Raises:
        HTTPException: If unauthorized or patient is missing.

    Effects:
        GetPatientById
        LogAuditEvent (via AuditedCompositeInterpreter)
    """

    # Create effect program with audit logging
    def get_program() -> Generator[AllEffects, object, PatientLookupResult]:
        result = yield GetPatientById(patient_id=UUID(patient_id))
        assert is_patient_lookup_result(result)
        return result

    # Run effect program
    lookup_result = await run_program(get_program(), interpreter)

    match lookup_result:
        case PatientFound(patient=patient):
            return patient_to_response(patient)
        case PatientMissingById(patient_id=missing_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Patient {missing_id} not found",
            )
        case _:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unexpected patient lookup result",
            )


@router.get("/by-user/{user_id}", response_model=PatientResponse)
async def get_patient_by_user(
    user_id: str,
    auth: Annotated[
        PatientAuthorized | DoctorAuthorized | AdminAuthorized,
        Depends(require_authenticated),
    ],
    interpreter: Annotated[
        AuditedCompositeInterpreter,
        Depends(get_audited_composite_interpreter),
    ],
    _rate_limit: Annotated[None, Depends(rate_limit(100, 60))],
) -> PatientResponse:
    """Get patient by user ID.

    Args:
        user_id: User UUID string.
        auth: Authorization state (patient self, doctor, or admin).
        interpreter: Audited composite interpreter (injected).
        _rate_limit: Rate limit guard (FastAPI dependency).

    Returns:
        Patient response for the associated user.

    Raises:
        HTTPException: If unauthorized or patient is missing.

    Effects:
        GetPatientByUserId
        LogAuditEvent (via AuditedCompositeInterpreter)
    """

    def get_by_user_program() -> Generator[AllEffects, object, PatientLookupResult]:
        result = yield GetPatientByUserId(user_id=UUID(user_id))
        assert is_patient_lookup_result(result)
        return result

    patient_result = await run_program(get_by_user_program(), interpreter)

    match patient_result:
        case PatientFound(patient=patient):
            return patient_to_response(patient)
        case PatientMissingById(patient_id=missing_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Patient {missing_id} not found",
            )
        case PatientMissingByUserId(user_id=missing_user_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Patient for user {missing_user_id} not found",
            )
        # MyPy enforces exhaustiveness - no fallback needed


@router.put("/{patient_id}", response_model=PatientResponse)
async def update_patient(
    patient_id: str,
    request: UpdatePatientRequest,
    auth: Annotated[
        PatientAuthorized | AdminAuthorized,
        Depends(require_authenticated),
    ],
    interpreter: Annotated[
        AuditedCompositeInterpreter,
        Depends(get_audited_composite_interpreter),
    ],
    _rate_limit: Annotated[None, Depends(rate_limit(100, 60))],
) -> PatientResponse:
    """Update patient record.

    Args:
        patient_id: Patient UUID string.
        request: Patch payload for mutable fields.
        auth: Authorization state (patient self or admin).
        interpreter: Audited composite interpreter (injected).
        _rate_limit: Rate limit guard (FastAPI dependency).

    Returns:
        Updated patient response.

    Raises:
        HTTPException: If unauthorized, patient missing, or update fails.

    Effects:
        GetPatientById
        UpdatePatient
        LogAuditEvent (via AuditedCompositeInterpreter)
    """
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

    def fetch_program() -> Generator[AllEffects, object, PatientLookupResult]:
        result = yield GetPatientById(patient_id=UUID(patient_id))
        assert is_patient_lookup_result(result)
        return result

    patient_lookup = await run_program(fetch_program(), interpreter)
    match patient_lookup:
        case PatientFound():
            pass
        case PatientMissingById(patient_id=missing_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Patient {missing_id} not found",
            )
        case PatientMissingByUserId(user_id=missing_user_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Patient for user {missing_user_id} not found",
            )
        # MyPy enforces exhaustiveness - no fallback needed

    def update_program() -> Generator[AllEffects, object, PatientUpdateResult]:
        result = yield UpdatePatient(
            patient_id=UUID(patient_id),
            first_name=request.first_name,
            last_name=request.last_name,
            blood_type=request.blood_type,
            allergies=request.allergies,
            insurance_id=request.insurance_id,
            emergency_contact=request.emergency_contact,
            phone=request.phone,
            address=request.address,
        )
        assert is_patient_update_result(result)
        return result

    update_result = await run_program(update_program(), interpreter)

    match update_result:
        case PatientUpdated(patient=patient):
            return patient_to_response(patient)
        case PatientUpdateMissing(patient_id=missing_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Patient {missing_id} not found",
            )
        case _:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unexpected patient update result",
            )


@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_patient(
    patient_id: str,
    auth: Annotated[AdminAuthorized, Depends(require_admin)],
    interpreter: Annotated[
        AuditedCompositeInterpreter,
        Depends(get_audited_composite_interpreter),
    ],
    _rate_limit: Annotated[None, Depends(rate_limit(100, 60))],
) -> None:
    """Delete patient record.

    Args:
        patient_id: Patient UUID string.
        auth: Authorization state (admin).
        interpreter: Audited composite interpreter (injected).
        _rate_limit: Rate limit guard (FastAPI dependency).

    Returns:
        None. Raises on failure.

    Raises:
        HTTPException: If patient is missing or authorization fails.

    Effects:
        DeletePatient
        LogAuditEvent (via AuditedCompositeInterpreter)
    """

    def delete_program() -> Generator[AllEffects, object, PatientDeleteResult]:
        deleted = yield DeletePatient(patient_id=UUID(patient_id))
        if not deleted:
            return PatientDeleteMissing(patient_id=UUID(patient_id))

        return PatientDeleted(patient_id=UUID(patient_id))

    delete_result = await run_program(delete_program(), interpreter)

    match delete_result:
        case PatientDeleted():
            return None
        case PatientDeleteMissing(patient_id=missing_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Patient {missing_id} not found",
            )
        case _:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unexpected patient delete result",
            )
