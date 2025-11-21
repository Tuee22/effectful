"""Pytest fixtures for integration testing with real infrastructure.

This module provides fixtures that connect to real Docker services:
- PostgreSQL (asyncpg)
- Redis (redis-py async)
- MinIO S3 (boto3)

These fixtures are used by integration tests in tests/test_integration/.
Unit tests should use pytest-mock instead.
"""

import os
from collections.abc import AsyncGenerator
from uuid import uuid4

import asyncpg
import boto3
import pytest
import pytest_asyncio
from redis.asyncio import Redis

from effectful.adapters.postgres import PostgresChatMessageRepository, PostgresUserRepository
from effectful.adapters.redis_cache import RedisProfileCache
from effectful.adapters.s3_storage import S3ObjectStorage


# Environment variables for Docker services
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "effectful_test")
POSTGRES_USER = os.getenv("POSTGRES_USER", "effectful")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "effectful_pass")

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "effectful-test")


@pytest_asyncio.fixture
async def postgres_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    """Provide a PostgreSQL connection for integration tests.

    Yields:
        Active asyncpg connection

    Note:
        Creates tables if they don't exist and truncates data between tests.
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
            name VARCHAR(255) NOT NULL
        )
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
async def redis_client() -> AsyncGenerator[Redis, None]:
    """Provide a Redis client for integration tests.

    Yields:
        Active Redis async client

    Note:
        Flushes the database between tests for isolation.
    """
    client: Redis = Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

    # Clean up data before test
    await client.flushdb()

    try:
        yield client
    finally:
        await client.aclose()


@pytest.fixture
def s3_bucket() -> str:
    """Ensure test bucket exists and is clean.

    Returns:
        Bucket name for testing
    """
    # Create client inline - boto3.client returns a dynamic type
    # that satisfies S3ObjectStorage's Protocol at runtime
    s3_client = boto3.client(
        "s3",
        endpoint_url=f"http://{MINIO_ENDPOINT}",
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
        region_name="us-east-1",
    )
    bucket_name = MINIO_BUCKET

    return bucket_name


# Repository fixtures using real PostgreSQL
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


# Cache fixture using real Redis
@pytest_asyncio.fixture
async def profile_cache(redis_client: Redis) -> RedisProfileCache:
    """Provide a profile cache backed by real Redis.

    Args:
        redis_client: Active Redis async client

    Returns:
        RedisProfileCache instance
    """
    return RedisProfileCache(redis_client)


# Storage fixture using real MinIO
@pytest.fixture
def object_storage() -> S3ObjectStorage:
    """Provide object storage backed by real MinIO.

    Returns:
        S3ObjectStorage instance
    """
    # Create client inline - boto3.client returns a dynamic type
    # S3ObjectStorage uses a Protocol that matches at runtime
    s3_client = boto3.client(
        "s3",
        endpoint_url=f"http://{MINIO_ENDPOINT}",
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
        region_name="us-east-1",
    )
    return S3ObjectStorage(s3_client)


# Test data fixtures
@pytest.fixture
def test_user_id() -> str:
    """Provide a unique user ID for testing.

    Returns:
        New UUID as string
    """
    return str(uuid4())
