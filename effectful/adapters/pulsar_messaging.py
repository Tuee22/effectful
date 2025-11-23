"""Pulsar implementations of messaging protocols.

This module provides production implementations of MessageProducer and MessageConsumer
using the Apache Pulsar Python client library.

Implementations:
    - PulsarMessageProducer: Publishes messages to Pulsar topics
    - PulsarMessageConsumer: Consumes messages from Pulsar subscriptions

Dependencies:
    Requires pulsar-client library:
    pip install pulsar-client

Type Safety:
    All implementations follow protocol contracts strictly. Domain failures return
    ADTs (PublishSuccess/PublishFailure), not exceptions.

Note on Purity:
    Adapters are at the I/O boundary and may use mutable state for connection/message
    caching. This is an acceptable exception to the purity doctrine. The for loops
    and dict mutations here are necessary for managing Pulsar client lifecycle.
"""

from datetime import UTC, datetime

try:
    import pulsar
except ImportError:
    raise ImportError(
        "Pulsar support requires pulsar-client library. " "Install with: pip install pulsar-client"
    )

from effectful.domain.message_envelope import (
    MessageEnvelope,
    PublishFailure,
    PublishResult,
    PublishSuccess,
)
from effectful.infrastructure.messaging import MessageConsumer, MessageProducer


class PulsarMessageProducer(MessageProducer):
    """Pulsar-based message producer.

    This implementation uses the Pulsar Python client to publish messages to topics.
    Producers are created lazily per topic and cached for reuse.

    Attributes:
        _client: Pulsar client instance
        _producers: Cache of topic -> producer mappings

    Example:
        >>> import pulsar
        >>> client = pulsar.Client("pulsar://localhost:6650")
        >>> producer = PulsarMessageProducer(client)
        >>>
        >>> result = await producer.publish(
        ...     topic="user-events",
        ...     payload=b'{"event": "login"}',
        ...     properties={"source": "web"},
        ... )
        >>>
        >>> match result:
        ...     case PublishSuccess(message_id=msg_id):
        ...         print(f"Published: {msg_id}")
    """

    def __init__(self, client: pulsar.Client) -> None:
        """Initialize producer with Pulsar client.

        Args:
            client: Connected Pulsar client instance
        """
        self._client = client
        self._producers: dict[str, pulsar.Producer] = {}

    async def publish(
        self,
        topic: str,
        payload: bytes,
        properties: dict[str, str] | None = None,
    ) -> PublishResult:
        """Publish message to Pulsar topic.

        Args:
            topic: Topic name to publish to
            payload: Message payload as bytes
            properties: Optional message properties

        Returns:
            PublishSuccess with message ID if successful.
            PublishFailure with reason if failed (timeout, quota, topic not found).

        Note:
            Producers are cached per topic for performance. First publish to a topic
            creates the producer; subsequent publishes reuse it.
        """
        try:
            # Get or create producer for topic
            if topic not in self._producers:
                self._producers[topic] = self._client.create_producer(
                    topic,
                    send_timeout_millis=30000,
                )

            producer = self._producers[topic]
            msg_id = producer.send(payload, properties=properties or {})

            return PublishSuccess(
                message_id=str(msg_id),
                topic=topic,
            )
        except pulsar.Timeout:
            return PublishFailure(topic=topic, reason="timeout")
        except pulsar.ProducerQueueIsFull:
            return PublishFailure(topic=topic, reason="quota_exceeded")
        except Exception as e:
            # Check for timeout pattern in exception
            error_msg = str(e).lower()
            if "timeout" in error_msg:
                return PublishFailure(topic=topic, reason="timeout")
            # Other exceptions (topic not found, permission denied, etc.)
            return PublishFailure(topic=topic, reason="topic_not_found")


