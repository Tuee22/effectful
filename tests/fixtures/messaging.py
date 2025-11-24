"""Apache Pulsar fixtures for integration and e2e testing.

Provides fixtures for:
- Pulsar client connections
- Message producers and consumers
"""

from collections.abc import Generator

import pulsar
import pytest

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
