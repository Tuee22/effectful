"""Unit tests for Pulsar messaging adapters.

Tests PulsarMessageProducer and PulsarMessageConsumer using pytest-mock.
"""

from datetime import UTC, datetime

import pulsar  # Only for InitialPosition constants, not infrastructure
import pytest
from pytest_mock import MockerFixture

from effectful.adapters.pulsar_messaging import (
    PulsarMessageConsumer,
    PulsarMessageProducer,
)
from effectful.domain.message_envelope import (
    AcknowledgeFailure,
    AcknowledgeSuccess,
    ConsumeTimeout,
    MessageEnvelope,
    NackFailure,
    NackSuccess,
    PublishFailure,
    PublishSuccess,
)


class TestPulsarMessageProducer:
    """Tests for PulsarMessageProducer."""

    @pytest.mark.asyncio
    async def test_publish_returns_success_with_message_id(self, mocker: MockerFixture) -> None:
        """Test successful publish returns PublishSuccess."""
        # Setup
        topic = "user-events"
        payload = b'{"event": "login"}'
        properties = {"source": "web"}

        mock_msg_id = mocker.MagicMock()
        mock_msg_id.__str__ = mocker.MagicMock(return_value="msg-123")

        mock_producer = mocker.MagicMock()
        mock_producer.send.return_value = mock_msg_id

        mock_client = mocker.MagicMock()
        mock_client.create_producer.return_value = mock_producer

        producer = PulsarMessageProducer(mock_client)

        # Execute
        result = await producer.publish(topic, payload, properties)

        # Assert
        assert isinstance(result, PublishSuccess)
        assert result.topic == topic
        assert "msg-123" in result.message_id

        # Verify calls
        mock_client.create_producer.assert_called_once_with(topic, send_timeout_millis=5000)
        mock_producer.send.assert_called_once_with(payload, properties=properties)

    @pytest.mark.asyncio
    async def test_publish_reuses_producer_for_same_topic(self, mocker: MockerFixture) -> None:
        """Test producer is cached and reused for same topic."""
        # Setup
        mock_msg_id = mocker.MagicMock()
        mock_producer = mocker.MagicMock()
        mock_producer.send.return_value = mock_msg_id

        mock_client = mocker.MagicMock()
        mock_client.create_producer.return_value = mock_producer

        producer = PulsarMessageProducer(mock_client)

        # Execute - publish twice to same topic
        await producer.publish("topic", b"msg1", None)
        await producer.publish("topic", b"msg2", None)

        # Assert - producer created only once
        mock_client.create_producer.assert_called_once()
        assert mock_producer.send.call_count == 2

    @pytest.mark.asyncio
    async def test_publish_returns_failure_for_timeout(self, mocker: MockerFixture) -> None:
        """Test publish timeout returns PublishFailure."""
        # Setup
        mock_producer = mocker.MagicMock()
        mock_producer.send.side_effect = TimeoutError("Timeout")

        mock_client = mocker.MagicMock()
        mock_client.create_producer.return_value = mock_producer

        producer = PulsarMessageProducer(mock_client)

        # Execute
        result = await producer.publish("topic", b"payload", None)

        # Assert
        assert isinstance(result, PublishFailure)
        assert result.topic == "topic"
        assert result.reason == "timeout"

    @pytest.mark.asyncio
    async def test_publish_returns_failure_for_queue_full(self, mocker: MockerFixture) -> None:
        """Test publish with full queue returns PublishFailure."""
        # Setup
        mock_producer = mocker.MagicMock()
        mock_producer.send.side_effect = RuntimeError("Queue full")

        mock_client = mocker.MagicMock()
        mock_client.create_producer.return_value = mock_producer

        producer = PulsarMessageProducer(mock_client)

        # Execute
        result = await producer.publish("topic", b"payload", None)

        # Assert
        assert isinstance(result, PublishFailure)
        assert result.reason == "quota_exceeded"

    @pytest.mark.asyncio
    async def test_publish_returns_failure_for_other_exceptions(
        self, mocker: MockerFixture
    ) -> None:
        """Test other exceptions return topic_not_found failure."""
        # Setup
        mock_producer = mocker.MagicMock()
        mock_producer.send.side_effect = RuntimeError("Unknown error")

        mock_client = mocker.MagicMock()
        mock_client.create_producer.return_value = mock_producer

        producer = PulsarMessageProducer(mock_client)

        # Execute
        result = await producer.publish("topic", b"payload", None)

        # Assert
        assert isinstance(result, PublishFailure)
        assert result.reason == "topic_not_found"


