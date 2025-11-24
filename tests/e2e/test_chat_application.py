"""E2E tests for the chat application.

These tests exercise all 6 infrastructure types:
- Auth (Redis JWT)
- Cache (Redis)
- Database (PostgreSQL)
- Messaging (Pulsar)
- Storage (MinIO S3)
- WebSocket

Each test uses clean_db, clean_redis, etc. fixtures for isolation.
The base_state fixture is available for tests that need pre-seeded data.
"""

from collections.abc import Generator
from datetime import datetime, timezone
from uuid import UUID, uuid4

import asyncpg
import pytest
from redis.asyncio import Redis

from effectful.adapters.postgres import PostgresChatMessageRepository, PostgresUserRepository
from effectful.adapters.pulsar_messaging import PulsarMessageConsumer, PulsarMessageProducer
from effectful.adapters.redis_auth import RedisAuthService
from effectful.adapters.redis_cache import RedisProfileCache
from effectful.adapters.s3_storage import S3ObjectStorage
from effectful.domain.cache_result import CacheMiss
from effectful.domain.message import ChatMessage
from effectful.domain.message_envelope import (
    AcknowledgeSuccess,
    ConsumeTimeout,
    MessageEnvelope,
    NackSuccess,
)
from effectful.domain.profile import ProfileData
from effectful.domain.token_result import TokenExpired, TokenInvalid, TokenValid
from effectful.domain.user import User, UserNotFound
from effectful.effects.auth import GenerateToken, HashPassword, ValidatePassword, ValidateToken
from effectful.effects.cache import GetCachedProfile, PutCachedProfile
from effectful.effects.database import (
    CreateUser,
    GetUserById,
    ListUsers,
    SaveChatMessage,
    UpdateUser,
)
from effectful.effects.messaging import (
    AcknowledgeMessage,
    ConsumeMessage,
    NegativeAcknowledge,
    PublishMessage,
)
from effectful.effects.storage import GetObject, PutObject
from effectful.effects.websocket import SendText
from effectful.interpreters.composite import create_composite_interpreter
from effectful.programs.program_types import AllEffects, EffectResult
from effectful.programs.runners import run_ws_program
from tests.e2e.client.ws_client import E2EWebSocketClient
from tests.fixtures.base_state import (
    ALICE_ID,
    ALICE_PASSWORD,
    ALICE_PASSWORD_HASH,
    BOB_ID,
)
from effectful.testing import unwrap_ok


class TestUserRegistration:
    """Test user registration flow."""

    @pytest.mark.asyncio
    async def test_register_new_user(
        self,
        clean_db: asyncpg.Connection,
        clean_redis: Redis,
        ws_client: E2EWebSocketClient,
        auth_service: RedisAuthService,
    ) -> None:
        """Register a new user with password hashing."""

        def register_user_program(
            email: str, name: str, password: str
        ) -> Generator[AllEffects, EffectResult, UUID | None]:
            """Register a new user with hashed password."""
            password_hash = yield HashPassword(password=password)
            assert isinstance(password_hash, str)

            user = yield CreateUser(email=email, name=name, password_hash=password_hash)

            if isinstance(user, User):
                yield SendText(text=f"User registered: {user.id}")
                return user.id

            return None

        interpreter = create_composite_interpreter(
            websocket_connection=ws_client,
            user_repo=PostgresUserRepository(clean_db),
            message_repo=PostgresChatMessageRepository(clean_db),
            cache=RedisProfileCache(clean_redis),
            auth_service=auth_service,
        )

        result = await run_ws_program(
            register_user_program("newuser@example.com", "New User", "securepass123"),
            interpreter,
        )

        user_id = unwrap_ok(result)
        assert user_id is not None

        # Verify user in database
        row = await clean_db.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
        assert row is not None
        assert row["email"] == "newuser@example.com"
        assert row["name"] == "New User"
        password_hash = row["password_hash"]
        assert isinstance(password_hash, str)
        # PBKDF2-HMAC-SHA256 hash format: "salt$hash"
        assert "$" in password_hash and len(password_hash) > 100

        # Verify WebSocket message
        assert "User registered" in ws_client.get_sent_messages()[0]


