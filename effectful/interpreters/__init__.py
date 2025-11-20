"""Interpreters for executing effects against infrastructure.

This module provides interpreters that handle effect execution:

- **WebSocketInterpreter** - Handles WebSocket effects (SendText, ReceiveText, Close)
- **DatabaseInterpreter** - Handles database effects (GetUserById, SaveChatMessage)
- **CacheInterpreter** - Handles cache effects (GetCachedProfile, PutCachedProfile)
- **MessagingInterpreter** - Handles messaging effects (PublishMessage, ConsumeMessage)
- **StorageInterpreter** - Handles storage effects (GetObject, PutObject, DeleteObject, ListObjects)
- **AuthInterpreter** - Handles auth effects (ValidateToken, GenerateToken, RefreshToken, RevokeToken)
- **CompositeInterpreter** - Routes effects to specialized interpreters
- **create_composite_interpreter()** - Factory for creating composite interpreters

Example:
    >>> from effectful.interpreters import create_composite_interpreter
    >>>
    >>> # Production setup
    >>> interpreter = create_composite_interpreter(
    ...     websocket_connection=real_websocket,
    ...     user_repo=postgres_user_repo,
    ...     message_repo=postgres_message_repo,
    ...     cache=redis_cache,
    ...     message_producer=pulsar_producer,  # Optional
    ...     message_consumer=pulsar_consumer,  # Optional
    ...     object_storage=s3_storage,         # Optional
    ...     auth_service=redis_auth_service,   # Optional
    ... )
    >>>
    >>> # Run program
    >>> result = await run_ws_program(my_program(), interpreter)

Architecture:
    CompositeInterpreter routes effects to specialized interpreters:

    - WebSocket effects -> WebSocketInterpreter
    - Database effects -> DatabaseInterpreter
    - Cache effects -> CacheInterpreter
    - Messaging effects -> MessagingInterpreter (if configured)
    - Storage effects -> StorageInterpreter (if configured)
    - Auth effects -> AuthInterpreter (if configured)

See Also:
    - functional_effects.programs.runners - run_ws_program function
    - functional_effects.testing - Test interpreters with fakes
    - functional_effects.interpreters.errors - Error types
"""

from effectful.interpreters.auth import AuthInterpreter
from effectful.interpreters.cache import CacheInterpreter
from effectful.interpreters.composite import (
    CompositeInterpreter,
    create_composite_interpreter,
)
from effectful.interpreters.database import DatabaseInterpreter
from effectful.interpreters.messaging import MessagingInterpreter
from effectful.interpreters.storage import StorageInterpreter
from effectful.interpreters.websocket import WebSocketInterpreter

__all__ = [
    "WebSocketInterpreter",
    "DatabaseInterpreter",
    "CacheInterpreter",
    "MessagingInterpreter",
    "StorageInterpreter",
    "AuthInterpreter",
    "CompositeInterpreter",
    "create_composite_interpreter",
]
