"""API routers for HealthHub."""

from app.api.health import router as health_router
from app.api.auth import router as auth_router
from app.api.patients import router as patients_router
from app.api.appointments import router as appointments_router
from app.api.prescriptions import router as prescriptions_router
from app.api.lab_results import router as lab_results_router
from app.api.invoices import router as invoices_router

__all__ = [
    "health_router",
    "auth_router",
    "patients_router",
    "appointments_router",
    "prescriptions_router",
    "lab_results_router",
    "invoices_router",
]