class TestAuthentication:
    """Test authentication flow with JWT tokens."""

    @pytest.mark.asyncio
    async def test_login_and_token_generation(
        self,
        clean_db: asyncpg.Connection,
        clean_redis: Redis,
        ws_client: E2EWebSocketClient,
        auth_service: RedisAuthService,
    ) -> None:
        """Login with valid credentials and receive JWT token."""
        # Seed a user
        user_id = uuid4()
        await clean_db.execute(
            "INSERT INTO users (id, email, name, password_hash) VALUES ($1, $2, $3, $4)",
            user_id,
            "alice@example.com",
            "Alice",
            ALICE_PASSWORD_HASH,
        )

        def login_program(
            uid: UUID, password: str, stored_hash: str
        ) -> Generator[AllEffects, EffectResult, str | None]:
            """Validate password and generate token."""
            is_valid = yield ValidatePassword(password=password, password_hash=stored_hash)

            if not is_valid:
                yield SendText(text="Invalid credentials")
                return None

            token = yield GenerateToken(
                user_id=uid,
                claims={"role": "user"},
                ttl_seconds=3600,
            )
            assert isinstance(token, str)

            yield SendText(text="Login successful")
            return token

        interpreter = create_composite_interpreter(
            websocket_connection=ws_client,
            user_repo=PostgresUserRepository(clean_db),
            message_repo=PostgresChatMessageRepository(clean_db),
            cache=RedisProfileCache(clean_redis),
            auth_service=auth_service,
        )

        result = await run_ws_program(
            login_program(user_id, ALICE_PASSWORD, ALICE_PASSWORD_HASH),
            interpreter,
        )

        token = unwrap_ok(result)
        assert token is not None
        assert len(token) > 50

        # Verify token is valid
        validation = await auth_service.validate_token(token)
        assert isinstance(validation, TokenValid)
        assert validation.user_id == user_id

    @pytest.mark.asyncio
    async def test_token_validation(
        self,
        clean_db: asyncpg.Connection,
        clean_redis: Redis,
        ws_client: E2EWebSocketClient,
        auth_service: RedisAuthService,
    ) -> None:
        """Validate an existing token."""
        user_id = uuid4()
        token = await auth_service.generate_token(
            user_id=user_id,
            claims={"role": "admin"},
            ttl_seconds=3600,
        )

        def validate_token_program(tok: str) -> Generator[AllEffects, EffectResult, bool]:
            """Validate a token and report result."""
            result = yield ValidateToken(token=tok)

            match result:
                case TokenValid(user_id=uid):
                    yield SendText(text=f"Token valid for user {uid}")
                    return True
                case TokenExpired():
                    yield SendText(text="Token expired")
                    return False
                case TokenInvalid():
                    yield SendText(text="Token invalid")
                    return False

            return False

        interpreter = create_composite_interpreter(
            websocket_connection=ws_client,
            user_repo=PostgresUserRepository(clean_db),
            message_repo=PostgresChatMessageRepository(clean_db),
            cache=RedisProfileCache(clean_redis),
            auth_service=auth_service,
        )

        result = await run_ws_program(validate_token_program(token), interpreter)

        is_valid = unwrap_ok(result)
        assert is_valid is True
        assert f"Token valid for user {user_id}" in ws_client.get_sent_messages()[0]


