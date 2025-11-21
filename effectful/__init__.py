"""functional_effects: Type-safe effect systems for Python.

A library for building composable, testable applications using algebraic effects,
with strict type safety and no runtime exceptions for business logic errors.

Quick Start:
    >>> from effectful import (
    ...     run_ws_program,
    ...     create_composite_interpreter,
    ...     Ok, Err,
    ... )
    >>> from effectful.effects.websocket import SendText
    >>> from effectful.programs.program_types import AllEffects, EffectResult
    >>> from collections.abc import Generator
    >>>
    >>> def hello_world() -> Generator[AllEffects, EffectResult, str]:
    ...     yield SendText(text="Hello, world!")
    ...     return "success"
    >>>
    >>> # Run with interpreter
    >>> result = await run_ws_program(hello_world(), interpreter)
    >>> match result:
    ...     case Ok(value): print(f"Program returned: {value}")
    ...     case Err(error): print(f"Program failed: {error}")

Public API organized by category:

1. Core Program Execution:
   - run_ws_program: Execute effect programs to completion

2. Result Types (Algebraic Data Types):
   - Ok, Err: Result[T, E] constructors for explicit error handling
   - EffectReturn: Wrapper for effect interpretation results

3. Effect Definitions:
   - WebSocket effects: SendText, SendJSON, SendBinary, Close, etc.
   - Database effects: GetUserById, SaveChatMessage, etc.
   - Cache effects: GetCachedProfile, PutCachedProfile

4. Domain Models:
   - User, ChatMessage, ProfileData: Core domain entities
   - ADTs for lookup results (UserFound/UserNotFound, etc.)

5. Interpreters:
   - create_composite_interpreter: Factory for production interpreter
   - Individual interpreters for testing (WebSocketInterpreter, etc.)

6. Program Types:
   - AllEffects: Union of all effect types
   - EffectResult: Union of all effect result types
   - WSProgram: Type alias for WebSocket programs

See README.md and documents/ for comprehensive guides and tutorials.
"""

# Core program execution
# Infrastructure adapters - Real implementations
from effectful.adapters.postgres import (
    PostgresChatMessageRepository,
    PostgresUserRepository,
)
from effectful.adapters.redis_cache import RedisProfileCache
from effectful.adapters.websocket_connection import RealWebSocketConnection
from effectful.algebraic.effect_return import EffectReturn

# Result types - Algebraic Data Types for error handling
from effectful.algebraic.result import Err, Ok, Result, assert_never

# Domain models - Cache
from effectful.domain.cache_result import CacheHit, CacheLookupResult, CacheMiss

# Domain models - Message
from effectful.domain.message import ChatMessage

# Domain models - Profile
from effectful.domain.profile import (
    ProfileData,
    ProfileFound,
    ProfileLookupResult,
    ProfileNotFound,
)

# Domain models - Auth Token
from effectful.domain.token_result import (
    TokenExpired,
    TokenInvalid,
    TokenValid,
    TokenValidationResult,
)

# Domain models - Messaging
from effectful.domain.message_envelope import (
    ConsumeResult,
    ConsumeTimeout,
    MessageEnvelope,
    PublishFailure,
    PublishResult,
    PublishSuccess,
)

# Domain models - Storage
from effectful.domain.s3_object import (
    PutFailure,
    PutResult,
    PutSuccess,
    S3Object,
)

# Domain models - User
from effectful.domain.user import (
    User,
    UserFound,
    UserLookupResult,
    UserNotFound,
)

# Effect definitions - Cache
from effectful.effects.cache import (
    GetCachedProfile,
    PutCachedProfile,
)

# Effect definitions - Database
from effectful.effects.database import (
    GetUserById,
    SaveChatMessage,
)

# Effect definitions - Auth
from effectful.effects.auth import (
    GenerateToken,
    GetUserByEmail,
    HashPassword,
    RefreshToken,
    RevokeToken,
    ValidatePassword,
    ValidateToken,
)

# Effect definitions - Messaging
from effectful.effects.messaging import (
    AcknowledgeMessage,
    ConsumeMessage,
    NegativeAcknowledge,
    PublishMessage,
)

# Effect definitions - Storage
from effectful.effects.storage import (
    DeleteObject,
    GetObject,
    ListObjects,
    PutObject,
)

