"""Integration tests for cache workflows with real Redis.

This module tests cache effect workflows using run_ws_program
with real Redis infrastructure. Each test uses clean_redis fixture
for declarative, idempotent test isolation.
"""

from collections.abc import Generator
from uuid import UUID, uuid4

import asyncpg
import pytest
from pytest_mock import MockerFixture
from redis.asyncio import Redis

from effectful.adapters.postgres import PostgresChatMessageRepository, PostgresUserRepository
from effectful.adapters.redis_cache import RedisProfileCache
from effectful.algebraic.result import Err, Ok
from effectful.domain.cache_result import CacheHit, CacheMiss
from effectful.domain.profile import ProfileData
from effectful.domain.user import User, UserNotFound
from effectful.effects.cache import (
    GetCachedProfile,
    GetCachedValue,
    InvalidateCache,
    PutCachedProfile,
    PutCachedValue,
)
from effectful.effects.database import GetUserById
from effectful.effects.websocket import SendText
from effectful.infrastructure.repositories import ChatMessageRepository, UserRepository
from effectful.infrastructure.websocket import WebSocketConnection
from effectful.interpreters.composite import create_composite_interpreter
from effectful.programs.program_types import AllEffects, EffectResult
from effectful.programs.runners import run_ws_program


class TestCacheWorkflowIntegration:
    """Integration tests for cache workflows with real Redis."""

    @pytest.mark.asyncio
    async def test_put_and_get_profile_workflow(
        self, clean_redis: Redis, mocker: MockerFixture
    ) -> None:
        """Workflow stores and retrieves profile from real Redis."""
        user_id = uuid4()
        profile = ProfileData(id=str(user_id), name="Alice")

        # Create interpreter with real Redis cache
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=RedisProfileCache(clean_redis),
        )

        # Define workflow
        def put_get_profile_program(
            uid: UUID, prof: ProfileData
        ) -> Generator[AllEffects, EffectResult, str]:
            # Put profile in cache
            yield PutCachedProfile(user_id=uid, profile_data=prof, ttl_seconds=300)

            # Get profile back
            cached = yield GetCachedProfile(user_id=uid)

            match cached:
                case ProfileData() as cached_profile:
                    yield SendText(text=f"Retrieved: {cached_profile.name}")
                    return cached_profile.name
                case CacheMiss():
                    yield SendText(text="Cache miss")
                    return "miss"
                case _:
                    return "error"

        # Act
        result = await run_ws_program(put_get_profile_program(user_id, profile), interpreter)

        # Assert
        match result:
            case Ok(name):
                assert name == "Alice"
                mock_ws.send_text.assert_called_once_with("Retrieved: Alice")

                # Verify in real Redis
                key = f"profile:{user_id}"
                exists = await clean_redis.exists(key)
                assert exists == 1
            case Err(error):
                pytest.fail(f"Expected Ok, got Err({error})")

    @pytest.mark.asyncio
    async def test_cache_miss_workflow(self, clean_redis: Redis, mocker: MockerFixture) -> None:
        """Workflow handles cache miss gracefully."""
        user_id = uuid4()  # No profile seeded

        # Create interpreter
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=RedisProfileCache(clean_redis),
        )

        # Define workflow
        def cache_miss_program(
            uid: UUID,
        ) -> Generator[AllEffects, EffectResult, str]:
            cached = yield GetCachedProfile(user_id=uid)

            match cached:
                case CacheMiss(key=key, reason=reason):
                    yield SendText(text=f"Miss: {reason}")
                    return "miss"
                case ProfileData():
                    return "hit"
                case _:
                    return "error"

        # Act
        result = await run_ws_program(cache_miss_program(user_id), interpreter)

        # Assert
        match result:
            case Ok(outcome):
                assert outcome == "miss"
                mock_ws.send_text.assert_called_once_with("Miss: not_found")
            case Err(error):
                pytest.fail(f"Expected Ok('miss'), got Err({error})")

    @pytest.mark.asyncio
    async def test_cache_with_database_fallback_workflow(
        self,
        clean_db: asyncpg.Connection,
        clean_redis: Redis,
        mocker: MockerFixture,
    ) -> None:
        """Workflow: check cache, fallback to DB, populate cache."""
        # Seed user in database (not in cache)
        user_id = uuid4()
        await clean_db.execute(
            "INSERT INTO users (id, email, name) VALUES ($1, $2, $3)",
            user_id,
            "bob@example.com",
            "Bob",
        )

        # Create interpreter with real DB and Redis
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=PostgresUserRepository(clean_db),
            message_repo=PostgresChatMessageRepository(clean_db),
            cache=RedisProfileCache(clean_redis),
        )

        # Define cache-aware workflow
        def cache_fallback_program(
            uid: UUID,
        ) -> Generator[AllEffects, EffectResult, str]:
            # 1. Try cache first
            cached = yield GetCachedProfile(user_id=uid)

            match cached:
                case ProfileData() as profile:
                    yield SendText(text=f"Cache hit: {profile.name}")
                    return "cache_hit"
                case CacheMiss():
                    # 2. Cache miss - fetch from database
                    user_result = yield GetUserById(user_id=uid)

                    match user_result:
                        case User() as user:
                            # 3. Create profile and cache it
                            profile = ProfileData(id=str(user.id), name=user.name)
                            yield PutCachedProfile(
                                user_id=uid, profile_data=profile, ttl_seconds=300
                            )
                            yield SendText(text=f"DB hit, cached: {user.name}")
                            return "db_hit"
                        case UserNotFound():
                            yield SendText(text="Not found in DB")
                            return "not_found"
                        case _:
                            return "error"
                case _:
                    return "error"

        # Act - First call (cache miss, DB hit)
        result1 = await run_ws_program(cache_fallback_program(user_id), interpreter)

        # Assert first call
        match result1:
            case Ok(outcome):
                assert outcome == "db_hit"
                mock_ws.send_text.assert_called_with("DB hit, cached: Bob")

                # Verify profile now in cache
                key = f"profile:{user_id}"
                exists = await clean_redis.exists(key)
                assert exists == 1
            case Err(error):
                pytest.fail(f"Expected Ok('db_hit'), got Err({error})")

        # Reset mock
        mock_ws.reset_mock()

        # Act - Second call (should be cache hit)
        result2 = await run_ws_program(cache_fallback_program(user_id), interpreter)

        # Assert second call
        match result2:
            case Ok(outcome):
                assert outcome == "cache_hit"
                mock_ws.send_text.assert_called_with("Cache hit: Bob")
            case Err(error):
                pytest.fail(f"Expected Ok('cache_hit'), got Err({error})")

    @pytest.mark.asyncio
    async def test_multiple_profiles_workflow(
        self, clean_redis: Redis, mocker: MockerFixture
    ) -> None:
        """Workflow stores and retrieves multiple profiles."""
        user_ids = [uuid4() for _ in range(3)]
        names = ["Alice", "Bob", "Charlie"]

        # Create interpreter
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=RedisProfileCache(clean_redis),
        )

        # Define workflow
        def multi_profile_program(
            uids: list[UUID], user_names: list[str]
        ) -> Generator[AllEffects, EffectResult, int]:
            # Store all profiles
            for uid, name in zip(uids, user_names, strict=True):
                profile = ProfileData(id=str(uid), name=name)
                yield PutCachedProfile(user_id=uid, profile_data=profile, ttl_seconds=300)

            # Retrieve and count
            found_count = 0
            for uid in uids:
                cached = yield GetCachedProfile(user_id=uid)
                match cached:
                    case ProfileData():
                        found_count += 1
                    case _:
                        pass

            yield SendText(text=f"Found {found_count} profiles")
            return found_count

        # Act
        result = await run_ws_program(multi_profile_program(user_ids, names), interpreter)

        # Assert
        match result:
            case Ok(count):
                assert count == 3
                mock_ws.send_text.assert_called_once_with("Found 3 profiles")

                # Verify all in Redis
                for uid in user_ids:
                    key = f"profile:{uid}"
                    exists = await clean_redis.exists(key)
                    assert exists == 1
            case Err(error):
                pytest.fail(f"Expected Ok(3), got Err({error})")

    @pytest.mark.asyncio
    async def test_invalidate_cache_workflow(
        self, clean_redis: Redis, mocker: MockerFixture
    ) -> None:
        """Workflow invalidates cache entry in real Redis."""
        user_id = uuid4()
        profile = ProfileData(id=str(user_id), name="To Invalidate")

        # Create interpreter
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=RedisProfileCache(clean_redis),
        )

        # Define workflow
        def invalidate_program(
            uid: UUID, prof: ProfileData
        ) -> Generator[AllEffects, EffectResult, bool]:
            # Put profile
            yield PutCachedProfile(user_id=uid, profile_data=prof, ttl_seconds=300)

            # Verify it exists
            cached = yield GetCachedProfile(user_id=uid)
            match cached:
                case ProfileData():
                    pass
                case CacheMiss():
                    return False
                case _:
                    return False

            # Invalidate
            key = f"profile:{uid}"
            deleted = yield InvalidateCache(key=key)
            assert isinstance(deleted, bool)

            yield SendText(text=f"Invalidated: {deleted}")

            # Verify it's gone
            cached_after = yield GetCachedProfile(user_id=uid)
            match cached_after:
                case CacheMiss():
                    yield SendText(text="Verified deleted")
                    return True
                case ProfileData():
                    return False
                case _:
                    return False

        # Act
        result = await run_ws_program(invalidate_program(user_id, profile), interpreter)

        # Assert
        match result:
            case Ok(success):
                assert success is True
                # Verify in real Redis
                key = f"profile:{user_id}"
                exists = await clean_redis.exists(key)
                assert exists == 0
            case Err(error):
                pytest.fail(f"Expected Ok(True), got Err({error})")

    @pytest.mark.asyncio
    async def test_get_cached_value_workflow(
        self, clean_redis: Redis, mocker: MockerFixture
    ) -> None:
        """Workflow gets generic cached value from real Redis."""
        key = f"test-key-{uuid4()}"
        value = b"test value bytes"

        # Create interpreter
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=RedisProfileCache(clean_redis),
        )

        # Define workflow
        def get_value_program(k: str, v: bytes) -> Generator[AllEffects, EffectResult, bool]:
            # Put value
            yield PutCachedValue(key=k, value=v, ttl_seconds=300)
            yield SendText(text="Value stored")

            # Get value
            result = yield GetCachedValue(key=k)

            match result:
                case bytes() as retrieved:
                    yield SendText(text=f"Retrieved {len(retrieved)} bytes")
                    return retrieved == v
                case CacheMiss():
                    yield SendText(text="Cache miss")
                    return False
                case _:
                    return False

        # Act
        result = await run_ws_program(get_value_program(key, value), interpreter)

        # Assert
        match result:
            case Ok(success):
                assert success is True
                assert mock_ws.send_text.call_count == 2
            case Err(error):
                pytest.fail(f"Expected Ok(True), got Err({error})")

    @pytest.mark.asyncio
    async def test_get_cached_value_miss_workflow(
        self, clean_redis: Redis, mocker: MockerFixture
    ) -> None:
        """Workflow handles cache miss for generic value."""
        key = f"nonexistent-key-{uuid4()}"

        # Create interpreter
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=RedisProfileCache(clean_redis),
        )

        # Define workflow
        def miss_program(k: str) -> Generator[AllEffects, EffectResult, str]:
            result = yield GetCachedValue(key=k)

            match result:
                case CacheMiss(key=key_name, reason=reason):
                    yield SendText(text=f"Miss: {reason}")
                    return "miss"
                case bytes():
                    return "hit"
                case _:
                    return "error"

        # Act
        result = await run_ws_program(miss_program(key), interpreter)

        # Assert
        match result:
            case Ok(outcome):
                assert outcome == "miss"
                mock_ws.send_text.assert_called_once_with("Miss: not_found")
            case Err(error):
                pytest.fail(f"Expected Ok('miss'), got Err({error})")

    @pytest.mark.asyncio
    async def test_put_cached_value_workflow(
        self, clean_redis: Redis, mocker: MockerFixture
    ) -> None:
        """Workflow puts generic value in real Redis."""
        key = f"put-test-{uuid4()}"
        value = b'{"data": "json bytes"}'

        # Create interpreter
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=RedisProfileCache(clean_redis),
        )

        # Define workflow
        def put_value_program(
            k: str, v: bytes, ttl: int
        ) -> Generator[AllEffects, EffectResult, bool]:
            result = yield PutCachedValue(key=k, value=v, ttl_seconds=ttl)
            # PutCachedValue returns True on success
            assert result is True

            yield SendText(text=f"Stored {len(v)} bytes with TTL {ttl}")
            return True

        # Act
        result = await run_ws_program(put_value_program(key, value, 300), interpreter)

        # Assert
        match result:
            case Ok(success):
                assert success is True
                # Verify in real Redis
                stored = await clean_redis.get(key)
                assert stored is not None
                # Check TTL is set
                ttl = await clean_redis.ttl(key)
                assert ttl > 0
                assert ttl <= 300
            case Err(error):
                pytest.fail(f"Expected Ok(True), got Err({error})")

    @pytest.mark.asyncio
    async def test_invalidate_nonexistent_key_workflow(
        self, clean_redis: Redis, mocker: MockerFixture
    ) -> None:
        """Workflow handles invalidation of non-existent key."""
        key = f"nonexistent-{uuid4()}"

        # Create interpreter
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=RedisProfileCache(clean_redis),
        )

        # Define workflow
        def invalidate_missing_program(k: str) -> Generator[AllEffects, EffectResult, bool]:
            deleted = yield InvalidateCache(key=k)
            assert isinstance(deleted, bool)

            yield SendText(text=f"Deleted: {deleted}")
            return deleted

        # Act
        result = await run_ws_program(invalidate_missing_program(key), interpreter)

        # Assert
        match result:
            case Ok(deleted):
                # Should return False since key didn't exist
                assert deleted is False
                mock_ws.send_text.assert_called_once_with("Deleted: False")
            case Err(error):
                pytest.fail(f"Expected Ok(False), got Err({error})")

    @pytest.mark.asyncio
    async def test_multiple_generic_values_workflow(
        self, clean_redis: Redis, mocker: MockerFixture
    ) -> None:
        """Workflow stores and retrieves multiple generic values."""
        keys = [f"multi-{uuid4()}" for _ in range(3)]
        values = [f"value-{i}".encode() for i in range(3)]

        # Create interpreter
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=RedisProfileCache(clean_redis),
        )

        # Define workflow
        def multi_value_program(
            ks: list[str], vs: list[bytes]
        ) -> Generator[AllEffects, EffectResult, int]:
            # Store all values
            for k, v in zip(ks, vs, strict=True):
                yield PutCachedValue(key=k, value=v, ttl_seconds=300)

            # Retrieve and count
            found_count = 0
            for k in ks:
                result = yield GetCachedValue(key=k)
                match result:
                    case bytes():
                        found_count += 1
                    case _:
                        pass

            yield SendText(text=f"Found {found_count} values")
            return found_count

        # Act
        result = await run_ws_program(multi_value_program(keys, values), interpreter)

        # Assert
        match result:
            case Ok(count):
                assert count == 3
                mock_ws.send_text.assert_called_once_with("Found 3 values")
            case Err(error):
                pytest.fail(f"Expected Ok(3), got Err({error})")
