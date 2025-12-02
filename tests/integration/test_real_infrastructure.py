"""Integration tests using real Docker infrastructure.

This module tests adapters against real services:
- PostgreSQL for user/message repositories
- Redis for profile caching
- MinIO S3 for object storage

These tests validate that adapters correctly implement protocols
when connected to actual infrastructure.
"""

import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import asyncpg
import pytest
from redis.asyncio import Redis

import boto3
from effectful.adapters.postgres import PostgresChatMessageRepository, PostgresUserRepository
from effectful.adapters.redis_cache import RedisProfileCache
from effectful.adapters.s3_storage import S3ObjectStorage
from effectful.domain.cache_result import CacheHit, CacheMiss
from effectful.domain.profile import ProfileData
from effectful.domain.s3_object import ObjectNotFound, PutSuccess, S3Object
from effectful.domain.user import User, UserFound, UserNotFound


class TestPostgresUserRepository:
    """Integration tests for PostgresUserRepository with real PostgreSQL."""

    @pytest.mark.asyncio
    async def test_get_user_not_found(self, user_repo: PostgresUserRepository) -> None:
        """get_by_id returns UserNotFound for nonexistent user."""
        user_id = uuid4()
        result = await user_repo.get_by_id(user_id)

        match result:
            case UserNotFound(user_id=uid, reason=reason):
                assert uid == user_id
                assert reason == "does_not_exist"
            case UserFound():
                pytest.fail("Expected UserNotFound, got UserFound")

    @pytest.mark.asyncio
    async def test_get_user_found(
        self, postgres_connection: asyncpg.Connection, user_repo: PostgresUserRepository
    ) -> None:
        """get_by_id returns UserFound for existing user."""
        # Insert user directly
        user_id = uuid4()
        email = f"test_{user_id}@example.com"
        name = "Test User"

        await postgres_connection.execute(
            "INSERT INTO users (id, email, name) VALUES ($1, $2, $3)",
            user_id,
            email,
            name,
        )

        # Fetch through repository
        result = await user_repo.get_by_id(user_id)

        match result:
            case UserFound(user=user, source=source):
                assert user.id == user_id
                assert user.email == email
                assert user.name == name
                assert source == "database"
            case UserNotFound():
                pytest.fail("Expected UserFound, got UserNotFound")


class TestPostgresChatMessageRepository:
    """Integration tests for PostgresChatMessageRepository with real PostgreSQL."""

    @pytest.mark.asyncio
    async def test_save_and_list_messages(
        self,
        postgres_connection: asyncpg.Connection,
        message_repo: PostgresChatMessageRepository,
    ) -> None:
        """save_message persists and list_messages_for_user retrieves."""
        # Create a user first (foreign key constraint)
        user_id = uuid4()
        await postgres_connection.execute(
            "INSERT INTO users (id, email, name) VALUES ($1, $2, $3)",
            user_id,
            f"user_{user_id}@example.com",
            "Test User",
        )

        # Save messages
        msg1 = await message_repo.save_message(user_id, "Hello")
        msg2 = await message_repo.save_message(user_id, "World")

        # Verify saved messages
        assert msg1.user_id == user_id
        assert msg1.text == "Hello"
        assert msg2.user_id == user_id
        assert msg2.text == "World"

        # List messages
        messages = await message_repo.list_messages_for_user(user_id)
        assert len(messages) == 2
        assert messages[0].text == "Hello"
        assert messages[1].text == "World"

    @pytest.mark.asyncio
    async def test_list_messages_empty(self, message_repo: PostgresChatMessageRepository) -> None:
        """list_messages_for_user returns empty list for user with no messages."""
        user_id = uuid4()
        messages = await message_repo.list_messages_for_user(user_id)
        assert messages == []


class TestRedisProfileCache:
    """Integration tests for RedisProfileCache with real Redis."""

    @pytest.mark.asyncio
    async def test_cache_miss(self, profile_cache: RedisProfileCache) -> None:
        """get_profile returns CacheMiss for nonexistent key."""
        user_id = uuid4()
        result = await profile_cache.get_profile(user_id)

        match result:
            case CacheMiss(key=key, reason=reason):
                assert key == f"profile:{user_id}"
                assert reason == "not_found"
            case CacheHit():
                pytest.fail("Expected CacheMiss, got CacheHit")

    @pytest.mark.asyncio
    async def test_put_and_get_profile(self, profile_cache: RedisProfileCache) -> None:
        """put_profile stores and get_profile retrieves with TTL."""
        user_id = uuid4()
        profile = ProfileData(id=str(user_id), name="Alice")

        # Store with 300s TTL
        await profile_cache.put_profile(user_id, profile, 300)

        # Retrieve
        result = await profile_cache.get_profile(user_id)

        match result:
            case CacheHit(value=cached_profile, ttl_remaining=ttl):
                assert cached_profile.id == str(user_id)
                assert cached_profile.name == "Alice"
                assert 0 < ttl <= 300  # TTL should be positive and <= 300
            case CacheMiss():
                pytest.fail("Expected CacheHit, got CacheMiss")

    @pytest.mark.asyncio
    async def test_cache_ttl_expiration(
        self, redis_client: Redis, profile_cache: RedisProfileCache
    ) -> None:
        """Profile expires after TTL."""
        user_id = uuid4()
        profile = ProfileData(id=str(user_id), name="Bob")

        # Store with 1 second TTL
        await profile_cache.put_profile(user_id, profile, 1)

        # Should exist immediately
        result1 = await profile_cache.get_profile(user_id)
        assert isinstance(result1, CacheHit)

        # Wait for expiration
        await asyncio.sleep(1.5)

        # Should be expired
        result2 = await profile_cache.get_profile(user_id)
        assert isinstance(result2, CacheMiss)


