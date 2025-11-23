"""Pytest fixtures for integration testing with real infrastructure.

This module provides fixtures that connect to real Docker services:
- PostgreSQL (asyncpg)
- Redis (redis-py async)
- MinIO S3 (boto3)
- Apache Pulsar (pulsar-client)

These fixtures are used by integration tests in tests/integration/.
Unit tests should use pytest-mock instead.

DRY Pattern: Use clean_* fixtures to get infrastructure pre-cleaned for your test.
Each test is self-contained with declarative, idempotent initialization.
"""

import os
from collections.abc import AsyncGenerator, Generator
from uuid import uuid4

import asyncpg
import boto3
import pytest
import pytest_asyncio
from botocore.exceptions import ClientError
from redis.asyncio import Redis

from effectful.adapters.postgres import PostgresChatMessageRepository, PostgresUserRepository
from effectful.adapters.redis_auth import RedisAuthService
from effectful.adapters.redis_cache import RedisProfileCache
from effectful.adapters.s3_storage import S3ObjectStorage

import pulsar

from effectful.adapters.pulsar_messaging import PulsarMessageConsumer, PulsarMessageProducer


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

PULSAR_URL = os.getenv("PULSAR_URL", "pulsar://localhost:6650")

# JWT secret for auth testing
JWT_SECRET = os.getenv("JWT_SECRET", "test-secret-key-for-integration-tests")


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

    # Create bucket if it doesn't exist
    try:
        s3_client.head_bucket(Bucket=bucket_name)
    except ClientError as e:
        # Check if bucket doesn't exist
        error_code = e.response.get("Error", {}).get("Code", "")
        if error_code in ("404", "NoSuchBucket"):
            s3_client.create_bucket(Bucket=bucket_name)

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


# =============================================================================
# DRY Clean Fixtures - Pre-cleaned infrastructure for tests
# =============================================================================


@pytest_asyncio.fixture
async def clean_db(
    postgres_connection: asyncpg.Connection,
) -> AsyncGenerator[asyncpg.Connection, None]:
    """Provide a clean PostgreSQL database.

    Truncates all tables before yielding, ensuring test isolation.
    Tests should seed their own data after receiving this fixture.

    Yields:
        Clean asyncpg connection with empty tables
    """
    await postgres_connection.execute("TRUNCATE TABLE chat_messages, users CASCADE")
    yield postgres_connection


@pytest_asyncio.fixture
async def clean_redis(redis_client: Redis) -> AsyncGenerator[Redis, None]:
    """Provide a clean Redis instance.

    Flushes the database before yielding, ensuring test isolation.
    Tests should seed their own data after receiving this fixture.

    Yields:
        Clean Redis client with empty database
    """
    await redis_client.flushdb()
    yield redis_client


@pytest.fixture
def clean_minio(s3_bucket: str) -> str:
    """Provide a clean MinIO bucket.

    Deletes all objects in the test bucket before returning.
    Tests should upload their own objects after receiving this fixture.

    Note: This is a sync fixture that creates its own client for cleanup.

    Returns:
        Name of the clean bucket
    """
    s3_client = boto3.client(
        "s3",
        endpoint_url=f"http://{MINIO_ENDPOINT}",
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
        region_name="us-east-1",
    )

    # List and delete all objects in bucket
    try:
        response = s3_client.list_objects_v2(Bucket=s3_bucket)
        if "Contents" in response:
            for obj in response["Contents"]:
                s3_client.delete_object(Bucket=s3_bucket, Key=obj["Key"])
    except ClientError:
        # Bucket might not exist yet, that's OK
        pass

    return s3_bucket


# =============================================================================
# Pulsar Fixtures
# =============================================================================


@pytest.fixture
def pulsar_client() -> Generator[pulsar.Client, None, None]:
    """Provide a Pulsar client for integration tests.

    Returns:
        Connected Pulsar client instance
    """
    client = pulsar.Client(
        PULSAR_URL,
        operation_timeout_seconds=30,
    )
    yield client
    try:
        client.close()
    except Exception:
        # Ignore timeout errors during cleanup
        pass


@pytest.fixture
def pulsar_producer(pulsar_client: pulsar.Client) -> PulsarMessageProducer:
    """Provide a Pulsar message producer.

    Args:
        pulsar_client: Connected Pulsar client

    Returns:
        PulsarMessageProducer instance
    """
    return PulsarMessageProducer(pulsar_client)


@pytest.fixture
def pulsar_consumer(pulsar_client: pulsar.Client) -> PulsarMessageConsumer:
    """Provide a Pulsar message consumer.

    Args:
        pulsar_client: Connected Pulsar client

    Returns:
        PulsarMessageConsumer instance
    """
    return PulsarMessageConsumer(pulsar_client)


# =============================================================================
# Auth Fixtures
# =============================================================================


@pytest_asyncio.fixture
async def auth_service(clean_redis: Redis) -> RedisAuthService:
    """Provide an auth service backed by real Redis.

    Uses clean_redis to ensure test isolation - the Redis database
    is flushed before each test.

    Args:
        clean_redis: Clean Redis async client

    Returns:
        RedisAuthService instance with empty blacklist/sessions
    """
    return RedisAuthService(
        redis_client=clean_redis,
        jwt_secret=JWT_SECRET,
        jwt_algorithm="HS256",
    )


# =============================================================================
# Composite Clean Fixtures
# =============================================================================


@pytest_asyncio.fixture
async def clean_all(
    clean_db: asyncpg.Connection,
    clean_redis: Redis,
    clean_minio: str,
) -> dict[str, asyncpg.Connection | Redis | str]:
    """Provide all infrastructure clean and ready.

    Convenience fixture that combines clean_db, clean_redis, and clean_minio.
    Use for composite workflow tests that span multiple services.

    Returns:
        Dict with keys: "db", "redis", "minio"
    """
    return {
        "db": clean_db,
        "redis": clean_redis,
        "minio": clean_minio,
    }
