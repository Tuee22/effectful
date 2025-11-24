"""Base state seeding for e2e tests.

Provides a unified base state that is seeded once and used by all e2e tests.
This ensures consistency and reduces setup time.
"""

from collections.abc import AsyncGenerator
from uuid import UUID

import asyncpg
import pytest_asyncio
from redis.asyncio import Redis

from effectful.domain.user import User

# =============================================================================
# Standard Test Users - Fixed UUIDs for predictable test data
# =============================================================================

ALICE_ID = UUID("11111111-1111-1111-1111-111111111111")
BOB_ID = UUID("22222222-2222-2222-2222-222222222222")
CHARLIE_ID = UUID("33333333-3333-3333-3333-333333333333")

ALICE = User(id=ALICE_ID, email="alice@example.com", name="Alice")
BOB = User(id=BOB_ID, email="bob@example.com", name="Bob")
CHARLIE = User(id=CHARLIE_ID, email="charlie@example.com", name="Charlie")

# Password hashes (PBKDF2-HMAC-SHA256) for test passwords
# In production these would be generated, but for tests we use fixed values
ALICE_PASSWORD = "password123"
BOB_PASSWORD = "password456"
CHARLIE_PASSWORD = "password789"

# Pre-computed PBKDF2-HMAC-SHA256 hashes in format "salt$hash"
# Format: <64 hex chars (salt)>$<64 hex chars (hash)> = 129 chars total
# These are actual hashes that can be verified by RedisAuthService
ALICE_PASSWORD_HASH = "e355e867a64144386b37bf22fc3c8aafc70ce5758bb6291352a48904b7ea46eb$4d25a45f0344604ea43acd8c16e6c429dbe6088530da69276d9eb3580b72d97a"
BOB_PASSWORD_HASH = "1778ad84654c257c5881916b89a6655e765e127e802f81692b928a2b40c63bf2$f429fc73353b7c9af5255b3a96817d9f547d7068494431559e523ece4ee75063"
CHARLIE_PASSWORD_HASH = "cc29eea7a8e674653d312a5ca2491bbebe4c77a84415fb064642156eaa4255e1$ec4742ea66aba45136865fc403530d6e3de1c72af8d089b0d2e37f2ff392f4ce"


# =============================================================================
# Base State Fixture
# =============================================================================


@pytest_asyncio.fixture
async def base_state(
    clean_db: asyncpg.Connection,
    clean_redis: Redis,
    clean_minio: str,
) -> AsyncGenerator[dict[str, asyncpg.Connection | Redis | str], None]:
    """Provide base state with seeded test data for e2e tests.

    Seeds:
    - 3 users (Alice, Bob, Charlie) with password hashes
    - Empty Redis (ready for cache/auth)
    - Empty S3 bucket (ready for storage)

    Tests can use any of the seeded data or add their own.

    Yields:
        Dict with keys: "db", "redis", "minio"
    """
    # Seed users - explicit sequential inserts following purity doctrine (no for-loops)
    await clean_db.execute(
        """
        INSERT INTO users (id, email, name, password_hash)
        VALUES ($1, $2, $3, $4)
        """,
        ALICE_ID,
        ALICE.email,
        ALICE.name,
        ALICE_PASSWORD_HASH,
    )
    await clean_db.execute(
        """
        INSERT INTO users (id, email, name, password_hash)
        VALUES ($1, $2, $3, $4)
        """,
        BOB_ID,
        BOB.email,
        BOB.name,
        BOB_PASSWORD_HASH,
    )
    await clean_db.execute(
        """
        INSERT INTO users (id, email, name, password_hash)
        VALUES ($1, $2, $3, $4)
        """,
        CHARLIE_ID,
        CHARLIE.email,
        CHARLIE.name,
        CHARLIE_PASSWORD_HASH,
    )

    yield {
        "db": clean_db,
        "redis": clean_redis,
        "minio": clean_minio,
    }


# =============================================================================
# Helper Functions for Test Data
# =============================================================================


async def get_user_count(conn: asyncpg.Connection) -> int:
    """Get the number of users in the database."""
    result = await conn.fetchval("SELECT COUNT(*) FROM users")
    if isinstance(result, int):
        return result
    return 0


async def get_message_count(conn: asyncpg.Connection) -> int:
    """Get the number of messages in the database."""
    result = await conn.fetchval("SELECT COUNT(*) FROM chat_messages")
    if isinstance(result, int):
        return result
    return 0
