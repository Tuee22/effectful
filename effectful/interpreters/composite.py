"""Composite interpreter implementation.

This module provides a composite interpreter that delegates to specialized interpreters.
Includes factory function for creating configured interpreters.
"""

from dataclasses import dataclass

from effectful.algebraic.effect_return import EffectReturn
from effectful.algebraic.result import Err, Result
from effectful.effects.base import Effect
from effectful.infrastructure.auth import AuthService
from effectful.infrastructure.cache import ProfileCache
from effectful.infrastructure.messaging import MessageConsumer, MessageProducer
from effectful.infrastructure.metrics import MetricsCollector
from effectful.infrastructure.repositories import (
    ChatMessageRepository,
    UserRepository,
)
from effectful.infrastructure.storage import ObjectStorage
from effectful.infrastructure.websocket import WebSocketConnection
from effectful.interpreters.auth import AuthInterpreter
from effectful.interpreters.cache import CacheInterpreter
from effectful.interpreters.database import DatabaseInterpreter
from effectful.interpreters.errors import InterpreterError, UnhandledEffectError
from effectful.interpreters.messaging import MessagingInterpreter
from effectful.interpreters.metrics import MetricsInterpreter
from effectful.interpreters.storage import StorageInterpreter
from effectful.interpreters.system import SystemInterpreter
from effectful.interpreters.websocket import WebSocketInterpreter
from effectful.programs.program_types import EffectResult


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
        metrics: Metrics effect interpreter (optional)
        system: System effect interpreter (always included)
    """

    websocket: WebSocketInterpreter
    database: DatabaseInterpreter
    cache: CacheInterpreter
    system: SystemInterpreter
    messaging: MessagingInterpreter | None = None
    storage: StorageInterpreter | None = None
    auth: AuthInterpreter | None = None
    metrics: MetricsInterpreter | None = None

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

        # Try System interpreter
        system_result = await self.system.interpret(effect)
        match system_result:
            case Err(UnhandledEffectError()):
                pass  # Try next
            case _:
                return system_result

        # Try Messaging interpreter if provided
        if self.messaging is not None:
            messaging_result = await self.messaging.interpret(effect)
            match messaging_result:
                case Err(UnhandledEffectError()):
                    pass  # Try next
                case _:
                    return messaging_result

        # Try Storage interpreter if provided
        if self.storage is not None:
            storage_result = await self.storage.interpret(effect)
            match storage_result:
                case Err(UnhandledEffectError()):
                    pass  # Try next
                case _:
                    return storage_result

        # Try Auth interpreter if provided
        if self.auth is not None:
            auth_result = await self.auth.interpret(effect)
            match auth_result:
                case Err(UnhandledEffectError()):
                    pass  # Try next
                case _:
                    return auth_result

        # Try Metrics interpreter if provided
        if self.metrics is not None:
            metrics_result = await self.metrics.interpret(effect)
            match metrics_result:
                case Err(UnhandledEffectError()):
                    pass  # No one handled it
                case _:
                    return metrics_result

        # No interpreter could handle this effect
        # Build available list immutably using tuple concatenation
        available = (
            "WebSocketInterpreter",
            "DatabaseInterpreter",
            "CacheInterpreter",
            "SystemInterpreter",
            *(("MessagingInterpreter",) if self.messaging is not None else ()),
            *(("StorageInterpreter",) if self.storage is not None else ()),
            *(("AuthInterpreter",) if self.auth is not None else ()),
            *(("MetricsInterpreter",) if self.metrics is not None else ()),
        )
        return Err(
            UnhandledEffectError(
                effect=effect,
                available_interpreters=list(available),
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
    metrics_collector: MetricsCollector | None = None,
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
        metrics_collector: Optional metrics collector for Prometheus/in-memory (if metrics needed)

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

    # Create optional metrics interpreter if metrics collector provided
    metrics_interpreter = None
    if metrics_collector is not None:
        metrics_interpreter = MetricsInterpreter(collector=metrics_collector)

    return CompositeInterpreter(
        websocket=WebSocketInterpreter(connection=websocket_connection),
        database=DatabaseInterpreter(user_repo=user_repo, message_repo=message_repo),
        cache=CacheInterpreter(cache=cache),
        system=SystemInterpreter(),
        messaging=messaging_interpreter,
        storage=storage_interpreter,
        auth=auth_interpreter,
        metrics=metrics_interpreter,
    )
