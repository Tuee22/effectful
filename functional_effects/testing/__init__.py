"""Testing utilities for effect programs.

This module provides test doubles and matchers for testing effect programs.

Available test doubles:
    - FakeMessageProducer / FailingMessageProducer: For messaging tests
    - FakeMessageConsumer / FailingMessageConsumer: For messaging tests
    - FakeObjectStorage / FailingObjectStorage: For storage tests

For testing effect programs, use pytest mocks (via pytest-mock):

Quick Start:
    >>> from functional_effects.testing import assert_ok, unwrap_ok, FakeObjectStorage
    >>> from functional_effects import create_composite_interpreter
    >>>
    >>> @pytest.mark.asyncio
    >>> async def test_my_program(mocker):
    ...     # Create mocks for infrastructure
    ...     mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
    ...     mock_repo = mocker.AsyncMock(spec=UserRepository)
    ...     fake_storage = FakeObjectStorage()
    ...
    ...     # Create interpreter with mocks
    ...     interpreter = create_composite_interpreter(
    ...         websocket_connection=mock_ws,
    ...         user_repo=mock_repo,
    ...         object_storage=fake_storage,
    ...         ...
    ...     )
    ...
    ...     # Run program and assert
    ...     result = await run_ws_program(my_program(), interpreter)
    ...     value = unwrap_ok(result)
    ...     assert value == "expected"
    ...
    ...     # Verify mock calls
    ...     mock_ws.send_text.assert_called_once_with("Hello!")

Available exports:

Matchers (assertions):
    - assert_ok: Assert result is Ok variant
    - assert_err: Assert result is Err variant
    - unwrap_ok: Extract value from Ok or fail
    - unwrap_err: Extract error from Err or fail
    - assert_ok_value: Assert Ok value matches expected
    - assert_err_message: Assert Err message contains substring

Fakes (in-memory test doubles):
    - FakeMessageProducer: In-memory message publisher
    - FakeMessageConsumer: In-memory message consumer
    - FakeObjectStorage: In-memory object storage

Failing variants (for error testing):
    - FailingMessageProducer: Always fails to publish
    - FailingMessageConsumer: Always fails to consume
    - FailingObjectStorage: Always fails storage operations
"""

# Fakes and failing variants
from functional_effects.testing.fakes import (
    FakeMessageConsumer,
    FakeMessageProducer,
    FakeObjectStorage,
)
from functional_effects.testing.failing import (
    FailingMessageConsumer,
    FailingMessageProducer,
    FailingObjectStorage,
)

# Matchers
from functional_effects.testing.matchers import (
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
    # Fakes
    "FakeMessageProducer",
    "FakeMessageConsumer",
    "FakeObjectStorage",
    # Failing variants
    "FailingMessageProducer",
    "FailingMessageConsumer",
    "FailingObjectStorage",
]
