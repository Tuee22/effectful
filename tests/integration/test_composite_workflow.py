"""Integration tests for composite workflows spanning multiple services.

This module tests workflows that combine multiple real infrastructure
components: PostgreSQL, Redis, MinIO. Each test uses clean_all fixture
for declarative, idempotent test isolation across all services.
"""

from collections.abc import Generator
from uuid import UUID, uuid4

import asyncpg
import pytest
from pytest_mock import MockerFixture
from redis.asyncio import Redis

from effectful.adapters.postgres import PostgresChatMessageRepository, PostgresUserRepository
from effectful.adapters.redis_cache import RedisProfileCache
from effectful.adapters.s3_storage import S3ObjectStorage
from effectful.algebraic.result import Err, Ok
from effectful.domain.cache_result import CacheMiss
from effectful.domain.message import ChatMessage
from effectful.domain.profile import ProfileData
from effectful.domain.s3_object import PutSuccess, S3Object
from effectful.domain.user import User, UserNotFound
from effectful.effects.cache import GetCachedProfile, PutCachedProfile
from effectful.effects.database import GetUserById, SaveChatMessage
from effectful.effects.storage import GetObject, PutObject
from effectful.effects.websocket import SendText
from effectful.infrastructure.websocket import WebSocketConnection
from effectful.interpreters.composite import create_composite_interpreter
from effectful.programs.program_types import AllEffects, EffectResult
from effectful.programs.runners import run_ws_program


