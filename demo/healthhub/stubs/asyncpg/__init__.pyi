"""
Custom asyncpg type stubs without Any types.
Provides strict typing for asyncpg usage in HealthHub.
"""

from asyncpg.connection import Connection
from asyncpg.pool import Pool
from asyncpg.protocol import Record
from asyncpg.exceptions import (
    PostgresError,
    IntegrityConstraintViolationError,
    UniqueViolationError,
    ForeignKeyViolationError,
)

# Main functions
async def connect(
    host: str | None = ...,
    port: int | None = ...,
    user: str | None = ...,
    password: str | None = ...,
    database: str | None = ...,
    dsn: str | None = ...,
    **kwargs: object,
) -> Connection: ...
async def create_pool(
    dsn: str | None = ...,
    *,
    min_size: int = ...,
    max_size: int = ...,
    command_timeout: float | None = ...,
    host: str | None = ...,
    port: int | None = ...,
    user: str | None = ...,
    password: str | None = ...,
    database: str | None = ...,
    **kwargs: object,
) -> Pool[Record]: ...

# Re-exports
__all__ = [
    "Connection",
    "Pool",
    "Record",
    "connect",
    "create_pool",
    "PostgresError",
    "IntegrityConstraintViolationError",
    "UniqueViolationError",
    "ForeignKeyViolationError",
]
