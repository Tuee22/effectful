"""Pattern matching helpers for Result types in tests.

This module provides helper functions to simplify pattern matching on Result
types in tests, making assertions clearer and more concise.

Example:
    >>> from effectful.testing import assert_ok, assert_err, unwrap_ok
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

from effectful.algebraic.effect_return import EffectReturn
from effectful.algebraic.result import Err, Ok, Result
from effectful.interpreters.errors import InterpreterError
from effectful.programs.program_types import EffectResult

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


def assert_effect_ok(
    result: Result[EffectReturn[EffectResult], InterpreterError],
    expected_value: EffectResult,
    effect_name: str,
) -> None:
    """Assert that result is Ok with EffectReturn containing expected value and effect name.

    This is a convenience function for testing interpreter results that return
    EffectReturn wrapped in Result.

    Args:
        result: The interpreter result to check
        expected_value: The expected value inside EffectReturn
        effect_name: The expected effect_name inside EffectReturn

    Raises:
        AssertionError: If result is Err or EffectReturn doesn't match

    Example:
        >>> result = await interpreter.interpret(GetUserById(user_id=user_id))
        >>> assert_effect_ok(result, user, "GetUserById")
    """
    match result:
        case Ok(EffectReturn(value=value, effect_name=name)):
            assert name == effect_name, f"Expected effect_name '{effect_name}', got '{name}'"
            assert value == expected_value, f"Expected value {expected_value!r}, got {value!r}"
        case Err(error):  # pragma: no cover
            pytest.fail(f"Expected Ok(EffectReturn({expected_value!r})), got Err({error})")
        case _:  # pragma: no cover
            pytest.fail(f"Expected Ok(EffectReturn), got {result}")


def assert_effect_err(
    result: Result[EffectReturn[EffectResult], InterpreterError],
    error_type: type[InterpreterError],
    **expected_fields: str | bool,
) -> InterpreterError:
    """Assert that result is Err with expected error type and fields.

    This is a convenience function for testing interpreter error results.

    Args:
        result: The interpreter result to check
        error_type: The expected error type (e.g., DatabaseError, CacheError)
        **expected_fields: Optional field values to check (e.g., db_error="timeout")

    Returns:
        The error for further assertions

    Raises:
        AssertionError: If result is Ok or error doesn't match

    Example:
        >>> result = await interpreter.interpret(GetUserById(user_id=user_id))
        >>> error = assert_effect_err(result, DatabaseError, is_retryable=True)
        >>> assert "timeout" in error.db_error
    """
    match result:
        case Err(error) if isinstance(error, error_type):
            # Check expected fields
            for field, expected in expected_fields.items():
                actual = getattr(error, field, None)
                assert actual == expected, f"Expected {field}={expected}, got {field}={actual}"
            return error
        case Err(error):  # pragma: no cover
            pytest.fail(f"Expected Err({error_type.__name__}), got Err({type(error).__name__})")
        case Ok(value):  # pragma: no cover
            pytest.fail(f"Expected Err({error_type.__name__}), got Ok({value})")
