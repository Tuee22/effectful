"""Patient domain model."""

from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from effectful.domain.optional_value import OptionalValue


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
    blood_type: OptionalValue[str]
    allergies: tuple[str, ...]
    insurance_id: OptionalValue[str]
    emergency_contact: str
    phone: OptionalValue[str]
    address: OptionalValue[str]
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "allergies", tuple(self.allergies))
