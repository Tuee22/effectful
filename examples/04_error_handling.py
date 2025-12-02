"""Example 04: Error Handling

Effect program demonstrating comprehensive error handling patterns.

Run:
    python -m examples.04_error_handling
"""

import asyncio
from collections.abc import Generator
from uuid import UUID, uuid4
from unittest.mock import AsyncMock

from effectful import (
    AllEffects,
    EffectResult,
    GetUserById,
    SendText,
    User,
    UserNotFound,
    run_ws_program,
)
from effectful.algebraic.result import Err, Ok
from effectful.infrastructure.cache import ProfileCache
from effectful.infrastructure.repositories import ChatMessageRepository, UserRepository
from effectful.infrastructure.websocket import WebSocketConnection
from effectful.interpreters.composite import create_composite_interpreter
from effectful.interpreters.errors import DatabaseError


def safe_user_lookup(user_id: UUID) -> Generator[AllEffects, EffectResult, str]:
    """Look up user with explicit error handling.

    Demonstrates:
    - Pattern matching on user result
    - Handling None (user not found)
    - Type narrowing

    Args:
        user_id: User to lookup

    Yields:
        GetUserById, SendText effects

    Returns:
        Status message
    """
    user_result = yield GetUserById(user_id=user_id)

    match user_result:
        case UserNotFound():
            yield SendText(text="User not found - please check the ID")
            return "not_found"

        case User(name=name, email=email):
            yield SendText(text=f"Found user: {name} ({email})")
            return "success"

        case unexpected:
            raise AssertionError(f"Unexpected type: {type(unexpected)}")


async def demo_user_not_found() -> None:
    """Demonstrate handling user not found case."""
    print("=== Demo 1: User Not Found ===")

    # Empty repository (returns UserNotFound)
    ws = AsyncMock(spec=WebSocketConnection)
    ws.is_open.return_value = True

    user_repo = AsyncMock(spec=UserRepository)
    user_repo.get_by_id.return_value = UserNotFound(user_id=uuid4(), reason="does_not_exist")

    interpreter = create_composite_interpreter(
        websocket_connection=ws,
        user_repo=user_repo,
        message_repo=AsyncMock(spec=ChatMessageRepository),
        cache=AsyncMock(spec=ProfileCache),
    )

    result = await run_ws_program(safe_user_lookup(uuid4()), interpreter)

    match result:
        case Ok(value):
            print(f"✓ Program completed: {value}")
            _ = [print(f"  → {call.args[0]}") for call in ws.send_text.call_args_list]
        case Err(error):
            print(f"✗ Unexpected error: {error}")


async def demo_database_failure() -> None:
    """Demonstrate handling database failure."""
    print("\n=== Demo 2: Database Failure ===")

    # Failing repository (simulates database timeout)
    ws = AsyncMock(spec=WebSocketConnection)
    ws.is_open.return_value = True

    user_repo = AsyncMock(spec=UserRepository)

    async def fail_lookup(_: UUID) -> User:
        raise TimeoutError("Connection timeout")

    user_repo.get_by_id.side_effect = fail_lookup

    interpreter = create_composite_interpreter(
        websocket_connection=ws,
        user_repo=user_repo,
        message_repo=AsyncMock(spec=ChatMessageRepository),
        cache=AsyncMock(spec=ProfileCache),
    )

    result = await run_ws_program(safe_user_lookup(uuid4()), interpreter)

    match result:
        case Ok(value):
            print(f"✗ Unexpected success: {value}")

        case Err(DatabaseError(db_error=error, is_retryable=retryable)):
            print(f"✓ Caught database error: {error}")
            print(f"  Retryable: {retryable}")
            if retryable:
                print("  → Could implement retry logic here")

        case Err(error):
            print(f"✓ Caught error: {error}")


