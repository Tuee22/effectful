"""
Custom asyncpg Connection type stubs without Any types.
"""

from typing import List
from asyncpg.protocol import Record

class Transaction:
    """AsyncPG Transaction with strict typing."""

    async def start(self) -> None: ...
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...

class Connection:
    """AsyncPG database connection with strict typing."""

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
    ) -> List[Record]: ...
    async def fetchrow(
        self,
        query: str,
        *args: object,
        timeout: float | None = ...,
    ) -> Record | None: ...
    async def fetchval(
        self,
        query: str,
        *args: object,
        column: int = 0,
        timeout: float | None = ...,
    ) -> object: ...
    async def close(self) -> None: ...
    def transaction(self) -> Transaction: ...
