"""
Custom asyncpg Pool type stubs without Any types.
"""

from typing import Generic, TypeVar
from types import TracebackType
from collections.abc import Awaitable, Generator
from asyncpg.connection import Connection
from asyncpg.protocol import Record

_RecordT = TypeVar("_RecordT", bound=Record)


class PoolAcquireContext(Awaitable[Connection]):
    """Context manager for pool.acquire() - also awaitable."""

    async def __aenter__(self) -> Connection: ...
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None: ...
    def __await__(self) -> Generator[object, None, Connection]: ...


class Pool(Generic[_RecordT]):
    """AsyncPG connection pool with strict typing."""

    def acquire(self, *, timeout: float | None = ...) -> PoolAcquireContext: ...
    async def release(self, connection: Connection) -> None: ...
    async def close(self) -> None: ...
    def get_size(self) -> int: ...
    def get_idle_size(self) -> int: ...
    def get_min_size(self) -> int: ...
    def get_max_size(self) -> int: ...
    # Direct query methods (pool can be used like a connection)
    async def execute(
        self,
        query: str,
        *args: object,
        timeout: float | None = ...,
    ) -> str: ...
    async def fetch(
        self,
        query: str,
        *args: object,
        timeout: float | None = ...,
    ) -> list[_RecordT]: ...
    async def fetchrow(
        self,
        query: str,
        *args: object,
        timeout: float | None = ...,
    ) -> _RecordT | None: ...
    async def fetchval(
        self,
        query: str,
        *args: object,
        column: int = 0,
        timeout: float | None = ...,
    ) -> object: ...
