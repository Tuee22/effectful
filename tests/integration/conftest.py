"""Pytest fixtures for integration testing.

This module imports all fixtures from tests/conftest.py.
Fixtures are now centralized in tests/fixtures/ for DRY reuse.

For integration tests, fixtures connect to real Docker services:
- PostgreSQL (asyncpg)
- Redis (redis-py async)
- MinIO S3 (boto3)
- Apache Pulsar (pulsar-client)
"""

from collections.abc import AsyncGenerator

import asyncpg
import pytest_asyncio
from redis.asyncio import Redis

# All fixtures are imported from the root conftest via tests/fixtures/
# This file only contains integration-specific composite fixtures

# =============================================================================
# Composite Clean Fixtures (Integration-specific)
# =============================================================================


@pytest_asyncio.fixture
async def clean_all(
    clean_db: asyncpg.Connection,
    clean_redis: Redis,
    clean_minio: str,
) -> AsyncGenerator[dict[str, asyncpg.Connection | Redis | str], None]:
    """Provide all infrastructure clean and ready.

    Convenience fixture that combines clean_db, clean_redis, and clean_minio.
    Use for composite workflow tests that span multiple services.

    Yields:
        Dict with keys: "db", "redis", "minio"
    """
    yield {
        "db": clean_db,
        "redis": clean_redis,
        "minio": clean_minio,
    }
