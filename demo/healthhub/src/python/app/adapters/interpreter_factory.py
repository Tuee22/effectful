"""Production interpreter factory implementation.

Boundary: OUTSIDE_PROOF
Target-Language: N/A (assumed correct)

Provides concrete implementation of InterpreterFactory protocol for production use.
Wires together interpreters with their dependencies (pool, redis, observability).

Assumptions:
- [Lifecycle] Factory caller manages pool/redis lifecycle correctly
- [Threading] Single factory instance per request scope
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

import redis.asyncio as redis

from app.interpreters.auditing_interpreter import (
    AuditContext,
    AuditedCompositeInterpreter,
)
from app.interpreters.composite_interpreter import CompositeInterpreter
from app.protocols.database import DatabasePool
from app.protocols.observability import ObservabilityInterpreter
from app.protocols.redis_factory import RedisClientFactory

if TYPE_CHECKING:
    from redis.asyncio import Redis


class ProductionInterpreterFactory:
    """Production factory creating interpreters with managed Redis lifecycle.

    This factory creates effect interpreters with automatic Redis client
    lifecycle management. Each interpreter gets a fresh Redis client that
    is automatically cleaned up when the context exits.

    The factory implements the InterpreterFactory protocol through structural
    typing, allowing for easy test mocking.

    Example usage:
        factory = ProductionInterpreterFactory(pool, redis_factory, obs_interpreter)
        async with factory.create_composite() as interpreter:
            result = await run_program(my_program(), interpreter)
        # Redis client automatically closed
    """

    def __init__(
        self,
        database_pool: DatabasePool,
        redis_factory: RedisClientFactory,
        observability_interpreter: ObservabilityInterpreter,
    ) -> None:
        """Initialize interpreter factory with protocol dependencies.

        Args:
            database_pool: Database pool protocol for data access.
            redis_factory: Factory for creating Redis clients.
            observability_interpreter: Observability interpreter protocol for metrics.
        """
        self._database_pool = database_pool
        self._redis_factory = redis_factory
        self._observability_interpreter = observability_interpreter

    @asynccontextmanager
    async def create_composite(self) -> AsyncIterator[CompositeInterpreter]:
        """Create CompositeInterpreter with automatic Redis cleanup.

        This context manager creates a CompositeInterpreter with a fresh Redis
        client and ensures the Redis connection is properly closed when the
        context exits.

        Yields:
            A CompositeInterpreter instance with managed Redis lifecycle.

        Example:
            async with factory.create_composite() as interpreter:
                result = await run_program(my_program(), interpreter)
        """
        redis_client: "Redis[bytes]"
        async with self._redis_factory.managed() as redis_client:
            interpreter = CompositeInterpreter(
                pool=self._database_pool,
                redis_client=redis_client,
                observability_interpreter=self._observability_interpreter,
            )
            yield interpreter

    @asynccontextmanager
    async def create_audited(
        self, audit_context: AuditContext
    ) -> AsyncIterator[AuditedCompositeInterpreter]:
        """Create AuditedCompositeInterpreter with automatic Redis cleanup.

        This context manager creates an AuditedCompositeInterpreter that wraps
        a CompositeInterpreter with audit logging capabilities. The Redis client
        lifecycle is automatically managed.

        Args:
            audit_context: Audit context containing user_id, ip_address, and
                user_agent for audit trail logging.

        Yields:
            An AuditedCompositeInterpreter instance with managed Redis lifecycle.

        Example:
            context = AuditContext(user_id=uid, ip_address=ip, user_agent=ua)
            async with factory.create_audited(context) as interpreter:
                result = await run_program(my_program(), interpreter)
        """
        redis_client: "Redis[bytes]"
        async with self._redis_factory.managed() as redis_client:
            base_interpreter = CompositeInterpreter(
                pool=self._database_pool,
                redis_client=redis_client,
                observability_interpreter=self._observability_interpreter,
            )
            audited_interpreter = AuditedCompositeInterpreter(base_interpreter, audit_context)
            yield audited_interpreter
