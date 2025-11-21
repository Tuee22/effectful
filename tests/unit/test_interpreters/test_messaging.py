"""Tests for Messaging interpreter.

This module tests the MessagingInterpreter using pytest mocks (via pytest-mock).
Tests cover:
- Message publishing (success, domain failures, infrastructure errors)
- Message consumption (success, timeout, errors)
- Message acknowledgment (success, errors)
- Negative acknowledgment (success, errors)
- Unhandled effects
- Immutability
- Retryable error detection
"""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

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


class TestPublishMessage:
    """Tests for PublishMessage effect handling."""

    @pytest.mark.asyncio()
    async def test_publish_message_success(self, mocker: MockerFixture) -> None:
        """Interpreter should return message_id on successful publish."""
        # Setup
        mock_producer = mocker.AsyncMock(spec=MessageProducer)
        mock_producer.publish.return_value = PublishSuccess(message_id="msg-123", topic="events")
        mock_consumer = mocker.AsyncMock(spec=MessageConsumer)

        interpreter = MessagingInterpreter(producer=mock_producer, consumer=mock_consumer)

        effect = PublishMessage(
            topic="events", payload=b'{"event": "test"}', properties={"source": "test"}
        )
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Ok(EffectReturn(value="msg-123", effect_name="PublishMessage")):
                pass  # Success
            case _:
                pytest.fail(f"Expected Ok with message_id, got {result}")

        # Verify mock was called correctly
        mock_producer.publish.assert_called_once_with(
            "events", b'{"event": "test"}', {"source": "test"}
        )

    @pytest.mark.asyncio()
    async def test_publish_message_timeout_failure(self, mocker: MockerFixture) -> None:
        """Interpreter should return MessagingError on publish timeout."""
        # Setup
        mock_producer = mocker.AsyncMock(spec=MessageProducer)
        mock_producer.publish.return_value = PublishFailure(topic="events", reason="timeout")
        mock_consumer = mocker.AsyncMock(spec=MessageConsumer)

        interpreter = MessagingInterpreter(producer=mock_producer, consumer=mock_consumer)

        effect = PublishMessage(topic="events", payload=b"data")
        result = await interpreter.interpret(effect)

        # Verify result - timeout is retryable
        match result:
            case Err(MessagingError(effect=e, messaging_error=err_msg, is_retryable=True)):
                assert e == effect
                assert "timeout" in err_msg
            case _:
                pytest.fail(f"Expected MessagingError with retryable=True, got {result}")

    @pytest.mark.asyncio()
    async def test_publish_message_quota_exceeded_failure(self, mocker: MockerFixture) -> None:
        """Interpreter should return MessagingError on quota exceeded."""
        # Setup
        mock_producer = mocker.AsyncMock(spec=MessageProducer)
        mock_producer.publish.return_value = PublishFailure(topic="events", reason="quota_exceeded")
        mock_consumer = mocker.AsyncMock(spec=MessageConsumer)

        interpreter = MessagingInterpreter(producer=mock_producer, consumer=mock_consumer)

        effect = PublishMessage(topic="events", payload=b"data")
        result = await interpreter.interpret(effect)

        # Verify result - quota_exceeded is retryable
        match result:
            case Err(MessagingError(effect=e, messaging_error=err_msg, is_retryable=True)):
                assert e == effect
                assert "quota_exceeded" in err_msg
            case _:
                pytest.fail(f"Expected MessagingError with retryable=True, got {result}")

    @pytest.mark.asyncio()
    async def test_publish_message_topic_not_found_failure(self, mocker: MockerFixture) -> None:
        """Interpreter should return MessagingError on topic not found."""
        # Setup
        mock_producer = mocker.AsyncMock(spec=MessageProducer)
        mock_producer.publish.return_value = PublishFailure(
            topic="events", reason="topic_not_found"
        )
        mock_consumer = mocker.AsyncMock(spec=MessageConsumer)

        interpreter = MessagingInterpreter(producer=mock_producer, consumer=mock_consumer)

        effect = PublishMessage(topic="events", payload=b"data")
        result = await interpreter.interpret(effect)

        # Verify result - topic_not_found is NOT retryable
        match result:
            case Err(MessagingError(effect=e, messaging_error=err_msg, is_retryable=False)):
                assert e == effect
                assert "topic_not_found" in err_msg
            case _:
                pytest.fail(f"Expected MessagingError with retryable=False, got {result}")

    @pytest.mark.asyncio()
    async def test_publish_message_infrastructure_error(self, mocker: MockerFixture) -> None:
        """Interpreter should return MessagingError on infrastructure failure."""
        # Setup
        mock_producer = mocker.AsyncMock(spec=MessageProducer)
        mock_producer.publish.side_effect = Exception("Connection timeout")
        mock_consumer = mocker.AsyncMock(spec=MessageConsumer)

        interpreter = MessagingInterpreter(producer=mock_producer, consumer=mock_consumer)

        effect = PublishMessage(topic="events", payload=b"data")
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Err(
                MessagingError(effect=e, messaging_error="Connection timeout", is_retryable=True)
            ):
                assert e == effect
            case _:
                pytest.fail(f"Expected MessagingError, got {result}")

    @pytest.mark.asyncio()
    async def test_publish_message_with_none_properties(self, mocker: MockerFixture) -> None:
        """Interpreter should handle None properties correctly."""
        # Setup
        mock_producer = mocker.AsyncMock(spec=MessageProducer)
        mock_producer.publish.return_value = PublishSuccess(message_id="msg-456", topic="events")
        mock_consumer = mocker.AsyncMock(spec=MessageConsumer)

        interpreter = MessagingInterpreter(producer=mock_producer, consumer=mock_consumer)

        effect = PublishMessage(topic="events", payload=b"data", properties=None)
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Ok(EffectReturn(value="msg-456", effect_name="PublishMessage")):
                pass  # Success
            case _:
                pytest.fail(f"Expected Ok, got {result}")

        # Verify mock was called with None
        mock_producer.publish.assert_called_once_with("events", b"data", None)


