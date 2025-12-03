"""Composite interpreter for routing effects.

Routes effects to specialized interpreters based on effect type.
"""

from __future__ import annotations

import asyncpg
import redis.asyncio as redis

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
from app.interpreters.healthcare_interpreter import HealthcareInterpreter
from app.interpreters.notification_interpreter import NotificationInterpreter


type AllEffects = HealthcareEffect | NotificationEffect

# Type for healthcare effect classes (for isinstance check)
_HEALTHCARE_EFFECTS = (
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


class CompositeInterpreter:
    """Composite interpreter that routes effects to specialized interpreters.

    This is Layer 3 in the 5-layer architecture:
    - Receives effects from the program runner
    - Routes to specialized interpreters (Layer 4)
    - Returns results back to the program
    """

    def __init__(
        self, pool: asyncpg.Pool[asyncpg.Record], redis_client: redis.Redis[bytes]
    ) -> None:
        """Initialize composite interpreter with infrastructure connections.

        Args:
            pool: asyncpg connection pool
            redis_client: Redis client for pub/sub
        """
        self.healthcare_interpreter = HealthcareInterpreter(pool)
        self.notification_interpreter = NotificationInterpreter(pool, redis_client)

    async def handle(self, effect: AllEffects) -> object:
        """Route effect to appropriate specialized interpreter.

        Args:
            effect: Effect to execute

        Returns:
            Result from specialized interpreter
        """
        # Route based on effect type using isinstance (avoids type alias pattern matching issues)
        if isinstance(effect, _HEALTHCARE_EFFECTS):
            return await self.healthcare_interpreter.handle(effect)
        else:
            # Must be NotificationEffect (PublishWebSocketNotification | LogAuditEvent)
            return await self.notification_interpreter.handle(effect)
