"""Patient domain model.

Boundary: PURITY
Target-Language: Haskell

Pure immutable data model representing a patient entity.
Contains no side effects, I/O operations, or mutable state.
All fields use frozen dataclasses with explicit types.
"""

from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from effectful.domain.optional_value import OptionalValue


@dataclass(frozen=True)
class Patient:
    """Patient entity with medical demographics.

    Immutable domain model following Effectful patterns.

    Attributes:
        id: Unique patient identifier
        user_id: Associated user account UUID
        first_name: Patient's first name
        last_name: Patient's last name
        date_of_birth: Patient's date of birth
        blood_type: Optional blood type
        allergies: Tuple of known allergies
        insurance_id: Optional insurance identifier
        emergency_contact: Emergency contact information
        phone: Optional phone number
        address: Optional address
        created_at: Timestamp when patient record was created
        updated_at: Timestamp of last update
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
