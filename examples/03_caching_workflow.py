"""Example 03: Caching Workflow

Effect program demonstrating cache-aside pattern with database fallback.

Run:
    python -m examples.03_caching_workflow
"""

import asyncio
from collections.abc import Generator
from uuid import UUID, uuid4
from unittest.mock import AsyncMock

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
from effectful.domain.cache_result import CacheHit
from effectful.infrastructure.cache import ProfileCache
from effectful.infrastructure.repositories import ChatMessageRepository, UserRepository
from effectful.infrastructure.websocket import WebSocketConnection
from effectful.interpreters.composite import create_composite_interpreter


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
    user_id = uuid4()

    # Typed AsyncMocks for infrastructure with simple in-memory behavior
    ws = AsyncMock(spec=WebSocketConnection)
    ws.is_open.return_value = True

    cache_store: dict[UUID, ProfileData] = {}

    async def get_profile(uid: UUID) -> CacheHit | CacheMiss:
        if uid in cache_store:
            return CacheHit(value=cache_store[uid], ttl_remaining=300)
        return CacheMiss(key=f"profile:{uid}", reason="not_found")

    async def put_profile(uid: UUID, profile: ProfileData, ttl_seconds: int) -> None:
        _ = ttl_seconds  # not used for demo
        cache_store[uid] = profile

    cache = AsyncMock(spec=ProfileCache)
    cache.get_profile.side_effect = get_profile
    cache.put_profile.side_effect = put_profile

    user_repo = AsyncMock(spec=UserRepository)
    user_repo.get_by_id.return_value = User(id=user_id, email="bob@example.com", name="Bob")

    message_repo = AsyncMock(spec=ChatMessageRepository)
    message_repo.save_message.return_value = None

    interpreter = create_composite_interpreter(
        websocket_connection=ws,
        user_repo=user_repo,
        message_repo=message_repo,
        cache=cache,
    )

    print(f"Running caching workflow for user {user_id}...\n")

    # First request (cache miss)
    print("=== First Request (expect cache miss) ===")
    result1 = await run_ws_program(get_profile_with_caching(user_id), interpreter)

    match result1:
        case Ok(value):
            print(f"✓ Result: {value}")
            print("  WebSocket send_text calls:")
            _ = [
                print(f"    → {call.args[0]}")
                for call in ws.send_text.call_args_list
            ]
        case Err(error):
            print(f"✗ Error: {error}")

    # Clear WebSocket messages for next request
    ws.send_text.reset_mock()

    # Second request (cache hit)
    print("\n=== Second Request (expect cache hit) ===")
    result2 = await run_ws_program(get_profile_with_caching(user_id), interpreter)

    match result2:
        case Ok(value):
            print(f"✓ Result: {value}")
            print("  WebSocket send_text calls:")
            _ = [
                print(f"    → {call.args[0]}")
                for call in ws.send_text.call_args_list
            ]
        case Err(error):
            print(f"✗ Error: {error}")

    # Show cache state
    print("\n=== Cache State ===")
    print(f"Cached profiles: {len(cache_store)}")
    _ = [print(f"  - {uid}: {profile.name} ({profile.email})") for uid, profile in cache_store.items()]


if __name__ == "__main__":
    asyncio.run(main())