class TestS3ObjectStorage:
    """Integration tests for S3ObjectStorage with real MinIO."""

    @pytest.mark.asyncio
    async def test_get_nonexistent_object(
        self, object_storage: S3ObjectStorage, s3_bucket: str
    ) -> None:
        """get_object returns ObjectNotFound for nonexistent key."""
        result = await object_storage.get_object(s3_bucket, "nonexistent/key.txt")
        assert result == ObjectNotFound(bucket=s3_bucket, key="nonexistent/key.txt")

    @pytest.mark.asyncio
    async def test_put_and_get_object(
        self, object_storage: S3ObjectStorage, s3_bucket: str
    ) -> None:
        """put_object stores and get_object retrieves."""
        key = f"test/{uuid4()}/data.txt"
        content = b"Hello, World!"
        metadata = {"uploaded-by": "test-suite"}

        # Put object
        put_result = await object_storage.put_object(
            bucket=s3_bucket,
            key=key,
            content=content,
            metadata=metadata,
            content_type="text/plain",
        )

        match put_result:
            case PutSuccess(key=stored_key, bucket=stored_bucket):
                assert stored_key == key
                assert stored_bucket == s3_bucket
            case _:
                pytest.fail(f"Expected PutSuccess, got {put_result}")

        # Get object
        obj = await object_storage.get_object(s3_bucket, key)
        assert isinstance(obj, S3Object)
        assert obj.content == content
        assert obj.key == key
        assert obj.bucket == s3_bucket
        assert obj.metadata.get("uploaded-by") == "test-suite"
        assert obj.content_type == "text/plain"
        assert obj.size == len(content)

    @pytest.mark.asyncio
    async def test_delete_object(self, object_storage: S3ObjectStorage, s3_bucket: str) -> None:
        """delete_object removes object from storage."""
        key = f"test/{uuid4()}/to-delete.txt"

        # Put object first
        await object_storage.put_object(s3_bucket, key, b"delete me")

        # Verify it exists
        obj = await object_storage.get_object(s3_bucket, key)
        assert isinstance(obj, S3Object)

        # Delete
        await object_storage.delete_object(s3_bucket, key)

        # Verify it's gone
        assert await object_storage.get_object(s3_bucket, key) == ObjectNotFound(
            bucket=s3_bucket, key=key
        )

    @pytest.mark.asyncio
    async def test_delete_nonexistent_idempotent(
        self, object_storage: S3ObjectStorage, s3_bucket: str
    ) -> None:
        """delete_object is idempotent (no error for nonexistent)."""
        # Should not raise
        await object_storage.delete_object(s3_bucket, "nonexistent/key.txt")

    @pytest.mark.asyncio
    async def test_list_objects(self, object_storage: S3ObjectStorage, s3_bucket: str) -> None:
        """list_objects returns keys matching prefix."""
        prefix = f"list-test/{uuid4()}"

        # Put multiple objects
        keys = [f"{prefix}/file1.txt", f"{prefix}/file2.txt", f"{prefix}/sub/file3.txt"]
        for key in keys:
            await object_storage.put_object(s3_bucket, key, b"content")

        # List with prefix
        result = await object_storage.list_objects(s3_bucket, prefix=prefix)
        assert len(result) == 3
        for key in keys:
            assert key in result

    @pytest.mark.asyncio
    async def test_list_objects_empty(
        self, object_storage: S3ObjectStorage, s3_bucket: str
    ) -> None:
        """list_objects returns empty list for no matches."""
        result = await object_storage.list_objects(s3_bucket, prefix="nonexistent/")
        assert result == []

    @pytest.mark.asyncio
    async def test_list_objects_max_keys(
        self, object_storage: S3ObjectStorage, s3_bucket: str
    ) -> None:
        """list_objects respects max_keys limit."""
        prefix = f"max-test/{uuid4()}"

        # Put 5 objects
        for i in range(5):
            await object_storage.put_object(s3_bucket, f"{prefix}/file{i}.txt", b"x")

        # List with max_keys=3
        result = await object_storage.list_objects(s3_bucket, prefix=prefix, max_keys=3)
        assert len(result) == 3
