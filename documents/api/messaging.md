# Messaging Effects API Reference

This document covers the messaging effect types for pub/sub communication with message brokers like Apache Pulsar.

## Effect Types

### PublishMessage

Publishes a message to a topic.

```python
from effectful import PublishMessage, MessageEnvelope

@dataclass(frozen=True)
class PublishMessage:
    topic: str
    payload: bytes
    properties: dict[str, str] | None = None
```

**Parameters:**
- `topic` - The topic/queue name to publish to
- `payload` - Message content as bytes
- `properties` - Optional metadata key-value pairs

**Returns:** `PublishResult` (see Domain Models below)

**Example:**
```python
import json
from effectful import PublishMessage, PublishSuccess, PublishFailure

def publish_event(
    event_type: str, data: dict[str, str]
) -> Generator[AllEffects, EffectResult, bool]:
    payload = json.dumps({"type": event_type, "data": data}).encode()

    result = yield PublishMessage(
        topic="events",
        payload=payload,
        properties={"event_type": event_type}
    )

    match result:
        case PublishSuccess(message_id=mid):
            yield SendText(text=f"Published: {mid}")
            return True
        case PublishFailure(error=err):
            yield SendText(text=f"Publish failed: {err}")
            return False
```

### ConsumeMessage

Consumes a message from a topic with timeout.

```python
@dataclass(frozen=True)
class ConsumeMessage:
    topic: str
    subscription: str
    timeout_ms: int = 5000
```

**Parameters:**
- `topic` - The topic/queue name to consume from
- `subscription` - Subscription name for this consumer
- `timeout_ms` - Timeout in milliseconds (default: 5000)

**Returns:** `ConsumeResult` (see Domain Models below)

**Example:**
```python
from effectful import ConsumeMessage, MessageEnvelope, ConsumeTimeout

def process_messages(
    topic: str
) -> Generator[AllEffects, EffectResult, int]:
    processed = 0

    while True:
        result = yield ConsumeMessage(
            topic=topic,
            subscription="my-subscription",
            timeout_ms=1000
        )

        match result:
            case MessageEnvelope() as msg:
                # Process the message
                yield SendText(text=f"Received: {msg.payload.decode()}")
                yield AcknowledgeMessage(message_id=msg.message_id, topic=topic)
                processed += 1
            case ConsumeTimeout():
                # No more messages
                break

    return processed
```

### AcknowledgeMessage

Acknowledges successful processing of a message.

```python
@dataclass(frozen=True)
class AcknowledgeMessage:
    message_id: str
    topic: str
```

**Parameters:**
- `message_id` - The ID of the message to acknowledge
- `topic` - The topic the message came from

**Returns:** `None`

**Example:**
```python
from effectful import AcknowledgeMessage, MessageEnvelope

def handle_message(
    msg: MessageEnvelope
) -> Generator[AllEffects, EffectResult, None]:
    # Process message...
    process_payload(msg.payload)

    # Acknowledge after successful processing
    yield AcknowledgeMessage(
        message_id=msg.message_id,
        topic=msg.topic
    )
```

### NegativeAcknowledge

Negative acknowledgment - signals processing failure for redelivery.

```python
@dataclass(frozen=True)
class NegativeAcknowledge:
    message_id: str
    topic: str
```

**Parameters:**
- `message_id` - The ID of the message to nack
- `topic` - The topic the message came from

**Returns:** `None`

**Example:**
```python
from effectful import NegativeAcknowledge, MessageEnvelope

def handle_with_retry(
    msg: MessageEnvelope
) -> Generator[AllEffects, EffectResult, bool]:
    try:
        result = process_payload(msg.payload)
        if result:
            yield AcknowledgeMessage(
                message_id=msg.message_id,
                topic=msg.topic
            )
            return True
        else:
            # Processing failed, request redelivery
            yield NegativeAcknowledge(
                message_id=msg.message_id,
                topic=msg.topic
            )
            return False
    except Exception:
        yield NegativeAcknowledge(
            message_id=msg.message_id,
            topic=msg.topic
        )
        return False
```