class TestConsumeMessage:
    """Tests for ConsumeMessage effect handling."""

    @pytest.mark.asyncio()
    async def test_consume_message_success(self, mocker: MockerFixture) -> None:
        """Interpreter should return MessageEnvelope on successful receive."""
        # Setup
        envelope = MessageEnvelope(
            message_id="msg-789",
            payload=b'{"event": "user_login"}',
            properties={"source": "web"},
            publish_time=datetime.now(UTC),
            topic="user-events",
        )
        mock_producer = mocker.AsyncMock(spec=MessageProducer)
        mock_consumer = mocker.AsyncMock(spec=MessageConsumer)
        mock_consumer.receive.return_value = envelope

        interpreter = MessagingInterpreter(producer=mock_producer, consumer=mock_consumer)

        effect = ConsumeMessage(subscription="my-sub", timeout_ms=5000)
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Ok(EffectReturn(value=msg, effect_name="ConsumeMessage")):
                assert msg == envelope
            case _:
                pytest.fail(f"Expected Ok with MessageEnvelope, got {result}")

        # Verify mock was called correctly
        mock_consumer.receive.assert_called_once_with("my-sub", 5000)

    @pytest.mark.asyncio()
    async def test_consume_message_timeout(self, mocker: MockerFixture) -> None:
        """Interpreter should return None on timeout (no messages available)."""
        # Setup
        mock_producer = mocker.AsyncMock(spec=MessageProducer)
        mock_consumer = mocker.AsyncMock(spec=MessageConsumer)
        mock_consumer.receive.return_value = None

        interpreter = MessagingInterpreter(producer=mock_producer, consumer=mock_consumer)

        effect = ConsumeMessage(subscription="my-sub", timeout_ms=1000)
        result = await interpreter.interpret(effect)

        # Verify result - timeout returns None (not an error)
        match result:
            case Ok(EffectReturn(value=None, effect_name="ConsumeMessage")):
                pass  # Success
            case _:
                pytest.fail(f"Expected Ok with None, got {result}")

        # Verify mock was called correctly
        mock_consumer.receive.assert_called_once_with("my-sub", 1000)

    @pytest.mark.asyncio()
    async def test_consume_message_infrastructure_error(self, mocker: MockerFixture) -> None:
        """Interpreter should return MessagingError on infrastructure failure."""
        # Setup
        mock_producer = mocker.AsyncMock(spec=MessageProducer)
        mock_consumer = mocker.AsyncMock(spec=MessageConsumer)
        mock_consumer.receive.side_effect = Exception("Broker unavailable")

        interpreter = MessagingInterpreter(producer=mock_producer, consumer=mock_consumer)

        effect = ConsumeMessage(subscription="my-sub", timeout_ms=5000)
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Err(
                MessagingError(effect=e, messaging_error="Broker unavailable", is_retryable=True)
            ):
                assert e == effect
            case _:
                pytest.fail(f"Expected MessagingError, got {result}")


