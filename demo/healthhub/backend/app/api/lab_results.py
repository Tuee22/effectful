"""Lab Results API endpoints.

Provides CRUD operations for lab test results.
"""

from collections.abc import Generator
from datetime import datetime
from typing import Annotated
from uuid import UUID, uuid4
from typing_extensions import assert_never

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.database.converters import (
    safe_bool,
    safe_datetime,
    safe_optional_str,
    safe_uuid,
)
from app.domain.lab_result import LabResult
from effectful.domain.optional_value import from_optional_value, to_optional_value
from app.domain.lookup_result import LabResultFound, LabResultMissing, is_lab_result_lookup_result
from app.effects.healthcare import (
    CreateLabResult,
    GetLabResultById,
    ListLabResults,
    ReviewLabResult,
)
from app.infrastructure.rate_limiter import rate_limit
from app.interpreters.auditing_interpreter import AuditedCompositeInterpreter
from app.interpreters.composite_interpreter import AllEffects
from app.programs.runner import run_program
from app.api.dependencies import (
    AdminAuthorized,
    DoctorAuthorized,
    PatientAuthorized,
    get_audited_composite_interpreter,
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
    # Convert result_data dict[str, object] to dict[str, str]
    result_data_raw = row["result_data"]
    result_data: dict[str, str] = {}
    if isinstance(result_data_raw, dict):
        result_data = {str(k): str(v) for k, v in result_data_raw.items()}

    return LabResult(
        id=safe_uuid(row["id"]),
        patient_id=safe_uuid(row["patient_id"]),
        doctor_id=safe_uuid(row["doctor_id"]),
        test_type=str(row["test_type"]),
        result_data=result_data,
        critical=safe_bool(row["critical"]),
        reviewed_by_doctor=safe_bool(row["reviewed_by_doctor"]),
        doctor_notes=to_optional_value(
            safe_optional_str(row["doctor_notes"]), reason="not_recorded"
        ),
        created_at=safe_datetime(row["created_at"]),
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
        doctor_notes=from_optional_value(lab_result.doctor_notes),
        created_at=lab_result.created_at,
    )


@router.get("/", response_model=list[LabResultResponse])
async def list_lab_results(
    auth: Annotated[
        PatientAuthorized | DoctorAuthorized | AdminAuthorized,
        Depends(require_authenticated),
    ],
    interpreter: Annotated[
        AuditedCompositeInterpreter,
        Depends(get_audited_composite_interpreter),
    ],
    _rate_limit: Annotated[None, Depends(rate_limit(100, 60))],
) -> list[LabResultResponse]:
    """List lab results with role-based filtering.

    - Patient: sees only their own lab results
    - Doctor: sees lab results they ordered
    - Admin: sees all lab results

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

    def list_program() -> Generator[AllEffects, object, list[LabResult]]:
        lab_results = yield ListLabResults(patient_id=patient_id, doctor_id=doctor_id)
        assert isinstance(lab_results, list)
        return lab_results

    # Run effect program
    lab_results = await run_program(list_program(), interpreter)

    return [lab_result_to_response(lr) for lr in lab_results]


@router.post("/", response_model=LabResultResponse, status_code=status.HTTP_201_CREATED)
async def create_lab_result(
    request_data: CreateLabResultRequest,
    auth: Annotated[
        DoctorAuthorized | AdminAuthorized,
        Depends(require_doctor_or_admin),
    ],
    interpreter: Annotated[
        AuditedCompositeInterpreter,
        Depends(get_audited_composite_interpreter),
    ],
    _rate_limit: Annotated[None, Depends(rate_limit(100, 60))],
) -> LabResultResponse:
    """Create a new lab result.

    Requires: Doctor or Admin role.
    Rate limit: 100 requests per 60 seconds per IP address.
    """

    # Create effect program with audit logging
    def create_program() -> Generator[AllEffects, object, LabResult]:
        lab_result = yield CreateLabResult(
            result_id=uuid4(),
            patient_id=UUID(request_data.patient_id),
            doctor_id=UUID(request_data.doctor_id),
            test_type=request_data.test_type,
            result_data=request_data.result_data,
            critical=request_data.critical,
            doctor_notes=to_optional_value(request_data.doctor_notes, reason="not_provided"),
        )
        assert isinstance(lab_result, LabResult)
        return lab_result

    # Run effect program
    lab_result = await run_program(create_program(), interpreter)

    return lab_result_to_response(lab_result)


@router.get("/{lab_result_id}", response_model=LabResultResponse)
async def get_lab_result(
    lab_result_id: str,
    auth: Annotated[
        PatientAuthorized | DoctorAuthorized | AdminAuthorized,
        Depends(require_authenticated),
    ],
    interpreter: Annotated[
        AuditedCompositeInterpreter,
        Depends(get_audited_composite_interpreter),
    ],
    _rate_limit: Annotated[None, Depends(rate_limit(100, 60))],
) -> LabResultResponse:
    """Get lab result by ID.

    Requires appropriate authorization based on role.
    Logs all PHI access for HIPAA compliance.
    Rate limit: 100 requests per 60 seconds per IP address.
    """

    # Create effect program with audit logging
    def get_program() -> Generator[AllEffects, object, LabResultFound | LabResultMissing]:
        result = yield GetLabResultById(result_id=UUID(lab_result_id))
        assert is_lab_result_lookup_result(result)
        return result

    # Run effect program
    lab_result_result = await run_program(get_program(), interpreter)

    match lab_result_result:
        case LabResultFound(lab_result=lab_result):
            current_lab_result = lab_result
        case LabResultMissing(result_id=missing_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Lab result {missing_id} not found",
            )
        case _:
            assert_never(lab_result_result)

    # Authorization check - patient can only see their own results
    match auth:
        case PatientAuthorized(patient_id=patient_id):
            if current_lab_result.patient_id != patient_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to view this lab result",
                )
        case _:
            pass  # Doctors and admins can view any result

    return lab_result_to_response(current_lab_result)


@router.post("/{lab_result_id}/review", response_model=LabResultResponse)
async def review_lab_result(
    lab_result_id: str,
    request: ReviewLabResultRequest,
    auth: Annotated[
        DoctorAuthorized | AdminAuthorized,
        Depends(require_doctor_or_admin),
    ],
    interpreter: Annotated[
        AuditedCompositeInterpreter,
        Depends(get_audited_composite_interpreter),
    ],
    _rate_limit: Annotated[None, Depends(rate_limit(100, 60))],
) -> LabResultResponse:
    """Mark lab result as reviewed by doctor.

    Requires: Doctor or Admin role.
    Rate limit: 100 requests per 60 seconds per IP address.
    """

    # Create effect program
    def review_program() -> Generator[AllEffects, object, LabResultFound | LabResultMissing]:
        result = yield ReviewLabResult(
            result_id=UUID(lab_result_id),
            doctor_notes=request.doctor_notes,
        )
        assert is_lab_result_lookup_result(result)
        return result

    # Run effect program
    lab_result_result = await run_program(review_program(), interpreter)

    match lab_result_result:
        case LabResultFound(lab_result=lab_result):
            return lab_result_to_response(lab_result)
        case LabResultMissing(result_id=missing_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Lab result {missing_id} not found",
            )
        case _:
            assert_never(lab_result_result)


@router.get("/patient/{patient_id}", response_model=list[LabResultResponse])
async def get_patient_lab_results(
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
) -> list[LabResultResponse]:
    """Get all lab results for a patient.

    Requires appropriate authorization.
    Logs all PHI access for HIPAA compliance.
    Rate limit: 100 requests per 60 seconds per IP address.
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

    def list_program() -> Generator[AllEffects, object, list[LabResult]]:
        lab_results = yield ListLabResults(patient_id=UUID(patient_id), doctor_id=None)
        assert isinstance(lab_results, list)
        return lab_results

    # Run effect program
    lab_results = await run_program(list_program(), interpreter)

    return [lab_result_to_response(lr) for lr in lab_results]