class PulsarMessageConsumer(MessageConsumer):
    """Pulsar-based message consumer.

    This implementation uses the Pulsar Python client to consume messages from
    subscriptions. Consumers are created lazily per subscription and cached.

    Note:
        This implementation stores message references in memory for ack/nack operations.
        In production, consider using Pulsar's built-in acknowledgment tracking.

    Attributes:
        _client: Pulsar client instance
        _consumers: Cache of subscription -> consumer mappings
        _messages: Cache of message_id -> message for ack/nack

    Example:
        >>> import pulsar
        >>> client = pulsar.Client("pulsar://localhost:6650")
        >>> consumer = PulsarMessageConsumer(client)
        >>>
        >>> envelope = await consumer.receive("my-subscription", timeout_ms=1000)
        >>> if envelope is not None:
        ...     # Process message...
        ...     await consumer.acknowledge(envelope.message_id)
    """

    def __init__(self, client: pulsar.Client) -> None:
        """Initialize consumer with Pulsar client.

        Args:
            client: Connected Pulsar client instance
        """
        self._client = client
        self._consumers: dict[str, pulsar.Consumer] = {}
        self._messages: dict[str, pulsar.Message] = {}

    async def receive(self, subscription: str, timeout_ms: int) -> MessageEnvelope | None:
        """Receive message from Pulsar subscription.

        Args:
            subscription: Subscription name to consume from
            timeout_ms: Timeout in milliseconds

        Returns:
            MessageEnvelope if message received before timeout.
            None if timeout occurred.

        Note:
            Subscription format: "topic/subscription-name"
            First part before "/" is topic, full string is subscription name.
        """
        # Get or create consumer for subscription
        if subscription not in self._consumers:
            # Extract topic from subscription name (assumes format: topic/sub-name)
            topic = subscription.split("/")[0] if "/" in subscription else subscription
            # Extract subscription name from format: topic/sub-name
            sub_name = subscription.split("/")[1] if "/" in subscription else subscription
            self._consumers[subscription] = self._client.subscribe(
                topic=topic,
                subscription_name=sub_name,
                initial_position=pulsar.InitialPosition.Earliest,
            )

        consumer = self._consumers[subscription]

        try:
            msg = consumer.receive(timeout_millis=timeout_ms)

            # Store message for later ack/nack
            msg_id = str(msg.message_id())
            self._messages[msg_id] = msg

            return MessageEnvelope(
                message_id=msg_id,
                payload=msg.data(),
                properties=msg.properties(),
                publish_time=datetime.fromtimestamp(msg.publish_timestamp() / 1000, UTC),
                topic=msg.topic_name(),
            )
        except pulsar.Timeout:
            return None

    async def acknowledge(self, message_id: str) -> None:
        """Acknowledge message processing.

        Args:
            message_id: Pulsar message ID to acknowledge

        Raises:
            KeyError: If message_id not found (message not received via this consumer)
        """
        msg = self._messages.get(message_id)
        if msg is None:
            raise KeyError(f"Message {message_id} not found in consumer cache")

        # Get consumer for this message's subscription
        for subscription, consumer in self._consumers.items():
            try:
                consumer.acknowledge(msg)
                # Remove from cache after ack
                del self._messages[message_id]
                return
            except Exception:
                continue

        raise KeyError(f"No consumer found for message {message_id}")

    async def negative_acknowledge(self, message_id: str, delay_ms: int = 0) -> None:
        """Negative acknowledge message for redelivery.

        Args:
            message_id: Pulsar message ID to negative acknowledge
            delay_ms: Redelivery delay in milliseconds (not supported by all Pulsar versions)

        Raises:
            KeyError: If message_id not found (message not received via this consumer)

        Note:
            The delay_ms parameter may not be supported by all Pulsar broker versions.
            If unsupported, message will be redelivered immediately.
        """
        msg = self._messages.get(message_id)
        if msg is None:
            raise KeyError(f"Message {message_id} not found in consumer cache")

        # Get consumer for this message's subscription
        for subscription, consumer in self._consumers.items():
            try:
                consumer.negative_acknowledge(msg)
                # Remove from cache after nack
                del self._messages[message_id]
                return
            except Exception:
                continue

        raise KeyError(f"No consumer found for message {message_id}")