class TestPulsarMessageConsumer:
    """Tests for PulsarMessageConsumer."""

    @pytest.mark.asyncio
    async def test_receive_returns_message_envelope(self, mocker: MockerFixture) -> None:
        """Test successful receive returns MessageEnvelope."""
        # Setup
        subscription = "user-events/my-subscription"

        mock_msg_id = mocker.MagicMock()
        mock_msg_id.__str__ = mocker.MagicMock(return_value="msg-456")

        publish_timestamp = int(datetime.now(UTC).timestamp() * 1000)

        mock_message = mocker.MagicMock()
        mock_message.message_id.return_value = mock_msg_id
        mock_message.data.return_value = b'{"event": "login"}'
        mock_message.properties.return_value = {"source": "web"}
        mock_message.publish_timestamp.return_value = publish_timestamp
        mock_message.topic_name.return_value = "user-events"

        mock_consumer = mocker.MagicMock()
        mock_consumer.receive.return_value = mock_message

        mock_client = mocker.MagicMock()
        mock_client.subscribe.return_value = mock_consumer

        consumer = PulsarMessageConsumer(mock_client)

        # Execute
        result = await consumer.receive(subscription, timeout_ms=1000)

        # Assert
        assert isinstance(result, MessageEnvelope)
        assert "msg-456" in result.message_id
        assert result.payload == b'{"event": "login"}'
        assert result.properties == {"source": "web"}
        assert result.topic == "user-events"

        # Verify subscription - adapter extracts sub_name from format "topic/sub-name"
        mock_client.subscribe.assert_called_once_with(
            topic="user-events",
            subscription_name="my-subscription",
            initial_position=pulsar.InitialPosition.Earliest,
        )
        mock_consumer.receive.assert_called_once_with(timeout_millis=1000)

    @pytest.mark.asyncio
    async def test_receive_returns_consume_timeout_on_timeout(self, mocker: MockerFixture) -> None:
        """Test receive timeout returns ConsumeTimeout ADT."""
        # Setup
        mock_consumer = mocker.MagicMock()
        mock_consumer.receive.side_effect = TimeoutError("Timeout")

        mock_client = mocker.MagicMock()
        mock_client.subscribe.return_value = mock_consumer

        consumer = PulsarMessageConsumer(mock_client)

        # Execute
        result = await consumer.receive("topic/sub", timeout_ms=100)

        # Assert
        assert isinstance(result, ConsumeTimeout)
        assert result.subscription == "topic/sub"
        assert result.timeout_ms == 100

    @pytest.mark.asyncio
    async def test_receive_reuses_consumer_for_same_subscription(
        self, mocker: MockerFixture
    ) -> None:
        """Test consumer is cached and reused for same subscription."""
        # Setup
        mock_msg = mocker.MagicMock()
        mock_msg.message_id.return_value = mocker.MagicMock()
        mock_msg.data.return_value = b"data"
        mock_msg.properties.return_value = {}
        mock_msg.publish_timestamp.return_value = 0
        mock_msg.topic_name.return_value = "topic"

        mock_consumer = mocker.MagicMock()
        mock_consumer.receive.return_value = mock_msg

        mock_client = mocker.MagicMock()
        mock_client.subscribe.return_value = mock_consumer

        consumer = PulsarMessageConsumer(mock_client)

        # Execute - receive twice from same subscription
        await consumer.receive("topic/sub", timeout_ms=100)
        await consumer.receive("topic/sub", timeout_ms=100)

        # Assert - consumer created only once
        mock_client.subscribe.assert_called_once()
        assert mock_consumer.receive.call_count == 2

    @pytest.mark.asyncio
    async def test_acknowledge_calls_consumer_acknowledge(self, mocker: MockerFixture) -> None:
        """Test acknowledge calls consumer.acknowledge with correct message."""
        # Setup
        mock_msg = mocker.MagicMock()
        mock_msg_id = mocker.MagicMock()
        mock_msg_id.__str__ = mocker.MagicMock(return_value="msg-789")
        mock_msg.message_id.return_value = mock_msg_id
        mock_msg.data.return_value = b"data"
        mock_msg.properties.return_value = {}
        mock_msg.publish_timestamp.return_value = 0
        mock_msg.topic_name.return_value = "topic"

        mock_consumer = mocker.MagicMock()
        mock_consumer.receive.return_value = mock_msg

        mock_client = mocker.MagicMock()
        mock_client.subscribe.return_value = mock_consumer

        consumer = PulsarMessageConsumer(mock_client)

        # Receive message first
        envelope = await consumer.receive("topic/sub", timeout_ms=100)
        assert isinstance(envelope, MessageEnvelope)

        # Execute
        result = await consumer.acknowledge(envelope.message_id)

        # Assert
        mock_consumer.acknowledge.assert_called_once_with(mock_msg)
        assert isinstance(result, AcknowledgeSuccess)
        assert result.message_id == envelope.message_id

    @pytest.mark.asyncio
    async def test_acknowledge_returns_failure_for_unknown_message(
        self, mocker: MockerFixture
    ) -> None:
        """Test acknowledge returns AcknowledgeFailure for unknown message_id."""
        # Setup
        mock_client = mocker.MagicMock()
        consumer = PulsarMessageConsumer(mock_client)

        # Execute
        result = await consumer.acknowledge("unknown-msg-id")

        # Assert
        assert isinstance(result, AcknowledgeFailure)
        assert result.message_id == "unknown-msg-id"
        assert result.reason == "message_not_found"

    @pytest.mark.asyncio
    async def test_negative_acknowledge_calls_consumer_nack(self, mocker: MockerFixture) -> None:
        """Test negative_acknowledge calls consumer.negative_acknowledge."""
        # Setup
        mock_msg = mocker.MagicMock()
        mock_msg_id = mocker.MagicMock()
        mock_msg_id.__str__ = mocker.MagicMock(return_value="msg-999")
        mock_msg.message_id.return_value = mock_msg_id
        mock_msg.data.return_value = b"data"
        mock_msg.properties.return_value = {}
        mock_msg.publish_timestamp.return_value = 0
        mock_msg.topic_name.return_value = "topic"

        mock_consumer = mocker.MagicMock()
        mock_consumer.receive.return_value = mock_msg

        mock_client = mocker.MagicMock()
        mock_client.subscribe.return_value = mock_consumer

        consumer = PulsarMessageConsumer(mock_client)

        # Receive message first
        envelope = await consumer.receive("topic/sub", timeout_ms=100)
        assert isinstance(envelope, MessageEnvelope)

        # Execute
        result = await consumer.negative_acknowledge(envelope.message_id, delay_ms=1000)

        # Assert
        mock_consumer.negative_acknowledge.assert_called_once_with(mock_msg)
        assert isinstance(result, NackSuccess)
        assert result.message_id == envelope.message_id

    @pytest.mark.asyncio
    async def test_negative_acknowledge_returns_failure_for_unknown_message(
        self, mocker: MockerFixture
    ) -> None:
        """Test negative_acknowledge returns NackFailure for unknown message_id."""
        # Setup
        mock_client = mocker.MagicMock()
        consumer = PulsarMessageConsumer(mock_client)

        # Execute
        result = await consumer.negative_acknowledge("unknown-msg-id")

        # Assert
        assert isinstance(result, NackFailure)
        assert result.message_id == "unknown-msg-id"
        assert result.reason == "message_not_found"

    @pytest.mark.asyncio
    async def test_receive_handles_simple_subscription_name(self, mocker: MockerFixture) -> None:
        """Test receive handles subscription without '/' separator."""
        # Setup
        mock_msg = mocker.MagicMock()
        mock_msg.message_id.return_value = mocker.MagicMock()
        mock_msg.data.return_value = b"data"
        mock_msg.properties.return_value = {}
        mock_msg.publish_timestamp.return_value = 0
        mock_msg.topic_name.return_value = "topic"

        mock_consumer = mocker.MagicMock()
        mock_consumer.receive.return_value = mock_msg

        mock_client = mocker.MagicMock()
        mock_client.subscribe.return_value = mock_consumer

        consumer = PulsarMessageConsumer(mock_client)

        # Execute
        await consumer.receive("simple-subscription", timeout_ms=100)

        # Assert - uses subscription name as topic
        mock_client.subscribe.assert_called_once_with(
            topic="simple-subscription",
            subscription_name="simple-subscription",
            initial_position=pulsar.InitialPosition.Earliest,
        )
