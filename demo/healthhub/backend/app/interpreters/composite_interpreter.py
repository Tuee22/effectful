"""Composite interpreter for routing effects.

Routes effects to specialized interpreters based on effect type.
"""

from __future__ import annotations

from typing import TypeGuard
from typing_extensions import assert_never

from app.protocols.database import DatabasePool
from app.protocols.observability import ObservabilityInterpreter as ObservabilityProtocol
from app.protocols.redis import RedisClient

from app.effects.healthcare import (
    AddInvoiceLineItem,
    HealthcareEffect,
    GetPatientById,
    GetDoctorById,
    GetDoctorByUserId,
    GetUserByEmail,
    CreateUser,
    UpdateUserLastLogin,
    CheckDatabaseHealth,
    CreateAppointment,
    GetAppointmentById,
    ListAppointments,
    TransitionAppointmentStatus,
    CreatePrescription,
    GetPrescriptionById,
    ListPrescriptions,
    CheckMedicationInteractions,
    CreateLabResult,
    GetLabResultById,
    ListLabResults,
    ReviewLabResult,
    CreateInvoice,
    GetInvoiceById,
    ListInvoices,
    UpdateInvoiceStatus,
    CreatePatient,
    ListPatients,
    UpdatePatient,
    DeletePatient,
    GetPatientByUserId,
    ListInvoiceLineItems,
)
from app.effects.notification import (
    NotificationEffect,
    PublishWebSocketNotification,
    LogAuditEvent,
)
from app.effects.observability import IncrementCounter, ObserveHistogram, ObservabilityEffect
from app.interpreters.healthcare_interpreter import HealthcareInterpreter
from app.interpreters.notification_interpreter import NotificationInterpreter


type AllEffects = HealthcareEffect | NotificationEffect | ObservabilityEffect

# Type for healthcare effect classes (for isinstance check)
_HEALTHCARE_EFFECTS: tuple[type[object], ...] = (
    GetPatientById,
    GetDoctorById,
    GetDoctorByUserId,
    GetUserByEmail,
    CreateUser,
    UpdateUserLastLogin,
    CreateAppointment,
    GetAppointmentById,
    ListAppointments,
    TransitionAppointmentStatus,
    CreatePrescription,
    GetPrescriptionById,
    ListPrescriptions,
    CheckMedicationInteractions,
    CreateLabResult,
    GetLabResultById,
    ListLabResults,
    ReviewLabResult,
    CreateInvoice,
    AddInvoiceLineItem,
    UpdateInvoiceStatus,
    GetInvoiceById,
    ListInvoices,
    CreatePatient,
    ListPatients,
    UpdatePatient,
    DeletePatient,
    GetPatientByUserId,
    ListInvoiceLineItems,
    CheckDatabaseHealth,
)

_NOTIFICATION_EFFECTS = (PublishWebSocketNotification, LogAuditEvent)
_OBSERVABILITY_EFFECTS = (IncrementCounter, ObserveHistogram)


def _is_healthcare_effect(effect: AllEffects) -> TypeGuard[HealthcareEffect]:
    return isinstance(effect, _HEALTHCARE_EFFECTS)


def _is_notification_effect(effect: AllEffects) -> TypeGuard[NotificationEffect]:
    return isinstance(effect, _NOTIFICATION_EFFECTS)


def _is_observability_effect(effect: AllEffects) -> TypeGuard[ObservabilityEffect]:
    return isinstance(effect, _OBSERVABILITY_EFFECTS)


class CompositeInterpreter:
    """Composite interpreter that routes effects to specialized interpreters.

    This is Layer 3 in the 5-layer architecture:
    - Receives effects from the program runner
    - Routes to specialized interpreters (Layer 4)
    - Returns results back to the program

    Accepts protocol dependencies, making lifecycle invisible to consumers.
    Zero awareness of whether dependencies are singletons, per-request, or test mocks.
    """

    def __init__(
        self,
        pool: DatabasePool,
        redis_client: RedisClient,
        observability_interpreter: ObservabilityProtocol,
    ) -> None:
        """Initialize composite interpreter with protocol implementations.

        Args:
            pool: Database pool protocol (production or test mock)
            redis_client: Redis client protocol (production or test mock)
            observability_interpreter: Observability interpreter protocol (production or test mock)

        Testing: Inject pytest-mock mocks with spec=Protocol
        """
        self.healthcare_interpreter = HealthcareInterpreter(pool)
        self.observability_interpreter = observability_interpreter
        self.notification_interpreter = NotificationInterpreter(
            pool, redis_client, self.observability_interpreter
        )

    async def handle(self, effect: AllEffects) -> object | None:
        """Route effect to appropriate specialized interpreter.

        Args:
            effect: Effect to execute

        Returns:
            Result from specialized interpreter
        """
        # Route based on effect type using isinstance (avoids type alias pattern matching issues)
        if _is_healthcare_effect(effect):
            return await self.healthcare_interpreter.handle(effect)
        if _is_notification_effect(effect):
            return await self.notification_interpreter.handle(effect)
        if _is_observability_effect(effect):
            return await self.observability_interpreter.handle(effect)
        raise AssertionError(f"Unhandled effect type: {type(effect).__name__}")
