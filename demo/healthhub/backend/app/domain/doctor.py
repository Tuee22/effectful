"""Doctor domain model."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.optional_value import OptionalValue


@dataclass(frozen=True)
class Doctor:
    """Doctor entity with credentials.

    Immutable domain model following Effectful patterns.
    """

    id: UUID
    user_id: UUID
    first_name: str
    last_name: str
    specialization: str
    license_number: str
    can_prescribe: bool
    phone: OptionalValue[str]
    created_at: datetime
    updated_at: datetime
