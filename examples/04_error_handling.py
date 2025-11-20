"""Example 04: Error Handling

Effect program demonstrating comprehensive error handling patterns.

Run:
    python -m examples.04_error_handling
"""

import asyncio
from collections.abc import Generator
from uuid import UUID, uuid4

from effectful import (
    AllEffects,
    EffectResult,
    GetUserById,
    SendText,
    User,
    run_ws_program,
)
from effectful.algebraic.result import Err, Ok
from effectful.interpreters.errors import DatabaseError
from effectful.testing import (
    FailingUserRepository,
    FakeUserRepository,
    create_test_interpreter,
)


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
        case None:
            yield SendText(text="User not found - please check the ID")
            return "not_found"

        case User(name=name, email=email):
            yield SendText(text=f"Found user: {name} ({email})")
            return "success"


async def demo_user_not_found() -> None:
    """Demonstrate handling user not found case."""
    print("=== Demo 1: User Not Found ===")

    # Empty repository
    interpreter = create_test_interpreter()

    result = await run_ws_program(safe_user_lookup(uuid4()), interpreter)

    match result:
        case Ok(value):
            print(f"✓ Program completed: {value}")
            websocket = interpreter._websocket._connection
            for msg in websocket._sent_messages:
                print(f"  → {msg}")
        case Err(error):
            print(f"✗ Unexpected error: {error}")


async def demo_database_failure() -> None:
    """Demonstrate handling database failure."""
    print("\n=== Demo 2: Database Failure ===")

    # Failing repository (simulates database timeout)
    failing_repo = FailingUserRepository(error_message="Connection timeout")
    interpreter = create_test_interpreter(user_repo=failing_repo)

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
    fake_repo = FakeUserRepository()
    user_id = uuid4()
    fake_repo._users[user_id] = User(id=user_id, email="charlie@example.com", name="Charlie")

    interpreter = create_test_interpreter(user_repo=fake_repo)

    result = await run_ws_program(safe_user_lookup(user_id), interpreter)

    match result:
        case Ok(value):
            print(f"✓ Program completed: {value}")
            websocket = interpreter._websocket._connection
            for msg in websocket._sent_messages:
                print(f"  → {msg}")

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
    """
    stats = {"found": 0, "not_found": 0}

    for user_id in user_ids:
        user_result = yield GetUserById(user_id=user_id)

        match user_result:
            case None:
                stats["not_found"] += 1
            case User(name=name):
                stats["found"] += 1
                yield SendText(text=f"Found: {name}")

    # Summary
    yield SendText(text=f"Lookup complete: {stats['found']} found, {stats['not_found']} not found")

    return stats


async def demo_batch_processing() -> None:
    """Demonstrate batch processing with mixed results."""
    print("\n=== Demo 4: Batch Processing ===")

    # Repository with some users
    fake_repo = FakeUserRepository()

    user_ids = [uuid4() for _ in range(5)]

    # Add 3 users, leave 2 missing
    fake_repo._users[user_ids[0]] = User(id=user_ids[0], email="user1@example.com", name="User 1")
    fake_repo._users[user_ids[2]] = User(id=user_ids[2], email="user3@example.com", name="User 3")
    fake_repo._users[user_ids[4]] = User(id=user_ids[4], email="user5@example.com", name="User 5")

    interpreter = create_test_interpreter(user_repo=fake_repo)

    result = await run_ws_program(multi_user_lookup(user_ids), interpreter)

    match result:
        case Ok(stats):
            print(f"✓ Batch complete: {stats}")
            websocket = interpreter._websocket._connection
            print("  Messages sent:")
            for msg in websocket._sent_messages:
                print(f"    → {msg}")

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
