"""Integration tests for complete messaging workflows.

This module tests complete messaging workflows combining messaging effects:
- Publishing messages to topics
- Consuming messages from subscriptions
- Acknowledging successful message processing
- Negative acknowledging failed message processing

These integration tests verify that the messaging interpreter works correctly
with both fake and failing implementations, testing both success and error paths.
"""

from collections.abc import Generator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pytest_mock import MockerFixture

from effectful.algebraic.result import Err, Ok
from effectful.domain.message_envelope import (
    MessageEnvelope,
    PublishFailure,
    PublishSuccess,
)
from effectful.effects.messaging import (
    AcknowledgeMessage,
    ConsumeMessage,
    NegativeAcknowledge,
    PublishMessage,
)
from effectful.infrastructure.messaging import MessageConsumer, MessageProducer
from effectful.interpreters.errors import MessagingError
from effectful.interpreters.messaging import MessagingInterpreter
from effectful.programs.program_types import AllEffects, EffectResult
from effectful.programs.runners import run_ws_program


class TestMessagingWorkflowIntegration:
    """Integration tests for complete messaging workflows."""

    @pytest.mark.asyncio()
    async def test_publish_consume_acknowledge_workflow(
        self, mocker: MockerFixture
    ) -> None:
        """Complete workflow: publish message, consume it, acknowledge processing."""
        # Create mocks
        mock_producer = mocker.AsyncMock(spec=MessageProducer)
        mock_consumer = mocker.AsyncMock(spec=MessageConsumer)

        # Configure publish to succeed
        mock_producer.publish.return_value = PublishSuccess(
            message_id="msg-123", topic="test-topic"
        )

        # Configure consume to return a message
        envelope = MessageEnvelope(
            message_id="msg-123",
            payload=b"test data",
            properties={"source": "test"},
            publish_time=datetime.now(UTC),
            topic="test-topic",
        )
        mock_consumer.receive.return_value = envelope

        interpreter = MessagingInterpreter(producer=mock_producer, consumer=mock_consumer)

        # Define complete workflow
        def publish_consume_ack_program() -> Generator[AllEffects, EffectResult, str]:
            """Publish message, consume it, and acknowledge."""
            # 1. Publish message
            message_id_result = yield PublishMessage(
                topic="test-topic", payload=b"test data", properties={"source": "test"}
            )
            assert isinstance(message_id_result, str)
            message_id = message_id_result

            # 2. Consume message
            envelope_result = yield ConsumeMessage(
                subscription="test-subscription", timeout_ms=1000
            )
            assert isinstance(envelope_result, MessageEnvelope)
            envelope = envelope_result

            # 3. Acknowledge message
            yield AcknowledgeMessage(message_id=envelope.message_id)

            return f"Processed message {message_id}"

        # Act
        result = await run_ws_program(publish_consume_ack_program(), interpreter)

        # Assert
        match result:
            case Ok(outcome):
                assert outcome == "Processed message msg-123"
                # Verify publish called
                mock_producer.publish.assert_called_once_with(
                    "test-topic", b"test data", {"source": "test"}
                )
                # Verify consume called
                mock_consumer.receive.assert_called_once_with("test-subscription", 1000)
                # Verify acknowledge called
                mock_consumer.acknowledge.assert_called_once_with("msg-123")
            case Err(error):
                pytest.fail(f"Expected Ok, got Err({error})")

    @pytest.mark.asyncio()
    async def test_publish_timeout_workflow(self, mocker: MockerFixture) -> None:
        """Workflow handles publish timeout failure gracefully."""
        # Create mocks
        mock_producer = mocker.AsyncMock(spec=MessageProducer)
        mock_consumer = mocker.AsyncMock(spec=MessageConsumer)

        # Configure publish to timeout
        mock_producer.publish.return_value = PublishFailure(
            topic="test-topic", reason="timeout"
        )

        interpreter = MessagingInterpreter(producer=mock_producer, consumer=mock_consumer)

        # Define workflow
        def publish_timeout_program() -> Generator[AllEffects, EffectResult, bool]:
            """Try to publish, handle timeout."""
            message_id = yield PublishMessage(topic="test-topic", payload=b"data")
            # Never reached - publish failed
            return True

        # Act
        result = await run_ws_program(publish_timeout_program(), interpreter)

        # Assert
        match result:
            case Err(error):
                # Verify error type and retryability
                assert isinstance(error, MessagingError)
                assert "timeout" in error.messaging_error
                assert error.is_retryable is True
                # Verify publish was attempted
                mock_producer.publish.assert_called_once()
            case Ok(value):
                pytest.fail(f"Expected Err(MessagingError), got Ok({value})")

    @pytest.mark.asyncio()
    async def test_publish_quota_exceeded_workflow(self, mocker: MockerFixture) -> None:
        """Workflow handles quota exceeded failure (retryable)."""
        # Create mocks
        mock_producer = mocker.AsyncMock(spec=MessageProducer)
        mock_consumer = mocker.AsyncMock(spec=MessageConsumer)

        # Configure publish to fail with quota exceeded
        mock_producer.publish.return_value = PublishFailure(
            topic="test-topic", reason="quota_exceeded"
        )

        interpreter = MessagingInterpreter(producer=mock_producer, consumer=mock_consumer)

        # Define workflow
        def publish_quota_program() -> Generator[AllEffects, EffectResult, bool]:
            """Try to publish, handle quota exceeded."""
            yield PublishMessage(topic="test-topic", payload=b"data")
            return True

        # Act
        result = await run_ws_program(publish_quota_program(), interpreter)

        # Assert
        match result:
            case Err(error):
                assert isinstance(error, MessagingError)
                assert "quota_exceeded" in error.messaging_error
                assert error.is_retryable is True
            case Ok(value):
                pytest.fail(f"Expected Err(MessagingError), got Ok({value})")

    @pytest.mark.asyncio()
    async def test_publish_topic_not_found_workflow(self, mocker: MockerFixture) -> None:
        """Workflow handles topic not found failure (non-retryable)."""
        # Create mocks
        mock_producer = mocker.AsyncMock(spec=MessageProducer)
        mock_consumer = mocker.AsyncMock(spec=MessageConsumer)

        # Configure publish to fail with topic not found
        mock_producer.publish.return_value = PublishFailure(
            topic="test-topic", reason="topic_not_found"
        )

        interpreter = MessagingInterpreter(producer=mock_producer, consumer=mock_consumer)

        # Define workflow
        def publish_topic_not_found_program() -> Generator[AllEffects, EffectResult, bool]:
            """Try to publish to nonexistent topic."""
            yield PublishMessage(topic="test-topic", payload=b"data")
            return True

        # Act
        result = await run_ws_program(publish_topic_not_found_program(), interpreter)

        # Assert
        match result:
            case Err(error):
                assert isinstance(error, MessagingError)
                assert "topic_not_found" in error.messaging_error
                assert error.is_retryable is False  # Non-retryable!
            case Ok(value):
                pytest.fail(f"Expected Err(MessagingError), got Ok({value})")

    @pytest.mark.asyncio()
    async def test_consume_timeout_workflow(self, mocker: MockerFixture) -> None:
        """Workflow handles consume timeout gracefully (not an error)."""
        # Create mocks
        mock_producer = mocker.AsyncMock(spec=MessageProducer)
        mock_consumer = mocker.AsyncMock(spec=MessageConsumer)

        # Configure consume to timeout (return None)
        mock_consumer.receive.return_value = None

        interpreter = MessagingInterpreter(producer=mock_producer, consumer=mock_consumer)

        # Define workflow
        def consume_timeout_program() -> Generator[AllEffects, EffectResult, str]:
            """Try to consume, handle timeout."""
            envelope = yield ConsumeMessage(subscription="test-sub", timeout_ms=1000)

            match envelope:
                case None:
                    return "timeout"
                case MessageEnvelope(message_id=msg_id):
                    yield AcknowledgeMessage(message_id=msg_id)
                    return "success"
                case _:
                    return "unexpected"

        # Act
        result = await run_ws_program(consume_timeout_program(), interpreter)

        # Assert
        match result:
            case Ok(outcome):
                assert outcome == "timeout"
                # Verify consume was attempted
                mock_consumer.receive.assert_called_once_with("test-sub", 1000)
                # Verify acknowledge NOT called (no message)
                mock_consumer.acknowledge.assert_not_called()
            case Err(error):
                pytest.fail(f"Expected Ok('timeout'), got Err({error})")

    @pytest.mark.asyncio()
    async def test_negative_acknowledge_workflow(self, mocker: MockerFixture) -> None:
        """Workflow with negative acknowledge for failed processing."""
        # Create mocks
        mock_producer = mocker.AsyncMock(spec=MessageProducer)
        mock_consumer = mocker.AsyncMock(spec=MessageConsumer)

        # Configure consume to return a message
        envelope = MessageEnvelope(
            message_id="msg-456",
            payload=b"invalid data",
            properties={},
            publish_time=datetime.now(UTC),
            topic="test-topic",
        )
        mock_consumer.receive.return_value = envelope

        interpreter = MessagingInterpreter(producer=mock_producer, consumer=mock_consumer)

        # Define workflow
        def nack_workflow() -> Generator[AllEffects, EffectResult, str]:
            """Consume message, fail processing, negative acknowledge."""
            # 1. Consume message
            envelope_result = yield ConsumeMessage(
                subscription="test-sub", timeout_ms=1000
            )
            assert isinstance(envelope_result, MessageEnvelope)
            envelope = envelope_result

            # 2. Try to process (simulate failure by checking payload)
            if envelope.payload == b"invalid data":
                # Processing failed - negative acknowledge with delay
                yield NegativeAcknowledge(message_id=envelope.message_id, delay_ms=5000)
                return "processing_failed"

            # 3. Success path
            yield AcknowledgeMessage(message_id=envelope.message_id)
            return "processing_success"

        # Act
        result = await run_ws_program(nack_workflow(), interpreter)

        # Assert
        match result:
            case Ok(outcome):
                assert outcome == "processing_failed"
                # Verify consume called
                mock_consumer.receive.assert_called_once()
                # Verify negative acknowledge called with delay
                mock_consumer.negative_acknowledge.assert_called_once_with("msg-456", 5000)
                # Verify acknowledge NOT called
                mock_consumer.acknowledge.assert_not_called()
            case Err(error):
                pytest.fail(f"Expected Ok('processing_failed'), got Err({error})")

    @pytest.mark.asyncio()
    async def test_multi_message_workflow(self, mocker: MockerFixture) -> None:
        """Workflow publishing multiple messages."""
        # Create mocks
        mock_producer = mocker.AsyncMock(spec=MessageProducer)
        mock_consumer = mocker.AsyncMock(spec=MessageConsumer)

        # Configure publish to succeed with different message IDs
        mock_producer.publish.side_effect = [
            PublishSuccess(message_id="msg-1", topic="events"),
            PublishSuccess(message_id="msg-2", topic="events"),
            PublishSuccess(message_id="msg-3", topic="events"),
        ]

        interpreter = MessagingInterpreter(producer=mock_producer, consumer=mock_consumer)

        # Define workflow
        def multi_publish_program() -> Generator[AllEffects, EffectResult, int]:
            """Publish multiple messages to a topic."""
            messages = [b"event-1", b"event-2", b"event-3"]
            published_count = 0

            for payload in messages:
                message_id = yield PublishMessage(topic="events", payload=payload)
                assert isinstance(message_id, str)
                published_count += 1

            return published_count

        # Act
        result = await run_ws_program(multi_publish_program(), interpreter)

        # Assert
        match result:
            case Ok(count):
                assert count == 3
                # Verify all publishes called
                assert mock_producer.publish.call_count == 3
                mock_producer.publish.assert_any_call("events", b"event-1", None)
                mock_producer.publish.assert_any_call("events", b"event-2", None)
                mock_producer.publish.assert_any_call("events", b"event-3", None)
            case Err(error):
                pytest.fail(f"Expected Ok(3), got Err({error})")

    @pytest.mark.asyncio()
    async def test_workflow_error_propagation(self, mocker: MockerFixture) -> None:
        """Workflow propagates errors correctly (fail-fast)."""
        # Create mocks
        mock_producer = mocker.AsyncMock(spec=MessageProducer)
        mock_consumer = mocker.AsyncMock(spec=MessageConsumer)

        # Configure producer to raise exception
        mock_producer.publish.side_effect = RuntimeError("connection unavailable")

        interpreter = MessagingInterpreter(producer=mock_producer, consumer=mock_consumer)

        # Define workflow
        def failing_workflow() -> Generator[AllEffects, EffectResult, str]:
            """Try to publish, fail, verify subsequent effects not executed."""
            # This will fail
            message_id1 = yield PublishMessage(topic="topic-1", payload=b"data-1")

            # Never reached (fail-fast)
            message_id2 = yield PublishMessage(topic="topic-2", payload=b"data-2")
            return "success"

        # Act
        result = await run_ws_program(failing_workflow(), interpreter)

        # Assert
        match result:
            case Err(error):
                # Verify error type and message
                assert isinstance(error, MessagingError)
                assert "connection unavailable" in error.messaging_error
                assert error.is_retryable is True
                # Verify only first publish was attempted (fail-fast)
                assert mock_producer.publish.call_count == 1
            case Ok(value):
                pytest.fail(f"Expected Err(MessagingError), got Ok({value})")

    @pytest.mark.asyncio()
    async def test_acknowledge_exception_workflow(self, mocker: MockerFixture) -> None:
        """Workflow handles acknowledge exceptions."""
        # Create mocks
        mock_producer = mocker.AsyncMock(spec=MessageProducer)
        mock_consumer = mocker.AsyncMock(spec=MessageConsumer)

        # Configure consume to return a message
        envelope = MessageEnvelope(
            message_id="msg-789",
            payload=b"data",
            properties={},
            publish_time=datetime.now(UTC),
            topic="test-topic",
        )
        mock_consumer.receive.return_value = envelope

        # Configure acknowledge to raise exception
        mock_consumer.acknowledge.side_effect = RuntimeError("connection timeout")

        interpreter = MessagingInterpreter(producer=mock_producer, consumer=mock_consumer)

        # Define workflow
        def ack_exception_program() -> Generator[AllEffects, EffectResult, str]:
            """Consume message, try to acknowledge, handle error."""
            envelope_result = yield ConsumeMessage(
                subscription="test-sub", timeout_ms=1000
            )
            assert isinstance(envelope_result, MessageEnvelope)

            # This will fail
            yield AcknowledgeMessage(message_id=envelope_result.message_id)
            return "success"

        # Act
        result = await run_ws_program(ack_exception_program(), interpreter)

        # Assert
        match result:
            case Err(error):
                assert isinstance(error, MessagingError)
                assert "connection timeout" in error.messaging_error
                assert error.is_retryable is True
            case Ok(value):
                pytest.fail(f"Expected Err(MessagingError), got Ok({value})")
