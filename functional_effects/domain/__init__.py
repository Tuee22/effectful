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
- DomainError: Domain-level error types
"""

from functional_effects.domain.errors import DomainError, InvalidMessageError, UserNotFoundError
from functional_effects.domain.message import ChatMessage
from functional_effects.domain.message_envelope import (
    MessageEnvelope,
    PublishFailure,
    PublishResult,
    PublishSuccess,
)
from functional_effects.domain.profile import (
    ProfileData,
    ProfileFound,
    ProfileLookupResult,
    ProfileNotFound,
)
from functional_effects.domain.s3_object import PutFailure, PutResult, PutSuccess, S3Object
from functional_effects.domain.token_result import (
    TokenExpired,
    TokenInvalid,
    TokenValid,
    TokenValidationResult,
)
from functional_effects.domain.user import User

__all__ = [
    "User",
    "ChatMessage",
    "ProfileData",
    "ProfileFound",
    "ProfileNotFound",
    "ProfileLookupResult",
    "MessageEnvelope",
    "PublishSuccess",
    "PublishFailure",
    "PublishResult",
    "S3Object",
    "PutSuccess",
    "PutFailure",
    "PutResult",
    "TokenValid",
    "TokenExpired",
    "TokenInvalid",
    "TokenValidationResult",
    "UserNotFoundError",
    "InvalidMessageError",
    "DomainError",
]
