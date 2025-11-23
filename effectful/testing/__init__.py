"""Testing utilities for effect programs.

This module provides matchers for testing effect programs with pytest-mock.

For testing effect programs, use generator-based testing with pytest-mock:

Quick Start:
    >>> from effectful.testing import assert_ok, unwrap_ok
    >>> from pytest_mock import MockerFixture
    >>>
    >>> def test_my_program(mocker: MockerFixture) -> None:
    ...     # Setup
    ...     user = User(id=uuid4(), email="test@example.com", name="Alice")
    ...
    ...     # Create generator
    ...     gen = get_user_program(user_id=user.id)
    ...
    ...     # Step 1: Get first effect
    ...     effect1 = next(gen)
    ...     assert effect1.__class__.__name__ == "GetUserById"
    ...
    ...     # Step 2: Send mock response
    ...     try:
    ...         gen.send(user)
    ...         pytest.fail("Expected StopIteration")
    ...     except StopIteration as e:
    ...         result = e.value
    ...
    ...     # Assert result
    ...     assert isinstance(result, Ok)
    ...     assert result.value.id == user.id

Available exports:

Matchers (assertions):
    - assert_ok: Assert result is Ok variant
    - assert_err: Assert result is Err variant
    - unwrap_ok: Extract value from Ok or fail
    - unwrap_err: Extract error from Err or fail
    - assert_ok_value: Assert Ok value matches expected
    - assert_err_message: Assert Err message contains substring

For more information, see docs/tutorials/04_testing_guide.md
"""

# Matchers
from effectful.testing.matchers import (
    assert_effect_err,
    assert_effect_ok,
    assert_err,
    assert_err_message,
    assert_ok,
    assert_ok_value,
    unwrap_err,
    unwrap_ok,
)

__all__ = [
    # Matchers
    "assert_ok",
    "assert_err",
    "unwrap_ok",
    "unwrap_err",
    "assert_ok_value",
    "assert_err_message",
    "assert_effect_ok",
    "assert_effect_err",
]
