"""Domain models for the functional effects system.

This package contains immutable domain entities and value objects:
- User: User entity
- ChatMessage: Message entity
- ProfileData: Cached profile value object
- ProfileLookupResult: ADT for profile lookup results
- MessageEnvelope: Pulsar message wrapper
- PublishResult: ADT for publish operation results (PublishSuccess | PublishFailure)
- S3Object: S3 object with metadata
- PutResult: ADT for put operation results (PutSuccess | PutFailure)
- MetricResult: ADT for metric recording results (MetricRecorded | MetricRecordingFailed)
- MetricQueryResult: ADT for metric query results (QuerySuccess | QueryFailure)
- DomainError: Domain-level error types
"""

from effectful.domain.cache_result import CacheHit, CacheLookupResult, CacheMiss
from effectful.domain.errors import DomainError, InvalidMessageError, UserNotFoundError
from effectful.domain.message import ChatMessage
from effectful.domain.message_envelope import (
    ConsumeResult,
    ConsumeTimeout,
    MessageEnvelope,
    PublishFailure,
    PublishResult,
    PublishSuccess,
)
from effectful.domain.metrics_result import (
    MetricQueryResult,
    MetricRecorded,
    MetricRecordingFailed,
    MetricResult,
    QueryFailure,
    QuerySuccess,
)
from effectful.domain.profile import (
    ProfileData,
    ProfileFound,
    ProfileLookupResult,
    ProfileNotFound,
)
from effectful.domain.s3_object import PutFailure, PutResult, PutSuccess, S3Object
from effectful.domain.token_result import (
    TokenExpired,
    TokenInvalid,
    TokenValid,
    TokenValidationResult,
)
from effectful.domain.user import User, UserFound, UserLookupResult, UserNotFound

__all__ = [
    # User ADTs
    "User",
    "UserFound",
    "UserNotFound",
    "UserLookupResult",
    # Message
    "ChatMessage",
    # Profile ADTs
    "ProfileData",
    "ProfileFound",
    "ProfileNotFound",
    "ProfileLookupResult",
    # Cache ADTs
    "CacheHit",
    "CacheMiss",
    "CacheLookupResult",
    # Messaging ADTs
    "MessageEnvelope",
    "ConsumeTimeout",
    "ConsumeResult",
    "PublishSuccess",
    "PublishFailure",
    "PublishResult",
    # Storage ADTs
    "S3Object",
    "PutSuccess",
    "PutFailure",
    "PutResult",
    # Token ADTs
    "TokenValid",
    "TokenExpired",
    "TokenInvalid",
    "TokenValidationResult",
    # Metrics ADTs
    "MetricRecorded",
    "MetricRecordingFailed",
    "MetricResult",
    "QuerySuccess",
    "QueryFailure",
    "MetricQueryResult",
    # Errors
    "UserNotFoundError",
    "InvalidMessageError",
    "DomainError",
]
