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
"""

import os
from datetime import UTC, datetime

try:
    import pulsar
except ImportError:
    raise ImportError(
        "Pulsar support requires pulsar-client library. " "Install with: pip install pulsar-client"
    ) from None

from effectful.domain.message_envelope import (
    AcknowledgeFailure,
    AcknowledgeResult,
    AcknowledgeSuccess,
    ConsumeFailure,
    ConsumeResult,
    ConsumeTimeout,
    MessageEnvelope,
    NackFailure,
    NackResult,
    NackSuccess,
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
                try:
                    self._producers[topic] = self._client.create_producer(
                        topic,
                        send_timeout_millis=int(os.environ["PULSAR_SEND_TIMEOUT_MS"]),
                    )
                except (TimeoutError, pulsar.Timeout):
                    # Timeout during producer creation indicates BookKeeper not ready
                    return PublishFailure(topic=topic, reason="bookkeeper_not_ready")
                except Exception as e:
                    # Error classification based on string matching
                    # Tested with pulsar-client 3.x - may need updates for other versions
                    error_msg = str(e).lower()
                    if "bookkeeper" in error_msg or "bookie" in error_msg:
                        return PublishFailure(topic=topic, reason="bookkeeper_not_ready")
                    if "connect" in error_msg or "unreachable" in error_msg:
                        return PublishFailure(topic=topic, reason="broker_unreachable")
                    if "auth" in error_msg:
                        return PublishFailure(topic=topic, reason="auth_failed")
                    return PublishFailure(topic=topic, reason="topic_not_found")

            producer = self._producers[topic]
            msg_id = producer.send(payload, properties=properties or {})

            return PublishSuccess(
                message_id=str(msg_id),
                topic=topic,
            )
        except (TimeoutError, pulsar.Timeout):
            return PublishFailure(topic=topic, reason="timeout")
        except Exception as e:
            # Analyze error message for specific failure reason
            # Tested with pulsar-client 3.x - may need updates for other versions
            error_msg = str(e).lower()
            error_type = type(e).__name__.lower()
            if "timeout" in error_msg:
                return PublishFailure(topic=topic, reason="timeout")
            if "bookkeeper" in error_msg or "bookie" in error_msg:
                return PublishFailure(topic=topic, reason="bookkeeper_not_ready")
            if "queue" in error_msg and "full" in error_msg:
                return PublishFailure(topic=topic, reason="quota_exceeded")
            if "blocked" in error_msg or "producerblocked" in error_type:
                return PublishFailure(topic=topic, reason="producer_blocked")
            if "too" in error_msg and ("big" in error_msg or "large" in error_msg):
                return PublishFailure(topic=topic, reason="message_too_large")
            if "connect" in error_msg or "closed" in error_msg:
                return PublishFailure(topic=topic, reason="connection_closed")
            if "auth" in error_msg:
                return PublishFailure(topic=topic, reason="auth_failed")
            # Default to topic_not_found for unknown errors
            return PublishFailure(topic=topic, reason="topic_not_found")

    def close_producers(self) -> None:
        """Close all cached producers and clear the cache.

        TESTING ONLY. Used to reset state between test cases.

        Example:
            >>> producer = PulsarMessageProducer(client)
            >>> await producer.publish("topic-1", b"data")
            >>> producer.close_producers()  # Cleanup between tests
        """

        # Close each producer using functional pattern
        def safe_close(producer: pulsar.Producer) -> bool:
            try:
                producer.close()
                return True
            except Exception:
                # Ignore errors during cleanup - test isolation is more important
                return True

        tuple(safe_close(p) for p in self._producers.values())

        # Clear the cache
        self._producers = {}


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

    async def receive(self, subscription: str, timeout_ms: int) -> ConsumeResult:
        """Receive message from Pulsar subscription.

        Args:
            subscription: Subscription name to consume from
            timeout_ms: Timeout in milliseconds

        Returns:
            MessageEnvelope if message received before timeout.
            ConsumeFailure if connection or subscription error occurred.
            None if timeout occurred (no message available).

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
            try:
                self._consumers[subscription] = self._client.subscribe(
                    topic=topic,
                    subscription_name=sub_name,
                    initial_position=pulsar.InitialPosition.Earliest,
                )
            except Exception as e:
                error_msg = str(e).lower()
                if "connect" in error_msg or "unreachable" in error_msg:
                    return ConsumeFailure(subscription=subscription, reason="broker_unreachable")
                if "auth" in error_msg:
                    return ConsumeFailure(subscription=subscription, reason="auth_failed")
                if "not found" in error_msg or "does not exist" in error_msg:
                    return ConsumeFailure(
                        subscription=subscription, reason="subscription_not_found"
                    )
                return ConsumeFailure(subscription=subscription, reason="subscription_not_found")

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
        except (TimeoutError, pulsar.Timeout):
            return ConsumeTimeout(subscription=subscription, timeout_ms=timeout_ms)
        except Exception as e:
            error_msg = str(e).lower()
            error_type = type(e).__name__.lower()
            if "closed" in error_msg or "consumerclosed" in error_type:
                return ConsumeFailure(subscription=subscription, reason="consumer_closed")
            if "connect" in error_msg:
                return ConsumeFailure(subscription=subscription, reason="connection_closed")
            return ConsumeFailure(subscription=subscription, reason="subscription_not_found")

    async def acknowledge(self, message_id: str) -> AcknowledgeResult:
        """Acknowledge message processing.

        Args:
            message_id: Pulsar message ID to acknowledge

        Returns:
            AcknowledgeSuccess if acknowledged successfully.
            AcknowledgeFailure with reason if acknowledgment failed.
        """
        msg = self._messages.get(message_id)
        if msg is None:
            return AcknowledgeFailure(message_id=message_id, reason="message_not_found")

        # Try each consumer to find the one that owns this message
        ack_errors: list[str] = []
        for _subscription, consumer in self._consumers.items():
            try:
                consumer.acknowledge(msg)
                # Remove from cache after successful ack
                self._messages = {k: v for k, v in self._messages.items() if k != message_id}
                return AcknowledgeSuccess(message_id=message_id)
            except Exception as e:
                error_msg = str(e).lower()
                if "closed" in error_msg:
                    return AcknowledgeFailure(message_id=message_id, reason="connection_closed")
                ack_errors.append(str(e))
                continue

        return AcknowledgeFailure(message_id=message_id, reason="consumer_not_found")

    async def negative_acknowledge(self, message_id: str, delay_ms: int = 0) -> NackResult:
        """Negative acknowledge message for redelivery.

        Args:
            message_id: Pulsar message ID to negative acknowledge
            delay_ms: Redelivery delay in milliseconds (not supported by all Pulsar versions)

        Returns:
            NackSuccess if nacked successfully.
            NackFailure with reason if nack failed.

        Note:
            The delay_ms parameter may not be supported by all Pulsar broker versions.
            If unsupported, message will be redelivered immediately.
        """
        msg = self._messages.get(message_id)
        if msg is None:
            return NackFailure(message_id=message_id, reason="message_not_found")

        # Try each consumer to find the one that owns this message
        for _subscription, consumer in self._consumers.items():
            try:
                consumer.negative_acknowledge(msg)
                # Remove from cache after successful nack
                self._messages = {k: v for k, v in self._messages.items() if k != message_id}
                return NackSuccess(message_id=message_id)
            except Exception as e:
                error_msg = str(e).lower()
                if "closed" in error_msg:
                    return NackFailure(message_id=message_id, reason="connection_closed")
                continue

        return NackFailure(message_id=message_id, reason="consumer_not_found")

    def close_consumers(self) -> None:
        """Close all cached consumers and clear message cache.

        TESTING ONLY. Used to reset state between test cases.

        Example:
            >>> consumer = PulsarMessageConsumer(client)
            >>> await consumer.receive("topic/sub", timeout_ms=1000)
            >>> consumer.close_consumers()  # Cleanup between tests
        """

        # Close each consumer using functional pattern
        def safe_close(consumer: pulsar.Consumer) -> bool:
            try:
                consumer.close()
                return True
            except Exception:
                # Ignore errors during cleanup - test isolation is more important
                return True

        tuple(safe_close(c) for c in self._consumers.values())

        # Clear both caches
        self._consumers = {}
        self._messages = {}  # Critical: prevents message reference leaks
