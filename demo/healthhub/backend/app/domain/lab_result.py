"""Lab result domain model."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class LabResult:
    """Lab test result entity.

    Immutable domain model following Effectful patterns.
    """

    id: UUID
    patient_id: UUID
    doctor_id: UUID
    test_type: str
    result_data: dict[str, str]  # Test-specific values
    critical: bool  # Requires immediate attention
    reviewed_by_doctor: bool
    doctor_notes: str | None
    created_at: datetime


# Lab Result Lookup ADT
@dataclass(frozen=True)
class LabResultFound:
    """Lab result lookup success."""

    lab_result: LabResult


@dataclass(frozen=True)
class LabResultNotFound:
    """Lab result lookup failure."""

    result_id: UUID
    reason: str


type LabResultLookupResult = LabResultFound | LabResultNotFound
