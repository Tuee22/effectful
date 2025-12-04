# Messaging Effects

**Status**: Authoritative source  
**Supersedes**: none  
**Referenced by**: documents/readme.md

> **Purpose**: Tutorial covering messaging effects for Apache Pulsar publish/subscribe workflows in effectful.

## Prerequisites

- Docker workflow running; commands executed via `docker compose ... exec effectful`.
- Completed [Tutorial 02: Effect Types](effect_types.md) and [Tutorial 03: ADTs and Result Types](adts_and_results.md).
- Reviewed the messaging interpreter and API reference: [Messaging API](../api/messaging.md).

## Learning Objectives

- Understand the Pulsar-oriented messaging effects and their lifecycle.
- Implement publish/consume flows that handle idle polls, retries, and acknowledgements.
- Test messaging programs with deterministic generator stepping and pattern matching.

## Step 1: Overview

- Messaging effects: `PublishMessage`, `ConsumeMessage`, `AcknowledgeMessage`, `NegativeAcknowledge`.
- Use this tutorial for workflow intent; see the SSoT API reference for fields, return types, and error domains: [Messaging API reference](../api/messaging.md).
- Architecture flows and interpreter responsibilities: [Architecture](../engineering/architecture.md#visual-data-flow).

## Step 2: Message lifecycle (conceptual)

```mermaid
flowchart TB
    Publish[PublishMessage(topic,payload)] --> Broker[Message queued in Pulsar]
    Broker --> Consume[ConsumeMessage(subscription)]
    Consume -->|MessageEnvelope| Process[Process payload]
    Process --> Ack[AcknowledgeMessage]
    Ack --> Removed[Message removed from queue]
    Process -->|Failure| Nack[NegativeAcknowledge(delay_ms)]
    Nack --> Redelivery[Message redelivered after delay]
    Consume -->|None| Idle[No message available (return None)]
```

**Key properties:**
- At-least-once delivery: messages redelivered if not acknowledged.
- Timeout is not an error: `ConsumeMessage` returns `None` when idle.
- Redelivery control: `NegativeAcknowledge` supports `delay_ms` backoff.
- Idempotency required: consumers must handle duplicates.

## Step 3: Publish and consume essentials

Keep programs focused on orchestration; let interpreters handle I/O and retries.

```python
# file: examples/08_messaging_effects.py
from collections.abc import Generator

from effectful.effects.messaging import (
    PublishMessage,
    ConsumeMessage,
    AcknowledgeMessage,
    NegativeAcknowledge,
)
from effectful.domain.message_envelope import MessageEnvelope
from effectful.programs.types import AllEffects, EffectResult

def publish_event(event: str) -> Generator[AllEffects, EffectResult, str]:
    message_id = yield PublishMessage(
        topic="user-events",
        payload=event.encode("utf-8"),
        properties={"type": "event", "version": "1.0"},
    )
    return f"published to user-events: {message_id}"

def consume_once() -> Generator[AllEffects, EffectResult, str]:
    envelope = yield ConsumeMessage(subscription="event-processor", timeout_ms=1_000)

    match envelope:
        case None:
            return "timeout"  # idle poll
        case MessageEnvelope(message_id=msg_id, payload=payload):
            # Process payload...
            yield AcknowledgeMessage(message_id=msg_id)
            return payload.decode("utf-8")
```

> **📖 See**: [Messaging API reference](../api/messaging.md) for signatures, ADTs, and error guarantees.

## Step 4: Ack/Nack rules

- Use `AcknowledgeMessage` after successful processing only.
- Use `NegativeAcknowledge` for transient failures; set `delay_ms` for backoff.
- Do not NACK permanent errors; route to dead-letter handling instead.
- Pattern-match on `ConsumeMessage` to treat `None` as a clean exit, not an error.

## Step 5: Testing pointers

## Summary

- Mapped Pulsar message lifecycles to effectful messaging effects and explicit ack/nack choices.
- Implemented publish/consume generators that treat idle polls and retries explicitly.
- Captured testing patterns for stepping generators and asserting on envelopes and acknowledgements.

## Next Steps

- Build production-ready consumers with backoff policies in [Effect Patterns](../engineering/effect_patterns.md#state-machines).
- Deep dive into observability for messaging flows in [Monitoring & Alerting](../engineering/monitoring_and_alerting.md).
- Explore storage integrations next in [Tutorial 09: Storage Effects](storage_effects.md).

- Unit-level: drive generators and assert yielded effects and return values.
- Interpreter-level: mock producers/consumers with `mocker.AsyncMock` and assert retryability handling.
- For full testing policy and timeout rules, see [Testing](../engineering/testing.md) and the broader [Testing Guide](testing_guide.md).

## Cross-References
- [Messaging API Reference](../api/messaging.md)
- [Architecture](../engineering/architecture.md#visual-data-flow)
- [Effect Patterns](../engineering/effect_patterns.md#state-machines)
- [Testing](../engineering/testing.md)
- [Documentation Standards](../documentation_standards.md)
