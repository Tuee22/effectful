"""Audited composite interpreter wrapper.

Automatically records audit events for healthcare effects using the
existing notification interpreter. Keeps core interpreter unchanged while
ensuring PHI access/write paths emit audit events.
"""

from dataclasses import dataclass
from uuid import UUID

from app.effects.notification import LogAuditEvent
from app.interpreters.composite_interpreter import (
    AllEffects,
    CompositeInterpreter,
    _HEALTHCARE_EFFECTS,
)
from effectful.domain.optional_value import Absent, OptionalValue, Provided, to_optional_value

_NIL_UUID = UUID("00000000-0000-0000-0000-000000000000")


@dataclass(frozen=True)
class AuditContext:
    """Per-request audit context."""

    user_id: UUID
    ip_address: str | None
    user_agent: str | None


class AuditedCompositeInterpreter:
    """Decorator that emits audit events after executing effects."""

    def __init__(self, inner: CompositeInterpreter, audit_context: AuditContext) -> None:
        self.inner = inner
        self.audit_context = audit_context

    async def handle(self, effect: AllEffects) -> object:
        """Delegate to inner interpreter and emit audit event for healthcare effects."""
        result = await self.inner.handle(effect)

        if isinstance(effect, _HEALTHCARE_EFFECTS):
            await self._audit_effect(effect)

        return result

    async def _audit_effect(self, effect: AllEffects) -> None:
        """Emit a coarse-grained audit log for healthcare effect execution."""

        def _unwrap(value: object | None) -> UUID | None:
            if isinstance(value, UUID):
                return value
            if isinstance(value, Provided):
                inner = value.value
                return inner if isinstance(inner, UUID) else None
            if isinstance(value, Absent):
                return None
            return None

        resource_id = (
            _unwrap(getattr(effect, "patient_id", None))
            or _unwrap(getattr(effect, "appointment_id", None))
            or _unwrap(getattr(effect, "invoice_id", None))
            or _unwrap(getattr(effect, "result_id", None))
            or _unwrap(getattr(effect, "prescription_id", None))
            or _NIL_UUID
        )

        await self.inner.notification_interpreter.handle(
            LogAuditEvent(
                user_id=self.audit_context.user_id,
                action=f"effect:{type(effect).__name__}",
                resource_type="healthcare_effect",
                resource_id=resource_id if isinstance(resource_id, UUID) else _NIL_UUID,
                ip_address=to_optional_value(self.audit_context.ip_address, reason="not_provided"),
                user_agent=to_optional_value(self.audit_context.user_agent, reason="not_provided"),
                metadata=to_optional_value(None, reason="not_provided"),
            )
        )
