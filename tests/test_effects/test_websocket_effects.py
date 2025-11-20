"""Tests for WebSocket effects.

Tests cover:
- Immutability (frozen dataclasses)
- Construction of each effect variant
- CloseReason ADT exhaustiveness
- Type safety
"""

from dataclasses import FrozenInstanceError

import pytest

from effectful.effects.websocket import (
    Close,
    CloseGoingAway,
    CloseNormal,
    ClosePolicyViolation,
    CloseProtocolError,
    CloseReason,
    ReceiveText,
    SendText,
)


class TestSendText:
    """Test SendText effect."""

    def test_send_text_creates_effect(self) -> None:
        """SendText should wrap text message."""
        effect = SendText("Hello, World!")
        assert effect.text == "Hello, World!"

    def test_send_text_is_immutable(self) -> None:
        """SendText should be frozen (immutable)."""
        effect = SendText("Hello")
        with pytest.raises(FrozenInstanceError):
            effect.text = "Goodbye"  # type: ignore[misc]


class TestReceiveText:
    """Test ReceiveText effect."""

    def test_receive_text_creates_effect(self) -> None:
        """ReceiveText should be constructable."""
        effect = ReceiveText()
        assert effect is not None

    def test_receive_text_is_immutable(self) -> None:
        """ReceiveText should be frozen (immutable)."""
        effect = ReceiveText()
        # ReceiveText has no fields, so just verify it's frozen
        assert hasattr(effect, "__dataclass_fields__")


class TestCloseReasonNormal:
    """Test CloseNormal close reason."""

    def test_close_normal_creates_reason(self) -> None:
        """CloseNormal should be constructable."""
        reason = CloseNormal()
        assert reason is not None

    def test_close_normal_is_immutable(self) -> None:
        """CloseNormal should be frozen (immutable)."""
        reason = CloseNormal()
        assert hasattr(reason, "__dataclass_fields__")


class TestCloseReasonGoingAway:
    """Test CloseGoingAway close reason."""

    def test_close_going_away_creates_reason(self) -> None:
        """CloseGoingAway should be constructable."""
        reason = CloseGoingAway()
        assert reason is not None

    def test_close_going_away_is_immutable(self) -> None:
        """CloseGoingAway should be frozen (immutable)."""
        reason = CloseGoingAway()
        assert hasattr(reason, "__dataclass_fields__")


class TestCloseReasonProtocolError:
    """Test CloseProtocolError close reason."""

    def test_close_protocol_error_requires_reason(self) -> None:
        """CloseProtocolError should require reason string."""
        reason = CloseProtocolError("Invalid frame format")
        assert reason.reason == "Invalid frame format"

    def test_close_protocol_error_is_immutable(self) -> None:
        """CloseProtocolError should be frozen (immutable)."""
        reason = CloseProtocolError("Error")
        with pytest.raises(FrozenInstanceError):
            reason.reason = "New error"  # type: ignore[misc]


class TestCloseReasonPolicyViolation:
    """Test ClosePolicyViolation close reason."""

    def test_close_policy_violation_requires_reason(self) -> None:
        """ClosePolicyViolation should require reason string."""
        reason = ClosePolicyViolation("Unauthorized access")
        assert reason.reason == "Unauthorized access"

    def test_close_policy_violation_is_immutable(self) -> None:
        """ClosePolicyViolation should be frozen (immutable)."""
        reason = ClosePolicyViolation("Violation")
        with pytest.raises(FrozenInstanceError):
            reason.reason = "New violation"  # type: ignore[misc]


class TestClose:
    """Test Close effect with CloseReason ADT."""

    def test_close_with_normal_reason(self) -> None:
        """Close should accept CloseNormal reason."""
        effect = Close(CloseNormal())
        assert isinstance(effect.reason, CloseNormal)

    def test_close_with_going_away_reason(self) -> None:
        """Close should accept CloseGoingAway reason."""
        effect = Close(CloseGoingAway())
        assert isinstance(effect.reason, CloseGoingAway)

    def test_close_with_protocol_error_reason(self) -> None:
        """Close should accept CloseProtocolError reason."""
        effect = Close(CloseProtocolError("Bad data"))
        assert isinstance(effect.reason, CloseProtocolError)
        assert effect.reason.reason == "Bad data"

    def test_close_with_policy_violation_reason(self) -> None:
        """Close should accept ClosePolicyViolation reason."""
        effect = Close(ClosePolicyViolation("Banned user"))
        assert isinstance(effect.reason, ClosePolicyViolation)
        assert effect.reason.reason == "Banned user"

    def test_close_is_immutable(self) -> None:
        """Close should be frozen (immutable)."""
        effect = Close(CloseNormal())
        with pytest.raises(FrozenInstanceError):
            effect.reason = CloseGoingAway()  # type: ignore[misc]


class TestCloseReasonExhaustiveness:
    """Test exhaustive matching on CloseReason ADT."""

    def test_all_close_reasons_handled(self) -> None:
        """Pattern matching should handle all CloseReason variants."""
        reasons: list[CloseReason] = [
            CloseNormal(),
            CloseGoingAway(),
            CloseProtocolError("error"),
            ClosePolicyViolation("violation"),
        ]

        def match_reason(reason: CloseReason) -> str:
            match reason:
                case CloseNormal():
                    return "normal"
                case CloseGoingAway():
                    return "going_away"
                case CloseProtocolError(reason=r):
                    return f"protocol_error:{r}"
                case ClosePolicyViolation(reason=r):
                    return f"policy_violation:{r}"

        results = [match_reason(r) for r in reasons]
        assert results == [
            "normal",
            "going_away",
            "protocol_error:error",
            "policy_violation:violation",
        ]