async def demo_success_case() -> None:
    """Demonstrate successful user lookup."""
    print("\n=== Demo 3: Success Case ===")

    # Repository with test user
    ws = AsyncMock(spec=WebSocketConnection)
    ws.is_open.return_value = True

    user_id = uuid4()
    user_repo = AsyncMock(spec=UserRepository)
    user_repo.get_by_id.return_value = User(id=user_id, email="charlie@example.com", name="Charlie")

    interpreter = create_composite_interpreter(
        websocket_connection=ws,
        user_repo=user_repo,
        message_repo=AsyncMock(spec=ChatMessageRepository),
        cache=AsyncMock(spec=ProfileCache),
    )

    result = await run_ws_program(safe_user_lookup(user_id), interpreter)

    match result:
        case Ok(value):
            print(f"✓ Program completed: {value}")
            _ = [print(f"  → {call.args[0]}") for call in ws.send_text.call_args_list]

        case Err(error):
            print(f"✗ Unexpected error: {error}")


def multi_user_lookup(user_ids: list[UUID]) -> Generator[AllEffects, EffectResult, dict[str, int]]:
    """Look up multiple users, handling errors gracefully.

    Demonstrates:
    - Processing multiple effects
    - Collecting results
    - Fail-fast on database errors (automatic via run_ws_program)

    Args:
        user_ids: Users to lookup

    Yields:
        GetUserById effects for each user

    Returns:
        Statistics: {"found": N, "not_found": M}

    Note:
        For loop is acceptable here because yield cannot be in comprehensions.
        Uses immutable dict updates instead of mutation.
    """
    # Initialize with immutable pattern
    found = 0
    not_found = 0

    # For loop with yield is acceptable (yield cannot be in comprehensions)
    for user_id in user_ids:
        user_result = yield GetUserById(user_id=user_id)

        match user_result:
            case UserNotFound():
                not_found = not_found + 1
            case User(name=name):
                found = found + 1
                yield SendText(text=f"Found: {name}")
            case unexpected:
                raise AssertionError(f"Unexpected type: {type(unexpected)}")

    # Summary
    stats = {"found": found, "not_found": not_found}
    yield SendText(text=f"Lookup complete: {stats['found']} found, {stats['not_found']} not found")

    return stats


async def demo_batch_processing() -> None:
    """Demonstrate batch processing with mixed results."""
    print("\n=== Demo 4: Batch Processing ===")

    ws = AsyncMock(spec=WebSocketConnection)
    ws.is_open.return_value = True

    user_ids = [uuid4() for _ in range(5)]
    existing_users = {
        user_ids[0]: User(id=user_ids[0], email="user1@example.com", name="User 1"),
        user_ids[2]: User(id=user_ids[2], email="user3@example.com", name="User 3"),
        user_ids[4]: User(id=user_ids[4], email="user5@example.com", name="User 5"),
    }

    async def lookup(uid: UUID):
        return existing_users.get(uid, UserNotFound(user_id=uid, reason="does_not_exist"))

    user_repo = AsyncMock(spec=UserRepository)
    user_repo.get_by_id.side_effect = lookup

    interpreter = create_composite_interpreter(
        websocket_connection=ws,
        user_repo=user_repo,
        message_repo=AsyncMock(spec=ChatMessageRepository),
        cache=AsyncMock(spec=ProfileCache),
    )

    result = await run_ws_program(multi_user_lookup(user_ids), interpreter)

    match result:
        case Ok(stats):
            print(f"✓ Batch complete: {stats}")
            print("  Messages sent:")
            _ = [print(f"    → {call.args[0]}") for call in ws.send_text.call_args_list]

        case Err(error):
            print(f"✗ Batch failed: {error}")


async def main() -> None:
    """Run all error handling demonstrations."""
    await demo_user_not_found()
    await demo_database_failure()
    await demo_success_case()
    await demo_batch_processing()

    print("\n" + "=" * 50)
    print("Key Takeaways:")
    print("1. Pattern matching makes error handling explicit")
    print("2. Result type forces handling both Ok and Err cases")
    print("3. run_ws_program provides fail-fast semantics")
    print("4. Type narrowing ensures type safety")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
