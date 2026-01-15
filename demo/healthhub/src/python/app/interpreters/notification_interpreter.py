"""Notification effect interpreter.

Boundary: OUTSIDE_PROOF
Target-Language: N/A (assumed correct)

Handles notification publishing and audit logging.

Assumptions:
- [Library] redis.asyncio correctly implements Redis protocol
- [Service] Redis pub/sub delivers messages at-most-once to subscribers
- [Database] Audit log inserts succeed atomically with PHI operations
- [Network] Redis connection pool handles transient failures
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import UUID, uuid4

import asyncpg
import redis.asyncio as redis

from app.protocols.database import DatabasePool
from app.protocols.redis import RedisClient
from app.protocols.observability import ObservabilityInterpreter as ObservabilityProtocol
from effectful.domain.optional_value import from_optional_value
from app.effects.notification import (
    AuditEventLogged,
    LogAuditEvent,
    NotificationEffect,
    NotificationPublished,
    NotificationValue,
    PublishFailed,
    PublishResult,
    PublishWebSocketNotification,
)
from app.effects.observability import IncrementCounter


class NotificationInterpreter:
    """Interpreter for notification effects.

    Handles ephemeral real-time notifications via Redis pub/sub
    and durable audit logging via PostgreSQL.
    """

    def __init__(
        self,
        pool: DatabasePool,
        redis_client: RedisClient,
        observability: ObservabilityProtocol | None = None,
    ) -> None:
        """Initialize interpreter with database pool and Redis client.

        Args:
            pool: Database pool protocol (production or test mock)
            redis_client: Redis client protocol (production or test mock)
            observability: Observability interpreter protocol (production or test mock)
        """
        self.pool = pool
        self.redis_client = redis_client
        self._observability = observability

    async def handle(self, effect: NotificationEffect) -> PublishResult | AuditEventLogged:
        """Handle a notification effect.

        Args:
            effect: Notification effect to execute

        Returns:
            Result of executing the effect
        """
        match effect:
            case PublishWebSocketNotification(
                channel=channel, message=message, recipient_id=recipient_id
            ):
                recipient = from_optional_value(recipient_id)
                return await self._publish_websocket_notification(channel, message, recipient)

            case LogAuditEvent(
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata=metadata,
            ):
                return await self._log_audit_event(
                    user_id,
                    action,
                    resource_type,
                    resource_id,
                    from_optional_value(ip_address),
                    from_optional_value(user_agent),
                    from_optional_value(metadata),
                )

    async def _publish_websocket_notification(
        self,
        channel: str,
        message: dict[str, NotificationValue],
        recipient_id: UUID | None,
    ) -> PublishResult:
        """Publish notification to Redis pub/sub channel.

        Args:
            channel: Redis pub/sub channel
            message: Message payload
            recipient_id: Target user (None = broadcast)

        Returns:
            PublishResult indicating success or failure
        """
        try:
            # Convert message to JSON string
            import json

            message_json = json.dumps(message)

            # Publish to Redis channel
            recipients_count = await self.redis_client.publish(channel, message_json)

            # Generate message ID for tracking
            message_id = str(uuid4())

            return NotificationPublished(
                channel=channel,
                message_id=message_id,
                recipients_count=recipients_count,
            )

        except Exception as e:
            return PublishFailed(channel=channel, reason=str(e))

    async def _log_audit_event(
        self,
        user_id: UUID,
        action: str,
        resource_type: str,
        resource_id: UUID,
        ip_address: str | None,
        user_agent: str | None,
        metadata: dict[str, str] | None,
    ) -> AuditEventLogged:
        """Log audit event to PostgreSQL.

        Args:
            user_id: User performing the action
            action: Action performed
            resource_type: Type of resource
            resource_id: ID of the resource
            ip_address: Client IP address
            user_agent: Client user agent
            metadata: Additional context

        Returns:
            AuditEventLogged with event ID and timestamp
        """
        now = datetime.now(timezone.utc)
        event_id = uuid4()

        # Convert metadata dict to JSON string for JSONB column
        # Use json.dumps because asyncpg needs string for JSONB with execute()
        metadata_json = json.dumps(metadata) if metadata else None

        await self.pool.execute(
            """
            INSERT INTO audit_log (
                id, user_id, action, resource_type, resource_id,
                ip_address, user_agent, metadata, created_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb, $9)
            """,
            event_id,
            user_id,
            action,
            resource_type,
            resource_id,
            ip_address,
            user_agent,
            metadata_json,
            now,
        )

        if self._observability is not None:
            await self._observability.handle(
                IncrementCounter(
                    metric_name="healthhub_audit_events_total",
                    labels={"action": action},
                )
            )

        return AuditEventLogged(event_id=event_id, logged_at=now)
