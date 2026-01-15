"""Prescription Management API endpoints.

Boundary: OUTSIDE_PROOF
Target-Language: N/A (assumed correct)

Provides prescription creation with medication interaction checking.
HTTP layer - converts requests to effect programs and runs them.

Assumptions:
- [Framework] FastAPI correctly routes requests and validates payloads
"""

from collections.abc import Generator
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from app.api.dependencies import (
    AdminAuthorized,
    DoctorAuthorized,
    PatientAuthorized,
    get_audited_composite_interpreter,
    require_authenticated,
    require_doctor_or_admin,
)
from app.domain.lookup_result import (
    PrescriptionFound,
    PrescriptionMissing,
    is_prescription_lookup_result,
)
from effectful.domain.optional_value import (
    Absent,
    OptionalValue,
    Provided,
    from_optional_value,
    to_optional_value,
)
from app.domain.prescription import MedicationInteractionWarning, Prescription
from app.effects.healthcare import GetPrescriptionById, ListPrescriptions
from app.infrastructure.rate_limiter import rate_limit
from app.interpreters.auditing_interpreter import AuditedCompositeInterpreter
from app.interpreters.composite_interpreter import AllEffects
from app.programs.prescription_programs import (
    PrescriptionBlocked,
    PrescriptionCreated,
    PrescriptionDoctorMissing,
    PrescriptionDoctorUnauthorized,
    PrescriptionPatientMissing,
    create_prescription_program,
)
from app.programs.runner import run_program, unwrap_program_result

router = APIRouter()


class PrescriptionResponse(BaseModel):
    """Prescription response model."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str
    patient_id: str
    doctor_id: str
    medication: str
    dosage: str
    frequency: str
    duration_days: int
    refills_remaining: int
    notes: OptionalValue[str] = Field(default_factory=lambda: Absent("not_recorded"))
    created_at: datetime
    expires_at: datetime

    @field_serializer("notes")
    def serialize_notes(self, notes: OptionalValue[str]) -> str | None:
        return from_optional_value(notes)


class CreatePrescriptionRequest(BaseModel):
    """Create prescription request."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    patient_id: str
    doctor_id: str
    medication: str
    dosage: str
    frequency: str
    duration_days: int
    refills_remaining: int
    notes: OptionalValue[str] = Field(default_factory=lambda: Absent("not_provided"))
    existing_medications: list[str] = Field(default_factory=list)

    @field_validator("notes", mode="before")
    @classmethod
    def normalize_notes(cls, value: object) -> OptionalValue[str]:
        if isinstance(value, (Provided, Absent)):
            return value
        return to_optional_value(value if isinstance(value, str) else None, reason="not_provided")


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
    auth: Annotated[
        PatientAuthorized | DoctorAuthorized | AdminAuthorized,
        Depends(require_authenticated),
    ],
    interpreter: Annotated[
        AuditedCompositeInterpreter,
        Depends(get_audited_composite_interpreter),
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
    # Determine filters based on role
    patient_id: UUID | None = None
    doctor_id: UUID | None = None

    match auth:
        case PatientAuthorized(patient_id=pid):
            patient_id = pid
        case DoctorAuthorized(doctor_id=did):
            doctor_id = did
        case AdminAuthorized():
            pass  # No filtering for admins

    def list_program() -> Generator[AllEffects, object, list[Prescription]]:
        prescriptions = yield ListPrescriptions(
            patient_id=to_optional_value(patient_id, reason="role_scope"),
            doctor_id=to_optional_value(doctor_id, reason="role_scope"),
        )
        assert isinstance(prescriptions, list)
        return prescriptions

    # Run effect program
    prescriptions = unwrap_program_result(await run_program(list_program(), interpreter))

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
    interpreter: Annotated[
        AuditedCompositeInterpreter,
        Depends(get_audited_composite_interpreter),
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

    result = unwrap_program_result(await run_program(program, interpreter))

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
    auth: Annotated[
        PatientAuthorized | DoctorAuthorized | AdminAuthorized,
        Depends(require_authenticated),
    ],
    interpreter: Annotated[
        AuditedCompositeInterpreter,
        Depends(get_audited_composite_interpreter),
    ],
    _rate_limit: Annotated[None, Depends(rate_limit(100, 60))],
) -> PrescriptionResponse:
    """Get prescription by ID.

    Requires: Patient (own prescription), Doctor (own prescription), or Admin.
    Logs all PHI access for HIPAA compliance.
    Rate limit: 100 requests per 60 seconds per IP address.
    """

    def get_program() -> Generator[AllEffects, object, PrescriptionFound | PrescriptionMissing]:
        result = yield GetPrescriptionById(prescription_id=UUID(prescription_id))
        assert is_prescription_lookup_result(result)
        return result

    # Run effect program
    prescription_result = unwrap_program_result(await run_program(get_program(), interpreter))

    match prescription_result:
        case PrescriptionFound(prescription=prescription):
            return prescription_to_response(prescription)
        case PrescriptionMissing():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Prescription {prescription_id} not found",
            )
        # MyPy enforces exhaustiveness - no fallback needed


@router.get("/patient/{patient_id}", response_model=list[PrescriptionResponse])
async def get_patient_prescriptions(
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
) -> list[PrescriptionResponse]:
    """Get all prescriptions for a patient.

    Requires: Patient (own prescriptions), Doctor, or Admin.
    Logs all PHI access for HIPAA compliance.
    Rate limit: 100 requests per 60 seconds per IP address.
    """

    def list_program() -> Generator[AllEffects, object, list[Prescription]]:
        prescriptions = yield ListPrescriptions(patient_id=UUID(patient_id), doctor_id=None)
        assert isinstance(prescriptions, list)
        return prescriptions

    # Run effect program
    prescriptions = unwrap_program_result(await run_program(list_program(), interpreter))

    return [prescription_to_response(p) for p in prescriptions]
