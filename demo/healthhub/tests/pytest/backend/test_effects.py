"""Unit tests for effect definitions.

Tests that effects are immutable frozen dataclasses and have correct structure.
"""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.domain.appointment import Confirmed
from app.domain.invoice import LineItem
from app.effects.healthcare import (
    CheckMedicationInteractions,
    CreateAppointment,
    CreateInvoice,
    CreateLabResult,
    CreatePrescription,
    GetAppointmentById,
    GetDoctorById,
    GetLabResultById,
    GetPatientById,
    TransitionAppointmentStatus,
)
from app.effects.notification import (
    LogAuditEvent,
    NotificationValue,
    PublishWebSocketNotification,
)


class TestHealthcareEffects:
    """Test healthcare effect definitions."""

    def test_get_patient_by_id_immutable(self) -> None:
        """GetPatientById should be immutable."""
        patient_id = uuid4()
        effect = GetPatientById(patient_id=patient_id)

        with pytest.raises(AttributeError):
            effect.patient_id = uuid4()  # type: ignore[misc]

    def test_get_patient_by_id_structure(self) -> None:
        """GetPatientById should have correct structure."""
        patient_id = uuid4()
        effect = GetPatientById(patient_id=patient_id)

        assert effect.patient_id == patient_id
        assert isinstance(effect.patient_id, UUID)

    def test_get_doctor_by_id_immutable(self) -> None:
        """GetDoctorById should be immutable."""
        doctor_id = uuid4()
        effect = GetDoctorById(doctor_id=doctor_id)

        with pytest.raises(AttributeError):
            effect.doctor_id = uuid4()  # type: ignore[misc]

    def test_create_appointment_immutable(self) -> None:
        """CreateAppointment should be immutable."""
        effect = CreateAppointment(
            patient_id=uuid4(),
            doctor_id=uuid4(),
            requested_time=datetime.now(timezone.utc),
            reason="Annual checkup",
        )

        with pytest.raises(AttributeError):
            effect.reason = "Different reason"  # type: ignore[misc]

    def test_create_appointment_structure(self) -> None:
        """CreateAppointment should have correct structure."""
        patient_id = uuid4()
        doctor_id = uuid4()
        requested_time = datetime.now(timezone.utc)
        reason = "Annual checkup"

        effect = CreateAppointment(
            patient_id=patient_id,
            doctor_id=doctor_id,
            requested_time=requested_time,
            reason=reason,
        )

        assert effect.patient_id == patient_id
        assert effect.doctor_id == doctor_id
        assert effect.requested_time == requested_time
        assert effect.reason == reason

    def test_transition_appointment_status_immutable(self) -> None:
        """TransitionAppointmentStatus should be immutable."""
        effect = TransitionAppointmentStatus(
            appointment_id=uuid4(),
            new_status=Confirmed(
                confirmed_at=datetime.now(timezone.utc),
                scheduled_time=datetime.now(timezone.utc),
            ),
            actor_id=uuid4(),
        )

        with pytest.raises(AttributeError):
            effect.actor_id = uuid4()  # type: ignore[misc]

    def test_create_prescription_immutable(self) -> None:
        """CreatePrescription should be immutable."""
        effect = CreatePrescription(
            patient_id=uuid4(),
            doctor_id=uuid4(),
            medication="Lisinopril",
            dosage="10mg",
            frequency="once daily",
            duration_days=30,
            refills_remaining=3,
            notes="Monitor blood pressure",
        )

        with pytest.raises(AttributeError):
            effect.dosage = "20mg"  # type: ignore[misc]

    def test_check_medication_interactions_immutable(self) -> None:
        """CheckMedicationInteractions should be immutable."""
        effect = CheckMedicationInteractions(medications=["Aspirin", "Warfarin"])

        with pytest.raises(AttributeError):
            effect.medications = ["Different"]  # type: ignore[misc]

    def test_create_lab_result_immutable(self) -> None:
        """CreateLabResult should be immutable."""
        effect = CreateLabResult(
            result_id=uuid4(),
            patient_id=uuid4(),
            doctor_id=uuid4(),
            test_type="CBC",
            result_data={"wbc": "7.5", "rbc": "4.8"},
            critical=False,
        )

        with pytest.raises(AttributeError):
            effect.critical = True  # type: ignore[misc]

    def test_create_invoice_immutable(self) -> None:
        """CreateInvoice should be immutable."""
        line_item = LineItem(
            id=uuid4(),
            invoice_id=uuid4(),
            description="Office visit",
            quantity=1,
            unit_price=Decimal("150.00"),
            total=Decimal("150.00"),
            created_at=datetime.now(timezone.utc),
        )

        effect = CreateInvoice(
            patient_id=uuid4(),
            appointment_id=uuid4(),
            line_items=[line_item],
            due_date=None,
        )

        with pytest.raises(AttributeError):
            effect.patient_id = uuid4()  # type: ignore[misc]


class TestNotificationEffects:
    """Test notification effect definitions."""

    def test_publish_websocket_notification_immutable(self) -> None:
        """PublishWebSocketNotification should be immutable."""
        effect = PublishWebSocketNotification(
            channel="patient:123:notifications",
            message={"type": "test", "data": "value"},
            recipient_id=uuid4(),
        )

        with pytest.raises(AttributeError):
            effect.channel = "different"  # type: ignore[misc]

    def test_publish_websocket_notification_structure(self) -> None:
        """PublishWebSocketNotification should have correct structure."""
        channel = "patient:123:notifications"
        message: dict[str, NotificationValue] = {"type": "test", "data": "value"}
        recipient_id = uuid4()

        effect = PublishWebSocketNotification(
            channel=channel,
            message=message,
            recipient_id=recipient_id,
        )

        assert effect.channel == channel
        assert effect.message == message
        assert effect.recipient_id == recipient_id

    def test_log_audit_event_immutable(self) -> None:
        """LogAuditEvent should be immutable."""
        effect = LogAuditEvent(
            user_id=uuid4(),
            action="view_patient",
            resource_type="patient",
            resource_id=uuid4(),
            ip_address="192.168.1.1",
            user_agent="Test Browser",
            metadata={"key": "value"},
        )

        with pytest.raises(AttributeError):
            effect.action = "different"  # type: ignore[misc]

    def test_log_audit_event_structure(self) -> None:
        """LogAuditEvent should have correct structure."""
        user_id = uuid4()
        action = "view_patient"
        resource_type = "patient"
        resource_id = uuid4()

        effect = LogAuditEvent(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=None,
            user_agent=None,
            metadata=None,
        )

        assert effect.user_id == user_id
        assert effect.action == action
        assert effect.resource_type == resource_type
        assert effect.resource_id == resource_id
        assert effect.ip_address is None