class TestCompositeWorkflowIntegration:
    """Integration tests for composite workflows with multiple real services."""

    @pytest.mark.asyncio
    async def test_db_to_cache_workflow(
        self,
        clean_db: asyncpg.Connection,
        clean_redis: Redis,
        mocker: MockerFixture,
    ) -> None:
        """Workflow: lookup user in DB, cache profile in Redis."""
        # Seed user in PostgreSQL
        user_id = uuid4()
        await clean_db.execute(
            "INSERT INTO users (id, email, name) VALUES ($1, $2, $3)",
            user_id,
            "alice@example.com",
            "Alice",
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

        # Define workflow
        def db_to_cache_program(
            uid: UUID,
        ) -> Generator[AllEffects, EffectResult, bool]:
            # 1. Lookup user in PostgreSQL
            user_result = yield GetUserById(user_id=uid)

            match user_result:
                case User() as user:
                    pass
                case _:
                    yield SendText(text="User not found")
                    return False

            # 2. Create profile and cache in Redis
            profile = ProfileData(id=str(user.id), name=user.name)
            yield PutCachedProfile(user_id=uid, profile_data=profile, ttl_seconds=300)
            yield SendText(text=f"Cached profile for {user.name}")

            # 3. Verify cache hit
            cached = yield GetCachedProfile(user_id=uid)
            match cached:
                case ProfileData() as cached_profile:
                    yield SendText(text=f"Cache verified: {cached_profile.name}")
                    return True
                case _:
                    return False

        # Act
        result = await run_ws_program(db_to_cache_program(user_id), interpreter)

        # Assert
        match result:
            case Ok(success):
                assert success is True
                assert mock_ws.send_text.call_count == 2
                mock_ws.send_text.assert_any_call("Cached profile for Alice")
                mock_ws.send_text.assert_any_call("Cache verified: Alice")

                # Verify in real Redis
                key = f"profile:{user_id}"
                exists = await clean_redis.exists(key)
                assert exists == 1
            case Err(error):
                pytest.fail(f"Expected Ok(True), got Err({error})")

    @pytest.mark.asyncio
    async def test_db_cache_storage_workflow(
        self,
        clean_db: asyncpg.Connection,
        clean_redis: Redis,
        clean_minio: str,
        object_storage: S3ObjectStorage,
        mocker: MockerFixture,
    ) -> None:
        """Workflow: lookup user, cache profile, save avatar to S3."""
        # Seed user in PostgreSQL
        user_id = uuid4()
        await clean_db.execute(
            "INSERT INTO users (id, email, name) VALUES ($1, $2, $3)",
            user_id,
            "bob@example.com",
            "Bob",
        )

        avatar_content = b"fake avatar image data"

        # Create interpreter with all real services
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=PostgresUserRepository(clean_db),
            message_repo=PostgresChatMessageRepository(clean_db),
            cache=RedisProfileCache(clean_redis),
            object_storage=object_storage,
        )

        # Define workflow
        def full_profile_workflow(
            uid: UUID, bucket: str, avatar: bytes
        ) -> Generator[AllEffects, EffectResult, str]:
            # 1. Lookup user in PostgreSQL
            user_result = yield GetUserById(user_id=uid)

            match user_result:
                case User() as user:
                    pass
                case _:
                    return "not_found"

            # 2. Cache profile in Redis
            profile = ProfileData(id=str(user.id), name=user.name)
            yield PutCachedProfile(user_id=uid, profile_data=profile, ttl_seconds=300)
            yield SendText(text=f"Profile cached: {user.name}")

            # 3. Save avatar to MinIO S3
            avatar_key = f"avatars/{uid}/avatar.png"
            put_result = yield PutObject(
                bucket=bucket,
                key=avatar_key,
                content=avatar,
                content_type="image/png",
            )

            match put_result:
                case PutSuccess():
                    yield SendText(text=f"Avatar saved: {avatar_key}")
                case _:
                    return "storage_failed"

            # 4. Verify everything is in place
            cached = yield GetCachedProfile(user_id=uid)
            obj = yield GetObject(bucket=bucket, key=avatar_key)

            cache_ok = isinstance(cached, ProfileData)
            storage_ok = isinstance(obj, S3Object)

            if cache_ok and storage_ok:
                yield SendText(text="All systems verified")
                return "success"
            else:
                return "verification_failed"

        # Act
        result = await run_ws_program(
            full_profile_workflow(user_id, clean_minio, avatar_content), interpreter
        )

        # Assert
        match result:
            case Ok(outcome):
                assert outcome == "success"
                assert mock_ws.send_text.call_count == 3

                # Verify in real PostgreSQL (user exists)
                row = await clean_db.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
                assert row is not None

                # Verify in real Redis (profile cached)
                key = f"profile:{user_id}"
                exists = await clean_redis.exists(key)
                assert exists == 1

                # Storage already verified in workflow
            case Err(error):
                pytest.fail(f"Expected Ok('success'), got Err({error})")

    @pytest.mark.asyncio
    async def test_message_with_cache_lookup_workflow(
        self,
        clean_db: asyncpg.Connection,
        clean_redis: Redis,
        mocker: MockerFixture,
    ) -> None:
        """Workflow: cache profile, save message, demonstrate cache usage."""
        # Seed user in PostgreSQL
        user_id = uuid4()
        await clean_db.execute(
            "INSERT INTO users (id, email, name) VALUES ($1, $2, $3)",
            user_id,
            "charlie@example.com",
            "Charlie",
        )

        # Create interpreter
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=PostgresUserRepository(clean_db),
            message_repo=PostgresChatMessageRepository(clean_db),
            cache=RedisProfileCache(clean_redis),
        )

        # Define workflow
        def message_with_cache_program(
            uid: UUID,
        ) -> Generator[AllEffects, EffectResult, int]:
            # 1. Check cache first
            cached = yield GetCachedProfile(user_id=uid)

            match cached:
                case ProfileData() as profile:
                    name = profile.name
                    yield SendText(text=f"Cache hit: {name}")
                case CacheMiss():
                    # 2. Cache miss - fetch from DB
                    user_result = yield GetUserById(user_id=uid)
                    match user_result:
                        case User() as user:
                            name = user.name
                        case _:
                            return 0

                    # 3. Cache the profile
                    profile = ProfileData(id=str(uid), name=name)
                    yield PutCachedProfile(user_id=uid, profile_data=profile, ttl_seconds=300)
                    yield SendText(text=f"Cached: {name}")
                case _:
                    return 0

            # 4. Save multiple messages
            messages = [
                f"Hello from {name}!",
                f"{name} is online",
                f"{name} says goodbye",
            ]

            for msg_text in messages:
                message = yield SaveChatMessage(user_id=uid, text=msg_text)
                assert isinstance(message, ChatMessage)

            yield SendText(text=f"Saved {len(messages)} messages for {name}")
            return len(messages)

        # Act
        result = await run_ws_program(message_with_cache_program(user_id), interpreter)

        # Assert
        match result:
            case Ok(count):
                assert count == 3

                # Verify messages in PostgreSQL
                rows = await clean_db.fetch(
                    "SELECT * FROM chat_messages WHERE user_id = $1 ORDER BY created_at",
                    user_id,
                )
                assert len(rows) == 3
                text_value = rows[0]["text"]
                assert isinstance(text_value, str)
                assert "Hello from Charlie!" in text_value

                # Verify profile in Redis
                key = f"profile:{user_id}"
                exists = await clean_redis.exists(key)
                assert exists == 1
            case Err(error):
                pytest.fail(f"Expected Ok(3), got Err({error})")

    @pytest.mark.asyncio
    async def test_error_propagation_across_services(
        self,
        clean_db: asyncpg.Connection,
        clean_redis: Redis,
        mocker: MockerFixture,
    ) -> None:
        """Workflow demonstrates fail-fast error propagation."""
        # No user seeded - will cause UserNotFound

        # Create interpreter
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=PostgresUserRepository(clean_db),
            message_repo=PostgresChatMessageRepository(clean_db),
            cache=RedisProfileCache(clean_redis),
        )

        # Define workflow that should fail gracefully
        def failing_workflow(
            uid: UUID,
        ) -> Generator[AllEffects, EffectResult, str]:
            # 1. Try to lookup nonexistent user
            user_result = yield GetUserById(user_id=uid)

            match user_result:
                case UserNotFound():
                    yield SendText(text="User not found")
                    return "not_found"
                case User() as user:
                    profile = ProfileData(id=str(user.id), name=user.name)
                    yield PutCachedProfile(user_id=uid, profile_data=profile, ttl_seconds=300)
                    return "success"
                case _:
                    return "error"

        # Act
        result = await run_ws_program(failing_workflow(uuid4()), interpreter)

        # Assert
        match result:
            case Ok(outcome):
                assert outcome == "not_found"
                mock_ws.send_text.assert_called_once_with("User not found")

                # Verify nothing was cached
                keys = await clean_redis.keys("profile:*")
                assert len(keys) == 0
            case Err(error):
                pytest.fail(f"Expected Ok('not_found'), got Err({error})")
