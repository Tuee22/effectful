"""Domain models with algebraic data types (ADTs).

All domain models are immutable (frozen dataclasses) following Effectful patterns.
"""

from app.domain.user import User, UserRole, UserStatus
from app.domain.patient import Patient
from app.domain.doctor import Doctor
from app.domain.authorization import (
    AuthorizationState,
    PatientAuthorized,
    DoctorAuthorized,
    AdminAuthorized,
    Unauthorized,
    create_patient_authorized,
    create_doctor_authorized,
    create_admin_authorized,
    create_unauthorized,
)

__all__ = [
    "User",
    "UserRole",
    "UserStatus",
    "Patient",
    "Doctor",
    "AuthorizationState",
    "PatientAuthorized",
    "DoctorAuthorized",
    "AdminAuthorized",
    "Unauthorized",
    "create_patient_authorized",
    "create_doctor_authorized",
    "create_admin_authorized",
    "create_unauthorized",
]
