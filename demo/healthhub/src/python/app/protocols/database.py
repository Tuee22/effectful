"""Database pool protocol for dependency injection."""

from typing import Protocol, AsyncContextManager
import asyncpg


class DatabasePool(Protocol):
    """Protocol for database connection pool operations.

    Allows production (asyncpg.Pool) and test mocks to be injected
    without consumers knowing which implementation they're using.

    Testing: Use pytest-mock with spec=DatabasePool
    """

    def acquire(self) -> AsyncContextManager[asyncpg.Connection]:
        """Acquire a connection from the pool."""
        ...

    async def close(self) -> None:
        """Close the connection pool."""
        ...

    async def execute(self, query: str, *args: object) -> str:
        """Execute a query without returning results."""
        ...

    async def fetch(self, query: str, *args: object) -> list[asyncpg.Record]:
        """Fetch all rows matching query."""
        ...

    async def fetchrow(self, query: str, *args: object) -> asyncpg.Record | None:
        """Fetch single row matching query."""
        ...

    async def fetchval(self, query: str, *args: object) -> object:
        """Fetch single value from query result."""
        ...
