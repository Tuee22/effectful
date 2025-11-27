"""Lab Results API endpoints.

Provides CRUD operations for lab test results.
"""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.domain.lab_result import LabResult
from app.infrastructure import get_database_manager
from app.api.dependencies import (
    AdminAuthorized,
    DoctorAuthorized,
    PatientAuthorized,
    require_authenticated,
    require_doctor_or_admin,
)

router = APIRouter()


class LabResultResponse(BaseModel):
    """Lab result response model."""

    id: str
    patient_id: str
    doctor_id: str
    test_type: str
    result_data: dict[str, str]
    critical: bool
    reviewed_by_doctor: bool
    doctor_notes: str | None
    created_at: datetime


class CreateLabResultRequest(BaseModel):
    """Create lab result request."""

    patient_id: str
    doctor_id: str
    test_type: str
    result_data: dict[str, str]
    critical: bool = False
    doctor_notes: str | None = None


class ReviewLabResultRequest(BaseModel):
    """Review lab result request (doctor marks as reviewed)."""

    doctor_notes: str | None = None


def _row_to_lab_result(row: dict[str, object]) -> LabResult:
    """Convert database row to LabResult domain model."""
    return LabResult(
        id=row["id"],  # type: ignore[arg-type]
        patient_id=row["patient_id"],  # type: ignore[arg-type]
        doctor_id=row["doctor_id"],  # type: ignore[arg-type]
        test_type=str(row["test_type"]),
        result_data=row["result_data"],  # type: ignore[arg-type]
        critical=bool(row["critical"]),
        reviewed_by_doctor=bool(row["reviewed_by_doctor"]),
        doctor_notes=row["doctor_notes"] if row["doctor_notes"] else None,  # type: ignore[arg-type]
        created_at=row["created_at"],  # type: ignore[arg-type]
    )


def lab_result_to_response(lab_result: LabResult) -> LabResultResponse:
    """Convert LabResult domain model to API response."""
    return LabResultResponse(
        id=str(lab_result.id),
        patient_id=str(lab_result.patient_id),
        doctor_id=str(lab_result.doctor_id),
        test_type=lab_result.test_type,
        result_data=lab_result.result_data,
        critical=lab_result.critical,
        reviewed_by_doctor=lab_result.reviewed_by_doctor,
        doctor_notes=lab_result.doctor_notes,
        created_at=lab_result.created_at,
    )


@router.get("/", response_model=list[LabResultResponse])
async def list_lab_results(
    auth: Annotated[
        PatientAuthorized | DoctorAuthorized | AdminAuthorized,
        Depends(require_authenticated),
    ],
) -> list[LabResultResponse]:
    """List lab results with role-based filtering.

    - Patient: sees only their own lab results
    - Doctor: sees lab results they ordered
    - Admin: sees all lab results
    """
    db_manager = get_database_manager()
    pool = db_manager.get_pool()

    # Build query based on role
    match auth:
        case PatientAuthorized(patient_id=patient_id):
            query = """
                SELECT id, patient_id, doctor_id, test_type, result_data,
                       critical, reviewed_by_doctor, doctor_notes, created_at
                FROM lab_results
                WHERE patient_id = $1
                ORDER BY created_at DESC
            """
            rows = await pool.fetch(query, patient_id)

        case DoctorAuthorized(doctor_id=doctor_id):
            query = """
                SELECT id, patient_id, doctor_id, test_type, result_data,
                       critical, reviewed_by_doctor, doctor_notes, created_at
                FROM lab_results
                WHERE doctor_id = $1
                ORDER BY created_at DESC
            """
            rows = await pool.fetch(query, doctor_id)

        case AdminAuthorized():
            query = """
                SELECT id, patient_id, doctor_id, test_type, result_data,
                       critical, reviewed_by_doctor, doctor_notes, created_at
                FROM lab_results
                ORDER BY created_at DESC
            """
            rows = await pool.fetch(query)

    lab_results = [_row_to_lab_result(dict(row)) for row in rows]
    return [lab_result_to_response(lr) for lr in lab_results]