# Effect definitions - WebSocket
from effectful.effects.websocket import (
    Close,
    CloseGoingAway,
    CloseNormal,
    ClosePolicyViolation,
    CloseProtocolError,
    CloseReason,
    ReceiveText,
    SendText,
)
from effectful.infrastructure.cache import ProfileCache
from effectful.infrastructure.repositories import (
    ChatMessageRepository,
    UserRepository,
)

# Infrastructure protocols (for dependency injection)
from effectful.infrastructure.websocket import WebSocketConnection
from effectful.interpreters.auth import AuthInterpreter
from effectful.interpreters.cache import CacheInterpreter

# Interpreters - Factory
from effectful.interpreters.composite import create_composite_interpreter
from effectful.interpreters.database import DatabaseInterpreter

# Interpreter errors
from effectful.interpreters.errors import (
    AuthError,
    CacheError,
    DatabaseError,
    InterpreterError,
    MessagingError,
    StorageError,
    UnhandledEffectError,
    WebSocketClosedError,
)
from effectful.interpreters.messaging import MessagingInterpreter
from effectful.interpreters.storage import StorageInterpreter

# Interpreters - Individual (for testing/customization)
from effectful.interpreters.websocket import WebSocketInterpreter

# Program types
from effectful.programs.program_types import (
    AllEffects,
    EffectResult,
    WSProgram,
)
from effectful.programs.runners import run_ws_program

__all__ = [
    # Core execution
    "run_ws_program",
    # Result types
    "Ok",
    "Err",
    "Result",
    "EffectReturn",
    "assert_never",
    # Auth effects
    "ValidateToken",
    "GenerateToken",
    "RefreshToken",
    "RevokeToken",
    "GetUserByEmail",
    "ValidatePassword",
    "HashPassword",
    # Cache effects
    "GetCachedProfile",
    "PutCachedProfile",
    # Database effects
    "GetUserById",
    "SaveChatMessage",
    # Messaging effects
    "PublishMessage",
    "ConsumeMessage",
    "AcknowledgeMessage",
    "NegativeAcknowledge",
    # Storage effects
    "GetObject",
    "PutObject",
    "DeleteObject",
    "ListObjects",
    # WebSocket effects
    "SendText",
    "ReceiveText",
    "Close",
    "CloseReason",
    "CloseNormal",
    "CloseGoingAway",
    "CloseProtocolError",
    "ClosePolicyViolation",
    # Domain - Auth Token
    "TokenValid",
    "TokenExpired",
    "TokenInvalid",
    "TokenValidationResult",
    # Domain - Message
    "ChatMessage",
    # Domain - Messaging
    "MessageEnvelope",
    "ConsumeTimeout",
    "ConsumeResult",
    "PublishSuccess",
    "PublishFailure",
    "PublishResult",
    # Domain - Cache
    "CacheHit",
    "CacheMiss",
    "CacheLookupResult",
    # Domain - Profile
    "ProfileData",
    "ProfileFound",
    "ProfileNotFound",
    "ProfileLookupResult",
    # Domain - Storage
    "S3Object",
    "PutSuccess",
    "PutFailure",
    "PutResult",
    # Domain - User
    "User",
    "UserFound",
    "UserNotFound",
    "UserLookupResult",
    # Interpreters
    "create_composite_interpreter",
    "AuthInterpreter",
    "CacheInterpreter",
    "DatabaseInterpreter",
    "MessagingInterpreter",
    "StorageInterpreter",
    "WebSocketInterpreter",
    # Errors
    "InterpreterError",
    "UnhandledEffectError",
    "AuthError",
    "CacheError",
    "DatabaseError",
    "MessagingError",
    "StorageError",
    "WebSocketClosedError",
    # Program types
    "AllEffects",
    "EffectResult",
    "WSProgram",
    # Infrastructure protocols
    "WebSocketConnection",
    "UserRepository",
    "ChatMessageRepository",
    "ProfileCache",
    # Infrastructure adapters (real implementations)
    "PostgresUserRepository",
    "PostgresChatMessageRepository",
    "RedisProfileCache",
    "RealWebSocketConnection",
]

__version__ = "0.1.0"