class TestAcknowledgeMessage:
    """Tests for AcknowledgeMessage effect handling."""

    @pytest.mark.asyncio()
    async def test_acknowledge_message_success(self, mocker: MockerFixture) -> None:
        """Interpreter should return None on successful acknowledgment."""
        # Setup
        mock_producer = mocker.AsyncMock(spec=MessageProducer)
        mock_consumer = mocker.AsyncMock(spec=MessageConsumer)

        interpreter = MessagingInterpreter(producer=mock_producer, consumer=mock_consumer)

        effect = AcknowledgeMessage(message_id="msg-123")
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Ok(EffectReturn(value=None, effect_name="AcknowledgeMessage")):
                pass  # Success
            case _:
                pytest.fail(f"Expected Ok with None, got {result}")

        # Verify mock was called correctly
        mock_consumer.acknowledge.assert_called_once_with("msg-123")

    @pytest.mark.asyncio()
    async def test_acknowledge_message_infrastructure_error(self, mocker: MockerFixture) -> None:
        """Interpreter should return MessagingError on infrastructure failure."""
        # Setup
        mock_producer = mocker.AsyncMock(spec=MessageProducer)
        mock_consumer = mocker.AsyncMock(spec=MessageConsumer)
        mock_consumer.acknowledge.side_effect = Exception("Connection timeout")

        interpreter = MessagingInterpreter(producer=mock_producer, consumer=mock_consumer)

        effect = AcknowledgeMessage(message_id="msg-123")
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Err(
                MessagingError(effect=e, messaging_error="Connection timeout", is_retryable=True)
            ):
                assert e == effect
            case _:
                pytest.fail(f"Expected MessagingError, got {result}")


class TestNegativeAcknowledge:
    """Tests for NegativeAcknowledge effect handling."""

    @pytest.mark.asyncio()
    async def test_negative_acknowledge_success(self, mocker: MockerFixture) -> None:
        """Interpreter should return None on successful nack."""
        # Setup
        mock_producer = mocker.AsyncMock(spec=MessageProducer)
        mock_consumer = mocker.AsyncMock(spec=MessageConsumer)

        interpreter = MessagingInterpreter(producer=mock_producer, consumer=mock_consumer)

        effect = NegativeAcknowledge(message_id="msg-456", delay_ms=1000)
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Ok(EffectReturn(value=None, effect_name="NegativeAcknowledge")):
                pass  # Success
            case _:
                pytest.fail(f"Expected Ok with None, got {result}")

        # Verify mock was called correctly
        mock_consumer.negative_acknowledge.assert_called_once_with("msg-456", 1000)

    @pytest.mark.asyncio()
    async def test_negative_acknowledge_with_zero_delay(self, mocker: MockerFixture) -> None:
        """Interpreter should handle zero delay for immediate redelivery."""
        # Setup
        mock_producer = mocker.AsyncMock(spec=MessageProducer)
        mock_consumer = mocker.AsyncMock(spec=MessageConsumer)

        interpreter = MessagingInterpreter(producer=mock_producer, consumer=mock_consumer)

        effect = NegativeAcknowledge(message_id="msg-789", delay_ms=0)
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Ok(EffectReturn(value=None, effect_name="NegativeAcknowledge")):
                pass  # Success
            case _:
                pytest.fail(f"Expected Ok with None, got {result}")

        # Verify mock was called with zero delay
        mock_consumer.negative_acknowledge.assert_called_once_with("msg-789", 0)

    @pytest.mark.asyncio()
    async def test_negative_acknowledge_infrastructure_error(self, mocker: MockerFixture) -> None:
        """Interpreter should return MessagingError on infrastructure failure."""
        # Setup
        mock_producer = mocker.AsyncMock(spec=MessageProducer)
        mock_consumer = mocker.AsyncMock(spec=MessageConsumer)
        mock_consumer.negative_acknowledge.side_effect = Exception("Backpressure error")

        interpreter = MessagingInterpreter(producer=mock_producer, consumer=mock_consumer)

        effect = NegativeAcknowledge(message_id="msg-456", delay_ms=1000)
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Err(
                MessagingError(effect=e, messaging_error="Backpressure error", is_retryable=True)
            ):
                assert e == effect
            case _:
                pytest.fail(f"Expected MessagingError, got {result}")


