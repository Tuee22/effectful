"""Integration tests for notification infrastructure.

Tests Redis pub/sub (ephemeral) and audit logging (durable) with real infrastructure.

Antipatterns avoided:
- #13: Incomplete assertions - verify Redis messages and DB audit logs
- #20: Holding database locks - TRUNCATE committed before tests
"""

from __future__ import annotations

import json
from collections.abc import Generator
from datetime import datetime, timezone
from uuid import UUID, uuid4

import asyncpg
import pytest
import redis.asyncio as redis

from app.effects.notification import (
    LogAuditEvent,
    NotificationValue,
    PublishWebSocketNotification,
)
from app.interpreters.composite_interpreter import AllEffects, CompositeInterpreter
from app.programs.runner import run_program


def parse_jsonb_metadata(metadata_val: object) -> dict[str, str]:
    """Parse JSONB metadata that may be returned as dict or string.

    asyncpg may return JSONB as string depending on codec registration.
    This helper ensures consistent dict access.
    """
    if metadata_val is None:
        return {}
    if isinstance(metadata_val, dict):
        result: dict[str, str] = {}
        for k, v in metadata_val.items():
            result[str(k)] = str(v)
        return result
    if isinstance(metadata_val, str):
        loaded = json.loads(metadata_val)
        if isinstance(loaded, dict):
            result = {}
            for k, v in loaded.items():
                result[str(k)] = str(v)
            return result
    return {}


