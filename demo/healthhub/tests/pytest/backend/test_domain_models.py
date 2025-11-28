"""Unit tests for domain models.

Tests immutability, ADT exhaustiveness, and state machine transitions.
"""

from datetime import datetime, timezone

import pytest

from app.domain.appointment import (
    Cancelled,
    Completed,
    Confirmed,
    InProgress,
    Requested,
    TransitionInvalid,
    TransitionSuccess,
    validate_transition,
)
from app.domain.prescription import MedicationInteractionWarning, NoInteractions
from ...conftest import assert_frozen


class TestAppointmentStateMachine:
    """Test appointment state machine transitions."""

    def test_requested_to_confirmed_valid(self) -> None:
        """Requested → Confirmed should be valid."""
        current = Requested(requested_at=datetime.now(timezone.utc))
        new = Confirmed(
            confirmed_at=datetime.now(timezone.utc),
            scheduled_time=datetime.now(timezone.utc),
        )

        result = validate_transition(current, new)

        assert isinstance(result, TransitionSuccess)
        assert result.new_status == new

    def test_requested_to_cancelled_valid(self) -> None:
        """Requested → Cancelled should be valid."""
        current = Requested(requested_at=datetime.now(timezone.utc))
        new = Cancelled(
            cancelled_at=datetime.now(timezone.utc),
            cancelled_by="patient",
            reason="Patient cancelled",
        )

        result = validate_transition(current, new)

        assert isinstance(result, TransitionSuccess)

    def test_confirmed_to_in_progress_valid(self) -> None:
        """Confirmed → InProgress should be valid."""
        current = Confirmed(
            confirmed_at=datetime.now(timezone.utc),
            scheduled_time=datetime.now(timezone.utc),
        )
        new = InProgress(started_at=datetime.now(timezone.utc))

        result = validate_transition(current, new)

        assert isinstance(result, TransitionSuccess)

    def test_in_progress_to_completed_valid(self) -> None:
        """InProgress → Completed should be valid."""
        current = InProgress(started_at=datetime.now(timezone.utc))
        new = Completed(completed_at=datetime.now(timezone.utc), notes="Appointment completed")

        result = validate_transition(current, new)

        assert isinstance(result, TransitionSuccess)

    def test_completed_to_requested_invalid(self) -> None:
        """Completed → Requested should be invalid."""
        current = Completed(completed_at=datetime.now(timezone.utc), notes="Completed")
        new = Requested(requested_at=datetime.now(timezone.utc))

        result = validate_transition(current, new)

        assert isinstance(result, TransitionInvalid)
        assert "Cannot transition" in result.reason

    def test_cancelled_to_any_invalid(self) -> None:
        """Cancelled → anything should be invalid."""
        current = Cancelled(
            cancelled_at=datetime.now(timezone.utc), cancelled_by="patient", reason="Test"
        )
        new = Requested(requested_at=datetime.now(timezone.utc))

        result = validate_transition(current, new)

        assert isinstance(result, TransitionInvalid)

    def test_completed_is_terminal(self) -> None:
        """Completed is terminal - no transitions allowed."""
        current = Completed(completed_at=datetime.now(timezone.utc), notes="Completed")
        new = InProgress(started_at=datetime.now(timezone.utc))

        result = validate_transition(current, new)

        assert isinstance(result, TransitionInvalid)


class TestDomainModelImmutability:
    """Test that domain models are immutable."""

    def test_requested_status_immutable(self) -> None:
        """Requested status should be immutable."""
        status = Requested(requested_at=datetime.now(timezone.utc))
        assert_frozen(status, "requested_at", datetime.now(timezone.utc))

    def test_confirmed_status_immutable(self) -> None:
        """Confirmed status should be immutable."""
        now = datetime.now(timezone.utc)
        status = Confirmed(confirmed_at=now, scheduled_time=now)
        assert_frozen(status, "confirmed_at", datetime.now(timezone.utc))

    def test_medication_warning_immutable(self) -> None:
        """MedicationInteractionWarning should be immutable."""
        warning = MedicationInteractionWarning(
            medications=["Aspirin", "Warfarin"],
            severity="severe",
            description="Increased bleeding risk",
        )
        assert_frozen(warning, "severity", "minor")

    def test_no_interactions_immutable(self) -> None:
        """NoInteractions should be immutable."""
        result = NoInteractions(medications_checked=["Lisinopril"])

        with pytest.raises(AttributeError):
            result.medications_checked = []  # type: ignore[misc]
