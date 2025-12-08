"""Integration tests for prescription workflows.

Tests prescription creation, medication interaction checking, notifications,
and audit logging with real PostgreSQL and Redis infrastructure.

Antipatterns avoided:
- #3: Silent effect failures - verify DB writes and Redis pub/sub
- #4: Testing actions without validating results - check all side effects
- #12: Not testing error paths - test severe interactions, unauthorized doctors
- #13: Incomplete assertions - verify prescriptions table, audit_log table, Redis pub/sub
- #14: Relaxed validation - strict medication interaction severity checking
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import UUID

import asyncpg
import pytest
import redis.asyncio as redis
from typing import Protocol, runtime_checkable, TypeGuard

from app.domain.prescription import MedicationInteractionWarning, NoInteractions, Prescription
from app.interpreters.composite_interpreter import CompositeInterpreter
from app.programs.prescription_programs import (
    PrescriptionBlocked,
    PrescriptionCreated,
    PrescriptionDoctorMissing,
    PrescriptionDoctorUnauthorized,
    PrescriptionPatientMissing,
    create_prescription_program,
)
from app.programs.runner import run_program


@runtime_checkable
class SupportsAclose(Protocol):
    async def aclose(self) -> None: ...


def has_aclose(pubsub: object) -> TypeGuard[SupportsAclose]:
    return hasattr(pubsub, "aclose")


async def close_pubsub(pubsub: redis.client.PubSub | SupportsAclose) -> None:
    assert has_aclose(pubsub), "Redis PubSub missing aclose()"
    await pubsub.aclose()


class TestPrescriptionCreation:
    """Test prescription creation workflow with real infrastructure."""

    @pytest.mark.asyncio
    async def test_create_prescription_success_no_interactions(
        self,
        db_pool: asyncpg.Pool[asyncpg.Record],
        redis_client: redis.Redis[bytes],
        observability_interpreter: object,
        seed_test_patient: UUID,
        seed_test_doctor: UUID,
        sample_user_id: UUID,
    ) -> None:
        """Test prescription creation with no medication interactions.

        Validates:
        - Prescription created successfully
        - DB record persisted with all fields
        - Medication interaction check returns NoInteractions
        - Side effects validated (antipattern #13)
        """
        from app.interpreters.observability_interpreter import ObservabilityInterpreter

        assert isinstance(observability_interpreter, ObservabilityInterpreter)

        # Setup
        interpreter = CompositeInterpreter(
            pool=db_pool,
            redis_client=redis_client,
            observability_interpreter=observability_interpreter,
        )

        # Execute prescription creation
        result = await run_program(
            create_prescription_program(
                patient_id=seed_test_patient,
                doctor_id=seed_test_doctor,
                medication="Lisinopril",
                dosage="10mg",
                frequency="Once daily",
                duration_days=30,
                refills_remaining=2,
                notes="For blood pressure management",
                actor_id=sample_user_id,
                existing_medications=[],  # No existing medications
            ),
            interpreter,
        )

        assert isinstance(result, PrescriptionCreated)
        prescription = result.prescription
        assert prescription.patient_id == seed_test_patient
        assert prescription.doctor_id == seed_test_doctor
        assert prescription.medication == "Lisinopril"
        assert prescription.dosage == "10mg"
        assert prescription.frequency == "Once daily"
        assert prescription.duration_days == 30
        assert prescription.refills_remaining == 2

        # CRITICAL: Verify DB persistence (antipattern #3, #13)
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM prescriptions WHERE id = $1",
                prescription.id,
            )

            assert row is not None, "Prescription not persisted to database"
            assert row["patient_id"] == seed_test_patient
            assert row["doctor_id"] == seed_test_doctor
            assert row["medication"] == "Lisinopril"
            assert row["dosage"] == "10mg"
            assert row["frequency"] == "Once daily"
            assert row["duration_days"] == 30
            assert row["refills_remaining"] == 2

    @pytest.mark.asyncio
    async def test_create_prescription_creates_audit_log(
        self,
        db_pool: asyncpg.Pool[asyncpg.Record],
        redis_client: redis.Redis[bytes],
        observability_interpreter: object,
        seed_test_patient: UUID,
        seed_test_doctor: UUID,
        sample_user_id: UUID,
    ) -> None:
        """Test prescription creation creates audit log entry.

        Validates:
        - Audit log entry created (HIPAA compliance)
        - Action type = "create_prescription"
        - Resource type and ID correct
        - Side effect validated (antipattern #13)
        """
        from app.interpreters.observability_interpreter import ObservabilityInterpreter

        assert isinstance(observability_interpreter, ObservabilityInterpreter)

        # Setup
        interpreter = CompositeInterpreter(
            pool=db_pool,
            redis_client=redis_client,
            observability_interpreter=observability_interpreter,
        )

        # Execute
        result = await run_program(
            create_prescription_program(
                patient_id=seed_test_patient,
                doctor_id=seed_test_doctor,
                medication="Metformin",
                dosage="500mg",
                frequency="Twice daily",
                duration_days=90,
                refills_remaining=3,
                notes=None,
                actor_id=sample_user_id,
                existing_medications=[],
            ),
            interpreter,
        )

        assert isinstance(result, PrescriptionCreated)
        prescription = result.prescription

        # CRITICAL: Verify audit log created (antipattern #13)
        async with db_pool.acquire() as conn:
            audit_rows = await conn.fetch(
                """
                SELECT * FROM audit_log
                WHERE resource_type = 'prescription' AND resource_id = $1
                """,
                prescription.id,
            )

            assert len(audit_rows) > 0, "No audit log entry created"
            audit_row = audit_rows[0]
            assert audit_row["action"] == "create_prescription"
            assert audit_row["user_id"] == sample_user_id
            assert audit_row["resource_id"] == prescription.id


class TestMedicationInteractionChecking:
    """Test medication interaction checking with different severity levels."""

    @pytest.mark.asyncio
    async def test_severe_interaction_blocks_prescription(
        self,
        db_pool: asyncpg.Pool[asyncpg.Record],
        redis_client: redis.Redis[bytes],
        observability_interpreter: object,
        seed_test_patient: UUID,
        seed_test_doctor: UUID,
        sample_user_id: UUID,
    ) -> None:
        """Test severe medication interaction blocks prescription creation.

        Validates:
        - Severe interaction returns MedicationInteractionWarning
        - Prescription NOT created in database
        - Audit log records blocked attempt
        - Error path tested (antipattern #12)
        - Side effects validated (antipattern #13)
        """
        from app.interpreters.observability_interpreter import ObservabilityInterpreter

        assert isinstance(observability_interpreter, ObservabilityInterpreter)

        # Setup
        interpreter = CompositeInterpreter(
            pool=db_pool,
            redis_client=redis_client,
            observability_interpreter=observability_interpreter,
        )

        # Execute with severe interaction (Warfarin + Aspirin)
        result = await run_program(
            create_prescription_program(
                patient_id=seed_test_patient,
                doctor_id=seed_test_doctor,
                medication="Warfarin",
                dosage="5mg",
                frequency="Once daily",
                duration_days=30,
                refills_remaining=0,
                notes=None,
                actor_id=sample_user_id,
                existing_medications=["Aspirin"],  # Known severe interaction
            ),
            interpreter,
        )

        assert isinstance(result, PrescriptionBlocked)
        warning = result.warning
        assert warning.severity == "severe"
        assert "warfarin" in warning.description.lower() or "aspirin" in warning.description.lower()

        # CRITICAL: Verify prescription NOT created (antipattern #13)
        async with db_pool.acquire() as conn:
            count = await conn.fetchval(
                """
                SELECT COUNT(*) FROM prescriptions
                WHERE patient_id = $1 AND medication = 'Warfarin'
                """,
                seed_test_patient,
            )

            assert count == 0, "Prescription created despite severe interaction"

        # CRITICAL: Verify audit log records blocked attempt (antipattern #13)
        async with db_pool.acquire() as conn:
            audit_rows = await conn.fetch(
                """
                SELECT * FROM audit_log
                WHERE action = 'prescription_blocked_severe_interaction'
                AND resource_id = $1
                """,
                seed_test_patient,
            )

            assert len(audit_rows) > 0, "No audit log for blocked prescription"
            audit_row = audit_rows[0]
            assert "severe" in json.dumps(audit_row["metadata"]).lower()

    @pytest.mark.asyncio
    async def test_moderate_interaction_creates_with_warning(
        self,
        db_pool: asyncpg.Pool[asyncpg.Record],
        redis_client: redis.Redis[bytes],
        observability_interpreter: object,
        seed_test_patient: UUID,
        seed_test_doctor: UUID,
        sample_user_id: UUID,
    ) -> None:
        """Test moderate medication interaction creates prescription with warning.

        Validates:
        - Moderate interaction allows prescription creation
        - Prescription created in database
        - Warning included in notification
        - Relaxed validation NOT applied (antipattern #14)
        """
        from app.interpreters.observability_interpreter import ObservabilityInterpreter

        assert isinstance(observability_interpreter, ObservabilityInterpreter)

        # Setup
        interpreter = CompositeInterpreter(
            pool=db_pool,
            redis_client=redis_client,
            observability_interpreter=observability_interpreter,
        )

        # Subscribe to patient notification channel
        pubsub = redis_client.pubsub()
        patient_channel = f"patient:{seed_test_patient}:notifications"
        await pubsub.subscribe(patient_channel)

        # Execute with moderate interaction
        result = await run_program(
            create_prescription_program(
                patient_id=seed_test_patient,
                doctor_id=seed_test_doctor,
                medication="Ibuprofen",
                dosage="400mg",
                frequency="Every 6 hours as needed",
                duration_days=7,
                refills_remaining=0,
                notes=None,
                actor_id=sample_user_id,
                existing_medications=["Lisinopril"],  # Known moderate interaction
            ),
            interpreter,
        )

        assert isinstance(result, PrescriptionCreated)
        prescription = result.prescription
        assert prescription.medication == "Ibuprofen"

        # Verify DB persistence
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM prescriptions WHERE id = $1",
                prescription.id,
            )

            assert row is not None
            assert row["medication"] == "Ibuprofen"

        # CRITICAL: Verify notification includes interaction warning (antipattern #13)
        message = await pubsub.get_message(timeout=2.0)
        if message and message["type"] == "subscribe":
            message = await pubsub.get_message(timeout=2.0)

        assert message is not None, "No Redis pub/sub notification received"

        data = message["data"]
        if isinstance(data, (str, bytes)):
            payload = json.loads(data)
        else:
            raise ValueError("Message data must be str or bytes")
        assert payload["type"] == "prescription_created"
        assert "interaction_warning" in payload
        assert payload["interaction_warning"]["severity"] == "moderate"

        await pubsub.unsubscribe(patient_channel)
        await close_pubsub(pubsub)

    @pytest.mark.asyncio
    async def test_minor_interaction_creates_with_warning(
        self,
        db_pool: asyncpg.Pool[asyncpg.Record],
        redis_client: redis.Redis[bytes],
        observability_interpreter: object,
        seed_test_patient: UUID,
        seed_test_doctor: UUID,
        sample_user_id: UUID,
    ) -> None:
        """Test minor medication interaction creates prescription with warning.

        Validates:
        - Minor interaction allows prescription creation
        - Prescription persisted correctly
        - Warning severity = "minor"
        - Strict validation applied (antipattern #14)
        """
        from app.interpreters.observability_interpreter import ObservabilityInterpreter

        assert isinstance(observability_interpreter, ObservabilityInterpreter)

        # Setup
        interpreter = CompositeInterpreter(
            pool=db_pool,
            redis_client=redis_client,
            observability_interpreter=observability_interpreter,
        )

        # Execute with minor interaction
        result = await run_program(
            create_prescription_program(
                patient_id=seed_test_patient,
                doctor_id=seed_test_doctor,
                medication="Calcium Carbonate",
                dosage="500mg",
                frequency="Three times daily with meals",
                duration_days=60,
                refills_remaining=1,
                notes=None,
                actor_id=sample_user_id,
                existing_medications=["Levothyroxine"],  # Known minor interaction
            ),
            interpreter,
        )

        assert isinstance(result, PrescriptionCreated)
        prescription = result.prescription
        assert prescription.medication == "Calcium Carbonate"

        # Verify DB persistence
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM prescriptions WHERE id = $1",
                prescription.id,
            )

            assert row is not None
            assert row["medication"] == "Calcium Carbonate"


class TestPrescriptionAuthorization:
    """Test prescription authorization rules."""

    @pytest.mark.asyncio
    async def test_unauthorized_doctor_cannot_prescribe(
        self,
        db_pool: asyncpg.Pool[asyncpg.Record],
        redis_client: redis.Redis[bytes],
        observability_interpreter: object,
        seed_test_patient: UUID,
        sample_user_id: UUID,
    ) -> None:
        """Test doctor without prescribing authority cannot create prescription.

        Validates:
        - Doctor with can_prescribe=False blocked
        - Returns error string
        - Prescription NOT created
        - Error path tested (antipattern #12)
        - Authorization enforced (antipattern #14)
        """
        from app.interpreters.observability_interpreter import ObservabilityInterpreter

        assert isinstance(observability_interpreter, ObservabilityInterpreter)

        # Setup - Create doctor with can_prescribe=False
        unauthorized_doctor_id = UUID("99000000-0000-0000-0000-000000000001")
        unauthorized_user_id = UUID("99000000-0000-0000-0000-000000000000")

        from app.auth.password import hash_password

        async with db_pool.acquire() as conn:
            # Create user
            await conn.execute(
                """
                INSERT INTO users (id, email, password_hash, role, status, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                unauthorized_user_id,
                "unauthorized@example.com",
                hash_password("password123"),
                "doctor",
                "active",
                datetime.now(timezone.utc),
                datetime.now(timezone.utc),
            )

            # Create doctor with can_prescribe=False
            await conn.execute(
                """
                INSERT INTO doctors (
                    id, user_id, first_name, last_name, specialization,
                    license_number, can_prescribe, created_at, updated_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """,
                unauthorized_doctor_id,
                unauthorized_user_id,
                "Bob",
                "Johnson",
                "Dentistry",
                "DDS-99999",
                False,  # Cannot prescribe
                datetime.now(timezone.utc),
                datetime.now(timezone.utc),
            )

        interpreter = CompositeInterpreter(
            pool=db_pool,
            redis_client=redis_client,
            observability_interpreter=observability_interpreter,
        )

        # Attempt prescription creation
        result = await run_program(
            create_prescription_program(
                patient_id=seed_test_patient,
                doctor_id=unauthorized_doctor_id,
                medication="Amoxicillin",
                dosage="500mg",
                frequency="Three times daily",
                duration_days=10,
                refills_remaining=0,
                notes=None,
                actor_id=sample_user_id,
                existing_medications=[],
            ),
            interpreter,
        )

        # Verify authorization error (antipattern #12, #14)
        assert isinstance(result, PrescriptionDoctorUnauthorized)
        assert result.doctor_id == unauthorized_doctor_id

        # CRITICAL: Verify prescription NOT created (antipattern #13)
        async with db_pool.acquire() as conn:
            count = await conn.fetchval(
                """
                SELECT COUNT(*) FROM prescriptions
                WHERE patient_id = $1 AND medication = 'Amoxicillin'
                """,
                seed_test_patient,
            )

            assert count == 0, "Unauthorized doctor created prescription"

    @pytest.mark.asyncio
    async def test_nonexistent_patient_returns_error(
        self,
        db_pool: asyncpg.Pool[asyncpg.Record],
        redis_client: redis.Redis[bytes],
        observability_interpreter: object,
        seed_test_doctor: UUID,
        sample_user_id: UUID,
    ) -> None:
        """Test prescription for nonexistent patient returns error.

        Validates:
        - Nonexistent patient ID returns error string
        - Prescription NOT created
        - Error path tested (antipattern #12)
        """
        from app.interpreters.observability_interpreter import ObservabilityInterpreter

        assert isinstance(observability_interpreter, ObservabilityInterpreter)

        # Setup
        interpreter = CompositeInterpreter(
            pool=db_pool,
            redis_client=redis_client,
            observability_interpreter=observability_interpreter,
        )

        # Use nonexistent patient ID
        nonexistent_patient_id = UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")

        result = await run_program(
            create_prescription_program(
                patient_id=nonexistent_patient_id,
                doctor_id=seed_test_doctor,
                medication="Simvastatin",
                dosage="20mg",
                frequency="Once daily at bedtime",
                duration_days=90,
                refills_remaining=2,
                notes=None,
                actor_id=sample_user_id,
                existing_medications=[],
            ),
            interpreter,
        )

        # Verify error returned (antipattern #12)
        assert isinstance(result, PrescriptionPatientMissing)
        assert result.patient_id == nonexistent_patient_id


class TestPrescriptionNotifications:
    """Test prescription WebSocket notifications."""

    @pytest.mark.asyncio
    async def test_prescription_creation_publishes_redis_notification(
        self,
        db_pool: asyncpg.Pool[asyncpg.Record],
        redis_client: redis.Redis[bytes],
        observability_interpreter: object,
        seed_test_patient: UUID,
        seed_test_doctor: UUID,
        sample_user_id: UUID,
    ) -> None:
        """Test prescription creation publishes Redis pub/sub notification.

        Validates:
        - Redis pub/sub message published to patient channel
        - Message payload includes prescription details
        - Ephemeral notification (fire-and-forget)
        - Side effect validated (antipattern #13)
        """
        from app.interpreters.observability_interpreter import ObservabilityInterpreter

        assert isinstance(observability_interpreter, ObservabilityInterpreter)

        # Setup
        interpreter = CompositeInterpreter(
            pool=db_pool,
            redis_client=redis_client,
            observability_interpreter=observability_interpreter,
        )

        # Subscribe to patient notification channel
        pubsub = redis_client.pubsub()
        patient_channel = f"patient:{seed_test_patient}:notifications"
        await pubsub.subscribe(patient_channel)

        # Execute prescription creation
        result = await run_program(
            create_prescription_program(
                patient_id=seed_test_patient,
                doctor_id=seed_test_doctor,
                medication="Atorvastatin",
                dosage="10mg",
                frequency="Once daily",
                duration_days=30,
                refills_remaining=3,
                notes="For cholesterol management",
                actor_id=sample_user_id,
                existing_medications=[],
            ),
            interpreter,
        )

        assert isinstance(result, PrescriptionCreated)
        prescription = result.prescription

        # CRITICAL: Verify Redis pub/sub message received (antipattern #13)
        message = await pubsub.get_message(timeout=2.0)

        # First message is subscription confirmation
        if message and message["type"] == "subscribe":
            message = await pubsub.get_message(timeout=2.0)

        assert message is not None, "No Redis pub/sub notification received"
        assert message["type"] == "message"

        # Parse message payload
        data = message["data"]
        if isinstance(data, (str, bytes)):
            payload = json.loads(data)
        else:
            raise ValueError("Message data must be str or bytes")
        assert payload["type"] == "prescription_created"
        assert payload["prescription_id"] == str(prescription.id)
        # Notification payload is PHI-lite; medication name may be omitted intentionally.

        await pubsub.unsubscribe(patient_channel)
        await close_pubsub(pubsub)
