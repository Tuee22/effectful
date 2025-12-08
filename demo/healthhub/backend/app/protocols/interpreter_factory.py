"""Interpreter factory protocol.

Defines the interface for creating effect interpreters with managed Redis lifecycle.
"""

from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from app.interpreters.auditing_interpreter import (
        AuditContext,
        AuditedCompositeInterpreter,
    )
    from app.interpreters.composite_interpreter import CompositeInterpreter


class InterpreterFactory(Protocol):
    """Protocol for creating interpreters with managed Redis lifecycle.

    This protocol defines the interface for factories that create effect
    interpreters with automatic Redis client lifecycle management. The factory
    ensures that Redis connections are properly created and cleaned up for
    each request.

    Example usage:
        async with factory.create_composite() as interpreter:
            result = await run_program(my_program(), interpreter)
        # Redis client automatically closed after context
    """

    def create_composite(self) -> AbstractAsyncContextManager["CompositeInterpreter"]:
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
        ...

    def create_audited(
        self, audit_context: "AuditContext"
    ) -> AbstractAsyncContextManager["AuditedCompositeInterpreter"]:
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
        ...
