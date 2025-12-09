"""User domain model with role-based access."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from uuid import UUID

from effectful.domain.optional_value import OptionalValue


class UserRole(str, Enum):
    """User role enumeration.

    Values:
        PATIENT: Patient role with patient-specific access
        DOCTOR: Doctor role with medical provider access
        ADMIN: Administrator role with full system access
    """

    PATIENT = "patient"
    DOCTOR = "doctor"
    ADMIN = "admin"


class UserStatus(str, Enum):
    """User account status.

    Values:
        ACTIVE: Account is active and can authenticate
        INACTIVE: Account is inactive (not deleted)
        SUSPENDED: Account is suspended (cannot authenticate)
    """

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


@dataclass(frozen=True)
class User:
    """User entity with authentication and role information.

    Immutable domain model following Effectful patterns.

    Attributes:
        id: Unique user identifier
        email: User's email address (login identifier)
        password_hash: Bcrypt-hashed password
        role: User's role (patient, doctor, or admin)
        status: Account status (active, inactive, or suspended)
        last_login: Optional timestamp of last successful login
        created_at: Timestamp when user was created
        updated_at: Timestamp of last update
    """

    id: UUID
    email: str
    password_hash: str
    role: UserRole
    status: UserStatus
    last_login: OptionalValue[datetime]
    created_at: datetime
    updated_at: datetime
