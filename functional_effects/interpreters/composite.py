"""Composite interpreter implementation.

This module provides a composite interpreter that delegates to specialized interpreters.
Includes factory function for creating configured interpreters.
"""

from dataclasses import dataclass

from functional_effects.algebraic.effect_return import EffectReturn
from functional_effects.algebraic.result import Err, Result
from functional_effects.effects.base import Effect
from functional_effects.infrastructure.auth import AuthService
from functional_effects.infrastructure.cache import ProfileCache
from functional_effects.infrastructure.messaging import MessageConsumer, MessageProducer
from functional_effects.infrastructure.repositories import (
    ChatMessageRepository,
    UserRepository,
)
from functional_effects.infrastructure.storage import ObjectStorage
from functional_effects.infrastructure.websocket import WebSocketConnection
from functional_effects.interpreters.auth import AuthInterpreter
from functional_effects.interpreters.cache import CacheInterpreter
from functional_effects.interpreters.database import DatabaseInterpreter
from functional_effects.interpreters.errors import InterpreterError, UnhandledEffectError
from functional_effects.interpreters.messaging import MessagingInterpreter
from functional_effects.interpreters.storage import StorageInterpreter
from functional_effects.interpreters.websocket import WebSocketInterpreter
from functional_effects.programs.program_types import EffectResult


@dataclass(frozen=True)
class CompositeInterpreter:
    """Composite interpreter that delegates to specialized interpreters.

    Tries each interpreter in order until one handles the effect.

    Attributes:
        websocket: WebSocket effect interpreter
        database: Database effect interpreter
        cache: Cache effect interpreter
        messaging: Messaging effect interpreter (optional)
        storage: Storage effect interpreter (optional)
        auth: Auth effect interpreter (optional)
    """

    websocket: WebSocketInterpreter
    database: DatabaseInterpreter
    cache: CacheInterpreter
    messaging: MessagingInterpreter | None = None
    storage: StorageInterpreter | None = None
    auth: AuthInterpreter | None = None

    async def interpret(
        self, effect: Effect
    ) -> Result[EffectReturn[EffectResult], InterpreterError]:
        """Interpret an effect by delegating to specialized interpreters.

        Args:
            effect: The effect to interpret

        Returns:
            Ok(EffectReturn(value)) if any interpreter handled it
            Err(UnhandledEffectError) if no interpreter could handle it
        """
        available = [
            "WebSocketInterpreter",
            "DatabaseInterpreter",
            "CacheInterpreter",
        ]

        # Try WebSocket interpreter first
        ws_result = await self.websocket.interpret(effect)
        match ws_result:
            case Err(UnhandledEffectError()):
                pass  # Try next
            case _:
                return ws_result

        # Try Database interpreter
        db_result = await self.database.interpret(effect)
        match db_result:
            case Err(UnhandledEffectError()):
                pass  # Try next
            case _:
                return db_result

        # Try Cache interpreter
        cache_result = await self.cache.interpret(effect)
        match cache_result:
            case Err(UnhandledEffectError()):
                pass  # Try next
            case _:
                return cache_result

        # Try Messaging interpreter if provided
        if self.messaging is not None:
            available.append("MessagingInterpreter")
            messaging_result = await self.messaging.interpret(effect)
            match messaging_result:
                case Err(UnhandledEffectError()):
                    pass  # Try next
                case _:
                    return messaging_result

        # Try Storage interpreter if provided
        if self.storage is not None:
            available.append("StorageInterpreter")
            storage_result = await self.storage.interpret(effect)
            match storage_result:
                case Err(UnhandledEffectError()):
                    pass  # Try next
                case _:
                    return storage_result

        # Try Auth interpreter if provided
        if self.auth is not None:
            available.append("AuthInterpreter")
            auth_result = await self.auth.interpret(effect)
            match auth_result:
                case Err(UnhandledEffectError()):
                    pass  # No one handled it
                case _:
                    return auth_result

        # No interpreter could handle this effect
        return Err(
            UnhandledEffectError(
                effect=effect,
                available_interpreters=available,
            )
        )


def create_composite_interpreter(
    websocket_connection: WebSocketConnection,
    user_repo: UserRepository,
    message_repo: ChatMessageRepository,
    cache: ProfileCache,
    message_producer: MessageProducer | None = None,
    message_consumer: MessageConsumer | None = None,
    object_storage: ObjectStorage | None = None,
    auth_service: AuthService | None = None,
) -> CompositeInterpreter:
    """Factory function to create a configured composite interpreter.

    Args:
        websocket_connection: WebSocket connection implementation
        user_repo: User repository implementation
        message_repo: Chat message repository implementation
        cache: Profile cache implementation
        message_producer: Optional message producer for Pulsar (if messaging needed)
        message_consumer: Optional message consumer for Pulsar (if messaging needed)
        object_storage: Optional object storage for S3 (if storage needed)
        auth_service: Optional auth service for JWT authentication (if auth needed)

    Returns:
        Configured CompositeInterpreter with all dependencies injected
    """
    # Create optional messaging interpreter if both producer and consumer provided
    messaging_interpreter = None
    if message_producer is not None and message_consumer is not None:
        messaging_interpreter = MessagingInterpreter(
            producer=message_producer, consumer=message_consumer
        )

    # Create optional storage interpreter if object storage provided
    storage_interpreter = None
    if object_storage is not None:
        storage_interpreter = StorageInterpreter(storage=object_storage)

    # Create optional auth interpreter if auth service provided
    auth_interpreter = None
    if auth_service is not None:
        auth_interpreter = AuthInterpreter(auth_service=auth_service)

    return CompositeInterpreter(
        websocket=WebSocketInterpreter(connection=websocket_connection),
        database=DatabaseInterpreter(user_repo=user_repo, message_repo=message_repo),
        cache=CacheInterpreter(cache=cache),
        messaging=messaging_interpreter,
        storage=storage_interpreter,
        auth=auth_interpreter,
    )
