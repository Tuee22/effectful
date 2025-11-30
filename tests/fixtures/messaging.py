"""Apache Pulsar fixtures for integration and e2e testing.

Provides fixtures for:
- Pulsar client connections
- Message producers and consumers
"""

import asyncio
from collections.abc import AsyncGenerator, Generator

import pulsar
import pytest
import pytest_asyncio

from effectful.adapters.pulsar_messaging import PulsarMessageConsumer, PulsarMessageProducer
from tests.fixtures.config import PULSAR_URL


@pytest.fixture
def pulsar_client() -> Generator[pulsar.Client, None, None]:
    """Provide a Pulsar client for integration tests.

    Yields:
        Connected Pulsar client instance
    """
    client = pulsar.Client(
        PULSAR_URL,
        operation_timeout_seconds=30,
    )
    yield client
    try:
        client.close()
    except Exception:
        # Ignore timeout errors during cleanup
        pass


@pytest.fixture
def pulsar_producer(pulsar_client: pulsar.Client) -> PulsarMessageProducer:
    """Provide a Pulsar message producer.

    Args:
        pulsar_client: Connected Pulsar client

    Returns:
        PulsarMessageProducer instance
    """
    return PulsarMessageProducer(pulsar_client)


@pytest.fixture
def pulsar_consumer(pulsar_client: pulsar.Client) -> PulsarMessageConsumer:
    """Provide a Pulsar message consumer.

    Args:
        pulsar_client: Connected Pulsar client

    Returns:
        PulsarMessageConsumer instance
    """
    return PulsarMessageConsumer(pulsar_client)


@pytest_asyncio.fixture
async def clean_pulsar(
    pulsar_producer: PulsarMessageProducer,
    pulsar_consumer: PulsarMessageConsumer,
) -> AsyncGenerator[tuple[PulsarMessageProducer, PulsarMessageConsumer], None]:
    """Provide clean Pulsar producer and consumer.

    Closes all cached producers/consumers before AND after test, ensuring isolation
    even when tests fail.

    Yields:
        Tuple of (PulsarMessageProducer, PulsarMessageConsumer) with clean state

    Note:
        Pre-cleanup: Ensures clean starting state
        Post-cleanup: Prevents resource leaks when tests fail/timeout
        Tests must use unique topic names (UUID) to avoid broker-level conflicts
    """
    # PRE-CLEANUP: Clean up BEFORE test runs (matches other clean_* fixtures)
    pulsar_producer.close_producers()
    pulsar_consumer.close_consumers()

    # Give broker time to process close operations
    # Pulsar broker needs ~100ms to finalize producer/consumer cleanup
    await asyncio.sleep(0.2)  # 200ms safety margin

    yield (pulsar_producer, pulsar_consumer)

    # POST-CLEANUP: Critical for preventing resource leaks on test failure
    try:
        pulsar_producer.close_producers()
        pulsar_consumer.close_consumers()
        await asyncio.sleep(0.2)  # Allow cleanup to propagate
    except Exception:
        # Ignore cleanup errors - test isolation is more important than cleanup failure
        pass
