"""Pattern matching helpers for Result types in tests.

This module provides helper functions to simplify pattern matching on Result
types in tests, making assertions clearer and more concise.

Example:
    >>> from functional_effects.testing import assert_ok, assert_err, unwrap_ok
    >>>
    >>> result = await run_ws_program(my_program(), interpreter)
    >>>
    >>> # Simple assertion
    >>> assert_ok(result)  # Fails test if Err
    >>>
    >>> # Extract value for further testing
    >>> value = unwrap_ok(result)
    >>> assert value == "expected"
    >>>
    >>> # Assert specific error type
    >>> assert_err(result, DatabaseError)
"""

from typing import TypeVar

import pytest

from functional_effects.algebraic.result import Err, Ok, Result
from functional_effects.interpreters.errors import InterpreterError

T = TypeVar("T")
E = TypeVar("E")


def assert_ok(result: Result[T, E]) -> None:
    """Assert that result is Ok, fail test if Err.

    Args:
        result: The Result to check

    Raises:
        AssertionError: If result is Err

    Example:
        >>> result = await run_ws_program(program(), interpreter)
        >>> assert_ok(result)  # Test fails if Err
    """
    match result:
        case Ok(_):
            pass
        case Err(error):  # pragma: no cover
            pytest.fail(f"Expected Ok, got Err({error})")


def assert_err(result: Result[T, E], error_type: type[E] | None = None) -> None:
    """Assert that result is Err, optionally checking error type.

    Args:
        result: The Result to check
        error_type: Optional error type to match

    Raises:
        AssertionError: If result is Ok or error type doesn't match

    Example:
        >>> result = await run_ws_program(failing_program(), interpreter)
        >>> assert_err(result)  # Any error
        >>> assert_err(result, DatabaseError)  # Specific error type
    """
    match result:
        case Err(error):
            if error_type is not None and not isinstance(error, error_type):  # pragma: no cover
                pytest.fail(f"Expected Err({error_type.__name__}), got Err({type(error).__name__})")
        case Ok(value):  # pragma: no cover
            pytest.fail(f"Expected Err, got Ok({value})")


def unwrap_ok(result: Result[T, E]) -> T:
    """Extract value from Ok result, fail test if Err.

    Args:
        result: The Result to unwrap

    Returns:
        The wrapped value

    Raises:
        AssertionError: If result is Err

    Example:
        >>> result = await run_ws_program(program(), interpreter)
        >>> value = unwrap_ok(result)
        >>> assert value == 42
    """
    match result:
        case Ok(value):
            return value
        case Err(error):  # pragma: no cover
            pytest.fail(f"Expected Ok, got Err({error})")


def unwrap_err(result: Result[T, E]) -> E:
    """Extract error from Err result, fail test if Ok.

    Args:
        result: The Result to unwrap

    Returns:
        The wrapped error

    Raises:
        AssertionError: If result is Ok

    Example:
        >>> result = await run_ws_program(failing_program(), interpreter)
        >>> error = unwrap_err(result)
        >>> assert error.db_error == "Connection timeout"
    """
    match result:
        case Err(error):
            return error
        case Ok(value):  # pragma: no cover
            pytest.fail(f"Expected Err, got Ok({value})")


def assert_ok_value(result: Result[T, E], expected: T) -> None:
    """Assert that result is Ok with specific value.

    Args:
        result: The Result to check
        expected: The expected value

    Raises:
        AssertionError: If result is Err or value doesn't match

    Example:
        >>> result = await run_ws_program(program(), interpreter)
        >>> assert_ok_value(result, "success")
    """
    match result:
        case Ok(value):
            assert value == expected, f"Expected Ok({expected}), got Ok({value})"
        case Err(error):  # pragma: no cover
            pytest.fail(f"Expected Ok({expected}), got Err({error})")


def assert_err_message(result: Result[T, InterpreterError], expected_msg: str) -> None:
    """Assert that result is Err containing specific message.

    Works with InterpreterError types that have message fields.

    Args:
        result: The Result to check
        expected_msg: Expected error message substring

    Raises:
        AssertionError: If result is Ok or message doesn't match

    Example:
        >>> result = await run_ws_program(failing_program(), interpreter)
        >>> assert_err_message(result, "Connection timeout")
    """
    match result:
        case Err(error):
            error_str = str(error)
            assert (
                expected_msg in error_str
            ), f"Expected error message containing '{expected_msg}', got: {error_str}"
        case Ok(value):  # pragma: no cover
            pytest.fail(f"Expected Err('{expected_msg}'), got Ok({value})")
