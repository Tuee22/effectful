"""Integration tests for messaging workflows with real Pulsar.

This module tests messaging effect workflows using run_ws_program
with real Apache Pulsar infrastructure. Each test uses pulsar_producer
and pulsar_consumer fixtures for real message queue operations.
"""

from collections.abc import Generator
from uuid import uuid4

import pytest
from pytest_mock import MockerFixture

from effectful.adapters.pulsar_messaging import PulsarMessageConsumer, PulsarMessageProducer
from effectful.algebraic.result import Err, Ok
from effectful.domain.message_envelope import ConsumeTimeout, MessageEnvelope
from effectful.effects.messaging import (
    AcknowledgeMessage,
    ConsumeMessage,
    NegativeAcknowledge,
    PublishMessage,
)
from effectful.effects.websocket import SendText
from effectful.infrastructure.cache import ProfileCache
from effectful.infrastructure.repositories import ChatMessageRepository, UserRepository
from effectful.infrastructure.websocket import WebSocketConnection
from effectful.interpreters.composite import create_composite_interpreter
from effectful.programs.program_types import AllEffects, EffectResult
from effectful.programs.runners import run_ws_program

import pulsar


class TestMessagingWorkflowIntegration:
    """Integration tests for messaging workflows with real Pulsar."""

    @pytest.mark.asyncio
    async def test_publish_message_workflow(
        self,
        pulsar_producer: PulsarMessageProducer,
        pulsar_consumer: PulsarMessageConsumer,
        mocker: MockerFixture,
    ) -> None:
        """Workflow publishes message to real Pulsar."""
        topic = f"test-topic-{uuid4()}"
        payload = b'{"event": "test_event"}'

        # Create interpreter with real Pulsar
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
        mock_cache = mocker.AsyncMock(spec=ProfileCache)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=mock_cache,
            message_producer=pulsar_producer,
            message_consumer=pulsar_consumer,
        )

        # Define workflow
        def publish_program(t: str, p: bytes) -> Generator[AllEffects, EffectResult, str]:
            message_id = yield PublishMessage(topic=t, payload=p, properties={"test": "true"})
            assert isinstance(message_id, str)

            yield SendText(text=f"Published: {message_id}")
            return message_id

        # Act
        result = await run_ws_program(publish_program(topic, payload), interpreter)

        # Assert
        match result:
            case Ok(message_id):
                assert message_id is not None
                assert len(message_id) > 0
                mock_ws.send_text.assert_called_once()
            case Err(error):
                pytest.fail(f"Expected Ok, got Err({error})")

    @pytest.mark.asyncio
    async def test_publish_and_consume_workflow(
        self,
        pulsar_producer: PulsarMessageProducer,
        pulsar_consumer: PulsarMessageConsumer,
        mocker: MockerFixture,
    ) -> None:
        """Workflow publishes and consumes message from real Pulsar."""
        topic = f"test-topic-{uuid4()}"
        subscription = f"{topic}/test-sub-{uuid4()}"
        payload = b'{"event": "roundtrip_test"}'

        # Create interpreter
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
        mock_cache = mocker.AsyncMock(spec=ProfileCache)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=mock_cache,
            message_producer=pulsar_producer,
            message_consumer=pulsar_consumer,
        )

        # Define workflow
        def roundtrip_program(
            t: str, sub: str, p: bytes
        ) -> Generator[AllEffects, EffectResult, bool]:
            # Publish message
            message_id = yield PublishMessage(topic=t, payload=p)
            assert isinstance(message_id, str)
            yield SendText(text=f"Published: {message_id}")

            # Consume message
            envelope = yield ConsumeMessage(subscription=sub, timeout_ms=5000)

            match envelope:
                case MessageEnvelope(payload=received_payload, message_id=recv_id):
                    yield SendText(text=f"Received: {recv_id}")

                    # Acknowledge message
                    yield AcknowledgeMessage(message_id=recv_id)
                    yield SendText(text="Acknowledged")

                    # Verify payload
                    return received_payload == p
                case ConsumeTimeout():
                    yield SendText(text="Timeout waiting for message")
                    return False
                case _:
                    return False

        # Act
        result = await run_ws_program(roundtrip_program(topic, subscription, payload), interpreter)

        # Assert
        match result:
            case Ok(success):
                assert success is True
                assert mock_ws.send_text.call_count == 3
                mock_ws.send_text.assert_any_call("Acknowledged")
            case Err(error):
                pytest.fail(f"Expected Ok(True), got Err({error})")

    @pytest.mark.asyncio
    async def test_consume_timeout_workflow(
        self,
        pulsar_producer: PulsarMessageProducer,
        pulsar_consumer: PulsarMessageConsumer,
        mocker: MockerFixture,
    ) -> None:
        """Workflow handles consume timeout gracefully."""
        # Use unique subscription with no messages
        subscription = f"empty-topic-{uuid4()}/test-sub-{uuid4()}"

        # Create interpreter
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
        mock_cache = mocker.AsyncMock(spec=ProfileCache)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=mock_cache,
            message_producer=pulsar_producer,
            message_consumer=pulsar_consumer,
        )

        # Define workflow
        def timeout_program(
            sub: str,
        ) -> Generator[AllEffects, EffectResult, str]:
            envelope = yield ConsumeMessage(subscription=sub, timeout_ms=100)

            match envelope:
                case ConsumeTimeout(subscription=s, timeout_ms=t):
                    yield SendText(text=f"Timeout on {s} after {t}ms")
                    return "timeout"
                case MessageEnvelope():
                    return "received"
                case _:
                    return "error"

        # Act
        result = await run_ws_program(timeout_program(subscription), interpreter)

        # Assert
        match result:
            case Ok(outcome):
                assert outcome == "timeout"
                mock_ws.send_text.assert_called_once()
            case Err(error):
                pytest.fail(f"Expected Ok('timeout'), got Err({error})")

    @pytest.mark.asyncio
    async def test_negative_acknowledge_workflow(
        self,
        pulsar_producer: PulsarMessageProducer,
        pulsar_consumer: PulsarMessageConsumer,
        mocker: MockerFixture,
    ) -> None:
        """Workflow negative acknowledges message for redelivery."""
        topic = f"test-topic-{uuid4()}"
        subscription = f"{topic}/test-sub-{uuid4()}"
        payload = b'{"event": "nack_test"}'

        # Create interpreter
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
        mock_cache = mocker.AsyncMock(spec=ProfileCache)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=mock_cache,
            message_producer=pulsar_producer,
            message_consumer=pulsar_consumer,
        )

        # Define workflow
        def nack_program(t: str, sub: str, p: bytes) -> Generator[AllEffects, EffectResult, bool]:
            # Publish message
            message_id = yield PublishMessage(topic=t, payload=p)
            assert isinstance(message_id, str)

            # Consume message
            envelope = yield ConsumeMessage(subscription=sub, timeout_ms=5000)

            match envelope:
                case MessageEnvelope(message_id=recv_id):
                    # Negative acknowledge for redelivery
                    yield NegativeAcknowledge(message_id=recv_id, delay_ms=0)
                    yield SendText(text=f"Nacked: {recv_id}")
                    return True
                case ConsumeTimeout():
                    yield SendText(text="Timeout")
                    return False
                case _:
                    return False

        # Act
        result = await run_ws_program(nack_program(topic, subscription, payload), interpreter)

        # Assert
        match result:
            case Ok(success):
                assert success is True
                mock_ws.send_text.assert_called()
            case Err(error):
                pytest.fail(f"Expected Ok(True), got Err({error})")

    @pytest.mark.asyncio
    async def test_publish_with_properties_workflow(
        self,
        pulsar_producer: PulsarMessageProducer,
        pulsar_consumer: PulsarMessageConsumer,
        mocker: MockerFixture,
    ) -> None:
        """Workflow publishes and receives message with properties."""
        topic = f"test-topic-{uuid4()}"
        subscription = f"{topic}/test-sub-{uuid4()}"
        payload = b'{"event": "properties_test"}'
        properties = {"source": "integration_test", "version": "1.0"}

        # Create interpreter
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
        mock_cache = mocker.AsyncMock(spec=ProfileCache)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=mock_cache,
            message_producer=pulsar_producer,
            message_consumer=pulsar_consumer,
        )

        # Define workflow
        def properties_program(
            t: str, sub: str, p: bytes, props: dict[str, str]
        ) -> Generator[AllEffects, EffectResult, dict[str, str]]:
            # Publish with properties
            message_id = yield PublishMessage(topic=t, payload=p, properties=props)
            assert isinstance(message_id, str)

            # Consume and check properties
            envelope = yield ConsumeMessage(subscription=sub, timeout_ms=5000)

            match envelope:
                case MessageEnvelope(properties=recv_props, message_id=recv_id):
                    yield AcknowledgeMessage(message_id=recv_id)
                    yield SendText(text=f"Got properties: {recv_props}")
                    return recv_props
                case ConsumeTimeout():
                    return {}
                case _:
                    return {}

        # Act
        result = await run_ws_program(
            properties_program(topic, subscription, payload, properties), interpreter
        )

        # Assert
        match result:
            case Ok(recv_props):
                assert recv_props.get("source") == "integration_test"
                assert recv_props.get("version") == "1.0"
            case Err(error):
                pytest.fail(f"Expected Ok, got Err({error})")

    @pytest.mark.asyncio
    async def test_multi_message_workflow(
        self,
        pulsar_producer: PulsarMessageProducer,
        pulsar_consumer: PulsarMessageConsumer,
        mocker: MockerFixture,
    ) -> None:
        """Workflow publishes and consumes multiple messages."""
        topic = f"test-topic-{uuid4()}"
        subscription = f"{topic}/test-sub-{uuid4()}"
        messages = [f"message-{i}".encode() for i in range(3)]

        # Create interpreter
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
        mock_cache = mocker.AsyncMock(spec=ProfileCache)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=mock_cache,
            message_producer=pulsar_producer,
            message_consumer=pulsar_consumer,
        )

        # Define workflow
        def multi_message_program(
            t: str, sub: str, msgs: list[bytes]
        ) -> Generator[AllEffects, EffectResult, int]:
            # Publish all messages
            for msg in msgs:
                message_id = yield PublishMessage(topic=t, payload=msg)
                assert isinstance(message_id, str)

            # Consume and acknowledge all
            received_count = 0
            for _ in msgs:
                envelope = yield ConsumeMessage(subscription=sub, timeout_ms=5000)

                match envelope:
                    case MessageEnvelope(message_id=recv_id):
                        yield AcknowledgeMessage(message_id=recv_id)
                        received_count += 1
                    case ConsumeTimeout():
                        break
                    case _:
                        break

            yield SendText(text=f"Processed {received_count} messages")
            return received_count

        # Act
        result = await run_ws_program(
            multi_message_program(topic, subscription, messages), interpreter
        )

        # Assert
        match result:
            case Ok(count):
                assert count == 3
                mock_ws.send_text.assert_called_with("Processed 3 messages")
            case Err(error):
                pytest.fail(f"Expected Ok(3), got Err({error})")
