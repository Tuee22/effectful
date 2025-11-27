"""Doctor domain model."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


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
    phone: str | None
    created_at: datetime
    updated_at: datetime