## Domain Models

### MessageEnvelope

Container for a consumed message with metadata.

```python
@dataclass(frozen=True)
class MessageEnvelope:
    message_id: str
    topic: str
    payload: bytes
    properties: dict[str, str]
    publish_time: datetime
```

**Fields:**
- `message_id` - Unique identifier for the message
- `topic` - Topic the message was consumed from
- `payload` - Message content as bytes
- `properties` - Metadata key-value pairs
- `publish_time` - When the message was published

### PublishResult

ADT for publish operation outcomes.

```python
type PublishResult = PublishSuccess | PublishFailure

@dataclass(frozen=True)
class PublishSuccess:
    message_id: str

@dataclass(frozen=True)
class PublishFailure:
    error: str
```

**Pattern Matching:**
```python
result = yield PublishMessage(topic="events", payload=data)

match result:
    case PublishSuccess(message_id=mid):
        # Handle success
        pass
    case PublishFailure(error=err):
        # Handle failure
        pass
```

### ConsumeResult

ADT for consume operation outcomes.

```python
type ConsumeResult = MessageEnvelope | ConsumeTimeout

@dataclass(frozen=True)
class ConsumeTimeout:
    pass
```

**Pattern Matching:**
```python
result = yield ConsumeMessage(topic="events", subscription="sub")

match result:
    case MessageEnvelope() as msg:
        # Process message
        pass
    case ConsumeTimeout():
        # No message available
        pass
```

## Error Handling

The `MessagingInterpreter` may return `MessagingError` for infrastructure failures:

```python
from effectful import MessagingError

result = await run_ws_program(my_program(), interpreter)

match result:
    case Ok(value):
        print(f"Success: {value}")
    case Err(MessagingError(message=msg)):
        print(f"Messaging error: {msg}")
    case Err(error):
        print(f"Other error: {error}")
```

## Complete Workflow Example

```python
from collections.abc import Generator
from effectful import (
    AllEffects,
    EffectResult,
    PublishMessage,
    ConsumeMessage,
    AcknowledgeMessage,
    NegativeAcknowledge,
    MessageEnvelope,
    ConsumeTimeout,
    PublishSuccess,
    PublishFailure,
    SendText,
)
import json

def event_processor() -> Generator[AllEffects, EffectResult, dict[str, int]]:
    """Process events from queue and publish results."""
    stats = {"processed": 0, "failed": 0}

    while True:
        # Consume next message
        result = yield ConsumeMessage(
            topic="incoming-events",
            subscription="processor",
            timeout_ms=2000
        )

        match result:
            case ConsumeTimeout():
                break

            case MessageEnvelope() as msg:
                # Parse and process
                try:
                    event = json.loads(msg.payload)
                    processed = {"original": event, "status": "processed"}

                    # Publish result
                    pub_result = yield PublishMessage(
                        topic="processed-events",
                        payload=json.dumps(processed).encode(),
                        properties={"source_id": msg.message_id}
                    )

                    match pub_result:
                        case PublishSuccess():
                            yield AcknowledgeMessage(
                                message_id=msg.message_id,
                                topic=msg.topic
                            )
                            stats["processed"] += 1
                        case PublishFailure():
                            yield NegativeAcknowledge(
                                message_id=msg.message_id,
                                topic=msg.topic
                            )
                            stats["failed"] += 1

                except json.JSONDecodeError:
                    yield NegativeAcknowledge(
                        message_id=msg.message_id,
                        topic=msg.topic
                    )
                    stats["failed"] += 1

    yield SendText(text=f"Stats: {stats}")
    return stats
```

## See Also

- [Effects Overview](effects.md) - All effect types
- [Storage Effects](storage.md) - S3/object storage effects
- [Interpreters](interpreters.md) - MessagingInterpreter details
- [Tutorial: Messaging Effects](../tutorials/08_messaging_effects.md) - Step-by-step guide
