"""User domain model with role-based access."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from uuid import UUID

from effectful.domain.optional_value import OptionalValue


class UserRole(str, Enum):
    """User role enumeration."""

    PATIENT = "patient"
    DOCTOR = "doctor"
    ADMIN = "admin"


class UserStatus(str, Enum):
    """User account status."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


@dataclass(frozen=True)
class User:
    """User entity with authentication and role information.

    Immutable domain model following Effectful patterns.
    """

    id: UUID
    email: str
    password_hash: str
    role: UserRole
    status: UserStatus
    last_login: OptionalValue[datetime]
    created_at: datetime
    updated_at: datetime
