"""Integration tests for interpreters with real infrastructure.

Covers healthcare and notification interpreters against Postgres and Redis.
No mocks or fakes are used; all effects hit real services.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

import asyncpg
import pytest
import redis.asyncio as redis
from typing import Protocol, runtime_checkable, TypeGuard

from app.domain.appointment import (
    Appointment,
    Cancelled,
    Completed,
    Confirmed,
    InProgress,
    Requested,
    TransitionInvalid,
    TransitionSuccess,
)
from app.domain.invoice import Invoice, LineItem
from app.domain.lab_result import LabResult
from app.domain.doctor import Doctor
from app.domain.patient import Patient
from app.domain.lookup_result import (
    AppointmentFound,
    DoctorFound,
    DoctorMissingById,
    InvoiceFound,
    LabResultFound,
    PatientFound,
    PatientMissingById,
)
from app.domain.prescription import (
    MedicationInteractionWarning,
    NoInteractions,
    Prescription,
)
from effectful.domain.optional_value import from_optional_value, to_optional_value
from app.effects.healthcare import (
    AddInvoiceLineItem,
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
    UpdateInvoiceStatus,
)
from app.effects.notification import (
    AuditEventLogged,
    LogAuditEvent,
    NotificationPublished,
    NotificationValue,
    PublishWebSocketNotification,
)
from app.interpreters.healthcare_interpreter import HealthcareInterpreter
from app.interpreters.notification_interpreter import NotificationInterpreter
from app.programs.runner import run_program


@runtime_checkable
class SupportsAclose(Protocol):
    async def aclose(self) -> None: ...


def has_aclose(pubsub: object) -> TypeGuard[SupportsAclose]:
    return hasattr(pubsub, "aclose")


async def close_pubsub(pubsub: redis.client.PubSub | SupportsAclose) -> None:
    assert has_aclose(pubsub), "Redis PubSub missing aclose()"
    await pubsub.aclose()


@pytest.mark.asyncio
class TestHealthcareInterpreterIntegration:
    """Integration coverage for HealthcareInterpreter."""

    async def test_get_patient_by_id_round_trip(
        self,
        db_pool: asyncpg.Pool[asyncpg.Record],
        seed_test_patient: UUID,
    ) -> None:
        """Integration: GetPatientById returns seeded patient; unknown returns None."""
        interpreter = HealthcareInterpreter(db_pool)

        result = await interpreter.handle(GetPatientById(patient_id=seed_test_patient))
        assert isinstance(result, PatientFound)
        assert result.patient.id == seed_test_patient

        missing = await interpreter.handle(GetPatientById(patient_id=uuid4()))
        assert isinstance(missing, PatientMissingById)

    async def test_get_doctor_by_id_round_trip(
        self,
        db_pool: asyncpg.Pool[asyncpg.Record],
        seed_test_doctor: UUID,
    ) -> None:
        """Integration: GetDoctorById returns seeded doctor; unknown returns None."""
        interpreter = HealthcareInterpreter(db_pool)

        result = await interpreter.handle(GetDoctorById(doctor_id=seed_test_doctor))
        assert isinstance(result, DoctorFound)
        assert result.doctor.id == seed_test_doctor

        missing = await interpreter.handle(GetDoctorById(doctor_id=uuid4()))
        assert isinstance(missing, DoctorMissingById)

    async def test_create_and_fetch_appointment(
        self,
        db_pool: asyncpg.Pool[asyncpg.Record],
        seed_test_patient: UUID,
        seed_test_doctor: UUID,
        sample_user_id: UUID,
    ) -> None:
        """Integration: CreateAppointment persists Requested status and can be fetched."""
        interpreter = HealthcareInterpreter(db_pool)
        requested_time = datetime(2025, 1, 5, 15, 0, tzinfo=timezone.utc)
        reason = "Routine check"

        created = await interpreter.handle(
            CreateAppointment(
                patient_id=seed_test_patient,
                doctor_id=seed_test_doctor,
                requested_time=to_optional_value(requested_time, reason="not_requested"),
                reason=reason,
            )
        )

        assert isinstance(created, Appointment)
        assert isinstance(created.status, Requested)
        assert created.reason == reason

        fetched = await interpreter.handle(GetAppointmentById(appointment_id=created.id))
        assert isinstance(fetched, AppointmentFound)
        assert fetched.appointment.id == created.id
        assert isinstance(fetched.appointment.status, Requested)

        async with db_pool.acquire() as conn:
            row = await conn.fetchrow("SELECT status FROM appointments WHERE id = $1", created.id)
            assert row is not None
            assert row["status"] == "requested"

    async def test_transition_appointment_status_valid_and_invalid(
        self,
        db_pool: asyncpg.Pool[asyncpg.Record],
        seed_test_patient: UUID,
        seed_test_doctor: UUID,
        sample_user_id: UUID,
    ) -> None:
        """Integration: valid transition succeeds; invalid transition rejected without DB drift."""
        interpreter = HealthcareInterpreter(db_pool)
        appointment = await interpreter.handle(
            CreateAppointment(
                patient_id=seed_test_patient,
                doctor_id=seed_test_doctor,
                requested_time=to_optional_value(
                    datetime.now(timezone.utc), reason="not_requested"
                ),
                reason="Follow up",
            )
        )
        assert isinstance(appointment, Appointment)

        confirmed_status = Confirmed(
            confirmed_at=datetime.now(timezone.utc),
            scheduled_time=datetime(2025, 1, 6, 10, 0, tzinfo=timezone.utc),
        )
        transition_result = await interpreter.handle(
            TransitionAppointmentStatus(
                appointment_id=appointment.id,
                new_status=confirmed_status,
                actor_id=sample_user_id,
            )
        )
        assert isinstance(transition_result, TransitionSuccess)
        assert transition_result.new_status == confirmed_status

        # Force terminal status directly in DB then attempt invalid transition back to Requested
        completed_status = Completed(
            completed_at=datetime.now(timezone.utc),
            notes="Visit closed",
        )
        completed_metadata = json.dumps(
            {
                "completed_at": completed_status.completed_at.isoformat(),
                "notes": completed_status.notes,
            }
        )
        async with db_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE appointments
                SET status = 'completed', status_metadata = $1
                WHERE id = $2
                """,
                completed_metadata,
                appointment.id,
            )

        invalid_result = await interpreter.handle(
            TransitionAppointmentStatus(
                appointment_id=appointment.id,
                new_status=Requested(requested_at=datetime.now(timezone.utc)),
                actor_id=sample_user_id,
            )
        )
        assert isinstance(invalid_result, TransitionInvalid)

        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT status FROM appointments WHERE id = $1", appointment.id
            )
            assert row is not None
            assert row["status"] == "completed"

    async def test_create_prescription_and_interactions(
        self,
        db_pool: asyncpg.Pool[asyncpg.Record],
        seed_test_patient: UUID,
        seed_test_doctor: UUID,
    ) -> None:
        """Integration: CreatePrescription persists and interaction checks return correct ADTs."""
        interpreter = HealthcareInterpreter(db_pool)

        prescription = await interpreter.handle(
            CreatePrescription(
                patient_id=seed_test_patient,
                doctor_id=seed_test_doctor,
                medication="Lisinopril",
                dosage="10mg",
                frequency="once daily",
                duration_days=30,
                refills_remaining=2,
                notes=to_optional_value("Monitor BP", reason="provided"),
            )
        )
        assert isinstance(prescription, Prescription)
        assert prescription.patient_id == seed_test_patient

        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT medication, dosage FROM prescriptions WHERE id = $1",
                prescription.id,
            )
            assert row is not None
            assert row["medication"] == "Lisinopril"
            assert row["dosage"] == "10mg"

        warning = await interpreter.handle(
            CheckMedicationInteractions(medications=["Warfarin", "Aspirin"])
        )
        assert isinstance(warning, MedicationInteractionWarning)
        assert warning.severity == "severe"

        safe = await interpreter.handle(
            CheckMedicationInteractions(medications=["Metformin", "Atorvastatin"])
        )
        assert isinstance(safe, NoInteractions)
        assert "Metformin" in safe.medications_checked

    async def test_create_and_fetch_lab_result(
        self,
        db_pool: asyncpg.Pool[asyncpg.Record],
        seed_test_patient: UUID,
        seed_test_doctor: UUID,
    ) -> None:
        """Integration: CreateLabResult persists JSONB payload and can be retrieved."""
        interpreter = HealthcareInterpreter(db_pool)
        result_id = uuid4()
        created = await interpreter.handle(
            CreateLabResult(
                result_id=result_id,
                patient_id=seed_test_patient,
                doctor_id=seed_test_doctor,
                test_type="CBC",
                result_data={"wbc": "7.5", "rbc": "4.8"},
                critical=False,
                doctor_notes=to_optional_value(None, reason="not_provided"),
            )
        )
        assert isinstance(created, LabResult)
        assert created.id == result_id
        assert created.test_type == "CBC"

        fetched = await interpreter.handle(GetLabResultById(result_id=result_id))
        assert isinstance(fetched, LabResultFound)
        assert fetched.lab_result.id == result_id

    async def test_invoice_lifecycle_with_real_db(
        self,
        db_pool: asyncpg.Pool[asyncpg.Record],
        seed_test_patient: UUID,
    ) -> None:
        """Integration: CreateInvoice, AddInvoiceLineItem, and UpdateInvoiceStatus persist correctly."""
        interpreter = HealthcareInterpreter(db_pool)

        invoice = await interpreter.handle(
            CreateInvoice(
                patient_id=seed_test_patient,
                appointment_id=to_optional_value(None, reason="not_linked"),
                line_items=[],
                due_date=to_optional_value(date(2025, 1, 31), reason="provided"),
            )
        )
        assert isinstance(invoice, Invoice)
        assert invoice.status == "draft"

        line_item = await interpreter.handle(
            AddInvoiceLineItem(
                invoice_id=invoice.id,
                description="Labs",
                quantity=1,
                unit_price=Decimal("50.00"),
            )
        )
        assert isinstance(line_item, LineItem)
        assert line_item.invoice_id == invoice.id

        paid_result = await interpreter.handle(
            UpdateInvoiceStatus(
                invoice_id=invoice.id,
                status="paid",
            )
        )
        assert isinstance(paid_result, InvoiceFound)
        assert paid_result.invoice.status == "paid"

        async with db_pool.acquire() as conn:
            invoice_row = await conn.fetchrow(
                "SELECT status FROM invoices WHERE id = $1",
                invoice.id,
            )
            assert invoice_row is not None
            assert invoice_row["status"] == "paid"

            line_rows = await conn.fetch(
                "SELECT description, unit_price FROM invoice_line_items WHERE invoice_id = $1",
                invoice.id,
            )
            assert len(line_rows) == 1
            assert line_rows[0]["description"] == "Labs"


