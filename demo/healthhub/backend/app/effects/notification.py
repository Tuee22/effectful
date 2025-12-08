"""Notification and audit effects.

All effects are immutable (frozen dataclasses) following Effectful patterns.
Effects are descriptions of operations, not execution.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

from effectful.domain.optional_value import OptionalValue


# Type for notification message values (supports nested dicts for warnings)
type NotificationValue = str | int | bool | dict[str, str]


@dataclass(frozen=True)
class PublishWebSocketNotification:
    """Effect: Publish ephemeral notification via Redis pub/sub.

    Used for real-time notifications to connected WebSocket clients.
    Messages are not persisted - only delivered to active connections.

    Args:
        channel: Redis pub/sub channel (e.g., "user:123:notifications").
        message: Notification payload.
        recipient_id: Optional recipient identifier (None = broadcast).

    Returns:
        NotificationPublished | PublishFailed
    """

    channel: str  # Redis pub/sub channel (e.g., "user:123:notifications")
    message: dict[str, NotificationValue]
    recipient_id: OptionalValue[UUID]  # User to notify (None = broadcast to channel)


@dataclass(frozen=True)
class LogAuditEvent:
    """Effect: Store audit event for HIPAA compliance.

    All sensitive operations (appointment access, prescription creation,
    lab result viewing) must be logged for regulatory compliance.

    Args:
        user_id: User performing the action.
        action: Action performed (e.g., "view_appointment").
        resource_type: Resource type affected.
        resource_id: Identifier of the resource.
        ip_address: Client IP address if available.
        user_agent: Client user agent if available.
        metadata: Additional context payload.

    Returns:
        AuditEventLogged
    """

    user_id: UUID  # User performing the action
    action: str  # Action performed (e.g., "view_appointment", "create_prescription")
    resource_type: str  # Type of resource (e.g., "appointment", "prescription")
    resource_id: UUID  # ID of the resource
    ip_address: OptionalValue[str]  # Client IP address
    user_agent: OptionalValue[str]  # Client user agent
    metadata: OptionalValue[dict[str, str]]  # Additional context


# Notification results ADT
@dataclass(frozen=True)
class NotificationPublished:
    """Notification successfully published to channel.

    Args:
        channel: Channel name where message was sent.
        message_id: Redis message identifier.
        recipients_count: Number of recipients that received the message.
    """

    channel: str
    message_id: str  # Redis message ID
    recipients_count: int  # Number of active connections that received it


@dataclass(frozen=True)
class PublishFailed:
    """Failed to publish notification.

    Args:
        channel: Channel attempted.
        reason: Human-readable failure reason.
    """

    channel: str
    reason: str


type PublishResult = NotificationPublished | PublishFailed


# Audit results ADT
@dataclass(frozen=True)
class AuditEventLogged:
    """Audit event successfully stored.

    Args:
        event_id: Stored event identifier.
        logged_at: Timestamp when the event was written.
    """

    event_id: UUID
    logged_at: datetime


type NotificationEffect = PublishWebSocketNotification | LogAuditEvent
