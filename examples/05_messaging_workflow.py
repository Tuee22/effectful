"""Example 05: Messaging Workflow

Effect program demonstrating publish/subscribe messaging with Apache Pulsar.

Run:
    python -m examples.05_messaging_workflow
"""

import asyncio
from collections.abc import Generator
from datetime import UTC, datetime

from effectful.algebraic.result import Err, Ok
from effectful.domain.message_envelope import ConsumeTimeout, MessageEnvelope
from effectful.effects.messaging import (
    AcknowledgeMessage,
    ConsumeMessage,
    NegativeAcknowledge,
    PublishMessage,
)
from effectful.interpreters.messaging import MessagingInterpreter
from effectful.programs.program_types import AllEffects, EffectResult
from effectful.programs.runners import run_ws_program
from effectful.testing.fakes import FakeMessageConsumer, FakeMessageProducer


def publish_events(events: list[str]) -> Generator[AllEffects, EffectResult, int]:
    """Publish multiple events to a topic.

    Flow:
    1. Publish each event to the "events" topic
    2. Track published message IDs
    3. Return count of successfully published messages

    Args:
        events: List of event messages to publish

    Yields:
        PublishMessage effects

    Returns:
        Count of successfully published messages
    """
    published_count = 0

    for event in events:
        # Publish event
        message_id = yield PublishMessage(
            topic="events", payload=event.encode("utf-8"), properties={"type": "event"}
        )
        assert isinstance(message_id, str)

        print(f"  ✓ Published event: {event} (ID: {message_id})")
        published_count += 1

    return published_count


def consume_and_process() -> Generator[AllEffects, EffectResult, str]:
    """Consume message and process it with acknowledgment.

    Flow:
    1. Consume message from subscription
    2. Process message payload
    3. Acknowledge successful processing or negative acknowledge on failure

    Yields:
        ConsumeMessage, AcknowledgeMessage, NegativeAcknowledge effects

    Returns:
        Processing status ("success" | "timeout" | "failed")
    """
    # Try to consume message
    envelope = yield ConsumeMessage(subscription="test-subscription", timeout_ms=1000)

    match envelope:
        case ConsumeTimeout():
            # Timeout - no message available
            print("  ⏱ No message available (timeout)")
            return "timeout"

        case MessageEnvelope(message_id=msg_id, payload=payload, properties=props):
            # Message received - try to process
            print(f"  → Received message: {msg_id}")
            print(f"    Payload: {payload.decode('utf-8')}")
            print(f"    Properties: {props}")

            # Simulate processing
            try:
                text = payload.decode("utf-8")

                # Simulate failure for "invalid" messages
                if "invalid" in text.lower():
                    print(f"  ✗ Processing failed - negative acknowledging with delay")
                    yield NegativeAcknowledge(message_id=msg_id, delay_ms=5000)
                    return "failed"

                # Success - acknowledge
                print(f"  ✓ Processing succeeded - acknowledging")
                yield AcknowledgeMessage(message_id=msg_id)
                return "success"

            except Exception as e:
                # Processing error - negative acknowledge
                print(f"  ✗ Processing error: {e}")
                yield NegativeAcknowledge(message_id=msg_id, delay_ms=1000)
                return "failed"

        case unexpected:
            raise AssertionError(f"Unexpected type: {type(unexpected)}")


def pubsub_workflow(messages: list[str]) -> Generator[AllEffects, EffectResult, dict[str, int]]:
    """Complete publish/subscribe workflow.

    Flow:
    1. Publish messages to topic
    2. Consume and process messages from subscription
    3. Track acknowledgments

    Args:
        messages: List of messages to publish and process

    Yields:
        PublishMessage, ConsumeMessage, AcknowledgeMessage effects

    Returns:
        Dictionary with counts: {"published": int, "acked": int, "nacked": int}
    """
    stats = {"published": 0, "acked": 0, "nacked": 0}

    # Phase 1: Publish messages
    print("Phase 1: Publishing messages...")
    published_count = yield from publish_events(messages)
    stats["published"] = published_count

    print(f"\n✓ Published {published_count} messages\n")

    # Phase 2: Consume and process messages
    print("Phase 2: Consuming and processing messages...")
    for _ in range(len(messages)):
        status = yield from consume_and_process()

        match status:
            case "success":
                stats["acked"] += 1
            case "failed":
                stats["nacked"] += 1
            case "timeout":
                break  # No more messages

    return stats


async def main() -> None:
    """Run the messaging workflow program."""
    # Setup fake messaging infrastructure
    fake_producer = FakeMessageProducer()
    fake_consumer = FakeMessageConsumer()

    # Pre-populate consumer queue with messages for demonstration
    messages = [
        "User logged in",
        "Order created",
        "Payment processed",
        "Invalid event",  # This will be nacked
    ]

    # Create message envelopes in consumer queue
    for i, msg in enumerate(messages):
        envelope = MessageEnvelope(
            message_id=f"msg-{i+1}",
            payload=msg.encode("utf-8"),
            properties={"type": "event", "index": str(i)},
            publish_time=datetime.now(UTC),
            topic="events",
        )
        fake_consumer._messages.append(envelope)

    # Create interpreter
    interpreter = MessagingInterpreter(producer=fake_producer, consumer=fake_consumer)

    print("Running messaging workflow...\n")

    # Run publish workflow
    print("=== Publishing Events ===")
    events_to_publish = ["User registered", "Email sent", "Profile updated"]
    result1 = await run_ws_program(publish_events(events_to_publish), interpreter)

    match result1:
        case Ok(count):
            print(f"\n✓ Successfully published {count} events")
        case Err(error):
            print(f"\n✗ Error publishing: {error}")

    # Show producer state
    print(f"\n=== Producer State ===")
    print(f"Published messages: {len(fake_producer._published)}")
    for topic, payload, props in fake_producer._published:
        print(f"  - Topic: {topic}")
        print(f"    Payload: {payload.decode('utf-8')}")
        print(f"    Properties: {props}")

    # Run consume and process workflow
    print(f"\n=== Consuming and Processing Messages ===")
    print(f"Messages in queue: {len(fake_consumer._messages)}\n")

    result2 = await run_ws_program(
        pubsub_workflow(messages), MessagingInterpreter(fake_producer, fake_consumer)
    )

    match result2:
        case Ok(stats):
            print(f"\n=== Workflow Statistics ===")
            print(f"  Published: {stats['published']}")
            print(f"  Acknowledged: {stats['acked']}")
            print(f"  Negative Acknowledged: {stats['nacked']}")
        case Err(error):
            print(f"\n✗ Error in workflow: {error}")

    # Show consumer state
    print(f"\n=== Consumer State ===")
    print(f"Messages acknowledged: {len(fake_consumer._acknowledged)}")
    for msg_id in fake_consumer._acknowledged:
        print(f"  ✓ {msg_id}")

    print(f"\nMessages negative acknowledged: {len(fake_consumer._nacked)}")
    for msg_id in fake_consumer._nacked:
        print(f"  ✗ {msg_id}")

    print(f"\nMessages remaining in queue: {len(fake_consumer._messages)}")


if __name__ == "__main__":
    asyncio.run(main())