class TestUnhandledEffect:
    """Tests for unhandled effect handling."""

    @pytest.mark.asyncio()
    async def test_unhandled_effect(self, mocker: MockerFixture) -> None:
        """Interpreter should return UnhandledEffectError for non-Messaging effects."""
        # Setup
        mock_producer = mocker.AsyncMock(spec=MessageProducer)
        mock_consumer = mocker.AsyncMock(spec=MessageConsumer)

        interpreter = MessagingInterpreter(producer=mock_producer, consumer=mock_consumer)

        effect = SendText(text="hello")
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Err(
                UnhandledEffectError(effect=e, available_interpreters=["MessagingInterpreter"])
            ):
                assert e == effect
            case _:
                pytest.fail(f"Expected UnhandledEffectError, got {result}")

        # Verify no messaging methods were called
        mock_producer.publish.assert_not_called()
        mock_consumer.receive.assert_not_called()
        mock_consumer.acknowledge.assert_not_called()
        mock_consumer.negative_acknowledge.assert_not_called()


class TestMessagingInterpreterImmutability:
    """Tests for MessagingInterpreter immutability."""

    def test_interpreter_is_immutable(self, mocker: MockerFixture) -> None:
        """MessagingInterpreter should be frozen."""
        mock_producer = mocker.AsyncMock(spec=MessageProducer)
        mock_consumer = mocker.AsyncMock(spec=MessageConsumer)
        interpreter = MessagingInterpreter(producer=mock_producer, consumer=mock_consumer)

        with pytest.raises(FrozenInstanceError):
            interpreter.producer = mocker.AsyncMock(spec=MessageProducer)  # type: ignore[misc]

        with pytest.raises(FrozenInstanceError):
            interpreter.consumer = mocker.AsyncMock(spec=MessageConsumer)  # type: ignore[misc]


class TestIsRetryableError:
    """Tests for _is_retryable_error helper method."""

    def test_detects_retryable_patterns(self, mocker: MockerFixture) -> None:
        """_is_retryable_error should detect retryable error patterns."""
        mock_producer = mocker.AsyncMock(spec=MessageProducer)
        mock_consumer = mocker.AsyncMock(spec=MessageConsumer)
        interpreter = MessagingInterpreter(producer=mock_producer, consumer=mock_consumer)

        assert interpreter._is_retryable_error(Exception("Connection timeout"))
        assert interpreter._is_retryable_error(Exception("connection refused"))
        assert interpreter._is_retryable_error(Exception("Broker unavailable"))
        assert interpreter._is_retryable_error(Exception("Backpressure detected"))

    def test_detects_non_retryable_patterns(self, mocker: MockerFixture) -> None:
        """_is_retryable_error should detect non-retryable error patterns."""
        mock_producer = mocker.AsyncMock(spec=MessageProducer)
        mock_consumer = mocker.AsyncMock(spec=MessageConsumer)
        interpreter = MessagingInterpreter(producer=mock_producer, consumer=mock_consumer)

        assert not interpreter._is_retryable_error(Exception("Invalid topic name"))
        assert not interpreter._is_retryable_error(Exception("Authentication failed"))
        assert not interpreter._is_retryable_error(Exception("Unknown error"))
