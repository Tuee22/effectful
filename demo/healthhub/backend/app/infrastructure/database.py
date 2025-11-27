"""Database connection management with asyncpg."""

from __future__ import annotations

import asyncpg

from app.config import settings


class DatabaseManager:
    """Manages PostgreSQL database connection pool.

    Uses asyncpg for high-performance async PostgreSQL access.
    """

    def __init__(self) -> None:
        """Initialize database manager (pool created on setup)."""
        self._pool: asyncpg.Pool[asyncpg.Record] | None = None

    async def setup(self) -> None:
        """Create database connection pool.

        Should be called once during application startup.
        """
        if self._pool is not None:
            return

        self._pool = await asyncpg.create_pool(
            host=settings.postgres_host,
            port=settings.postgres_port,
            database=settings.postgres_db,
            user=settings.postgres_user,
            password=settings.postgres_password,
            min_size=5,
            max_size=20,
            command_timeout=60.0,
        )

    async def teardown(self) -> None:
        """Close database connection pool.

        Should be called once during application shutdown.
        """
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    def get_pool(self) -> asyncpg.Pool[asyncpg.Record]:
        """Get the database connection pool.

        Raises:
            RuntimeError: If pool not initialized

        Returns:
            Database connection pool
        """
        if self._pool is None:
            raise RuntimeError("Database pool not initialized. Call setup() first.")
        return self._pool


# Global database manager instance
_db_manager: DatabaseManager | None = None


def get_database_manager() -> DatabaseManager:
    """Get the global database manager instance.

    Returns:
        Database manager singleton
    """
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager
