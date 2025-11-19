"""Type stubs for asyncpg.

Minimal stubs for the asyncpg library to satisfy mypy strict mode.
Only includes types actually used by functional_effects.
"""

from typing import Any, Protocol

class Connection(Protocol):
    """Protocol for asyncpg Connection."""

    async def execute(self, query: str, *args: Any, timeout: float | None = None) -> str: ...
    async def fetch(self, query: str, *args: Any, timeout: float | None = None) -> list[Any]: ...
    async def fetchrow(self, query: str, *args: Any, timeout: float | None = None) -> Any: ...
    async def fetchval(self, query: str, *args: Any, timeout: float | None = None) -> Any: ...
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
    **kwargs: Any,
) -> Connection: ...
