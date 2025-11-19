"""functional_effects: Type-safe effect systems for Python.

A library for building composable, testable applications using algebraic effects,
with strict type safety and no runtime exceptions for business logic errors.

Quick Start:
    >>> from functional_effects import (
    ...     run_ws_program,
    ...     create_composite_interpreter,
    ...     Ok, Err,
    ... )
    >>> from functional_effects.effects.websocket import SendText
    >>> from functional_effects.programs.program_types import AllEffects, EffectResult
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

See README.md and docs/ for comprehensive guides and tutorials.
"""

# Core program execution
# Infrastructure adapters - Real implementations
from functional_effects.adapters.postgres import (
    PostgresChatMessageRepository,
    PostgresUserRepository,
)
from functional_effects.adapters.redis_cache import RedisProfileCache
from functional_effects.adapters.websocket_connection import RealWebSocketConnection
from functional_effects.algebraic.effect_return import EffectReturn

# Result types - Algebraic Data Types for error handling
from functional_effects.algebraic.result import Err, Ok, Result

# Domain models - Message
from functional_effects.domain.message import ChatMessage

# Domain models - Profile
from functional_effects.domain.profile import (
    ProfileData,
    ProfileFound,
    ProfileLookupResult,
    ProfileNotFound,
)

# Domain models - Auth Token
from functional_effects.domain.token_result import (
    TokenExpired,
    TokenInvalid,
    TokenValid,
    TokenValidationResult,
)

# Domain models - Messaging
from functional_effects.domain.message_envelope import (
    MessageEnvelope,
    PublishFailure,
    PublishResult,
    PublishSuccess,
)

# Domain models - Storage
from functional_effects.domain.s3_object import (
    PutFailure,
    PutResult,
    PutSuccess,
    S3Object,
)

# Domain models - User
from functional_effects.domain.user import (
    User,
    UserFound,
    UserLookupResult,
    UserNotFound,
)

# Effect definitions - Cache
from functional_effects.effects.cache import (
    GetCachedProfile,
    PutCachedProfile,
)

# Effect definitions - Database
from functional_effects.effects.database import (
    GetUserById,
    SaveChatMessage,
)

# Effect definitions - Auth
from functional_effects.effects.auth import (
    GenerateToken,
    GetUserByEmail,
    HashPassword,
    RefreshToken,
    RevokeToken,
    ValidatePassword,
    ValidateToken,
)

# Effect definitions - Messaging
from functional_effects.effects.messaging import (
    AcknowledgeMessage,
    ConsumeMessage,
    NegativeAcknowledge,
    PublishMessage,
)

# Effect definitions - Storage
from functional_effects.effects.storage import (
    DeleteObject,
    GetObject,
    ListObjects,
    PutObject,
)

# Effect definitions - WebSocket
from functional_effects.effects.websocket import (
    Close,
    CloseGoingAway,
    CloseNormal,
    ClosePolicyViolation,
    CloseProtocolError,
    CloseReason,
    ReceiveText,
    SendText,
)
from functional_effects.infrastructure.cache import ProfileCache
from functional_effects.infrastructure.repositories import (
    ChatMessageRepository,
    UserRepository,
)

# Infrastructure protocols (for dependency injection)
from functional_effects.infrastructure.websocket import WebSocketConnection
from functional_effects.interpreters.auth import AuthInterpreter
from functional_effects.interpreters.cache import CacheInterpreter

# Interpreters - Factory
from functional_effects.interpreters.composite import create_composite_interpreter
from functional_effects.interpreters.database import DatabaseInterpreter

# Interpreter errors
from functional_effects.interpreters.errors import (
    AuthError,
    CacheError,
    DatabaseError,
    InterpreterError,
    MessagingError,
    StorageError,
    UnhandledEffectError,
    WebSocketClosedError,
)
from functional_effects.interpreters.messaging import MessagingInterpreter
from functional_effects.interpreters.storage import StorageInterpreter

# Interpreters - Individual (for testing/customization)
from functional_effects.interpreters.websocket import WebSocketInterpreter

# Program types
from functional_effects.programs.program_types import (
    AllEffects,
    EffectResult,
    WSProgram,
)
from functional_effects.programs.runners import run_ws_program

__all__ = [
    # Core execution
    "run_ws_program",
    # Result types
    "Ok",
    "Err",
    "Result",
    "EffectReturn",
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
    "PublishSuccess",
    "PublishFailure",
    "PublishResult",
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
