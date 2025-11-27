"""Notification and audit effects.

All effects are immutable (frozen dataclasses) following Effectful patterns.
Effects are descriptions of operations, not execution.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID


# Type for notification message values (supports nested dicts for warnings)
type NotificationValue = str | int | bool | dict[str, str]


@dataclass(frozen=True)
class PublishWebSocketNotification:
    """Effect: Publish ephemeral notification via Redis pub/sub.

    Used for real-time notifications to connected WebSocket clients.
    Messages are not persisted - only delivered to active connections.

    Returns: NotificationPublished | PublishFailed
    """

    channel: str  # Redis pub/sub channel (e.g., "user:123:notifications")
    message: dict[str, NotificationValue]
    recipient_id: UUID | None  # User to notify (None = broadcast to channel)


@dataclass(frozen=True)
class LogAuditEvent:
    """Effect: Store audit event for HIPAA compliance.

    All sensitive operations (appointment access, prescription creation,
    lab result viewing) must be logged for regulatory compliance.

    Returns: AuditEventLogged
    """

    user_id: UUID  # User performing the action
    action: str  # Action performed (e.g., "view_appointment", "create_prescription")
    resource_type: str  # Type of resource (e.g., "appointment", "prescription")
    resource_id: UUID  # ID of the resource
    ip_address: str | None  # Client IP address
    user_agent: str | None  # Client user agent
    metadata: dict[str, str] | None  # Additional context


# Notification results ADT
@dataclass(frozen=True)
class NotificationPublished:
    """Notification successfully published to channel."""

    channel: str
    message_id: str  # Redis message ID
    recipients_count: int  # Number of active connections that received it


@dataclass(frozen=True)
class PublishFailed:
    """Failed to publish notification."""

    channel: str
    reason: str


type PublishResult = NotificationPublished | PublishFailed


# Audit results ADT
@dataclass(frozen=True)
class AuditEventLogged:
    """Audit event successfully stored."""

    event_id: UUID
    logged_at: datetime


type NotificationEffect = PublishWebSocketNotification | LogAuditEvent
