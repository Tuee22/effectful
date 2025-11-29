"""Infrastructure protocols for external dependencies.

This module defines protocols (interfaces) that infrastructure must implement.
Interpreters depend on these protocols, not concrete implementations.

Available protocols:

- **WebSocketConnection** - Real-time communication protocol
- **UserRepository** - User data access protocol
- **ChatMessageRepository** - Message persistence protocol
- **ProfileCache** - Profile caching protocol
- **MessageProducer** - Message publishing protocol (Pulsar, Kafka, etc.)
- **MessageConsumer** - Message consumption protocol (Pulsar, Kafka, etc.)
- **ObjectStorage** - Object storage protocol (S3, MinIO, etc.)
- **MetricsCollector** - Metrics collection protocol (Prometheus, in-memory, etc.)

Example:
    >>> from effectful.infrastructure import UserRepository, ObjectStorage
    >>> class PostgresUserRepository:
    ...     async def get_by_id(self, user_id: UUID) -> UserLookupResult:
    ...         # Implementation using PostgreSQL
    ...         ...
    >>>
    >>> class S3ObjectStorage:
    ...     async def get_object(self, bucket: str, key: str) -> S3Object | None:
    ...         # Implementation using AWS S3
    ...         ...

See Also:
    - effectful.interpreters - Interpreters using these protocols
    - effectful.adapters - Production implementations (Pulsar, S3, etc.)
"""

from effectful.infrastructure.auth import AuthService
from effectful.infrastructure.cache import ProfileCache
from effectful.infrastructure.messaging import MessageConsumer, MessageProducer
from effectful.infrastructure.metrics import MetricsCollector
from effectful.infrastructure.repositories import (
    ChatMessageRepository,
    UserRepository,
)
from effectful.infrastructure.storage import ObjectStorage
from effectful.infrastructure.websocket import WebSocketConnection

__all__ = [
    "WebSocketConnection",
    "UserRepository",
    "ChatMessageRepository",
    "ProfileCache",
    "MessageProducer",
    "MessageConsumer",
    "ObjectStorage",
    "AuthService",
    "MetricsCollector",
]
