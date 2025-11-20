"""Unit tests for messaging interpreter.

Tests use pytest-mock with spec parameter for type-safe mocking. Tests verify:
- Success cases return Ok with correct values
- Error cases return Err with MessagingError
- Unhandled effects return UnhandledEffectError
- Retryability detection works correctly

Coverage: 100% of messaging interpreter module.
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pytest_mock import MockerFixture

from effectful.algebraic.effect_return import EffectReturn
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
from effectful.effects.websocket import SendText
from effectful.infrastructure.messaging import MessageConsumer, MessageProducer
from effectful.interpreters.errors import MessagingError, UnhandledEffectError
from effectful.interpreters.messaging import MessagingInterpreter


class TestMessagingInterpreterPublish:
    """Tests for PublishMessage effect interpretation."""

    @pytest.mark.asyncio()
    async def test_publish_success(self, mocker: MockerFixture) -> None:
        """PublishMessage with success should return Ok with message_id."""
        # Setup mock
        mock_producer = mocker.AsyncMock(spec=MessageProducer)
        mock_producer.publish.return_value = PublishSuccess(
            message_id="msg-123", topic="test-topic"
        )
        mock_consumer = mocker.AsyncMock(spec=MessageConsumer)

        interpreter = MessagingInterpreter(producer=mock_producer, consumer=mock_consumer)

        # Execute
        effect = PublishMessage(topic="test-topic", payload=b"test data")
        result = await interpreter.interpret(effect)

        # Verify
        match result:
            case Ok(EffectReturn(value=message_id, effect_name="PublishMessage")):
                assert message_id == "msg-123"
            case _:
                pytest.fail(f"Expected Ok with message_id, got {result}")

        # Verify mock calls
        mock_producer.publish.assert_called_once_with("test-topic", b"test data", None)

    @pytest.mark.asyncio()
    async def test_publish_with_properties(self, mocker: MockerFixture) -> None:
        """PublishMessage with properties should pass them to producer."""
        mock_producer = mocker.AsyncMock(spec=MessageProducer)
        mock_producer.publish.return_value = PublishSuccess(
            message_id="msg-456", topic="events"
        )
        mock_consumer = mocker.AsyncMock(spec=MessageConsumer)

        interpreter = MessagingInterpreter(producer=mock_producer, consumer=mock_consumer)

        effect = PublishMessage(
            topic="events",
            payload=b"data",
            properties={"key": "value"},
        )
        result = await interpreter.interpret(effect)

        # Verify properties passed correctly
        mock_producer.publish.assert_called_once_with(
            "events", b"data", {"key": "value"}
        )

    @pytest.mark.asyncio()
    async def test_publish_failure_timeout(self, mocker: MockerFixture) -> None:
        """PublishMessage with timeout failure should return Err with MessagingError."""
        mock_producer = mocker.AsyncMock(spec=MessageProducer)
        mock_producer.publish.return_value = PublishFailure(
            topic="test-topic", reason="timeout"
        )
        mock_consumer = mocker.AsyncMock(spec=MessageConsumer)

        interpreter = MessagingInterpreter(producer=mock_producer, consumer=mock_consumer)

        effect = PublishMessage(topic="test-topic", payload=b"data")
        result = await interpreter.interpret(effect)

        # Verify error with retryability
        match result:
            case Err(MessagingError(messaging_error=msg, is_retryable=True)):
                assert "timeout" in msg
            case _:
                pytest.fail(f"Expected Err(MessagingError), got {result}")

    @pytest.mark.asyncio()
    async def test_publish_failure_quota_exceeded(self, mocker: MockerFixture) -> None:
        """PublishMessage with quota exceeded should return retryable error."""
        mock_producer = mocker.AsyncMock(spec=MessageProducer)
        mock_producer.publish.return_value = PublishFailure(
            topic="test-topic", reason="quota_exceeded"
        )
        mock_consumer = mocker.AsyncMock(spec=MessageConsumer)

        interpreter = MessagingInterpreter(producer=mock_producer, consumer=mock_consumer)

        effect = PublishMessage(topic="test-topic", payload=b"data")
        result = await interpreter.interpret(effect)

        match result:
            case Err(MessagingError(messaging_error=msg, is_retryable=True)):
                assert "quota_exceeded" in msg
            case _:
                pytest.fail(f"Expected retryable error, got {result}")

    @pytest.mark.asyncio()
    async def test_publish_failure_topic_not_found(self, mocker: MockerFixture) -> None:
        """PublishMessage with topic not found should return non-retryable error."""
        mock_producer = mocker.AsyncMock(spec=MessageProducer)
        mock_producer.publish.return_value = PublishFailure(
            topic="test-topic", reason="topic_not_found"
        )
        mock_consumer = mocker.AsyncMock(spec=MessageConsumer)

        interpreter = MessagingInterpreter(producer=mock_producer, consumer=mock_consumer)

        effect = PublishMessage(topic="test-topic", payload=b"data")
        result = await interpreter.interpret(effect)

        match result:
            case Err(MessagingError(messaging_error=msg, is_retryable=False)):
                assert "topic_not_found" in msg
            case _:
                pytest.fail(f"Expected non-retryable error, got {result}")

    @pytest.mark.asyncio()
    async def test_publish_exception_retryable(self, mocker: MockerFixture) -> None:
        """PublishMessage with connection exception should be retryable."""
        mock_producer = mocker.AsyncMock(spec=MessageProducer)
        mock_producer.publish.side_effect = RuntimeError("connection timeout")
        mock_consumer = mocker.AsyncMock(spec=MessageConsumer)

        interpreter = MessagingInterpreter(producer=mock_producer, consumer=mock_consumer)

        effect = PublishMessage(topic="test-topic", payload=b"data")
        result = await interpreter.interpret(effect)

        match result:
            case Err(MessagingError(messaging_error=msg, is_retryable=True)):
                assert "connection timeout" in msg
            case _:
                pytest.fail(f"Expected retryable error, got {result}")

    @pytest.mark.asyncio()
    async def test_publish_exception_non_retryable(self, mocker: MockerFixture) -> None:
        """PublishMessage with config exception should not be retryable."""
        mock_producer = mocker.AsyncMock(spec=MessageProducer)
        mock_producer.publish.side_effect = RuntimeError("invalid configuration")
        mock_consumer = mocker.AsyncMock(spec=MessageConsumer)

        interpreter = MessagingInterpreter(producer=mock_producer, consumer=mock_consumer)

        effect = PublishMessage(topic="test-topic", payload=b"data")
        result = await interpreter.interpret(effect)

        match result:
            case Err(MessagingError(messaging_error=msg, is_retryable=False)):
                assert "invalid configuration" in msg
            case _:
                pytest.fail(f"Expected non-retryable error, got {result}")


class TestMessagingInterpreterConsume:
    """Tests for ConsumeMessage effect interpretation."""

    @pytest.mark.asyncio()
    async def test_consume_success(self, mocker: MockerFixture) -> None:
        """ConsumeMessage with message should return Ok with MessageEnvelope."""
        # Setup mock
        envelope = MessageEnvelope(
            message_id="msg-789",
            payload=b"test message",
            properties={"key": "value"},
            publish_time=datetime.now(UTC),
            topic="test-topic",
        )

        mock_producer = mocker.AsyncMock(spec=MessageProducer)
        mock_consumer = mocker.AsyncMock(spec=MessageConsumer)
        mock_consumer.receive.return_value = envelope

        interpreter = MessagingInterpreter(producer=mock_producer, consumer=mock_consumer)

        # Execute
        effect = ConsumeMessage(subscription="test-sub", timeout_ms=1000)
        result = await interpreter.interpret(effect)

        # Verify
        match result:
            case Ok(EffectReturn(value=received_envelope, effect_name="ConsumeMessage")):
                assert received_envelope == envelope
            case _:
                pytest.fail(f"Expected Ok with MessageEnvelope, got {result}")

        # Verify mock calls
        mock_consumer.receive.assert_called_once_with("test-sub", 1000)

    @pytest.mark.asyncio()
    async def test_consume_timeout(self, mocker: MockerFixture) -> None:
        """ConsumeMessage with timeout should return Ok with None."""
        mock_producer = mocker.AsyncMock(spec=MessageProducer)
        mock_consumer = mocker.AsyncMock(spec=MessageConsumer)
        mock_consumer.receive.return_value = None  # Timeout

        interpreter = MessagingInterpreter(producer=mock_producer, consumer=mock_consumer)

        effect = ConsumeMessage(subscription="test-sub", timeout_ms=1000)
        result = await interpreter.interpret(effect)

        # Verify - timeout is OK, not an error
        match result:
            case Ok(EffectReturn(value=None, effect_name="ConsumeMessage")):
                assert True  # Expected
            case _:
                pytest.fail(f"Expected Ok with None (timeout), got {result}")

    @pytest.mark.asyncio()
    async def test_consume_exception(self, mocker: MockerFixture) -> None:
        """ConsumeMessage with exception should return Err."""
        mock_producer = mocker.AsyncMock(spec=MessageProducer)
        mock_consumer = mocker.AsyncMock(spec=MessageConsumer)
        mock_consumer.receive.side_effect = RuntimeError("connection unavailable")

        interpreter = MessagingInterpreter(producer=mock_producer, consumer=mock_consumer)

        effect = ConsumeMessage(subscription="test-sub", timeout_ms=1000)
        result = await interpreter.interpret(effect)

        match result:
            case Err(MessagingError(messaging_error=msg, is_retryable=True)):
                assert "connection unavailable" in msg
            case _:
                pytest.fail(f"Expected Err(MessagingError), got {result}")


class TestMessagingInterpreterAcknowledge:
    """Tests for AcknowledgeMessage effect interpretation."""

    @pytest.mark.asyncio()
    async def test_acknowledge_success(self, mocker: MockerFixture) -> None:
        """AcknowledgeMessage should return Ok with None."""
        mock_producer = mocker.AsyncMock(spec=MessageProducer)
        mock_consumer = mocker.AsyncMock(spec=MessageConsumer)

        interpreter = MessagingInterpreter(producer=mock_producer, consumer=mock_consumer)

        effect = AcknowledgeMessage(message_id="msg-123")
        result = await interpreter.interpret(effect)

        # Verify
        match result:
            case Ok(EffectReturn(value=None, effect_name="AcknowledgeMessage")):
                assert True  # Expected
            case _:
                pytest.fail(f"Expected Ok with None, got {result}")

        # Verify mock calls
        mock_consumer.acknowledge.assert_called_once_with("msg-123")

    @pytest.mark.asyncio()
    async def test_acknowledge_exception(self, mocker: MockerFixture) -> None:
        """AcknowledgeMessage with exception should return Err."""
        mock_producer = mocker.AsyncMock(spec=MessageProducer)
        mock_consumer = mocker.AsyncMock(spec=MessageConsumer)
        mock_consumer.acknowledge.side_effect = RuntimeError("connection timeout")

        interpreter = MessagingInterpreter(producer=mock_producer, consumer=mock_consumer)

        effect = AcknowledgeMessage(message_id="msg-123")
        result = await interpreter.interpret(effect)

        match result:
            case Err(MessagingError(messaging_error=msg, is_retryable=True)):
                assert "connection timeout" in msg
            case _:
                pytest.fail(f"Expected Err(MessagingError), got {result}")


class TestMessagingInterpreterNegativeAcknowledge:
    """Tests for NegativeAcknowledge effect interpretation."""

    @pytest.mark.asyncio()
    async def test_negative_acknowledge_success(self, mocker: MockerFixture) -> None:
        """NegativeAcknowledge should return Ok with None."""
        mock_producer = mocker.AsyncMock(spec=MessageProducer)
        mock_consumer = mocker.AsyncMock(spec=MessageConsumer)

        interpreter = MessagingInterpreter(producer=mock_producer, consumer=mock_consumer)

        effect = NegativeAcknowledge(message_id="msg-456", delay_ms=1000)
        result = await interpreter.interpret(effect)

        # Verify
        match result:
            case Ok(EffectReturn(value=None, effect_name="NegativeAcknowledge")):
                assert True  # Expected
            case _:
                pytest.fail(f"Expected Ok with None, got {result}")

        # Verify mock calls
        mock_consumer.negative_acknowledge.assert_called_once_with("msg-456", 1000)

    @pytest.mark.asyncio()
    async def test_negative_acknowledge_exception(self, mocker: MockerFixture) -> None:
        """NegativeAcknowledge with exception should return Err."""
        mock_producer = mocker.AsyncMock(spec=MessageProducer)
        mock_consumer = mocker.AsyncMock(spec=MessageConsumer)
        mock_consumer.negative_acknowledge.side_effect = RuntimeError("backpressure")

        interpreter = MessagingInterpreter(producer=mock_producer, consumer=mock_consumer)

        effect = NegativeAcknowledge(message_id="msg-456", delay_ms=1000)
        result = await interpreter.interpret(effect)

        match result:
            case Err(MessagingError(messaging_error=msg, is_retryable=True)):
                assert "backpressure" in msg
            case _:
                pytest.fail(f"Expected Err(MessagingError), got {result}")


class TestMessagingInterpreterUnhandled:
    """Tests for unhandled effects."""

    @pytest.mark.asyncio()
    async def test_unhandled_effect(self, mocker: MockerFixture) -> None:
        """Non-messaging effects should return UnhandledEffectError."""
        mock_producer = mocker.AsyncMock(spec=MessageProducer)
        mock_consumer = mocker.AsyncMock(spec=MessageConsumer)

        interpreter = MessagingInterpreter(producer=mock_producer, consumer=mock_consumer)

        # Try to interpret a WebSocket effect
        effect = SendText(text="Hello")
        result = await interpreter.interpret(effect)

        # Verify
        match result:
            case Err(
                UnhandledEffectError(
                    effect=unhandled_effect, available_interpreters=interpreters
                )
            ):
                assert unhandled_effect == effect
                assert "MessagingInterpreter" in interpreters
            case _:
                pytest.fail(f"Expected Err(UnhandledEffectError), got {result}")


class TestMessagingInterpreterRetryability:
    """Tests for retryability detection logic."""

    def test_retryable_connection_error(self, mocker: MockerFixture) -> None:
        """Connection errors should be retryable."""
        mock_producer = mocker.AsyncMock(spec=MessageProducer)
        mock_consumer = mocker.AsyncMock(spec=MessageConsumer)

        interpreter = MessagingInterpreter(
            producer=mock_producer, consumer=mock_consumer
        )

        error = RuntimeError("connection refused")
        assert interpreter._is_retryable_error(error) is True

    def test_retryable_timeout_error(self, mocker: MockerFixture) -> None:
        """Timeout errors should be retryable."""
        mock_producer = mocker.AsyncMock(spec=MessageProducer)
        mock_consumer = mocker.AsyncMock(spec=MessageConsumer)

        interpreter = MessagingInterpreter(
            producer=mock_producer, consumer=mock_consumer
        )

        error = RuntimeError("request timeout")
        assert interpreter._is_retryable_error(error) is True

    def test_retryable_unavailable_error(self, mocker: MockerFixture) -> None:
        """Unavailable errors should be retryable."""
        mock_producer = mocker.AsyncMock(spec=MessageProducer)
        mock_consumer = mocker.AsyncMock(spec=MessageConsumer)

        interpreter = MessagingInterpreter(
            producer=mock_producer, consumer=mock_consumer
        )

        error = RuntimeError("service unavailable")
        assert interpreter._is_retryable_error(error) is True

    def test_retryable_backpressure_error(self, mocker: MockerFixture) -> None:
        """Backpressure errors should be retryable."""
        mock_producer = mocker.AsyncMock(spec=MessageProducer)
        mock_consumer = mocker.AsyncMock(spec=MessageConsumer)

        interpreter = MessagingInterpreter(
            producer=mock_producer, consumer=mock_consumer
        )

        error = RuntimeError("backpressure limit exceeded")
        assert interpreter._is_retryable_error(error) is True

    def test_non_retryable_config_error(self, mocker: MockerFixture) -> None:
        """Configuration errors should not be retryable."""
        mock_producer = mocker.AsyncMock(spec=MessageProducer)
        mock_consumer = mocker.AsyncMock(spec=MessageConsumer)

        interpreter = MessagingInterpreter(
            producer=mock_producer, consumer=mock_consumer
        )

        error = RuntimeError("invalid configuration")
        assert interpreter._is_retryable_error(error) is False

    def test_non_retryable_auth_error(self, mocker: MockerFixture) -> None:
        """Authentication errors should not be retryable."""
        mock_producer = mocker.AsyncMock(spec=MessageProducer)
        mock_consumer = mocker.AsyncMock(spec=MessageConsumer)

        interpreter = MessagingInterpreter(
            producer=mock_producer, consumer=mock_consumer
        )

        error = RuntimeError("authentication failed")
        assert interpreter._is_retryable_error(error) is False
