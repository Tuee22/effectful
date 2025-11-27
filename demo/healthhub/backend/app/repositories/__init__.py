"""Repository pattern for database access."""

from app.repositories.user_repository import UserRepository
from app.repositories.patient_repository import PatientRepository
from app.repositories.doctor_repository import DoctorRepository

__all__ = [
    "UserRepository",
    "PatientRepository",
    "DoctorRepository",
]