class TestCaching:
    """Test cache operations."""

    @pytest.mark.asyncio
    async def test_cache_miss_then_hit(
        self,
        clean_db: asyncpg.Connection,
        clean_redis: Redis,
        ws_client: E2EWebSocketClient,
    ) -> None:
        """Test cache miss on first request, hit on second."""
        # Seed a user
        user_id = uuid4()
        await clean_db.execute(
            "INSERT INTO users (id, email, name) VALUES ($1, $2, $3)",
            user_id,
            "alice@example.com",
            "Alice",
        )

        def get_profile_with_cache(
            uid: UUID,
        ) -> Generator[AllEffects, EffectResult, str]:
            """Get profile with cache-aside pattern."""
            cached = yield GetCachedProfile(user_id=uid)

            match cached:
                case ProfileData(name=name):
                    yield SendText(text=f"Cache hit: {name}")
                    return "cache_hit"
                case CacheMiss():
                    user_result = yield GetUserById(user_id=uid)

                    match user_result:
                        case User(id=user_uid, name=name):
                            profile = ProfileData(id=str(user_uid), name=name)
                            yield PutCachedProfile(
                                user_id=user_uid, profile_data=profile, ttl_seconds=300
                            )
                            yield SendText(text=f"Cache miss: {name}")
                            return "cache_miss"
                        case _:
                            yield SendText(text="User not found")
                            return "not_found"

            return "error"

        interpreter = create_composite_interpreter(
            websocket_connection=ws_client,
            user_repo=PostgresUserRepository(clean_db),
            message_repo=PostgresChatMessageRepository(clean_db),
            cache=RedisProfileCache(clean_redis),
        )

        # First request - cache miss
        result1 = await run_ws_program(get_profile_with_cache(user_id), interpreter)
        assert unwrap_ok(result1) == "cache_miss"
        assert "Cache miss: Alice" in ws_client.get_sent_messages()[0]

        ws_client.clear_sent_messages()

        # Second request - cache hit
        result2 = await run_ws_program(get_profile_with_cache(user_id), interpreter)
        assert unwrap_ok(result2) == "cache_hit"
        assert "Cache hit: Alice" in ws_client.get_sent_messages()[0]