@pytest.mark.asyncio
class TestNotificationInterpreterIntegration:
    """Integration coverage for NotificationInterpreter against Redis and Postgres."""

    async def test_publish_websocket_notification_to_redis(
        self,
        db_pool: asyncpg.Pool[asyncpg.Record],
        redis_client: redis.Redis[bytes],
        clean_db: None,
    ) -> None:
        """Integration: PublishWebSocketNotification sends message to Redis pub/sub."""
        interpreter = NotificationInterpreter(db_pool, redis_client)

        channel = f"user:{uuid4()}:notifications"
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(channel)

        message: dict[str, NotificationValue] = {
            "type": "integration_notification",
            "content": "hello",
        }
        result = await interpreter.handle(
            PublishWebSocketNotification(
                channel=channel,
                message=message,
                recipient_id=to_optional_value(uuid4(), reason="recipient"),
            )
        )

        assert isinstance(result, NotificationPublished)

        received = await pubsub.get_message(timeout=2.0)
        if received and received["type"] == "subscribe":
            received = await pubsub.get_message(timeout=2.0)

        assert received is not None
        payload = received["data"]
        assert isinstance(payload, (str, bytes))
        parsed = json.loads(payload)
        assert parsed["type"] == "integration_notification"
        assert parsed["content"] == "hello"

        await pubsub.unsubscribe(channel)
        await close_pubsub(pubsub)

    async def test_log_audit_event_persists_to_db(
        self,
        db_pool: asyncpg.Pool[asyncpg.Record],
        redis_client: redis.Redis[bytes],
        seed_test_user: UUID,
        clean_db: None,
    ) -> None:
        """Integration: LogAuditEvent writes durable audit row."""
        interpreter = NotificationInterpreter(db_pool, redis_client)
        resource_id = uuid4()

        result = await interpreter.handle(
            LogAuditEvent(
                user_id=seed_test_user,
                action="view_record",
                resource_type="patient",
                resource_id=resource_id,
                ip_address=to_optional_value("10.0.0.1"),
                user_agent=to_optional_value("pytest"),
                metadata=to_optional_value({"context": "integration"}),
            )
        )
        assert isinstance(result, AuditEventLogged)

        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT action, resource_type, resource_id, user_id, metadata
                FROM audit_log
                WHERE resource_id = $1
                """,
                resource_id,
            )
            assert row is not None
            assert row["action"] == "view_record"
            assert row["resource_type"] == "patient"
            assert row["user_id"] == seed_test_user
            metadata_val = row["metadata"]
            if isinstance(metadata_val, str):
                parsed = json.loads(metadata_val)
            elif isinstance(metadata_val, dict):
                parsed = {str(k): str(v) for k, v in metadata_val.items()}
            else:
                parsed = {}
            assert parsed.get("context") == "integration"
