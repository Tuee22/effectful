"""Effect DSL for functional programs.

This package provides immutable effect types for describing program behavior:
- WebSocket effects: SendText, ReceiveText, Close (with typed CloseReason)
- Database effects: GetUserById, SaveChatMessage, ListMessagesForUser
- Cache effects: GetCachedProfile, PutCachedProfile
- Messaging effects: PublishMessage, ConsumeMessage, AcknowledgeMessage, NegativeAcknowledge
- Storage effects: GetObject, PutObject, DeleteObject, ListObjects
- Auth effects: ValidateToken, GenerateToken, RefreshToken, RevokeToken

All effects are frozen dataclasses ensuring immutability.
"""

from effectful.effects.auth import (
    AuthEffect,
    GenerateToken,
    RefreshToken,
    RevokeToken,
    ValidateToken,
)
from effectful.effects.base import Effect
from effectful.effects.cache import CacheEffect, GetCachedProfile, PutCachedProfile
from effectful.effects.database import (
    DatabaseEffect,
    GetUserById,
    ListMessagesForUser,
    SaveChatMessage,
)
from effectful.effects.messaging import (
    AcknowledgeMessage,
    ConsumeMessage,
    MessagingEffect,
    NegativeAcknowledge,
    PublishMessage,
)
from effectful.effects.storage import (
    DeleteObject,
    GetObject,
    ListObjects,
    PutObject,
    StorageEffect,
)
from effectful.effects.websocket import (
    Close,
    CloseGoingAway,
    CloseNormal,
    ClosePolicyViolation,
    CloseProtocolError,
    CloseReason,
    ReceiveText,
    SendText,
    WebSocketEffect,
)

__all__ = [
    # Base
    "Effect",
    # WebSocket
    "SendText",
    "ReceiveText",
    "Close",
    "CloseNormal",
    "CloseGoingAway",
    "CloseProtocolError",
    "ClosePolicyViolation",
    "CloseReason",
    "WebSocketEffect",
    # Database
    "GetUserById",
    "SaveChatMessage",
    "ListMessagesForUser",
    "DatabaseEffect",
    # Cache
    "GetCachedProfile",
    "PutCachedProfile",
    "CacheEffect",
    # Messaging
    "PublishMessage",
    "ConsumeMessage",
    "AcknowledgeMessage",
    "NegativeAcknowledge",
    "MessagingEffect",
    # Storage
    "GetObject",
    "PutObject",
    "DeleteObject",
    "ListObjects",
    "StorageEffect",
    # Auth
    "ValidateToken",
    "GenerateToken",
    "RefreshToken",
    "RevokeToken",
    "AuthEffect",
]
