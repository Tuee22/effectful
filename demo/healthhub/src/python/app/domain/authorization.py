"""ADT-based authorization states.

Boundary: PURITY
Target-Language: Haskell

Makes invalid authorization states unrepresentable through the type system.
Pattern: Instead of checking roles imperatively, we use ADT variants.
This is core to the Byzantine security model - unsafe auth states cannot be constructed.
"""

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from effectful.domain.optional_value import OptionalValue, to_optional_value
from app.domain.user import User


@dataclass(frozen=True)
class PatientAuthorized:
    """Patient authorized state.

    Represents a validated patient user with access to patient-specific resources.

    Attributes:
        user_id: Authenticated user's UUID
        patient_id: Associated patient record UUID
        email: User's email address
        role: Literal role indicator for type narrowing
    """

    user_id: UUID
    patient_id: UUID
    email: str
    role: Literal["patient"] = "patient"


@dataclass(frozen=True)
class DoctorAuthorized:
    """Doctor authorized state.

    Represents a validated doctor user with access to doctor-specific resources.

    Attributes:
        user_id: Authenticated user's UUID
        doctor_id: Associated doctor record UUID
        email: User's email address
        specialization: Doctor's medical specialization
        can_prescribe: Whether doctor is authorized to prescribe medications
        role: Literal role indicator for type narrowing
    """

    user_id: UUID
    doctor_id: UUID
    email: str
    specialization: str
    can_prescribe: bool
    role: Literal["doctor"] = "doctor"


@dataclass(frozen=True)
class AdminAuthorized:
    """Admin authorized state.

    Represents a validated admin user with full system access.

    Attributes:
        user_id: Authenticated user's UUID
        email: User's email address
        role: Literal role indicator for type narrowing
    """

    user_id: UUID
    email: str
    role: Literal["admin"] = "admin"


@dataclass(frozen=True)
class Unauthorized:
    """Unauthorized state.

    Represents failed authentication or insufficient permissions.

    Attributes:
        reason: Primary reason for authorization failure
        detail: Optional additional context about the failure
    """

    reason: str
    detail: OptionalValue[str]


# Authorization state ADT - makes illegal states unrepresentable
type AuthorizationState = PatientAuthorized | DoctorAuthorized | AdminAuthorized | Unauthorized
"""Authorization state ADT for role-based access control.

Variants:
    PatientAuthorized: Validated patient with patient_id and patient-specific access
    DoctorAuthorized: Validated doctor with doctor_id, specialization, and prescribe capability
    AdminAuthorized: Validated admin with full system access
    Unauthorized: Failed authentication or insufficient permissions with reason
"""


# Helper functions for creating authorization states
def create_patient_authorized(user: User, patient_id: UUID) -> PatientAuthorized:
    """Create patient authorized state from user and patient ID."""
    return PatientAuthorized(
        user_id=user.id,
        patient_id=patient_id,
        email=user.email,
    )


def create_doctor_authorized(
    user: User,
    doctor_id: UUID,
    specialization: str,
    can_prescribe: bool,
) -> DoctorAuthorized:
    """Create doctor authorized state from user and doctor info."""
    return DoctorAuthorized(
        user_id=user.id,
        doctor_id=doctor_id,
        email=user.email,
        specialization=specialization,
        can_prescribe=can_prescribe,
    )


def create_admin_authorized(user: User) -> AdminAuthorized:
    """Create admin authorized state from user."""
    return AdminAuthorized(
        user_id=user.id,
        email=user.email,
    )


def create_unauthorized(reason: str, detail: str | None = None) -> Unauthorized:
    """Create unauthorized state with reason."""
    return Unauthorized(reason=reason, detail=to_optional_value(detail, reason="not_provided"))
