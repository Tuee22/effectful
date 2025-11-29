"""Program type definitions.

This module defines type aliases for effect programs including:
- AllEffects: Union of all effect types
- EffectResult: Union of all possible effect return values
- WSProgram: Generator type for WebSocket programs
"""

from collections.abc import Generator
from datetime import datetime
from uuid import UUID

from effectful.domain.cache_result import CacheMiss
from effectful.domain.message import ChatMessage
from effectful.domain.message_envelope import (
    AcknowledgeResult,
    ConsumeFailure,
    ConsumeTimeout,
    MessageEnvelope,
    NackResult,
    PublishResult,
)
from effectful.domain.metrics_result import (
    MetricQueryResult,
    MetricRecorded,
    MetricRecordingFailed,
    QueryFailure,
    QuerySuccess,
)
from effectful.domain.profile import ProfileData
from effectful.domain.s3_object import PutSuccess, S3Object
from effectful.domain.token_result import TokenValidationResult
from effectful.domain.user import User, UserNotFound
from effectful.effects.auth import AuthEffect
from effectful.effects.cache import CacheEffect
from effectful.effects.database import DatabaseEffect
from effectful.effects.messaging import MessagingEffect
from effectful.effects.metrics import MetricsEffect
from effectful.effects.storage import StorageEffect
from effectful.effects.system import SystemEffect
from effectful.effects.websocket import WebSocketEffect

# Union of all effects using PEP 695 type statement
type AllEffects = (
    WebSocketEffect
    | DatabaseEffect
    | CacheEffect
    | MessagingEffect
    | StorageEffect
    | AuthEffect
    | SystemEffect
    | MetricsEffect
)

# Union of all possible return values from effects
# This replaces 'Any' for strict type safety
# ADT types are used instead of None for explicit domain semantics
type EffectResult = (
    None  # Most effects return None (SendText, Close, PutCachedProfile, DeleteObject, RevokeToken)
    | str  # ReceiveText, PublishMessage, GenerateToken, RefreshToken, HashPassword return str
    | bool  # ValidatePassword, InvalidateCache, PutCachedValue return bool
    | bytes  # GetCachedValue returns bytes on cache hit
    | UUID  # CreateUser, GenerateUUID return UUID
    | datetime  # GetCurrentTime returns datetime
    # User ADTs
    | User  # GetUserById, GetUserByEmail returns User on success
    | UserNotFound  # GetUserById, GetUserByEmail returns UserNotFound when not found
    # Message types
    | ChatMessage  # SaveChatMessage returns ChatMessage
    # Cache ADTs
    | ProfileData  # GetCachedProfile returns ProfileData on cache hit
    | CacheMiss  # GetCachedProfile returns CacheMiss on cache miss
    # Messaging ADTs
    | MessageEnvelope  # ConsumeMessage returns MessageEnvelope on success
    | ConsumeTimeout  # ConsumeMessage returns ConsumeTimeout on timeout
    | ConsumeFailure  # ConsumeMessage returns ConsumeFailure on connection/subscription errors
    | PublishResult  # PublishMessage returns PublishResult ADT (PublishSuccess | PublishFailure)
    | AcknowledgeResult  # AcknowledgeMessage returns AcknowledgeResult ADT (AcknowledgeSuccess | AcknowledgeFailure)
    | NackResult  # NegativeAcknowledge returns NackResult ADT (NackSuccess | NackFailure)
    # Storage types
    | S3Object  # GetObject returns S3Object on success (None for not found)
    | PutSuccess  # PutObject returns PutSuccess on success
    # Token ADTs
    | TokenValidationResult  # ValidateToken returns TokenValidationResult ADT (TokenValid | TokenExpired | TokenInvalid)
    # Metrics ADTs
    | MetricRecorded  # IncrementCounter, RecordGauge, ObserveHistogram, RecordSummary return MetricRecorded on success
    | MetricRecordingFailed  # Metrics recording operations return MetricRecordingFailed on validation/collector error
    | QuerySuccess  # QueryMetrics returns QuerySuccess with metrics dict
    | QueryFailure  # QueryMetrics returns QueryFailure when metric not found or collector unavailable
    # List types
    | list[ChatMessage]  # ListMessagesForUser returns list[ChatMessage]
    | list[str]  # ListObjects returns list[str] (object keys)
    | list[User]  # ListUsers returns list[User]
)

# Program type alias: Generator that yields effects and receives results
type WSProgram = Generator[AllEffects, EffectResult, None]
