"""Prescription Management API endpoints.

Provides prescription creation with medication interaction checking.
"""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
import redis.asyncio as redis

from app.domain.prescription import (
    MedicationInteractionWarning,
    Prescription,
)
from app.infrastructure import get_database_manager
from app.interpreters.composite_interpreter import CompositeInterpreter
from app.interpreters.healthcare_interpreter import HealthcareInterpreter
from app.programs.prescription_programs import create_prescription_program
from app.programs.runner import run_program
from app.api.dependencies import (
    AdminAuthorized,
    DoctorAuthorized,
    PatientAuthorized,
    require_authenticated,
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
    existing_medications: list[str] = []


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
) -> list[PrescriptionResponse]:
    """List prescriptions with role-based filtering.

    - Patient: sees only their own prescriptions
    - Doctor: sees prescriptions they created
    - Admin: sees all prescriptions
    """
    db_manager = get_database_manager()
    pool = db_manager.get_pool()
    interpreter = HealthcareInterpreter(pool)

    # Build query based on role
    match auth:
        case PatientAuthorized(patient_id=patient_id):
            query = """
                SELECT id, patient_id, doctor_id, medication, dosage,
                       frequency, duration_days, refills_remaining, notes,
                       created_at, expires_at
                FROM prescriptions
                WHERE patient_id = $1
                ORDER BY created_at DESC
            """
            rows = await pool.fetch(query, patient_id)

        case DoctorAuthorized(doctor_id=doctor_id):
            query = """
                SELECT id, patient_id, doctor_id, medication, dosage,
                       frequency, duration_days, refills_remaining, notes,
                       created_at, expires_at
                FROM prescriptions
                WHERE doctor_id = $1
                ORDER BY created_at DESC
            """
            rows = await pool.fetch(query, doctor_id)

        case AdminAuthorized():
            query = """
                SELECT id, patient_id, doctor_id, medication, dosage,
                       frequency, duration_days, refills_remaining, notes,
                       created_at, expires_at
                FROM prescriptions
                ORDER BY created_at DESC
            """
            rows = await pool.fetch(query)

    prescriptions = [interpreter._row_to_prescription(row) for row in rows]

    return [prescription_to_response(p) for p in prescriptions]


@router.post(
    "/",
    response_model=PrescriptionResponse | dict[str, object],
    status_code=status.HTTP_201_CREATED,
)
async def create_prescription(
    request: CreatePrescriptionRequest,
) -> PrescriptionResponse | dict[str, object]:
    """Create new prescription with interaction checking.

    Uses effect program: create_prescription_program
    Checks medication interactions before creating.
    Blocks creation if severe interaction detected.

    Requires: Doctor role (TODO: add authorization)

    Returns:
        - PrescriptionResponse: if created successfully
        - dict with warning: if severe interaction blocks creation
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
    program = create_prescription_program(
        patient_id=UUID(request.patient_id),
        doctor_id=UUID(request.doctor_id),
        medication=request.medication,
        dosage=request.dosage,
        frequency=request.frequency,
        duration_days=request.duration_days,
        refills_remaining=request.refills_remaining,
        notes=request.notes,
        actor_id=UUID(request.doctor_id),  # TODO: Get from JWT
        existing_medications=request.existing_medications,
    )

    result = await run_program(program, interpreter)

    await redis_client.aclose()

    # Handle result
    match result:
        case Prescription():
            return prescription_to_response(result)

        case MedicationInteractionWarning():
            # Severe interaction blocked creation
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "severe_medication_interaction",
                    "medications": result.medications,
                    "severity": result.severity,
                    "description": result.description,
                },
            )

        case str():
            # Validation error
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result,
            )

        case _:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unexpected error creating prescription",
            )


@router.get("/{prescription_id}", response_model=PrescriptionResponse)
async def get_prescription(prescription_id: str) -> PrescriptionResponse:
    """Get prescription by ID.

    Requires: Patient (own prescription), Doctor (own prescription), or Admin (TODO: add authorization)
    """
    db_manager = get_database_manager()
    pool = db_manager.get_pool()

    row = await pool.fetchrow(
        """
        SELECT id, patient_id, doctor_id, medication, dosage,
               frequency, duration_days, refills_remaining, notes,
               created_at, expires_at
        FROM prescriptions
        WHERE id = $1
        """,
        UUID(prescription_id),
    )

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prescription {prescription_id} not found",
        )

    # Convert row to Prescription
    interpreter = HealthcareInterpreter(pool)
    prescription = interpreter._row_to_prescription(row)

    return prescription_to_response(prescription)


@router.get("/patient/{patient_id}", response_model=list[PrescriptionResponse])
async def get_patient_prescriptions(patient_id: str) -> list[PrescriptionResponse]:
    """Get all prescriptions for a patient.

    Requires: Patient (own prescriptions), Doctor, or Admin (TODO: add authorization)
    """
    db_manager = get_database_manager()
    pool = db_manager.get_pool()

    rows = await pool.fetch(
        """
        SELECT id, patient_id, doctor_id, medication, dosage,
               frequency, duration_days, refills_remaining, notes,
               created_at, expires_at
        FROM prescriptions
        WHERE patient_id = $1
        ORDER BY created_at DESC
        """,
        UUID(patient_id),
    )

    interpreter = HealthcareInterpreter(pool)
    prescriptions = [interpreter._row_to_prescription(row) for row in rows]

    return [prescription_to_response(p) for p in prescriptions]
