"""Lab result domain model.

Boundary: PURITY
Target-Language: Haskell

Pure immutable data model for lab test results.
Critical value indicators use typed ADTs, not boolean flags.
"""

from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from typing import Mapping
from uuid import UUID

from effectful.domain.optional_value import OptionalValue


@dataclass(frozen=True)
class LabResult:
    """Lab test result entity.

    Immutable domain model following Effectful patterns.

    Attributes:
        id: Unique lab result identifier
        patient_id: Patient UUID reference
        doctor_id: Ordering doctor UUID reference
        test_type: Type of lab test performed
        result_data: Test-specific result values (immutable mapping)
        critical: Whether result requires immediate attention
        reviewed_by_doctor: Whether doctor has reviewed the result
        doctor_notes: Optional doctor review notes
        created_at: Timestamp when result was created
    """

    id: UUID
    patient_id: UUID
    doctor_id: UUID
    test_type: str
    result_data: Mapping[str, str]  # Test-specific values
    critical: bool  # Requires immediate attention
    reviewed_by_doctor: bool
    doctor_notes: OptionalValue[str]
    created_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "result_data", MappingProxyType(dict(self.result_data)))


# Lab Result Lookup ADT
@dataclass(frozen=True)
class LabResultFound:
    """Lab result lookup success.

    Attributes:
        lab_result: The found lab result entity
    """

    lab_result: LabResult


@dataclass(frozen=True)
class LabResultNotFound:
    """Lab result lookup failure.

    Attributes:
        result_id: UUID of the lab result that was not found
        reason: Reason why result was not found
    """

    result_id: UUID
    reason: str


type LabResultLookupResult = LabResultFound | LabResultNotFound
"""Lab result lookup ADT.

Variants:
    LabResultFound: Lab result found successfully
    LabResultNotFound: Lab result not found with reason
"""
