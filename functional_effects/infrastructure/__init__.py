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

Example:
    >>> from functional_effects.infrastructure import UserRepository, ObjectStorage
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
    - functional_effects.interpreters - Interpreters using these protocols
    - functional_effects.testing.fakes - Test implementations of protocols
    - functional_effects.adapters - Production implementations (Pulsar, S3, etc.)
"""

from functional_effects.infrastructure.auth import AuthService
from functional_effects.infrastructure.cache import ProfileCache
from functional_effects.infrastructure.messaging import MessageConsumer, MessageProducer
from functional_effects.infrastructure.repositories import (
    ChatMessageRepository,
    UserRepository,
)
from functional_effects.infrastructure.storage import ObjectStorage
from functional_effects.infrastructure.websocket import WebSocketConnection

__all__ = [
    "WebSocketConnection",
    "UserRepository",
    "ChatMessageRepository",
    "ProfileCache",
    "MessageProducer",
    "MessageConsumer",
    "ObjectStorage",
    "AuthService",
]
