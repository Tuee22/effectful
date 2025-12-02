"""Messaging effect DSL for Apache Pulsar.

This module defines effects for message queue operations with Pulsar:
- PublishMessage: Send message to topic
- ConsumeMessage: Receive message from subscription
- AcknowledgeMessage: Acknowledge message processing
- NegativeAcknowledge: Negative acknowledge for redelivery

All effects are immutable (frozen dataclasses) and describe *what* should happen,
not *how* to do it. The interpreter handles the actual Pulsar interaction.

Example:
    >>> from effectful import PublishMessage, ConsumeMessage
    >>> from collections.abc import Generator
    >>> from effectful import AllEffects, EffectResult
    >>>
    >>> def publish_event(event_data: bytes) -> Generator[AllEffects, EffectResult, str]:
    ...     message_id = yield PublishMessage(
    ...         topic="user-events",
    ...         payload=event_data,
    ...         properties={"event_type": "login"},
    ...     )
    ...     assert isinstance(message_id, str)
    ...     return message_id

Type Safety:
    All effects are frozen dataclasses with strict type hints. No `Any`, `cast`, or
    `type: ignore` allowed. Pattern match on effect types for exhaustive handling.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class PublishMessage:
    """Effect: Publish message to Pulsar topic.

    This effect describes publishing a message to a Pulsar topic. The interpreter
    handles the actual publish operation and returns the message ID on success.

    Attributes:
        topic: Topic name to publish to (e.g., "persistent://tenant/namespace/topic")
        payload: Message payload as bytes
        properties: Optional message properties (metadata key-value pairs)

    Returns:
        When yielded in a program, returns message ID (str) on success.

    Example:
        >>> def publish_user_event(user_id: str) -> Generator[AllEffects, EffectResult, str]:
        ...     message_id = yield PublishMessage(
        ...         topic="user-events",
        ...         payload=f'{{"user_id": "{user_id}"}}'.encode(),
        ...         properties={"source": "web_app"},
        ...     )
        ...     assert isinstance(message_id, str)
        ...     return message_id
    """

    topic: str
    payload: bytes
    properties: dict[str, str] | None = None


@dataclass(frozen=True)
class ConsumeMessage:
    """Effect: Consume message from Pulsar subscription.

    This effect describes receiving a message from a Pulsar subscription. The
    interpreter handles the actual receive operation with timeout semantics.

    Attributes:
        subscription: Subscription name to consume from
        timeout_ms: Timeout for receive operation in milliseconds (default: 5000)

    Returns:
        When yielded in a program, returns MessageEnvelope on success, ConsumeTimeout on timeout.

    Example:
        >>> def process_events() -> Generator[AllEffects, EffectResult, int]:
        ...     processed = 0
        ...     while True:
        ...         consume_result = yield ConsumeMessage(
        ...             subscription="my-subscription",
        ...             timeout_ms=1000,
        ...         )
        ...         match consume_result:
        ...             case ConsumeTimeout():
        ...                 break  # Timeout - no more messages
        ...             case MessageEnvelope():
        ...                 # Process message...
        ...                 processed += 1
        ...             case ConsumeFailure():
        ...                 raise RuntimeError("Failed to consume message")
        ...     return processed
    """

    subscription: str
    timeout_ms: int = 5000


@dataclass(frozen=True)
class AcknowledgeMessage:
    """Effect: Acknowledge message processing.

    This effect describes acknowledging a message after successful processing.
    Acknowledged messages will not be redelivered.

    Attributes:
        message_id: Pulsar message ID to acknowledge

    Returns:
        When yielded in a program, returns None on success.

    Example:
        >>> def consume_and_ack() -> Generator[AllEffects, EffectResult, None]:
        ...     envelope_result = yield ConsumeMessage(subscription="my-sub")
        ...     match envelope_result:
        ...         case MessageEnvelope(message_id=msg_id):
        ...             # Process message...
        ...             yield AcknowledgeMessage(message_id=msg_id)
        ...         case ConsumeTimeout():
        ...             return None
        ...         case ConsumeFailure():
        ...             return None
    """

    message_id: str


@dataclass(frozen=True)
class NegativeAcknowledge:
    """Effect: Negative acknowledge message for redelivery.

    This effect describes negative acknowledgment of a message, indicating that
    processing failed and the message should be redelivered (possibly after a delay).

    Attributes:
        message_id: Pulsar message ID to negative acknowledge
        delay_ms: Redelivery delay in milliseconds (default: 0 = immediate)

    Returns:
        When yielded in a program, returns None on success.

    Example:
        >>> def consume_with_retry() -> Generator[AllEffects, EffectResult, None]:
        ...     envelope = yield ConsumeMessage(subscription="my-sub")
        ...     if envelope is not None:
        ...         # Try to process...
        ...         success = process_message(envelope.payload)
        ...         if success:
        ...             yield AcknowledgeMessage(message_id=envelope.message_id)
        ...         else:
        ...             # Nack for redelivery after 1 second
        ...             yield NegativeAcknowledge(
        ...                 message_id=envelope.message_id,
        ...                 delay_ms=1000,
        ...             )
        ...     return None
    """

    message_id: str
    delay_ms: int = 0


# Type alias: Union of all messaging effects (PEP 695)
type MessagingEffect = (PublishMessage | ConsumeMessage | AcknowledgeMessage | NegativeAcknowledge)
