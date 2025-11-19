"""Message envelope domain model for Pulsar messages.

This module defines domain models for Pulsar message envelopes and publish results.
All models use algebraic data types (ADTs) to make all possible states explicit.

Domain Models:
    - MessageEnvelope: Complete message with metadata
    - PublishSuccess: Message published successfully
    - PublishFailure: Message publish failed
    - PublishResult: ADT for publish outcomes

Type Safety:
    All models are frozen dataclasses with strict type hints. Use pattern matching
    for exhaustive case handling.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal


@dataclass(frozen=True)
class MessageEnvelope:
    """Pulsar message envelope with metadata.

    This is the complete message object returned when consuming from a Pulsar
    subscription. Contains both the payload and all message metadata.

    Attributes:
        message_id: Pulsar message ID (unique identifier)
        payload: Message payload as bytes
        properties: Message properties (metadata key-value pairs)
        publish_time: Timestamp when message was published
        topic: Topic name where message was published

    Example:
        >>> envelope = MessageEnvelope(
        ...     message_id="msg-123",
        ...     payload=b'{"event": "user_login"}',
        ...     properties={"source": "web_app"},
        ...     publish_time=datetime.now(UTC),
        ...     topic="user-events",
        ... )
        >>> data = envelope.payload.decode()
    """

    message_id: str
    payload: bytes
    properties: dict[str, str]
    publish_time: datetime
    topic: str


@dataclass(frozen=True)
class PublishSuccess:
    """Message published successfully.

    This ADT variant represents successful message publication.

    Attributes:
        message_id: Pulsar message ID assigned by broker
        topic: Topic where message was published

    Example:
        >>> result = PublishSuccess(message_id="msg-456", topic="user-events")
        >>> match result:
        ...     case PublishSuccess(message_id=msg_id, topic=topic):
        ...         print(f"Published to {topic}: {msg_id}")
    """

    message_id: str
    topic: str


@dataclass(frozen=True)
class PublishFailure:
    """Message publish failed.

    This ADT variant represents failed message publication with a specific reason.

    Attributes:
        topic: Topic where publish was attempted
        reason: Specific failure reason (timeout, quota, or topic not found)

    Example:
        >>> result = PublishFailure(topic="user-events", reason="timeout")
        >>> match result:
        ...     case PublishFailure(topic=topic, reason="timeout"):
        ...         print(f"Timeout publishing to {topic} - retry")
        ...     case PublishFailure(topic=topic, reason="quota_exceeded"):
        ...         print(f"Quota exceeded on {topic} - backoff")
        ...     case PublishFailure(topic=topic, reason="topic_not_found"):
        ...         print(f"Topic {topic} does not exist")
    """

    topic: str
    reason: Literal["timeout", "quota_exceeded", "topic_not_found"]


# Type alias: ADT for publish results (PEP 695)
type PublishResult = PublishSuccess | PublishFailure