class TestMessaging:
    """Test Pulsar messaging operations."""

    @pytest.mark.asyncio
    async def test_publish_message_to_pulsar(
        self,
        clean_db: asyncpg.Connection,
        clean_redis: Redis,
        ws_client: E2EWebSocketClient,
        pulsar_producer: PulsarMessageProducer,
        pulsar_consumer: PulsarMessageConsumer,
    ) -> None:
        """Publish a message to Pulsar."""
        user_id = uuid4()

        def publish_notification(
            uid: UUID, message: str
        ) -> Generator[AllEffects, EffectResult, str | None]:
            """Publish a notification to Pulsar."""
            payload = f"{uid}:{message}".encode()
            message_id = yield PublishMessage(
                topic="persistent://public/default/notifications",
                payload=payload,
                properties={"user_id": str(uid)},
            )

            if isinstance(message_id, str):
                yield SendText(text=f"Published message: {message_id}")
                return message_id

            return None

        interpreter = create_composite_interpreter(
            websocket_connection=ws_client,
            user_repo=PostgresUserRepository(clean_db),
            message_repo=PostgresChatMessageRepository(clean_db),
            cache=RedisProfileCache(clean_redis),
            message_producer=pulsar_producer,
            message_consumer=pulsar_consumer,
        )

        result = await run_ws_program(
            publish_notification(user_id, "Hello from e2e test"),
            interpreter,
        )

        message_id = unwrap_ok(result)
        assert message_id is not None
        assert "Published message" in ws_client.get_sent_messages()[0]

    @pytest.mark.asyncio
    async def test_consume_and_acknowledge_message(
        self,
        clean_db: asyncpg.Connection,
        clean_redis: Redis,
        ws_client: E2EWebSocketClient,
        pulsar_producer: PulsarMessageProducer,
        pulsar_consumer: PulsarMessageConsumer,
    ) -> None:
        """Publish, consume, and acknowledge a message."""
        user_id = uuid4()
        topic = f"e2e-ack-test-{uuid4()}"
        subscription = f"{topic}/e2e-ack-subscription"

        # First, publish a message directly using the producer
        test_payload = f"{user_id}:test-ack".encode()
        publish_result = await pulsar_producer.publish(
            topic=topic,
            payload=test_payload,
            properties={"test": "acknowledge"},
        )
        # Verify publish succeeded
        from effectful.domain.message_envelope import PublishSuccess

        assert isinstance(publish_result, PublishSuccess)

        def consume_and_ack() -> Generator[AllEffects, EffectResult, str]:
            """Consume message and acknowledge it."""
            # Consume the message
            consume_result = yield ConsumeMessage(
                subscription=subscription,
                timeout_ms=5000,
            )

            # Type narrow and verify we got the message
            match consume_result:
                case MessageEnvelope(message_id=msg_id, payload=payload):
                    yield SendText(text=f"Received: {payload.decode()}")

                    # Acknowledge the message
                    ack_result = yield AcknowledgeMessage(message_id=msg_id)

                    # Verify acknowledgment succeeded
                    match ack_result:
                        case AcknowledgeSuccess():
                            yield SendText(text="Message acknowledged")
                            return "success"
                        case _:
                            yield SendText(text="Ack failed")
                            return "ack_failed"
                case ConsumeTimeout():
                    yield SendText(text="Timeout - no message")
                    return "timeout"
                case _:
                    yield SendText(text="Consume failed")
                    return "consume_failed"

        interpreter = create_composite_interpreter(
            websocket_connection=ws_client,
            user_repo=PostgresUserRepository(clean_db),
            message_repo=PostgresChatMessageRepository(clean_db),
            cache=RedisProfileCache(clean_redis),
            message_producer=pulsar_producer,
            message_consumer=pulsar_consumer,
        )

        result = await run_ws_program(consume_and_ack(), interpreter)

        status = unwrap_ok(result)
        assert status == "success"
        messages = ws_client.get_sent_messages()
        assert any("Received:" in msg and "test-ack" in msg for msg in messages)
        assert "Message acknowledged" in messages

    @pytest.mark.asyncio
    async def test_negative_acknowledge_message(
        self,
        clean_db: asyncpg.Connection,
        clean_redis: Redis,
        ws_client: E2EWebSocketClient,
        pulsar_producer: PulsarMessageProducer,
        pulsar_consumer: PulsarMessageConsumer,
    ) -> None:
        """Publish, consume, and negative acknowledge a message."""
        user_id = uuid4()
        topic = f"e2e-nack-test-{uuid4()}"
        subscription = f"{topic}/e2e-nack-subscription"

        # Publish a message directly using the producer
        test_payload = f"{user_id}:test-nack".encode()
        publish_result = await pulsar_producer.publish(
            topic=topic,
            payload=test_payload,
            properties={"test": "nack"},
        )
        # Verify publish succeeded
        from effectful.domain.message_envelope import PublishSuccess

        assert isinstance(publish_result, PublishSuccess)

        def consume_and_nack() -> Generator[AllEffects, EffectResult, str]:
            """Consume message and negative acknowledge it."""
            # Consume the message
            consume_result = yield ConsumeMessage(
                subscription=subscription,
                timeout_ms=5000,
            )

            # Type narrow and verify we got the message
            match consume_result:
                case MessageEnvelope(message_id=msg_id, payload=payload):
                    yield SendText(text=f"Received: {payload.decode()}")

                    # Negative acknowledge with delay (simulating processing failure)
                    nack_result = yield NegativeAcknowledge(
                        message_id=msg_id,
                        delay_ms=100,  # Small delay for test
                    )

                    # Verify nack succeeded
                    match nack_result:
                        case NackSuccess():
                            yield SendText(text="Message nacked for redelivery")
                            return "success"
                        case _:
                            yield SendText(text="Nack failed")
                            return "nack_failed"
                case ConsumeTimeout():
                    yield SendText(text="Timeout - no message")
                    return "timeout"
                case _:
                    yield SendText(text="Consume failed")
                    return "consume_failed"

        interpreter = create_composite_interpreter(
            websocket_connection=ws_client,
            user_repo=PostgresUserRepository(clean_db),
            message_repo=PostgresChatMessageRepository(clean_db),
            cache=RedisProfileCache(clean_redis),
            message_producer=pulsar_producer,
            message_consumer=pulsar_consumer,
        )

        result = await run_ws_program(consume_and_nack(), interpreter)

        status = unwrap_ok(result)
        assert status == "success"
        messages = ws_client.get_sent_messages()
        assert any("Received:" in msg and "test-nack" in msg for msg in messages)
        assert "Message nacked for redelivery" in messages


class TestStorage:
    """Test S3 storage operations."""

    @pytest.mark.asyncio
    async def test_store_and_retrieve_object(
        self,
        clean_db: asyncpg.Connection,
        clean_redis: Redis,
        clean_minio: str,
        ws_client: E2EWebSocketClient,
        object_storage: S3ObjectStorage,
    ) -> None:
        """Store an object in S3 and retrieve it."""
        user_id = uuid4()
        bucket = clean_minio

        def archive_message(uid: UUID, message: str) -> Generator[AllEffects, EffectResult, bool]:
            """Archive a message to S3."""
            timestamp = datetime.now(timezone.utc).isoformat()
            key = f"messages/{uid}/{timestamp}.txt"

            yield PutObject(
                bucket=bucket,
                key=key,
                content=message.encode(),
                metadata={"user_id": str(uid)},
                content_type="text/plain",
            )

            yield SendText(text=f"Archived to {key}")

            obj = yield GetObject(bucket=bucket, key=key)

            if obj is not None:
                yield SendText(text="Archive verified")
                return True

            return False

        interpreter = create_composite_interpreter(
            websocket_connection=ws_client,
            user_repo=PostgresUserRepository(clean_db),
            message_repo=PostgresChatMessageRepository(clean_db),
            cache=RedisProfileCache(clean_redis),
            object_storage=object_storage,
        )

        result = await run_ws_program(
            archive_message(user_id, "Important message to archive"),
            interpreter,
        )

        assert unwrap_ok(result) is True
        messages = ws_client.get_sent_messages()
        assert any("Archived to" in m for m in messages)
        assert any("verified" in m for m in messages)


