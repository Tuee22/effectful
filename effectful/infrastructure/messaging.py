"""Messaging protocols for Pulsar operations.

This module defines protocol interfaces for message producer and consumer operations.
Protocols use structural typing - any class implementing these methods satisfies
the protocol.

Protocols:
    - MessageProducer: Message publishing operations
    - MessageConsumer: Message consumption and acknowledgment operations

Implementation Notes:
    Real implementations use Pulsar client library (pulsar-client).
    Test implementations use in-memory fakes.

Type Safety:
    All methods have strict type signatures. Return ADTs instead of raising
    exceptions for domain-level failures.
"""

from typing import Protocol

from effectful.domain.message_envelope import (
    AcknowledgeResult,
    ConsumeResult,
    NackResult,
    PublishResult,
)


class MessageProducer(Protocol):
    """Protocol for message publishing operations.

    Implementations must handle message publishing to Pulsar topics. Domain-level
    failures (timeout, quota exceeded, topic not found) should return PublishFailure,
    not raise exceptions.

    Example Implementation:
        >>> class PulsarMessageProducer:
        ...     def __init__(self, client: pulsar.Client) -> None:
        ...         self._client = client
        ...
        ...     async def publish(
        ...         self,
        ...         topic: str,
        ...         payload: bytes,
        ...         properties: dict[str, str] | None = None,
        ...     ) -> PublishResult:
        ...         try:
        ...             producer = self._client.create_producer(topic)
        ...             msg_id = producer.send(payload, properties=properties or {})
        ...             return PublishSuccess(message_id=str(msg_id), topic=topic)
        ...         except pulsar.Timeout:
        ...             return PublishFailure(topic=topic, reason="timeout")
    """

    async def publish(
        self,
        topic: str,
        payload: bytes,
        properties: dict[str, str] | None = None,
    ) -> PublishResult:
        """Publish message to topic.

        Args:
            topic: Topic name to publish to
            payload: Message payload as bytes
            properties: Optional message properties

        Returns:
            PublishSuccess with message ID if successful.
            PublishFailure with reason if failed (timeout, quota, topic not found).

        Note:
            Does NOT raise exceptions for domain failures. Infrastructure failures
            (connection errors, etc.) may raise exceptions that interpreters convert
            to MessagingError.
        """
        ...


class MessageConsumer(Protocol):
    """Protocol for message consumption operations.

    Implementations must handle message consumption from Pulsar subscriptions and
    message acknowledgment operations.

    Example Implementation:
        >>> class PulsarMessageConsumer:
        ...     def __init__(self, client: pulsar.Client) -> None:
        ...         self._client = client
        ...         self._consumers: dict[str, pulsar.Consumer] = {}
        ...
        ...     async def receive(
        ...         self, subscription: str, timeout_ms: int
        ...     ) -> MessageEnvelope | None:
        ...         consumer = self._get_or_create_consumer(subscription)
        ...         try:
        ...             msg = consumer.receive(timeout_millis=timeout_ms)
        ...             return MessageEnvelope(
        ...                 message_id=str(msg.message_id()),
        ...                 payload=msg.data(),
        ...                 properties=msg.properties(),
        ...                 publish_time=msg.publish_timestamp(),
        ...                 topic=msg.topic_name(),
        ...             )
        ...         except pulsar.Timeout:
        ...             return None
    """

    async def receive(self, subscription: str, timeout_ms: int) -> ConsumeResult:
        """Receive message from subscription.

        Args:
            subscription: Subscription name to consume from
            timeout_ms: Timeout in milliseconds

        Returns:
            MessageEnvelope if message received before timeout.
            ConsumeTimeout if timeout occurred (no messages available).
            ConsumeFailure if connection or subscription error occurred.

        Note:
            Timeout is NOT an error - it's a normal outcome when queue is empty.
            All outcomes are explicit ADTs for exhaustive pattern matching.
        """
        ...

    async def acknowledge(self, message_id: str) -> AcknowledgeResult:
        """Acknowledge message processing.

        Args:
            message_id: Pulsar message ID to acknowledge

        Returns:
            AcknowledgeSuccess if acknowledged successfully.
            AcknowledgeFailure if acknowledgment failed.

        Note:
            Acknowledged messages will not be redelivered.
            Failures are explicit ADTs for exhaustive pattern matching.
        """
        ...

    async def negative_acknowledge(self, message_id: str, delay_ms: int = 0) -> NackResult:
        """Negative acknowledge message for redelivery.

        Args:
            message_id: Pulsar message ID to negative acknowledge
            delay_ms: Redelivery delay in milliseconds (0 = immediate)

        Returns:
            NackSuccess if nacked successfully.
            NackFailure if nack failed.

        Note:
            Nacked messages will be redelivered after the specified delay.
            Failures are explicit ADTs for exhaustive pattern matching.
        """
        ...
