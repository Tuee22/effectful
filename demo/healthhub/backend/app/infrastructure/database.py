"""Database connection management with asyncpg."""

from __future__ import annotations

import asyncpg

from app.config import Settings


class DatabaseManager:
    """Manages PostgreSQL database connection pool.

    Uses asyncpg for high-performance async PostgreSQL access.
    """

    def __init__(self, settings: Settings) -> None:
        """Initialize database manager with settings."""
        self._pool: asyncpg.Pool[asyncpg.Record] | None = None
        self._settings = settings

    async def setup(self) -> None:
        """Create database connection pool.

        Should be called once during application startup.
        """
        if self._pool is not None:
            return

        self._pool = await asyncpg.create_pool(
            host=self._settings.postgres_host,
            port=self._settings.postgres_port,
            database=self._settings.postgres_db,
            user=self._settings.postgres_user,
            password=self._settings.postgres_password,
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