class TestFullWorkflow:
    """Test full workflow using all 6 infrastructure types."""

    @pytest.mark.asyncio
    async def test_authenticated_message_send(
        self,
        clean_db: asyncpg.Connection,
        clean_redis: Redis,
        clean_minio: str,
        ws_client: E2EWebSocketClient,
        auth_service: RedisAuthService,
        object_storage: S3ObjectStorage,
        pulsar_producer: PulsarMessageProducer,
        pulsar_consumer: PulsarMessageConsumer,
    ) -> None:
        """Send an authenticated message using all 6 infrastructure types."""
        # Seed a user
        user_id = uuid4()
        await clean_db.execute(
            "INSERT INTO users (id, email, name) VALUES ($1, $2, $3)",
            user_id,
            "alice@example.com",
            "Alice",
        )

        # Generate a valid token
        token = await auth_service.generate_token(
            user_id=user_id,
            claims={"role": "user"},
            ttl_seconds=3600,
        )

        bucket = clean_minio

        def send_authenticated_message(
            tok: str, message_text: str
        ) -> Generator[AllEffects, EffectResult, str | None]:
            """Send authenticated message using all infrastructure types."""
            # 1. AUTH: Validate token
            auth_result = yield ValidateToken(token=tok)

            match auth_result:
                case TokenValid(user_id=auth_user_id):
                    pass
                case _:
                    yield SendText(text="Authentication failed")
                    return None

            # 2. CACHE: Try to get cached profile
            cached = yield GetCachedProfile(user_id=auth_user_id)
            user_name: str

            match cached:
                case ProfileData(name=name):
                    user_name = name
                case CacheMiss():
                    user_result = yield GetUserById(user_id=auth_user_id)
                    match user_result:
                        case User(name=name):
                            user_name = name
                            profile = ProfileData(id=str(auth_user_id), name=name)
                            yield PutCachedProfile(
                                user_id=auth_user_id,
                                profile_data=profile,
                                ttl_seconds=300,
                            )
                        case _:
                            yield SendText(text="User not found")
                            return None

            # 3. DATABASE: Save the message
            chat_message = yield SaveChatMessage(user_id=auth_user_id, text=message_text)
            assert isinstance(chat_message, ChatMessage)

            # 4. STORAGE: Archive the message
            timestamp = datetime.now(timezone.utc).isoformat()
            archive_key = f"archive/{auth_user_id}/{chat_message.id}.txt"
            yield PutObject(
                bucket=bucket,
                key=archive_key,
                content=message_text.encode(),
                metadata={"message_id": str(chat_message.id)},
                content_type="text/plain",
            )

            # 5. MESSAGING: Publish notification
            notification = f"New message from {user_name}: {message_text}"
            yield PublishMessage(
                topic="persistent://public/default/chat-events",
                payload=notification.encode(),
                properties={"user_id": str(auth_user_id), "type": "new_message"},
            )

            # 6. WEBSOCKET: Send confirmation
            yield SendText(text=f"Message sent by {user_name}: {message_text}")

            return str(chat_message.id)

        interpreter = create_composite_interpreter(
            websocket_connection=ws_client,
            user_repo=PostgresUserRepository(clean_db),
            message_repo=PostgresChatMessageRepository(clean_db),
            cache=RedisProfileCache(clean_redis),
            auth_service=auth_service,
            object_storage=object_storage,
            message_producer=pulsar_producer,
            message_consumer=pulsar_consumer,
        )

        result = await run_ws_program(
            send_authenticated_message(token, "Hello from full workflow test!"),
            interpreter,
        )

        message_id = unwrap_ok(result)
        assert message_id is not None

        # Verify message in database
        row = await clean_db.fetchrow(
            "SELECT * FROM chat_messages WHERE id = $1",
            UUID(message_id),
        )
        assert row is not None
        assert row["text"] == "Hello from full workflow test!"

        # Verify WebSocket message
        messages = ws_client.get_sent_messages()
        assert len(messages) >= 1
        assert "Message sent by Alice" in messages[-1]


class TestErrorHandling:
    """Test error propagation and handling."""

    @pytest.mark.asyncio
    async def test_invalid_token_error(
        self,
        clean_db: asyncpg.Connection,
        clean_redis: Redis,
        ws_client: E2EWebSocketClient,
        auth_service: RedisAuthService,
    ) -> None:
        """Invalid token should return appropriate error."""

        def auth_required_program(
            tok: str,
        ) -> Generator[AllEffects, EffectResult, bool]:
            """Program that requires valid authentication."""
            result = yield ValidateToken(token=tok)

            match result:
                case TokenValid():
                    yield SendText(text="Authorized")
                    return True
                case TokenInvalid():
                    yield SendText(text="Invalid token")
                    return False
                case TokenExpired():
                    yield SendText(text="Token expired")
                    return False

            return False

        interpreter = create_composite_interpreter(
            websocket_connection=ws_client,
            user_repo=PostgresUserRepository(clean_db),
            message_repo=PostgresChatMessageRepository(clean_db),
            cache=RedisProfileCache(clean_redis),
            auth_service=auth_service,
        )

        result = await run_ws_program(
            auth_required_program("invalid-token"),
            interpreter,
        )

        is_authorized = unwrap_ok(result)
        assert is_authorized is False
        assert "Invalid token" in ws_client.get_sent_messages()[0]

    @pytest.mark.asyncio
    async def test_user_not_found_error(
        self,
        clean_db: asyncpg.Connection,
        clean_redis: Redis,
        ws_client: E2EWebSocketClient,
    ) -> None:
        """User not found should be handled gracefully."""
        non_existent_id = uuid4()

        def lookup_user_program(
            uid: UUID,
        ) -> Generator[AllEffects, EffectResult, str]:
            """Lookup a user by ID."""
            result = yield GetUserById(user_id=uid)

            match result:
                case User(name=name):
                    yield SendText(text=f"Found: {name}")
                    return "found"
                case UserNotFound():
                    yield SendText(text="User not found")
                    return "not_found"

            return "error"

        interpreter = create_composite_interpreter(
            websocket_connection=ws_client,
            user_repo=PostgresUserRepository(clean_db),
            message_repo=PostgresChatMessageRepository(clean_db),
            cache=RedisProfileCache(clean_redis),
        )

        result = await run_ws_program(
            lookup_user_program(non_existent_id),
            interpreter,
        )

        status = unwrap_ok(result)
        assert status == "not_found"
        assert "User not found" in ws_client.get_sent_messages()[0]


