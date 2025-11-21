"""Messaging interpreter implementation for Pulsar effects.

This module implements the interpreter for messaging effects (PublishMessage,
ConsumeMessage, AcknowledgeMessage, NegativeAcknowledge).

Components:
    - MessagingError: Error type for messaging failures
    - MessagingInterpreter: Interpreter for messaging effects

The interpreter delegates to MessageProducer and MessageConsumer protocol
implementations, converting protocol results to Result[EffectReturn, InterpreterError].

Type Safety:
    All pattern matching is exhaustive. All return types use Result for explicit
    error handling.
"""

from dataclasses import dataclass

from effectful.algebraic.effect_return import EffectReturn
from effectful.algebraic.result import Err, Ok, Result
from effectful.domain.message_envelope import ConsumeTimeout, PublishFailure, PublishSuccess
from effectful.effects.base import Effect
from effectful.effects.messaging import (
    AcknowledgeMessage,
    ConsumeMessage,
    NegativeAcknowledge,
    PublishMessage,
)
from effectful.infrastructure.messaging import MessageConsumer, MessageProducer
from effectful.interpreters.errors import (
    InterpreterError,
    MessagingError,
    UnhandledEffectError,
)
from effectful.programs.program_types import EffectResult


@dataclass(frozen=True)
class MessagingInterpreter:
    """Interpreter for messaging effects.

    This interpreter handles PublishMessage, ConsumeMessage, AcknowledgeMessage,
    and NegativeAcknowledge effects by delegating to MessageProducer and
    MessageConsumer implementations.

    Attributes:
        producer: Message producer implementation
        consumer: Message consumer implementation

    Example:
        >>> from effectful.testing.fakes import (
        ...     FakeMessageProducer,
        ...     FakeMessageConsumer,
        ... )
        >>>
        >>> interpreter = MessagingInterpreter(
        ...     producer=FakeMessageProducer(),
        ...     consumer=FakeMessageConsumer(),
        ... )
        >>>
        >>> effect = PublishMessage(topic="events", payload=b"data")
        >>> result = await interpreter.interpret(effect)
        >>>
        >>> match result:
        ...     case Ok(EffectReturn(value=message_id, effect_name="PublishMessage")):
        ...         print(f"Published: {message_id}")
    """

    producer: MessageProducer
    consumer: MessageConsumer

    async def interpret(
        self, effect: Effect
    ) -> Result[EffectReturn[EffectResult], InterpreterError]:
        """Interpret a messaging effect.

        Args:
            effect: The effect to interpret (must be a MessagingEffect)

        Returns:
            Ok(EffectReturn) with effect result on success.
            Err(MessagingError) on infrastructure failure.
            Err(UnhandledEffectError) if effect is not a messaging effect.

        Note:
            Domain failures (publish timeout, etc.) return Ok with appropriate result.
            Only infrastructure failures return Err.
        """
        match effect:
            case PublishMessage(topic=topic, payload=payload, properties=props):
                return await self._handle_publish(topic, payload, props, effect)
            case ConsumeMessage(subscription=sub, timeout_ms=timeout):
                return await self._handle_consume(sub, timeout, effect)
            case AcknowledgeMessage(message_id=msg_id):
                return await self._handle_ack(msg_id, effect)
            case NegativeAcknowledge(message_id=msg_id, delay_ms=delay):
                return await self._handle_nack(msg_id, delay, effect)
            case _:
                return Err(
                    UnhandledEffectError(
                        effect=effect,
                        available_interpreters=["MessagingInterpreter"],
                    )
                )

    async def _handle_publish(
        self,
        topic: str,
        payload: bytes,
        properties: dict[str, str] | None,
        effect: Effect,
    ) -> Result[EffectReturn[EffectResult], InterpreterError]:
        """Handle PublishMessage effect.

        Returns:
            Ok with message_id (str) on successful publish.
            Ok with None if publish failed (domain failure - handled by program).
            Err(MessagingError) on infrastructure failure.
        """
        try:
            publish_result = await self.producer.publish(topic, payload, properties)

            # Pattern match on PublishResult ADT
            match publish_result:
                case PublishSuccess(message_id=msg_id, topic=_):
                    # Success - return message ID
                    return Ok(EffectReturn(value=msg_id, effect_name="PublishMessage"))
                case PublishFailure(topic=_, reason=reason):
                    # Domain failure (timeout, quota, topic not found)
                    # Return as error for fail-fast semantics
                    return Err(
                        MessagingError(
                            effect=effect,
                            messaging_error=f"Publish failed: {reason}",
                            is_retryable=reason in ["timeout", "quota_exceeded"],
                        )
                    )
        except Exception as e:
            # Infrastructure failure (connection error, etc.)
            return Err(
                MessagingError(
                    effect=effect,
                    messaging_error=str(e),
                    is_retryable=self._is_retryable_error(e),
                )
            )

    async def _handle_consume(
        self, subscription: str, timeout_ms: int, effect: Effect
    ) -> Result[EffectReturn[EffectResult], InterpreterError]:
        """Handle ConsumeMessage effect.

        Returns:
            Ok with MessageEnvelope on successful receive.
            Ok with ConsumeTimeout ADT on timeout (not an error - queue empty).
            Err(MessagingError) on infrastructure failure.
        """
        try:
            envelope = await self.consumer.receive(subscription, timeout_ms)
            # Return appropriate ADT based on result
            if envelope is None:
                # Timeout - return the ADT type for explicit semantics
                timeout = ConsumeTimeout(subscription=subscription, timeout_ms=timeout_ms)
                return Ok(EffectReturn(value=timeout, effect_name="ConsumeMessage"))
            return Ok(EffectReturn(value=envelope, effect_name="ConsumeMessage"))
        except Exception as e:
            return Err(
                MessagingError(
                    effect=effect,
                    messaging_error=str(e),
                    is_retryable=self._is_retryable_error(e),
                )
            )

    async def _handle_ack(
        self, message_id: str, effect: Effect
    ) -> Result[EffectReturn[EffectResult], InterpreterError]:
        """Handle AcknowledgeMessage effect.

        Returns:
            Ok with None on successful ack.
            Err(MessagingError) on infrastructure failure.
        """
        try:
            await self.consumer.acknowledge(message_id)
            return Ok(EffectReturn(value=None, effect_name="AcknowledgeMessage"))
        except Exception as e:
            return Err(
                MessagingError(
                    effect=effect,
                    messaging_error=str(e),
                    is_retryable=self._is_retryable_error(e),
                )
            )

    async def _handle_nack(
        self, message_id: str, delay_ms: int, effect: Effect
    ) -> Result[EffectReturn[EffectResult], InterpreterError]:
        """Handle NegativeAcknowledge effect.

        Returns:
            Ok with None on successful nack.
            Err(MessagingError) on infrastructure failure.
        """
        try:
            await self.consumer.negative_acknowledge(message_id, delay_ms)
            return Ok(EffectReturn(value=None, effect_name="NegativeAcknowledge"))
        except Exception as e:
            return Err(
                MessagingError(
                    effect=effect,
                    messaging_error=str(e),
                    is_retryable=self._is_retryable_error(e),
                )
            )

    def _is_retryable_error(self, error: Exception) -> bool:
        """Determine if error might succeed on retry.

        Args:
            error: The exception that occurred

        Returns:
            True if error is likely transient (connection, timeout, backpressure).
            False if error is likely permanent (config, authentication).

        Note:
            This is a heuristic based on error message patterns.
        """
        error_str = str(error).lower()
        retryable_patterns = ["connection", "timeout", "unavailable", "backpressure"]
        return any(pattern in error_str for pattern in retryable_patterns)
