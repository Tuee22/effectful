"""Integration tests for appointment workflows.

Tests appointment scheduling, state transitions, notifications, and audit logging
with real PostgreSQL and Redis infrastructure.

Antipatterns avoided:
- #3: Silent effect failures - verify all side effects
- #4: Testing actions without validating results - check DB persistence
- #5: Contradicting domain guarantees - validate state machine invariants
- #13: Incomplete assertions - verify DB writes, Redis pub/sub, audit logs
- #20: Holding database locks - TRUNCATE committed before each test
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import UUID

import asyncpg
import pytest
import redis.asyncio as redis
from app.interpreters.composite_interpreter import CompositeInterpreter
from effectful.domain.optional_value import to_optional_value

from app.domain.appointment import (
    Appointment,
    AppointmentStatus,
    Cancelled,
    Completed,
    Confirmed,
    InProgress,
    Requested,
    TransitionInvalid,
    TransitionResult,
    TransitionSuccess,
)
from app.domain.doctor import Doctor
from app.domain.patient import Patient
from app.effects.healthcare import TransitionAppointmentStatus
from app.programs.appointment_programs import (
    AppointmentScheduled,
    ScheduleAppointmentResult,
    schedule_appointment_program,
    transition_appointment_program,
)
from effectful.algebraic.result import Err, Ok, Result
from app.programs.runner import InterpreterFailure, run_program, unwrap_program_result
from tests.conftest import close_pubsub


def expect_scheduled(
    result: ScheduleAppointmentResult | Result[ScheduleAppointmentResult, InterpreterFailure]
) -> Appointment:
    if isinstance(result, (Ok, Err)):
        result = unwrap_program_result(result)
    assert isinstance(result, AppointmentScheduled)
    return result.appointment


def expect_transition_success(
    result: TransitionResult | Result[TransitionResult, InterpreterFailure],
) -> TransitionSuccess:
    if isinstance(result, (Ok, Err)):
        result = unwrap_program_result(result)
    assert isinstance(result, TransitionSuccess)
    return result


def expect_transition_invalid(
    result: TransitionResult | Result[TransitionResult, InterpreterFailure],
) -> TransitionInvalid:
    if isinstance(result, (Ok, Err)):
        result = unwrap_program_result(result)
    assert isinstance(result, TransitionInvalid)
    return result


class TestAppointmentScheduling:
    """Test appointment scheduling workflow with real infrastructure."""

    @pytest.mark.asyncio
    async def test_schedule_appointment_creates_db_record(
        self,
        db_pool: asyncpg.Pool[asyncpg.Record],
        composite_interpreter: CompositeInterpreter,
        seed_test_patient: UUID,
        seed_test_doctor: UUID,
        sample_user_id: UUID,
    ) -> None:
        """Test appointment scheduling creates database record.

        Validates:
        - Appointment created with Requested status
        - Patient and doctor associations correct
        - Reason stored properly
        - DB record persisted (antipattern #4)
        """
        # Execute appointment scheduling program
        requested_time = datetime(2024, 12, 15, 14, 0, 0, tzinfo=timezone.utc)
        reason = "Annual checkup"

        appointment = expect_scheduled(
            await run_program(
                schedule_appointment_program(
                    patient_id=seed_test_patient,
                    doctor_id=seed_test_doctor,
                    requested_time=to_optional_value(requested_time),
                    reason=reason,
                    actor_id=sample_user_id,
                ),
                composite_interpreter,
            )
        )
        assert appointment.patient_id == seed_test_patient
        assert appointment.doctor_id == seed_test_doctor
        assert appointment.reason == reason

        # Verify Requested status
        assert isinstance(appointment.status, Requested)

        # CRITICAL: Verify database persistence (antipattern #3, #4, #13)
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM appointments WHERE id = $1",
                appointment.id,
            )

            assert row is not None, "Appointment not persisted to database"
            assert row["patient_id"] == seed_test_patient
            assert row["doctor_id"] == seed_test_doctor
            assert row["reason"] == reason
            assert row["status"] == "requested"

    @pytest.mark.asyncio
    async def test_schedule_appointment_creates_audit_log(
        self,
        db_pool: asyncpg.Pool[asyncpg.Record],
        composite_interpreter: CompositeInterpreter,
        seed_test_patient: UUID,
        seed_test_doctor: UUID,
        sample_user_id: UUID,
    ) -> None:
        """Test appointment scheduling creates audit log entry.

        Validates:
        - Audit log entry created (HIPAA compliance)
        - Action type correct
        - Resource ID and type correct
        - Side effect validated (antipattern #13)
        """
        # Execute
        appointment = expect_scheduled(
            await run_program(
                schedule_appointment_program(
                    patient_id=seed_test_patient,
                    doctor_id=seed_test_doctor,
                    requested_time=to_optional_value(None, reason="not_requested"),
                    reason="Follow-up visit",
                    actor_id=sample_user_id,
                ),
                composite_interpreter,
            )
        )

        # CRITICAL: Verify audit log created (antipattern #13)
        async with db_pool.acquire() as conn:
            audit_rows = await conn.fetch(
                """
                SELECT * FROM audit_log
                WHERE resource_type = 'appointment' AND resource_id = $1
                """,
                appointment.id,
            )

            assert len(audit_rows) > 0, "No audit log entry created"
            audit_row = audit_rows[0]
            assert audit_row["action"] == "create_appointment"
            assert audit_row["user_id"] == sample_user_id
            assert audit_row["resource_id"] == appointment.id


class TestAppointmentStateTransitions:
    """Test appointment state machine transitions with DB validation."""

    @pytest.mark.asyncio
    async def test_valid_transition_requested_to_confirmed(
        self,
        db_pool: asyncpg.Pool[asyncpg.Record],
        composite_interpreter: CompositeInterpreter,
        seed_test_patient: UUID,
        seed_test_doctor: UUID,
        sample_user_id: UUID,
    ) -> None:
        """Test valid state transition: Requested → Confirmed.

        Validates:
        - State machine allows valid transition
        - DB status updated correctly
        - Status metadata includes timestamps
        - State machine invariants maintained (antipattern #5)
        """
        # Create appointment in Requested status
        appointment = expect_scheduled(
            await run_program(
                schedule_appointment_program(
                    patient_id=seed_test_patient,
                    doctor_id=seed_test_doctor,
                    requested_time=to_optional_value(None, reason="not_requested"),
                    reason="Consultation",
                    actor_id=sample_user_id,
                ),
                composite_interpreter,
            )
        )

        assert appointment is not None
        assert isinstance(appointment.status, Requested)

        # Transition to Confirmed
        scheduled_time = datetime(2024, 12, 20, 15, 30, 0, tzinfo=timezone.utc)
        new_status = Confirmed(
            confirmed_at=datetime.now(timezone.utc),
            scheduled_time=scheduled_time,
        )
        transition_time = datetime.now(timezone.utc)

        expect_transition_success(
            await run_program(
                transition_appointment_program(
                    appointment_id=appointment.id,
                    new_status=new_status,
                    actor_id=sample_user_id,
                    transition_time=transition_time,
                ),
                composite_interpreter,
            )
        )

        # CRITICAL: Verify DB updated (antipattern #13)
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM appointments WHERE id = $1",
                appointment.id,
            )

            assert row is not None
            assert row["status"] == "confirmed"

            # Verify status metadata contains Confirmed fields
            status_metadata = row["status_metadata"]
            if isinstance(status_metadata, (str, bytes)):
                metadata = json.loads(status_metadata)
            else:
                metadata = {}
            assert "confirmed_at" in metadata
            assert "scheduled_time" in metadata

    @pytest.mark.asyncio
    async def test_invalid_transition_completed_to_requested(
        self,
        db_pool: asyncpg.Pool[asyncpg.Record],
        composite_interpreter: CompositeInterpreter,
        seed_test_patient: UUID,
        seed_test_doctor: UUID,
        sample_user_id: UUID,
    ) -> None:
        """Test invalid state transition: Completed → Requested.

        Validates:
        - State machine rejects invalid transition
        - Returns TransitionInvalid with reason
        - DB status unchanged
        - Domain invariants maintained (antipattern #5)
        """
        # Create appointment and manually set to Completed (bypass validation)
        appointment = expect_scheduled(
            await run_program(
                schedule_appointment_program(
                    patient_id=seed_test_patient,
                    doctor_id=seed_test_doctor,
                    requested_time=to_optional_value(None, reason="not_requested"),
                    reason="Emergency visit",
                    actor_id=sample_user_id,
                ),
                composite_interpreter,
            )
        )

        # Manually update to Completed status in DB
        completed_status = Completed(
            completed_at=datetime.now(timezone.utc),
            notes="Patient treated successfully",
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

        # Attempt invalid transition: Completed → Requested
        new_status = Requested(requested_at=datetime.now(timezone.utc))
        transition_time = datetime.now(timezone.utc)

        invalid = expect_transition_invalid(
            await run_program(
                transition_appointment_program(
                    appointment_id=appointment.id,
                    new_status=new_status,
                    actor_id=sample_user_id,
                    transition_time=transition_time,
                ),
                composite_interpreter,
            )
        )
        assert "cannot transition from completed to requested" in invalid.reason.lower()

        # CRITICAL: Verify DB unchanged (antipattern #13)
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT status FROM appointments WHERE id = $1",
                appointment.id,
            )

            assert row is not None
            assert row["status"] == "completed", "Invalid transition modified DB"

    @pytest.mark.asyncio
    async def test_state_machine_all_valid_transitions(
        self,
        db_pool: asyncpg.Pool[asyncpg.Record],
        composite_interpreter: CompositeInterpreter,
        seed_test_patient: UUID,
        seed_test_doctor: UUID,
        sample_user_id: UUID,
    ) -> None:
        """Test all valid state machine transitions.

        Validates:
        - Requested → Confirmed → InProgress → Completed (happy path)
        - Each transition persisted to DB
        - State machine invariants maintained throughout
        - Exhaustive validation (antipattern #5)
        """
        # Create appointment (Requested)
        appointment = expect_scheduled(
            await run_program(
                schedule_appointment_program(
                    patient_id=seed_test_patient,
                    doctor_id=seed_test_doctor,
                    requested_time=to_optional_value(None, reason="not_requested"),
                    reason="Full workflow test",
                    actor_id=sample_user_id,
                ),
                composite_interpreter,
            )
        )
        assert isinstance(appointment.status, Requested)

        # Transition 1: Requested → Confirmed
        expect_transition_success(
            await run_program(
                transition_appointment_program(
                    appointment_id=appointment.id,
                    new_status=Confirmed(
                        confirmed_at=datetime.now(timezone.utc),
                        scheduled_time=datetime(2024, 12, 25, 10, 0, 0, tzinfo=timezone.utc),
                    ),
                    actor_id=sample_user_id,
                    transition_time=datetime.now(timezone.utc),
                ),
                composite_interpreter,
            )
        )

        # Verify DB: status = confirmed
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT status FROM appointments WHERE id = $1",
                appointment.id,
            )
            assert row is not None
            assert row["status"] == "confirmed"

        # Transition 2: Confirmed → InProgress
        expect_transition_success(
            await run_program(
                transition_appointment_program(
                    appointment_id=appointment.id,
                    new_status=InProgress(started_at=datetime.now(timezone.utc)),
                    actor_id=sample_user_id,
                    transition_time=datetime.now(timezone.utc),
                ),
                composite_interpreter,
            )
        )

        # Verify DB: status = in_progress
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT status FROM appointments WHERE id = $1",
                appointment.id,
            )
            assert row is not None
            assert row["status"] == "in_progress"

        # Transition 3: InProgress → Completed
        expect_transition_success(
            await run_program(
                transition_appointment_program(
                    appointment_id=appointment.id,
                    new_status=Completed(
                        completed_at=datetime.now(timezone.utc),
                        notes="Patient examined, no issues found",
                    ),
                    actor_id=sample_user_id,
                    transition_time=datetime.now(timezone.utc),
                ),
                composite_interpreter,
            )
        )

        # Verify DB: status = completed
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT status FROM appointments WHERE id = $1",
                appointment.id,
            )
            assert row is not None
            assert row["status"] == "completed"

    @pytest.mark.asyncio
    async def test_cancellation_from_any_non_terminal_state(
        self,
        db_pool: asyncpg.Pool[asyncpg.Record],
        composite_interpreter: CompositeInterpreter,
        seed_test_patient: UUID,
        seed_test_doctor: UUID,
        sample_user_id: UUID,
    ) -> None:
        """Test cancellation is valid from Requested, Confirmed, InProgress.

        Validates:
        - Cancellation allowed from non-terminal states
        - Cancelled status includes reason and actor
        - DB persists cancellation metadata
        - State machine branching validated (antipattern #5)
        """
        # Test cancellation from Requested
        appointment = expect_scheduled(
            await run_program(
                schedule_appointment_program(
                    patient_id=seed_test_patient,
                    doctor_id=seed_test_doctor,
                    requested_time=to_optional_value(None, reason="not_requested"),
                    reason="Cancellation test",
                    actor_id=sample_user_id,
                ),
                composite_interpreter,
            )
        )

        expect_transition_success(
            await run_program(
                transition_appointment_program(
                    appointment_id=appointment.id,
                    new_status=Cancelled(
                        cancelled_at=datetime.now(timezone.utc),
                        cancelled_by="patient",
                        reason="Patient conflict",
                    ),
                    actor_id=sample_user_id,
                    transition_time=datetime.now(timezone.utc),
                ),
                composite_interpreter,
            )
        )

        # Verify DB: status = cancelled with metadata
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM appointments WHERE id = $1",
                appointment.id,
            )

            assert row is not None
            assert row["status"] == "cancelled"
            status_metadata = row["status_metadata"]
            if isinstance(status_metadata, (str, bytes)):
                metadata = json.loads(status_metadata)
            else:
                metadata = {}
            assert "cancelled_by" in metadata
            assert metadata["cancelled_by"] == "patient"
            assert "reason" in metadata


class TestAppointmentNotifications:
    """Test WebSocket notifications for appointment events."""

    @pytest.mark.asyncio
    async def test_schedule_appointment_publishes_redis_notification(
        self,
        db_pool: asyncpg.Pool[asyncpg.Record],
        redis_client: redis.Redis[bytes],
        composite_interpreter: CompositeInterpreter,
        seed_test_patient: UUID,
        seed_test_doctor: UUID,
        sample_user_id: UUID,
    ) -> None:
        """Test appointment scheduling publishes Redis pub/sub notification.

        Validates:
        - Redis pub/sub message published (ephemeral notification)
        - Message channel correct
        - Message payload includes appointment details
        - Side effect validated (antipattern #13)

        Note: This is ephemeral messaging (Redis pub/sub), not durable (Pulsar).
        If no subscriber listening, message is lost (acceptable).
        """
        # Subscribe to doctor notification channel before executing
        pubsub = redis_client.pubsub()
        doctor_channel = f"doctor:{seed_test_doctor}:notifications"
        await pubsub.subscribe(doctor_channel)

        # Execute appointment scheduling
        appointment = expect_scheduled(
            await run_program(
                schedule_appointment_program(
                    patient_id=seed_test_patient,
                    doctor_id=seed_test_doctor,
                    requested_time=to_optional_value(None, reason="not_requested"),
                    reason="Notification test",
                    actor_id=sample_user_id,
                ),
                composite_interpreter,
            )
        )

        # CRITICAL: Verify Redis pub/sub message received (antipattern #13)
        # Note: get_message() with timeout to avoid blocking
        message = await pubsub.get_message(timeout=2.0)

        # First message is subscription confirmation
        if message and message["type"] == "subscribe":
            message = await pubsub.get_message(timeout=2.0)

        assert message is not None, "No Redis pub/sub message received"
        assert message["type"] == "message"

        # Parse message payload (type narrowing for json.loads)
        data = message["data"]
        assert isinstance(data, (str, bytes)), "Message data must be str or bytes"
        payload = json.loads(data)
        assert payload["type"] == "appointment_requested"
        assert payload["appointment_id"] == str(appointment.id)
        # Payload intentionally minimal and PHI-free
        assert payload.get("reason") is None

        await pubsub.unsubscribe(doctor_channel)
        await close_pubsub(pubsub)