class TestUserCRUD:
    """Test user CRUD operations."""

    @pytest.mark.asyncio
    async def test_update_user(
        self,
        clean_db: asyncpg.Connection,
        clean_redis: Redis,
        ws_client: E2EWebSocketClient,
    ) -> None:
        """Update user email and name."""
        # Seed a user
        user_id = uuid4()
        await clean_db.execute(
            "INSERT INTO users (id, email, name) VALUES ($1, $2, $3)",
            user_id,
            "bob@example.com",
            "Bob",
        )

        def update_user_program(
            uid: UUID, new_email: str, new_name: str
        ) -> Generator[AllEffects, EffectResult, bool]:
            """Update user details."""
            success = yield UpdateUser(user_id=uid, email=new_email, name=new_name)

            if success:
                yield SendText(text=f"Updated user {uid}")
                return True
            else:
                yield SendText(text="Update failed")
                return False

        interpreter = create_composite_interpreter(
            websocket_connection=ws_client,
            user_repo=PostgresUserRepository(clean_db),
            message_repo=PostgresChatMessageRepository(clean_db),
            cache=RedisProfileCache(clean_redis),
        )

        result = await run_ws_program(
            update_user_program(user_id, "bob.updated@example.com", "Bob Updated"),
            interpreter,
        )

        assert unwrap_ok(result) is True

        # Verify in database
        row = await clean_db.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
        assert row is not None
        assert row["email"] == "bob.updated@example.com"
        assert row["name"] == "Bob Updated"

    @pytest.mark.asyncio
    async def test_list_users_with_pagination(
        self,
        clean_db: asyncpg.Connection,
        clean_redis: Redis,
        ws_client: E2EWebSocketClient,
    ) -> None:
        """List users with pagination."""
        # Seed users - explicit sequential inserts following purity doctrine
        await clean_db.execute(
            "INSERT INTO users (id, email, name) VALUES ($1, $2, $3)",
            uuid4(),
            "user0@example.com",
            "User 0",
        )
        await clean_db.execute(
            "INSERT INTO users (id, email, name) VALUES ($1, $2, $3)",
            uuid4(),
            "user1@example.com",
            "User 1",
        )
        await clean_db.execute(
            "INSERT INTO users (id, email, name) VALUES ($1, $2, $3)",
            uuid4(),
            "user2@example.com",
            "User 2",
        )

        def list_users_program(limit: int, offset: int) -> Generator[AllEffects, EffectResult, int]:
            """List users with pagination."""
            users = yield ListUsers(limit=limit, offset=offset)
            assert isinstance(users, list)

            yield SendText(text=f"Found {len(users)} users")
            return len(users)

        interpreter = create_composite_interpreter(
            websocket_connection=ws_client,
            user_repo=PostgresUserRepository(clean_db),
            message_repo=PostgresChatMessageRepository(clean_db),
            cache=RedisProfileCache(clean_redis),
        )

        # List all 3 seeded users
        result = await run_ws_program(list_users_program(10, 0), interpreter)
        count = unwrap_ok(result)
        assert count == 3

        ws_client.clear_sent_messages()

        # List with pagination
        result = await run_ws_program(list_users_program(2, 0), interpreter)
        count = unwrap_ok(result)
        assert count == 2
