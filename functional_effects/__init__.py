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
from functional_effects.interpreters.cache import CacheInterpreter

# Interpreters - Factory
from functional_effects.interpreters.composite import create_composite_interpreter
from functional_effects.interpreters.database import DatabaseInterpreter

# Interpreter errors
from functional_effects.interpreters.errors import (
    CacheError,
    DatabaseError,
    InterpreterError,
    UnhandledEffectError,
    WebSocketClosedError,
)

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
    # WebSocket effects
    "SendText",
    "ReceiveText",
    "Close",
    "CloseReason",
    "CloseNormal",
    "CloseGoingAway",
    "CloseProtocolError",
    "ClosePolicyViolation",
    # Database effects
    "GetUserById",
    "SaveChatMessage",
    # Cache effects
    "GetCachedProfile",
    "PutCachedProfile",
    # Domain - User
    "User",
    "UserFound",
    "UserNotFound",
    "UserLookupResult",
    # Domain - Message
    "ChatMessage",
    # Domain - Profile
    "ProfileData",
    "ProfileFound",
    "ProfileNotFound",
    "ProfileLookupResult",
    # Interpreters
    "create_composite_interpreter",
    "WebSocketInterpreter",
    "DatabaseInterpreter",
    "CacheInterpreter",
    # Errors
    "InterpreterError",
    "UnhandledEffectError",
    "DatabaseError",
    "WebSocketClosedError",
    "CacheError",
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
