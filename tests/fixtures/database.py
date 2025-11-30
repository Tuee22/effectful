"""PostgreSQL fixtures for integration and e2e testing.

Provides fixtures for:
- Database connections
- Table creation and cleanup
- User and message repositories
"""

from collections.abc import AsyncGenerator

import asyncpg
import pytest_asyncio

from effectful.adapters.postgres import PostgresChatMessageRepository, PostgresUserRepository
from tests.fixtures.config import (
    POSTGRES_DB,
    POSTGRES_HOST,
    POSTGRES_PASSWORD,
    POSTGRES_PORT,
    POSTGRES_USER,
)


@pytest_asyncio.fixture
async def postgres_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    """Provide a PostgreSQL connection for integration tests.

    Creates tables if they don't exist and truncates data between tests.

    Yields:
        Active asyncpg connection
    """
    conn = await asyncpg.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        database=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
    )

    # Create tables if they don't exist
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY,
            email VARCHAR(255) NOT NULL UNIQUE,
            name VARCHAR(255) NOT NULL,
            password_hash VARCHAR(255)
        )
    """
    )
    # Add password_hash column if it doesn't exist (for migrations)
    await conn.execute(
        """
        ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255)
    """
    )
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_messages (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users(id),
            text TEXT NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL
        )
    """
    )

    # Clean up data before test
    await conn.execute("TRUNCATE TABLE chat_messages, users CASCADE")

    try:
        yield conn
    finally:
        await conn.close()


@pytest_asyncio.fixture
async def clean_db(
    postgres_connection: asyncpg.Connection,
) -> AsyncGenerator[asyncpg.Connection, None]:
    """Provide a clean PostgreSQL database.

    Truncates all tables before AND after yielding, ensuring test isolation
    even when tests fail.

    Yields:
        Clean asyncpg connection with empty tables

    Note:
        Pre-cleanup: Ensures clean starting state
        Post-cleanup: Prevents orphaned data when tests fail
    """
    # PRE-CLEANUP: Clean up BEFORE test runs
    await postgres_connection.execute("TRUNCATE TABLE chat_messages, users CASCADE")

    yield postgres_connection

    # POST-CLEANUP: Prevent data leaks on test failure
    try:
        await postgres_connection.execute("TRUNCATE TABLE chat_messages, users CASCADE")
    except Exception:
        # Ignore cleanup errors - test isolation is more important
        pass


@pytest_asyncio.fixture
async def user_repo(
    postgres_connection: asyncpg.Connection,
) -> PostgresUserRepository:
    """Provide a user repository backed by real PostgreSQL.

    Args:
        postgres_connection: Active asyncpg connection

    Returns:
        PostgresUserRepository instance
    """
    return PostgresUserRepository(postgres_connection)


@pytest_asyncio.fixture
async def message_repo(
    postgres_connection: asyncpg.Connection,
) -> PostgresChatMessageRepository:
    """Provide a message repository backed by real PostgreSQL.

    Args:
        postgres_connection: Active asyncpg connection

    Returns:
        PostgresChatMessageRepository instance
    """
    return PostgresChatMessageRepository(postgres_connection)
