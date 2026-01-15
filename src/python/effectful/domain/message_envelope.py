"""Message envelope domain model for Pulsar messages.

This module defines domain models for Pulsar message envelopes and messaging results.
All models use algebraic data types (ADTs) to make all possible states explicit.

Domain Models:
    - MessageEnvelope: Complete message with metadata
    - PublishSuccess/PublishFailure: Publish operation results
    - ConsumeTimeout/ConsumeFailure: Consume operation results
    - AcknowledgeSuccess/AcknowledgeFailure: Ack operation results
    - NackSuccess/NackFailure: Negative-ack operation results

Type Aliases:
    - PublishResult: ADT for publish outcomes
    - ConsumeResult: ADT for consume outcomes
    - AcknowledgeResult: ADT for ack outcomes
    - NackResult: ADT for nack outcomes

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
    All possible Pulsar failure modes are explicitly modeled to force exhaustive
    handling in business logic.

    Attributes:
        topic: Topic where publish was attempted
        reason: Specific failure reason categorized by type:
            - Connection failures: broker_unreachable, bookkeeper_not_ready,
              auth_failed, connection_closed
            - Operational failures: timeout, quota_exceeded, topic_not_found,
              message_too_large, producer_blocked

    Example:
        >>> result = PublishFailure(topic="user-events", reason="timeout")
        >>> match result:
        ...     case PublishFailure(topic=topic, reason="timeout"):
        ...         print(f"Timeout publishing to {topic} - retry")
        ...     case PublishFailure(topic=topic, reason="quota_exceeded"):
        ...         print(f"Quota exceeded on {topic} - backoff")
        ...     case PublishFailure(topic=topic, reason="bookkeeper_not_ready"):
        ...         print(f"Pulsar storage not ready - wait and retry")
        ...     case PublishFailure(topic=topic, reason="broker_unreachable"):
        ...         print(f"Cannot reach Pulsar broker")
        ...     case PublishFailure(topic=topic, reason=r):
        ...         print(f"Publish failed: {r}")
    """

    topic: str
    reason: Literal[
        # Connection failures
        "broker_unreachable",
        "bookkeeper_not_ready",
        "auth_failed",
        "connection_closed",
        # Operational failures
        "timeout",
        "quota_exceeded",
        "topic_not_found",
        "message_too_large",
        "producer_blocked",
    ]


# Type alias: ADT for publish results (PEP 695)
type PublishResult = PublishSuccess | PublishFailure


@dataclass(frozen=True)
class ConsumeTimeout:
    """No message received within timeout period.

    This ADT variant replaces None for consume operations, making timeout
    handling explicit in the type system.

    Attributes:
        subscription: The subscription that was polled
        timeout_ms: How long we waited before timeout

    Example:
        >>> result = ConsumeTimeout(subscription="my-sub", timeout_ms=1000)
        >>> match result:
        ...     case ConsumeTimeout(subscription=sub, timeout_ms=ms):
        ...         print(f"No message on {sub} after {ms}ms")
    """

    subscription: str
    timeout_ms: int


@dataclass(frozen=True)
class ConsumeFailure:
    """Message consume operation failed.

    This ADT variant represents failed consume operations with a specific reason.
    All possible Pulsar consumer failure modes are explicitly modeled.

    Attributes:
        subscription: The subscription that was being consumed
        reason: Specific failure reason:
            - Connection failures: broker_unreachable, auth_failed, connection_closed
            - Operational failures: subscription_not_found, consumer_closed

    Example:
        >>> result = ConsumeFailure(subscription="my-sub", reason="broker_unreachable")
        >>> match result:
        ...     case ConsumeFailure(subscription=sub, reason="broker_unreachable"):
        ...         print(f"Cannot reach broker for {sub}")
        ...     case ConsumeFailure(subscription=sub, reason="subscription_not_found"):
        ...         print(f"Subscription {sub} does not exist")
    """

    subscription: str
    reason: Literal[
        # Connection failures
        "broker_unreachable",
        "auth_failed",
        "connection_closed",
        # Operational failures
        "subscription_not_found",
        "consumer_closed",
    ]


# ADT: Union of consume results (no Optional!)
type ConsumeResult = MessageEnvelope | ConsumeTimeout | ConsumeFailure


@dataclass(frozen=True)
class AcknowledgeSuccess:
    """Message acknowledged successfully.

    This ADT variant represents successful message acknowledgment.

    Attributes:
        message_id: The message ID that was acknowledged

    Example:
        >>> result = AcknowledgeSuccess(message_id="msg-123")
        >>> match result:
        ...     case AcknowledgeSuccess(message_id=mid):
        ...         print(f"Acknowledged: {mid}")
    """

    message_id: str


@dataclass(frozen=True)
class AcknowledgeFailure:
    """Message acknowledgment failed.

    This ADT variant represents failed acknowledgment with a specific reason.

    Attributes:
        message_id: The message ID that failed to acknowledge
        reason: Specific failure reason:
            - message_not_found: Message ID not in consumer cache
            - consumer_not_found: No consumer found for this message
            - already_acknowledged: Message was already acknowledged
            - connection_closed: Consumer connection lost

    Example:
        >>> result = AcknowledgeFailure(message_id="msg-123", reason="message_not_found")
        >>> match result:
        ...     case AcknowledgeFailure(message_id=mid, reason="message_not_found"):
        ...         print(f"Message {mid} not found in cache")
    """

    message_id: str
    reason: Literal[
        "message_not_found",
        "consumer_not_found",
        "already_acknowledged",
        "connection_closed",
    ]


# ADT: Union of acknowledge results
type AcknowledgeResult = AcknowledgeSuccess | AcknowledgeFailure


@dataclass(frozen=True)
class NackSuccess:
    """Message negative-acknowledged successfully.

    This ADT variant represents successful negative acknowledgment (nack),
    which schedules the message for redelivery.

    Attributes:
        message_id: The message ID that was nacked

    Example:
        >>> result = NackSuccess(message_id="msg-123")
        >>> match result:
        ...     case NackSuccess(message_id=mid):
        ...         print(f"Nacked for redelivery: {mid}")
    """

    message_id: str


@dataclass(frozen=True)
class NackFailure:
    """Message negative-acknowledgment failed.

    This ADT variant represents failed negative acknowledgment with a specific reason.

    Attributes:
        message_id: The message ID that failed to nack
        reason: Specific failure reason:
            - message_not_found: Message ID not in consumer cache
            - consumer_not_found: No consumer found for this message
            - connection_closed: Consumer connection lost

    Example:
        >>> result = NackFailure(message_id="msg-123", reason="message_not_found")
        >>> match result:
        ...     case NackFailure(message_id=mid, reason="message_not_found"):
        ...         print(f"Message {mid} not found for nack")
    """

    message_id: str
    reason: Literal[
        "message_not_found",
        "consumer_not_found",
        "connection_closed",
    ]


# ADT: Union of negative-acknowledge results
type NackResult = NackSuccess | NackFailure
