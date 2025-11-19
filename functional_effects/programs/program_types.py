"""Program type definitions.

This module defines type aliases for effect programs including:
- AllEffects: Union of all effect types
- EffectResult: Union of all possible effect return values
- WSProgram: Generator type for WebSocket programs
"""

from collections.abc import Generator

from functional_effects.domain.message import ChatMessage
from functional_effects.domain.message_envelope import MessageEnvelope
from functional_effects.domain.profile import ProfileData
from functional_effects.domain.s3_object import S3Object
from functional_effects.domain.token_result import TokenValidationResult
from functional_effects.domain.user import User
from functional_effects.effects.auth import AuthEffect
from functional_effects.effects.cache import CacheEffect
from functional_effects.effects.database import DatabaseEffect
from functional_effects.effects.messaging import MessagingEffect
from functional_effects.effects.storage import StorageEffect
from functional_effects.effects.websocket import WebSocketEffect

# Union of all effects using PEP 695 type statement
type AllEffects = (
    WebSocketEffect | DatabaseEffect | CacheEffect | MessagingEffect | StorageEffect | AuthEffect
)

# Union of all possible return values from effects
# This replaces 'Any' for strict type safety
type EffectResult = (
    None  # Most effects return None (SendText, Close, PutCachedProfile, AcknowledgeMessage, NegativeAcknowledge, DeleteObject, RevokeToken)
    | str  # ReceiveText, PublishMessage, PutObject, GenerateToken, RefreshToken return str (RefreshToken can also return None)
    | User  # GetUserById returns Optional[User] (None handled in union)
    | ChatMessage  # SaveChatMessage returns ChatMessage
    | ProfileData  # GetCachedProfile returns Optional[ProfileData]
    | MessageEnvelope  # ConsumeMessage returns Optional[MessageEnvelope]
    | S3Object  # GetObject returns Optional[S3Object]
    | TokenValidationResult  # ValidateToken returns TokenValidationResult ADT (TokenValid | TokenExpired | TokenInvalid)
    | list[ChatMessage]  # ListMessagesForUser returns list[ChatMessage]
    | list[str]  # ListObjects returns list[str] (object keys)
)

# Program type alias: Generator that yields effects and receives results
type WSProgram = Generator[AllEffects, EffectResult, None]
