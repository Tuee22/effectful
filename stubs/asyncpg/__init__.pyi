"""Type stubs for asyncpg.

Minimal stubs for the asyncpg library to satisfy mypy strict mode.
Only includes types actually used by effectful.
"""

from typing import Protocol
from datetime import datetime
from uuid import UUID

class Record(Protocol):
    """Protocol for asyncpg Record (row result)."""

    def __getitem__(self, key: str) -> UUID | str | datetime | int | None: ...

class Connection(Protocol):
    """Protocol for asyncpg Connection."""

    async def execute(
        self,
        query: str,
        *args: UUID | str | datetime | int | None,
        timeout: float | None = None,
    ) -> str: ...
    async def fetch(
        self,
        query: str,
        *args: UUID | str | datetime | int | None,
        timeout: float | None = None,
    ) -> list[Record]: ...
    async def fetchrow(
        self,
        query: str,
        *args: UUID | str | datetime | int | None,
        timeout: float | None = None,
    ) -> Record | None: ...
    async def fetchval(
        self,
        query: str,
        *args: UUID | str | datetime | int | None,
        timeout: float | None = None,
    ) -> UUID | str | datetime | int | None: ...
    async def close(self) -> None: ...

async def connect(
    dsn: str | None = None,
    *,
    host: str | None = None,
    port: int | None = None,
    user: str | None = None,
    password: str | None = None,
    database: str | None = None,
    timeout: float = 60.0,
) -> Connection: ...
