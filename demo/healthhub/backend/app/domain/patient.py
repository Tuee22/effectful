"""Patient domain model."""

from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID


@dataclass(frozen=True)
class Patient:
    """Patient entity with medical demographics.

    Immutable domain model following Effectful patterns.
    """

    id: UUID
    user_id: UUID
    first_name: str
    last_name: str
    date_of_birth: date
    blood_type: str | None
    allergies: list[str]
    insurance_id: str | None
    emergency_contact: str
    phone: str | None
    address: str | None
    created_at: datetime
    updated_at: datetime
