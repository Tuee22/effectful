"""Tests for functional_effects.testing.matchers module."""

from uuid import uuid4

import pytest

from functional_effects.algebraic.result import Err, Ok, Result
from functional_effects.effects.database import GetUserById
from functional_effects.interpreters.errors import DatabaseError
from functional_effects.testing.matchers import (
    assert_err,
    assert_err_message,
    assert_ok,
    assert_ok_value,
    unwrap_err,
    unwrap_ok,
)


class TestAssertOk:
    """Tests for assert_ok matcher."""

    def test_passes_for_ok_result(self) -> None:
        """assert_ok should pass for Ok result."""
        result: Result[int, str] = Ok(42)

        # Should not raise
        assert_ok(result)


class TestAssertErr:
    """Tests for assert_err matcher."""

    def test_passes_for_err_result(self) -> None:
        """assert_err should pass for Err result."""
        result: Result[int, str] = Err("failed")

        # Should not raise
        assert_err(result)

    def test_passes_for_matching_error_type(self) -> None:
        """assert_err should pass when error type matches."""
        effect = GetUserById(user_id=uuid4())
        error = DatabaseError(effect=effect, db_error="Connection failed", is_retryable=True)
        result: Result[int, DatabaseError] = Err(error)

        # Should not raise
        assert_err(result, DatabaseError)


class TestUnwrapOk:
    """Tests for unwrap_ok matcher."""

    def test_returns_value_for_ok_result(self) -> None:
        """unwrap_ok should return value for Ok result."""
        result: Result[int, str] = Ok(42)

        value = unwrap_ok(result)

        assert value == 42


class TestUnwrapErr:
    """Tests for unwrap_err matcher."""

    def test_returns_error_for_err_result(self) -> None:
        """unwrap_err should return error for Err result."""
        result: Result[int, str] = Err("failed")

        error = unwrap_err(result)

        assert error == "failed"


class TestAssertOkValue:
    """Tests for assert_ok_value matcher."""

    def test_passes_for_matching_value(self) -> None:
        """assert_ok_value should pass when value matches."""
        result: Result[int, str] = Ok(42)

        # Should not raise
        assert_ok_value(result, 42)

    def test_fails_for_non_matching_value(self) -> None:
        """assert_ok_value should fail when value doesn't match."""
        result: Result[int, str] = Ok(42)

        with pytest.raises(AssertionError, match="Expected Ok\\(100\\), got Ok\\(42\\)"):
            assert_ok_value(result, 100)


class TestAssertErrMessage:
    """Tests for assert_err_message matcher."""

    def test_passes_for_matching_substring(self) -> None:
        """assert_err_message should pass when message contains substring."""
        effect = GetUserById(user_id=uuid4())
        error = DatabaseError(effect=effect, db_error="Connection timeout error", is_retryable=True)
        result: Result[int, DatabaseError] = Err(error)

        # Should not raise
        assert_err_message(result, "Connection timeout")  # type: ignore[arg-type]

    def test_fails_for_non_matching_substring(self) -> None:
        """assert_err_message should fail when message doesn't contain substring."""
        effect = GetUserById(user_id=uuid4())
        error = DatabaseError(effect=effect, db_error="Connection timeout", is_retryable=True)
        result: Result[int, DatabaseError] = Err(error)

        with pytest.raises(AssertionError, match="Expected error message containing"):
            assert_err_message(result, "Deadlock")  # type: ignore[arg-type]
