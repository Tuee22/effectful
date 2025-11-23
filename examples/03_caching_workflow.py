"""Example 03: Caching Workflow

Effect program demonstrating cache-aside pattern with database fallback.

Run:
    python -m examples.03_caching_workflow
"""

import asyncio
from collections.abc import Generator
from uuid import UUID, uuid4

from effectful import (
    AllEffects,
    CacheMiss,
    EffectResult,
    GetCachedProfile,
    GetUserById,
    ProfileData,
    PutCachedProfile,
    SendText,
    User,
    UserNotFound,
    run_ws_program,
)
from effectful.algebraic.result import Err, Ok
from effectful.testing import (
    FakeProfileCache,
    FakeUserRepository,
    create_test_interpreter,
)


def get_profile_with_caching(user_id: UUID) -> Generator[AllEffects, EffectResult, str]:
    """Get user profile with cache-aside pattern.

    Flow:
    1. Try cache first
    2. On cache miss, lookup user in database
    3. Store profile in cache
    4. Send profile to client

    Args:
        user_id: User to lookup

    Yields:
        GetCachedProfile, GetUserById, PutCachedProfile, SendText effects

    Returns:
        Status message ("cache_hit" | "cache_miss" | "not_found")
    """
    # Try cache first
    cached = yield GetCachedProfile(user_id=user_id)

    match cached:
        case ProfileData(name=name, email=email):
            # Cache hit
            yield SendText(text=f"Profile: {name} ({email}) [from cache]")
            return "cache_hit"

        case CacheMiss():
            # Cache miss - lookup user in database
            yield SendText(text="Cache miss - querying database...")

            user_result = yield GetUserById(user_id=user_id)

            match user_result:
                case UserNotFound():
                    # User not found
                    yield SendText(text="Error: User not found")
                    return "not_found"

                case User(id=uid, name=name, email=email):
                    # User found - cache the profile
                    profile = ProfileData(id=str(uid), name=name, email=email)

                    yield PutCachedProfile(user_id=uid, profile_data=profile, ttl_seconds=300)

                    # Send profile to client
                    yield SendText(text=f"Profile: {name} ({email}) [from database]")

                    return "cache_miss"

                case _:
                    # All expected cases handled above - defensive
                    return "error"

        case _:
            # All expected cases handled above - defensive
            return "error"


async def main() -> None:
    """Run the caching workflow program."""
    # Setup test data
    fake_repo = FakeUserRepository()
    fake_cache = FakeProfileCache()
    user_id = uuid4()

    fake_repo._users[user_id] = User(id=user_id, email="bob@example.com", name="Bob")

    # Create interpreter
    interpreter = create_test_interpreter(user_repo=fake_repo, cache=fake_cache)

    print(f"Running caching workflow for user {user_id}...\n")

    # First request (cache miss)
    print("=== First Request (expect cache miss) ===")
    result1 = await run_ws_program(get_profile_with_caching(user_id), interpreter)

    match result1:
        case Ok(value):
            print(f"✓ Result: {value}")
            websocket = interpreter._websocket._connection
            _ = [print(f"  → {msg}") for msg in websocket._sent_messages]
        case Err(error):
            print(f"✗ Error: {error}")

    # Clear WebSocket messages for next request
    interpreter._websocket._connection._sent_messages.clear()

    # Second request (cache hit)
    print("\n=== Second Request (expect cache hit) ===")
    result2 = await run_ws_program(get_profile_with_caching(user_id), interpreter)

    match result2:
        case Ok(value):
            print(f"✓ Result: {value}")
            websocket = interpreter._websocket._connection
            _ = [print(f"  → {msg}") for msg in websocket._sent_messages]
        case Err(error):
            print(f"✗ Error: {error}")

    # Show cache state
    print("\n=== Cache State ===")
    print(f"Cached profiles: {len(fake_cache._cache)}")
    _ = [
        print(f"  - {uid}: {profile.name} ({profile.email})")
        for uid, profile in fake_cache._cache.items()
    ]


if __name__ == "__main__":
    asyncio.run(main())
