"""Lab Results API endpoints.

Provides CRUD operations for lab test results.
"""

from collections.abc import Generator
from datetime import datetime
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
import redis.asyncio as redis

from app.database.converters import (
    safe_bool,
    safe_datetime,
    safe_optional_str,
    safe_uuid,
)
from app.domain.lab_result import LabResult
from app.effects.healthcare import (
    CreateLabResult,
    GetLabResultById,
    ListLabResults,
    ReviewLabResult,
)
from app.effects.notification import LogAuditEvent
from app.infrastructure import get_database_manager, rate_limit
from app.interpreters.composite_interpreter import AllEffects, CompositeInterpreter
from app.programs.runner import run_program
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
        doctor_notes=safe_optional_str(row["doctor_notes"]),
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
        doctor_notes=lab_result.doctor_notes,
        created_at=lab_result.created_at,
    )


@router.get("/", response_model=list[LabResultResponse])
async def list_lab_results(
    request: Request,
    auth: Annotated[
        PatientAuthorized | DoctorAuthorized | AdminAuthorized,
        Depends(require_authenticated),
    ],
    _rate_limit: Annotated[None, Depends(rate_limit(100, 60))],
) -> list[LabResultResponse]:
    """List lab results with role-based filtering.

    - Patient: sees only their own lab results
    - Doctor: sees lab results they ordered
    - Admin: sees all lab results

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

    try:
        # Create composite interpreter
        interpreter = CompositeInterpreter(pool, redis_client)

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

        # Create effect program with audit logging
        def list_program() -> Generator[AllEffects, object, list[LabResult]]:
            lab_results = yield ListLabResults(patient_id=patient_id, doctor_id=doctor_id)
            assert isinstance(lab_results, list)

            # HIPAA-required audit logging (log all PHI list access)
            resource_id = (
                lab_results[0].id if lab_results else UUID("00000000-0000-0000-0000-000000000000")
            )
            yield LogAuditEvent(
                user_id=actor_id,
                action="list_lab_results",
                resource_type="lab_result",
                resource_id=resource_id,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata={"count": str(len(lab_results))},
            )

            return lab_results

        # Run effect program
        lab_results = await run_program(list_program(), interpreter)

        return [lab_result_to_response(lr) for lr in lab_results]

    finally:
        await redis_client.aclose()


@router.post("/", response_model=LabResultResponse, status_code=status.HTTP_201_CREATED)
async def create_lab_result(
    request_data: CreateLabResultRequest,
    http_request: Request,
    auth: Annotated[
        DoctorAuthorized | AdminAuthorized,
        Depends(require_doctor_or_admin),
    ],
    _rate_limit: Annotated[None, Depends(rate_limit(100, 60))],
) -> LabResultResponse:
    """Create a new lab result.

    Requires: Doctor or Admin role.
    Rate limit: 100 requests per 60 seconds per IP address.
    """
    db_manager = get_database_manager()
    pool = db_manager.get_pool()

    # Create Redis client with resource management
    redis_client: redis.Redis[bytes] = redis.Redis(
        host="redis",
        port=6379,
        decode_responses=False,
    )

    try:
        # Create composite interpreter
        interpreter = CompositeInterpreter(pool, redis_client)

        # Extract actor ID from auth state
        actor_id: UUID
        match auth:
            case DoctorAuthorized(user_id=uid):
                actor_id = uid
            case AdminAuthorized(user_id=uid):
                actor_id = uid

        # Extract IP and user agent from request
        ip_address = http_request.client.host if http_request.client else None
        user_agent = http_request.headers.get("user-agent")

        # Create effect program with audit logging
        def create_program() -> Generator[AllEffects, object, LabResult]:
            lab_result = yield CreateLabResult(
                result_id=uuid4(),
                patient_id=UUID(request_data.patient_id),
                doctor_id=UUID(request_data.doctor_id),
                test_type=request_data.test_type,
                result_data=request_data.result_data,
                critical=request_data.critical,
                doctor_notes=request_data.doctor_notes,
            )

            # HIPAA-required audit logging
            assert isinstance(lab_result, LabResult)
            yield LogAuditEvent(
                user_id=actor_id,
                action="create_lab_result",
                resource_type="lab_result",
                resource_id=lab_result.id,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata={
                    "patient_id": str(request_data.patient_id),
                    "critical": str(request_data.critical),
                },
            )

            return lab_result

        # Run effect program
        lab_result = await run_program(create_program(), interpreter)

        return lab_result_to_response(lab_result)

    finally:
        await redis_client.aclose()


@router.get("/{lab_result_id}", response_model=LabResultResponse)
async def get_lab_result(
    lab_result_id: str,
    request: Request,
    auth: Annotated[
        PatientAuthorized | DoctorAuthorized | AdminAuthorized,
        Depends(require_authenticated),
    ],
    _rate_limit: Annotated[None, Depends(rate_limit(100, 60))],
) -> LabResultResponse:
    """Get lab result by ID.

    Requires appropriate authorization based on role.
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

    # Create composite interpreter
    interpreter = CompositeInterpreter(pool, redis_client)

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

    # Create effect program with audit logging
    def get_program() -> Generator[AllEffects, object, LabResult]:
        lab_result = yield GetLabResultById(result_id=UUID(lab_result_id))

        # HIPAA-required audit logging (log all access attempts)
        yield LogAuditEvent(
            user_id=actor_id,
            action="view_lab_result",
            resource_type="lab_result",
            resource_id=UUID(lab_result_id),
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={"status": "found" if lab_result else "not_found"},
        )

        if lab_result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Lab result {lab_result_id} not found",
            )
        assert isinstance(lab_result, LabResult)
        return lab_result

    # Run effect program
    lab_result = await run_program(get_program(), interpreter)

    await redis_client.aclose()

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
    _rate_limit: Annotated[None, Depends(rate_limit(100, 60))],
) -> LabResultResponse:
    """Mark lab result as reviewed by doctor.

    Requires: Doctor or Admin role.
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
    interpreter = CompositeInterpreter(pool, redis_client)

    # Create effect program
    def review_program() -> Generator[AllEffects, object, LabResult]:
        lab_result = yield ReviewLabResult(
            result_id=UUID(lab_result_id),
            doctor_notes=request.doctor_notes,
        )
        if lab_result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Lab result {lab_result_id} not found",
            )
        assert isinstance(lab_result, LabResult)
        return lab_result

    # Run effect program
    lab_result = await run_program(review_program(), interpreter)

    await redis_client.aclose()

    return lab_result_to_response(lab_result)


@router.get("/patient/{patient_id}", response_model=list[LabResultResponse])
async def get_patient_lab_results(
    patient_id: str,
    request: Request,
    auth: Annotated[
        PatientAuthorized | DoctorAuthorized | AdminAuthorized,
        Depends(require_authenticated),
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

    # Create effect program with audit logging
    def list_program() -> Generator[AllEffects, object, list[LabResult]]:
        lab_results = yield ListLabResults(patient_id=UUID(patient_id), doctor_id=None)
        assert isinstance(lab_results, list)

        # HIPAA-required audit logging (log all PHI list access)
        resource_id = (
            lab_results[0].id if lab_results else UUID("00000000-0000-0000-0000-000000000000")
        )
        yield LogAuditEvent(
            user_id=actor_id,
            action="list_patient_lab_results",
            resource_type="lab_result",
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={"count": str(len(lab_results)), "patient_id": patient_id},
        )

        return lab_results

    # Run effect program
    lab_results = await run_program(list_program(), interpreter)

    await redis_client.aclose()

    return [lab_result_to_response(lr) for lr in lab_results]
