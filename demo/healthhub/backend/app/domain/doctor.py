"""Doctor domain model."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from effectful.domain.optional_value import OptionalValue


@dataclass(frozen=True)
class Doctor:
    """Doctor entity with credentials.

    Immutable domain model following Effectful patterns.

    Attributes:
        id: Unique doctor identifier
        user_id: Associated user account UUID
        first_name: Doctor's first name
        last_name: Doctor's last name
        specialization: Medical specialization
        license_number: Medical license number
        can_prescribe: Whether authorized to prescribe medications
        phone: Optional phone number
        created_at: Timestamp when doctor record was created
        updated_at: Timestamp of last update
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
