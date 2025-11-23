"""Tests for System interpreter.

This module tests the SystemInterpreter.
Tests cover:
- GetCurrentTime effect execution
- GenerateUUID effect execution
- Unhandled effects
- Immutability
"""

from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
from uuid import UUID

import pytest

from effectful.algebraic.effect_return import EffectReturn
from effectful.algebraic.result import Err, Ok
from effectful.effects.system import GenerateUUID, GetCurrentTime
from effectful.effects.websocket import SendText
from effectful.interpreters.errors import UnhandledEffectError
from effectful.interpreters.system import SystemInterpreter


class TestSystemInterpreter:
    """Tests for SystemInterpreter."""

    @pytest.mark.asyncio()
    async def test_get_current_time_returns_datetime(self) -> None:
        """Interpreter should return current UTC datetime."""
        interpreter = SystemInterpreter()
        effect = GetCurrentTime()

        before = datetime.now(timezone.utc)
        result = await interpreter.interpret(effect)
        after = datetime.now(timezone.utc)

        # Verify result
        match result:
            case Ok(EffectReturn(value=dt, effect_name="GetCurrentTime")):
                assert isinstance(dt, datetime)
                assert dt.tzinfo is not None  # Should be timezone-aware
                assert before <= dt <= after
            case _:
                pytest.fail(f"Expected Ok with datetime, got {result}")

    @pytest.mark.asyncio()
    async def test_generate_uuid_returns_uuid(self) -> None:
        """Interpreter should return a UUID v4."""
        interpreter = SystemInterpreter()
        effect = GenerateUUID()

        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Ok(EffectReturn(value=uid, effect_name="GenerateUUID")):
                assert isinstance(uid, UUID)
                # UUID v4 has version 4
                assert uid.version == 4
            case _:
                pytest.fail(f"Expected Ok with UUID, got {result}")

    @pytest.mark.asyncio()
    async def test_generate_uuid_returns_unique_values(self) -> None:
        """Each call to GenerateUUID should return a unique UUID."""
        interpreter = SystemInterpreter()

        results: list[UUID] = []
        for _ in range(100):
            result = await interpreter.interpret(GenerateUUID())
            match result:
                case Ok(EffectReturn(value=uid)):
                    assert isinstance(uid, UUID)
                    results.append(uid)
                case _:
                    pytest.fail(f"Unexpected result: {result}")

        # All UUIDs should be unique
        assert len(set(results)) == 100

    @pytest.mark.asyncio()
    async def test_unhandled_effect_returns_error(self) -> None:
        """Interpreter should return UnhandledEffectError for unknown effects."""
        interpreter = SystemInterpreter()
        effect = SendText(text="Hello")

        result = await interpreter.interpret(effect)

        match result:
            case Err(UnhandledEffectError(effect=e, available_interpreters=interpreters)):
                assert e == effect
                assert "SystemInterpreter" in interpreters
            case _:
                pytest.fail(f"Expected Err with UnhandledEffectError, got {result}")

    def test_system_interpreter_is_immutable(self) -> None:
        """SystemInterpreter should be frozen (immutable)."""
        interpreter = SystemInterpreter()
        with pytest.raises(FrozenInstanceError):
            setattr(interpreter, "dummy", "value")
