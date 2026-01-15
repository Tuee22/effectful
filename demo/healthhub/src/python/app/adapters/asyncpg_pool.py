"""Production asyncpg pool adapter implementing DatabasePool protocol.

Boundary: OUTSIDE_PROOF
Target-Language: N/A (assumed correct)

Implements DatabasePool protocol via structural typing.
Wraps asyncpg for production database access.

Assumptions:
- [Library] asyncpg pool correctly manages connection lifecycle
- [Protocol] DatabasePool interface matches asyncpg behavior
"""

from typing import TYPE_CHECKING, AsyncContextManager
import asyncpg

if TYPE_CHECKING:
    from asyncpg import Pool, Record, Connection


class AsyncPgPoolAdapter:
    """Production database pool using asyncpg.

    Implements DatabasePool protocol via structural typing.
    Lifecycle managed by ApplicationContainer.

    Testing: Mock with mocker.AsyncMock(spec=DatabasePool)
    """

    def __init__(self, pool: "Pool[Record]") -> None:
        """Initialize adapter with asyncpg pool."""
        self._pool = pool

    def acquire(self) -> "AsyncContextManager[Connection]":
        """Acquire connection from pool (implements DatabasePool.acquire)."""
        return self._pool.acquire()

    async def close(self) -> None:
        """Close the pool (implements DatabasePool.close)."""
        await self._pool.close()

    async def execute(self, query: str, *args: object) -> str:
        """Execute query (implements DatabasePool.execute)."""
        return await self._pool.execute(query, *args)

    async def fetch(self, query: str, *args: object) -> "list[Record]":
        """Fetch all rows (implements DatabasePool.fetch)."""
        return await self._pool.fetch(query, *args)

    async def fetchrow(self, query: str, *args: object) -> "Record | None":
        """Fetch single row (implements DatabasePool.fetchrow)."""
        return await self._pool.fetchrow(query, *args)

    async def fetchval(self, query: str, *args: object) -> object:
        """Fetch single value (implements DatabasePool.fetchval)."""
        return await self._pool.fetchval(query, *args)