class TestRedisPublishSubscribe:
    """Test Redis pub/sub for ephemeral WebSocket notifications."""

    @pytest.mark.asyncio
    async def test_publish_notification_sends_redis_message(
        self,
        db_pool: asyncpg.Pool[asyncpg.Record],
        redis_client: redis.Redis[bytes],
        sample_user_id: UUID,
    ) -> None:
        """Test PublishWebSocketNotification sends Redis pub/sub message.

        Validates:
        - Message published to correct channel
        - Payload structure correct
        - Ephemeral (fire-and-forget) - no persistence
        - Side effect validated (antipattern #13)
        """
        # Create composite interpreter
        interpreter = CompositeInterpreter(pool=db_pool, redis_client=redis_client)

        # Subscribe to channel
        pubsub = redis_client.pubsub()
        channel = f"user:{sample_user_id}:notifications"
        await pubsub.subscribe(channel)

        # Define test program
        def notification_program() -> Generator[AllEffects, object, None]:
            message: dict[str, NotificationValue] = {
                "type": "test_notification",
                "key": "value",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            yield PublishWebSocketNotification(
                channel=channel,
                message=message,
                recipient_id=sample_user_id,
            )

        # Execute program
        await run_program(notification_program(), interpreter)

        # CRITICAL: Verify message received (antipattern #13)
        message = await pubsub.get_message(timeout=2.0)

        # First message is subscription confirmation
        if message and message["type"] == "subscribe":
            message = await pubsub.get_message(timeout=2.0)

        assert message is not None, "No Redis pub/sub message received"
        assert message["type"] == "message"

        channel_bytes = message["channel"]
        if isinstance(channel_bytes, bytes):
            assert channel_bytes.decode() == channel

        # Parse payload
        data = message["data"]
        if isinstance(data, (str, bytes)):
            payload = json.loads(data)
            assert payload["type"] == "test_notification"
            assert payload["key"] == "value"
            assert "timestamp" in payload

        await pubsub.unsubscribe(channel)
        await pubsub.aclose()

    @pytest.mark.asyncio
    async def test_publish_to_multiple_channels(
        self,
        db_pool: asyncpg.Pool[asyncpg.Record],
        redis_client: redis.Redis[bytes],
    ) -> None:
        """Test publishing to multiple channels simultaneously.

        Validates:
        - Multiple Redis channels can receive messages
        - Each channel receives correct message
        - No cross-channel pollution
        """
        # Create composite interpreter
        interpreter = CompositeInterpreter(pool=db_pool, redis_client=redis_client)

        # Subscribe to multiple channels
        user1_id = uuid4()
        user2_id = uuid4()
        channel1 = f"user:{user1_id}:notifications"
        channel2 = f"user:{user2_id}:notifications"

        pubsub1 = redis_client.pubsub()
        pubsub2 = redis_client.pubsub()

        await pubsub1.subscribe(channel1)
        await pubsub2.subscribe(channel2)

        # Define test program publishing to both channels
        def multi_channel_program() -> Generator[AllEffects, object, None]:
            message1: dict[str, NotificationValue] = {
                "type": "message_for_user1",
                "content": "Hello User 1",
            }
            yield PublishWebSocketNotification(
                channel=channel1,
                message=message1,
                recipient_id=user1_id,
            )

            message2: dict[str, NotificationValue] = {
                "type": "message_for_user2",
                "content": "Hello User 2",
            }
            yield PublishWebSocketNotification(
                channel=channel2,
                message=message2,
                recipient_id=user2_id,
            )

        # Execute program
        await run_program(multi_channel_program(), interpreter)

        # Verify channel 1 received correct message
        msg1 = await pubsub1.get_message(timeout=2.0)
        if msg1 and msg1["type"] == "subscribe":
            msg1 = await pubsub1.get_message(timeout=2.0)

        assert msg1 is not None
        data1 = msg1["data"]
        if isinstance(data1, (str, bytes)):
            payload1 = json.loads(data1)
            assert payload1["type"] == "message_for_user1"
            assert payload1["content"] == "Hello User 1"

        # Verify channel 2 received correct message
        msg2 = await pubsub2.get_message(timeout=2.0)
        if msg2 and msg2["type"] == "subscribe":
            msg2 = await pubsub2.get_message(timeout=2.0)

        assert msg2 is not None
        data2 = msg2["data"]
        if isinstance(data2, (str, bytes)):
            payload2 = json.loads(data2)
            assert payload2["type"] == "message_for_user2"
            assert payload2["content"] == "Hello User 2"

        await pubsub1.unsubscribe(channel1)
        await pubsub2.unsubscribe(channel2)
        await pubsub1.aclose()
        await pubsub2.aclose()

    @pytest.mark.asyncio
    async def test_ephemeral_message_lost_without_subscriber(
        self,
        db_pool: asyncpg.Pool[asyncpg.Record],
        redis_client: redis.Redis[bytes],
    ) -> None:
        """Test Redis pub/sub message is lost if no subscriber listening.

        Validates:
        - Ephemeral messaging behavior (not durable like Pulsar)
        - Message not persisted if no listener
        - This is ACCEPTABLE for real-time notifications
        """
        # Create composite interpreter
        interpreter = CompositeInterpreter(pool=db_pool, redis_client=redis_client)

        user_id = uuid4()
        channel = f"user:{user_id}:notifications"

        # Publish WITHOUT subscribing first
        def publish_program() -> Generator[AllEffects, object, None]:
            message: dict[str, NotificationValue] = {
                "type": "lost_message",
                "content": "This will be lost",
            }
            yield PublishWebSocketNotification(
                channel=channel,
                message=message,
                recipient_id=user_id,
            )

        await run_program(publish_program(), interpreter)

        # NOW subscribe (after publishing)
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(channel)

        # Try to receive message (should be None - message lost)
        message = await pubsub.get_message(timeout=1.0)

        # Only subscription confirmation received
        if message:
            assert message["type"] == "subscribe"
            # No actual message should follow
            message = await pubsub.get_message(timeout=1.0)
            assert message is None, "Message should be lost (ephemeral behavior)"

        await pubsub.unsubscribe(channel)
        await pubsub.aclose()


class TestAuditLogging:
    """Test audit logging for HIPAA compliance."""

    @pytest.mark.asyncio
    async def test_audit_log_creates_db_record(
        self,
        db_pool: asyncpg.Pool[asyncpg.Record],
        redis_client: redis.Redis[bytes],
        sample_user_id: UUID,
    ) -> None:
        """Test LogAuditEvent creates database record.

        Validates:
        - Audit log entry persisted to PostgreSQL
        - All fields populated correctly
        - Durable storage (HIPAA requirement)
        - Side effect validated (antipattern #13)
        """
        # Setup
        interpreter = CompositeInterpreter(pool=db_pool, redis_client=redis_client)

        # Define audit logging program
        resource_id = uuid4()

        def audit_program() -> Generator[AllEffects, object, None]:
            metadata: dict[str, str] = {
                "test_key": "test_value",
                "severity": "info",
            }
            yield LogAuditEvent(
                user_id=sample_user_id,
                action="test_action",
                resource_type="test_resource",
                resource_id=resource_id,
                ip_address="192.168.1.100",
                user_agent="Mozilla/5.0",
                metadata=metadata,
            )

        # Execute program
        await run_program(audit_program(), interpreter)

        # CRITICAL: Verify audit log persisted (antipattern #13)
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM audit_log
                WHERE user_id = $1 AND resource_id = $2
                """,
                sample_user_id,
                resource_id,
            )

            assert row is not None, "Audit log not persisted to database"
            assert row["action"] == "test_action"
            assert row["resource_type"] == "test_resource"
            assert row["resource_id"] == resource_id
            assert row["ip_address"] == "192.168.1.100"
            assert row["user_agent"] == "Mozilla/5.0"

            # Verify metadata JSONB field
            metadata = parse_jsonb_metadata(row["metadata"])
            assert metadata["test_key"] == "test_value"
            assert metadata["severity"] == "info"

    @pytest.mark.asyncio
    async def test_audit_log_supports_null_optional_fields(
        self,
        db_pool: asyncpg.Pool[asyncpg.Record],
        redis_client: redis.Redis[bytes],
        sample_user_id: UUID,
    ) -> None:
        """Test audit log allows NULL for optional fields.

        Validates:
        - Optional fields (ip_address, user_agent) can be NULL
        - DB record created successfully
        - No relaxed validation (antipattern #14)
        """
        # Setup
        interpreter = CompositeInterpreter(pool=db_pool, redis_client=redis_client)

        # Define audit logging program with NULL optional fields
        resource_id = uuid4()

        def audit_program() -> Generator[AllEffects, object, None]:
            metadata: dict[str, str] = {"context": "background_job"}
            yield LogAuditEvent(
                user_id=sample_user_id,
                action="test_action_null_fields",
                resource_type="test_resource",
                resource_id=resource_id,
                ip_address=None,  # NULL
                user_agent=None,  # NULL
                metadata=metadata,
            )

        # Execute program
        await run_program(audit_program(), interpreter)

        # Verify audit log created with NULL fields
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM audit_log
                WHERE resource_id = $1
                """,
                resource_id,
            )

            assert row is not None
            assert row["ip_address"] is None
            assert row["user_agent"] is None
            metadata = parse_jsonb_metadata(row["metadata"])
            assert metadata["context"] == "background_job"

    @pytest.mark.asyncio
    async def test_audit_log_multiple_entries_same_resource(
        self,
        db_pool: asyncpg.Pool[asyncpg.Record],
        redis_client: redis.Redis[bytes],
        sample_user_id: UUID,
    ) -> None:
        """Test multiple audit log entries for same resource.

        Validates:
        - Multiple audit entries can reference same resource
        - Each entry has unique timestamp
        - Audit trail maintained chronologically
        - HIPAA compliance (complete history)
        """
        # Setup
        interpreter = CompositeInterpreter(pool=db_pool, redis_client=redis_client)

        # Define program with multiple audit events for same resource
        resource_id = uuid4()

        def multi_audit_program() -> Generator[AllEffects, object, None]:
            metadata1: dict[str, str] = {"step": "1"}
            yield LogAuditEvent(
                user_id=sample_user_id,
                action="create_resource",
                resource_type="prescription",
                resource_id=resource_id,
                ip_address=None,
                user_agent=None,
                metadata=metadata1,
            )

            metadata2: dict[str, str] = {"step": "2"}
            yield LogAuditEvent(
                user_id=sample_user_id,
                action="update_resource",
                resource_type="prescription",
                resource_id=resource_id,
                ip_address=None,
                user_agent=None,
                metadata=metadata2,
            )

            metadata3: dict[str, str] = {"step": "3"}
            yield LogAuditEvent(
                user_id=sample_user_id,
                action="delete_resource",
                resource_type="prescription",
                resource_id=resource_id,
                ip_address=None,
                user_agent=None,
                metadata=metadata3,
            )

        # Execute program
        await run_program(multi_audit_program(), interpreter)

        # Verify all audit entries created
        async with db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM audit_log
                WHERE resource_id = $1
                ORDER BY created_at ASC
                """,
                resource_id,
            )

            assert len(rows) == 3, "Not all audit entries created"

            # Verify sequence
            assert rows[0]["action"] == "create_resource"
            metadata_0 = parse_jsonb_metadata(rows[0]["metadata"])
            assert metadata_0["step"] == "1"

            assert rows[1]["action"] == "update_resource"
            metadata_1 = parse_jsonb_metadata(rows[1]["metadata"])
            assert metadata_1["step"] == "2"

            assert rows[2]["action"] == "delete_resource"
            metadata_2 = parse_jsonb_metadata(rows[2]["metadata"])
            assert metadata_2["step"] == "3"

            # Verify timestamps are chronological
            created_at_0 = rows[0]["created_at"]
            created_at_1 = rows[1]["created_at"]
            created_at_2 = rows[2]["created_at"]
            assert isinstance(created_at_0, datetime)
            assert isinstance(created_at_1, datetime)
            assert isinstance(created_at_2, datetime)
            assert created_at_0 <= created_at_1
            assert created_at_1 <= created_at_2


class TestNotificationIntegration:
    """Test notification system integration (Redis + audit log)."""

    @pytest.mark.asyncio
    async def test_notification_with_audit_log(
        self,
        db_pool: asyncpg.Pool[asyncpg.Record],
        redis_client: redis.Redis[bytes],
        sample_user_id: UUID,
    ) -> None:
        """Test combined ephemeral notification and durable audit log.

        Validates:
        - Redis pub/sub notification sent (ephemeral)
        - Audit log entry created (durable)
        - Both side effects validated (antipattern #13)
        - Separation of concerns (ephemeral vs durable)
        """
        # Setup
        interpreter = CompositeInterpreter(pool=db_pool, redis_client=redis_client)

        # Subscribe to Redis channel
        pubsub = redis_client.pubsub()
        channel = f"user:{sample_user_id}:notifications"
        await pubsub.subscribe(channel)

        # Define combined program
        resource_id = uuid4()

        def combined_program() -> Generator[AllEffects, object, None]:
            # Ephemeral notification (Redis pub/sub)
            notification_message: dict[str, NotificationValue] = {
                "type": "resource_updated",
                "resource_id": str(resource_id),
            }
            yield PublishWebSocketNotification(
                channel=channel,
                message=notification_message,
                recipient_id=sample_user_id,
            )

            # Durable audit log (PostgreSQL)
            audit_metadata: dict[str, str] = {"channel": channel}
            yield LogAuditEvent(
                user_id=sample_user_id,
                action="resource_update_notification",
                resource_type="notification",
                resource_id=resource_id,
                ip_address=None,
                user_agent=None,
                metadata=audit_metadata,
            )

        # Execute program
        await run_program(combined_program(), interpreter)

        # CRITICAL: Verify Redis notification (antipattern #13)
        message = await pubsub.get_message(timeout=2.0)
        if message and message["type"] == "subscribe":
            message = await pubsub.get_message(timeout=2.0)

        assert message is not None, "Redis notification not received"
        data = message["data"]
        if isinstance(data, (str, bytes)):
            payload = json.loads(data)
            assert payload["type"] == "resource_updated"
            assert payload["resource_id"] == str(resource_id)

        # CRITICAL: Verify audit log (antipattern #13)
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM audit_log
                WHERE resource_id = $1
                """,
                resource_id,
            )

            assert row is not None, "Audit log not created"
            assert row["action"] == "resource_update_notification"
            metadata = parse_jsonb_metadata(row["metadata"])
            assert metadata["channel"] == channel

        await pubsub.unsubscribe(channel)
        await pubsub.aclose()
