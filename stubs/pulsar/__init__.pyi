"""Type stubs for pulsar-client.

Minimal stubs for the Apache Pulsar Python client to satisfy mypy strict mode.
Only includes types actually used by effectful.
"""

class InitialPosition:
    """Pulsar subscription initial position enum."""

    Earliest: InitialPosition
    Latest: InitialPosition

class MessageId:
    """Pulsar message identifier."""

    def __str__(self) -> str: ...

class Message:
    """Pulsar message."""

    def message_id(self) -> MessageId: ...
    def data(self) -> bytes: ...
    def properties(self) -> dict[str, str]: ...
    def publish_timestamp(self) -> int: ...
    def topic_name(self) -> str: ...

class Producer:
    """Pulsar producer for publishing messages to a topic."""

    def send(
        self,
        content: bytes,
        *,
        properties: dict[str, str] | None = None,
        partition_key: str | None = None,
        sequence_id: int | None = None,
        replication_clusters: list[str] | None = None,
        disable_replication: bool = False,
        event_timestamp: int | None = None,
    ) -> MessageId: ...
    def close(self) -> None: ...

class Consumer:
    """Pulsar consumer for receiving messages from a subscription."""

    def receive(self, timeout_millis: int | None = None) -> Message: ...
    def acknowledge(self, message: Message) -> None: ...
    def negative_acknowledge(self, message: Message) -> None: ...
    def close(self) -> None: ...

class Client:
    """Pulsar client for creating producers and consumers."""

    def __init__(
        self,
        service_url: str,
        *,
        authentication: object | None = None,
        operation_timeout_seconds: int = 30,
        io_threads: int = 1,
        message_listener_threads: int = 1,
        concurrent_lookup_requests: int = 50000,
        log_conf_file_path: str | None = None,
        use_tls: bool = False,
        tls_trust_certs_file_path: str | None = None,
        tls_allow_insecure_connection: bool = False,
    ) -> None: ...
    def create_producer(
        self,
        topic: str,
        *,
        producer_name: str | None = None,
        initial_sequence_id: int | None = None,
        send_timeout_millis: int = 30000,
        compression_type: int = 0,
        max_pending_messages: int = 1000,
        block_if_queue_full: bool = True,
        batching_enabled: bool = True,
        batching_max_messages: int = 1000,
        batching_max_allowed_size_in_bytes: int = 131072,
        batching_max_publish_delay_ms: int = 10,
    ) -> Producer: ...
    def subscribe(
        self,
        topic: str,
        subscription_name: str,
        *,
        consumer_type: int = 0,
        message_listener: object | None = None,
        receiver_queue_size: int = 1000,
        max_total_receiver_queue_size_across_partitions: int = 50000,
        consumer_name: str | None = None,
        unacked_messages_timeout_ms: int | None = None,
        broker_consumer_stats_cache_time_ms: int = 30000,
        is_read_compacted: bool = False,
        properties: dict[str, str] | None = None,
        pattern_auto_discovery_period: int = 60,
        initial_position: InitialPosition = ...,
    ) -> Consumer: ...
    def close(self) -> None: ...

# Exceptions
class Timeout(Exception):
    """Timeout exception for Pulsar operations."""

    pass

class ProducerQueueIsFull(Exception):
    """Exception when producer queue is full."""

    pass