@router.post("/", response_model=LabResultResponse, status_code=status.HTTP_201_CREATED)
async def create_lab_result(
    request: CreateLabResultRequest,
    auth: Annotated[
        DoctorAuthorized | AdminAuthorized,
        Depends(require_doctor_or_admin),
    ],
) -> LabResultResponse:
    """Create a new lab result.

    Requires: Doctor or Admin role.
    """
    db_manager = get_database_manager()
    pool = db_manager.get_pool()

    import json

    row = await pool.fetchrow(
        """
        INSERT INTO lab_results (patient_id, doctor_id, test_type, result_data, critical, doctor_notes)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING id, patient_id, doctor_id, test_type, result_data, critical,
                  reviewed_by_doctor, doctor_notes, created_at
        """,
        UUID(request.patient_id),
        UUID(request.doctor_id),
        request.test_type,
        json.dumps(request.result_data),
        request.critical,
        request.doctor_notes,
    )

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create lab result",
        )

    lab_result = _row_to_lab_result(dict(row))
    return lab_result_to_response(lab_result)


@router.get("/{lab_result_id}", response_model=LabResultResponse)
async def get_lab_result(
    lab_result_id: str,
    auth: Annotated[
        PatientAuthorized | DoctorAuthorized | AdminAuthorized,
        Depends(require_authenticated),
    ],
) -> LabResultResponse:
    """Get lab result by ID.

    Requires appropriate authorization based on role.
    """
    db_manager = get_database_manager()
    pool = db_manager.get_pool()

    row = await pool.fetchrow(
        """
        SELECT id, patient_id, doctor_id, test_type, result_data,
               critical, reviewed_by_doctor, doctor_notes, created_at
        FROM lab_results
        WHERE id = $1
        """,
        UUID(lab_result_id),
    )

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lab result {lab_result_id} not found",
        )

    lab_result = _row_to_lab_result(dict(row))

    # Authorization check - patient can only see their own results
    match auth:
        case PatientAuthorized(patient_id=patient_id):
            if lab_result.patient_id != patient_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to view this lab result",
                )
        case _:
            pass  # Doctors and admins can view any result

    return lab_result_to_response(lab_result)


@router.post("/{lab_result_id}/review", response_model=LabResultResponse)
async def review_lab_result(
    lab_result_id: str,
    request: ReviewLabResultRequest,
    auth: Annotated[
        DoctorAuthorized | AdminAuthorized,
        Depends(require_doctor_or_admin),
    ],
) -> LabResultResponse:
    """Mark lab result as reviewed by doctor.

    Requires: Doctor or Admin role.
    """
    db_manager = get_database_manager()
    pool = db_manager.get_pool()

    row = await pool.fetchrow(
        """
        UPDATE lab_results
        SET reviewed_by_doctor = TRUE, doctor_notes = COALESCE($2, doctor_notes)
        WHERE id = $1
        RETURNING id, patient_id, doctor_id, test_type, result_data, critical,
                  reviewed_by_doctor, doctor_notes, created_at
        """,
        UUID(lab_result_id),
        request.doctor_notes,
    )

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lab result {lab_result_id} not found",
        )

    lab_result = _row_to_lab_result(dict(row))
    return lab_result_to_response(lab_result)


@router.get("/patient/{patient_id}", response_model=list[LabResultResponse])
async def get_patient_lab_results(
    patient_id: str,
    auth: Annotated[
        PatientAuthorized | DoctorAuthorized | AdminAuthorized,
        Depends(require_authenticated),
    ],
) -> list[LabResultResponse]:
    """Get all lab results for a patient.

    Requires appropriate authorization.
    """
    # Authorization check
    match auth:
        case PatientAuthorized(patient_id=auth_patient_id):
            if str(auth_patient_id) != patient_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to view these lab results",
                )
        case _:
            pass  # Doctors and admins can view any patient's results

    db_manager = get_database_manager()
    pool = db_manager.get_pool()

    rows = await pool.fetch(
        """
        SELECT id, patient_id, doctor_id, test_type, result_data,
               critical, reviewed_by_doctor, doctor_notes, created_at
        FROM lab_results
        WHERE patient_id = $1
        ORDER BY created_at DESC
        """,
        UUID(patient_id),
    )

    lab_results = [_row_to_lab_result(dict(row)) for row in rows]
    return [lab_result_to_response(lr) for lr in lab_results]
