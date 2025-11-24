"""Testing utilities for effectful programs.

This module provides minimal testing utilities for working with Result types.
All infrastructure mocking should use pytest-mock directly.

Exports:
    - assert_ok: Assert result is Ok
    - assert_err: Assert result is Err
    - unwrap_ok: Extract value from Ok
    - unwrap_err: Extract error from Err
    - assert_ok_value: Assert Ok with specific value
    - assert_err_message: Assert Err with message substring
"""

from effectful.testing.matchers import (
    assert_err,
    assert_err_message,
    assert_ok,
    assert_ok_value,
    unwrap_err,
    unwrap_ok,
)

__all__ = [
    "assert_err",
    "assert_err_message",
    "assert_ok",
    "assert_ok_value",
    "unwrap_err",
    "unwrap_ok",
]
