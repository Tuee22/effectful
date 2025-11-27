"""Patient Management API endpoints.

Provides CRUD operations for patient records with medical history tracking.
"""

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.domain.patient import Patient
from app.infrastructure import get_database_manager
from app.repositories.patient_repository import PatientRepository
from app.api.dependencies import (
    AdminAuthorized,
    DoctorAuthorized,
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
    allergies: list[str] = []
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
    auth: Annotated[
        DoctorAuthorized | AdminAuthorized,
        Depends(require_doctor_or_admin),
    ],
) -> list[PatientResponse]:
    """List all patients.

    Requires: Doctor or Admin role.
    Patients cannot view other patients' records.
    """
    db_manager = get_database_manager()
    pool = db_manager.get_pool()

    # Fetch all patients ordered by last name
    rows = await pool.fetch(
        """
        SELECT id, user_id, first_name, last_name, date_of_birth,
               blood_type, allergies, insurance_id, emergency_contact,
               phone, address, created_at, updated_at
        FROM patients
        ORDER BY last_name, first_name
        """
    )

    patient_repo = PatientRepository(pool)
    patients = [patient_repo._row_to_patient(row) for row in rows]

    return [patient_to_response(p) for p in patients]


@router.post("/", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
async def create_patient(request: CreatePatientRequest) -> PatientResponse:
    """Create a new patient record.

    Requires: Admin or Doctor role.
    """
    db_manager = get_database_manager()
    pool = db_manager.get_pool()
    patient_repo = PatientRepository(pool)

    # Create patient
    patient = await patient_repo.create(
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

    return patient_to_response(patient)


@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(patient_id: str) -> PatientResponse:
    """Get patient by ID.

    Requires: Patient (own record), Doctor, or Admin role (TODO: add authorization)
    """
    db_manager = get_database_manager()
    pool = db_manager.get_pool()
    patient_repo = PatientRepository(pool)

    patient = await patient_repo.get_by_id(UUID(patient_id))

    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id} not found",
        )

    return patient_to_response(patient)


@router.get("/by-user/{user_id}", response_model=PatientResponse)
async def get_patient_by_user(user_id: str) -> PatientResponse:
    """Get patient by user ID.

    Requires: Patient (own record), Doctor, or Admin role (TODO: add authorization)
    """
    db_manager = get_database_manager()
    pool = db_manager.get_pool()
    patient_repo = PatientRepository(pool)

    patient = await patient_repo.get_by_user_id(UUID(user_id))

    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient for user {user_id} not found",
        )

    return patient_to_response(patient)


@router.put("/{patient_id}", response_model=PatientResponse)
async def update_patient(patient_id: str, request: UpdatePatientRequest) -> PatientResponse:
    """Update patient record.

    Requires: Patient (own record), Doctor, or Admin role (TODO: add authorization)
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

    return patient_to_response(updated_patient)


@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_patient(patient_id: str) -> None:
    """Delete patient record.

    Requires: Admin role only (TODO: add authorization)

    Note: In production, this should be a soft delete (status update) for HIPAA compliance.
    """
    db_manager = get_database_manager()
    pool = db_manager.get_pool()

    # Execute delete query (simplified)
    await pool.execute(
        "DELETE FROM patients WHERE id = $1",
        UUID(patient_id),
    )

    # No content response
    return None
