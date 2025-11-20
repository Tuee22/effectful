"""Integration tests for storage effect workflows.

Tests verify end-to-end storage workflows using the effect system with mock
implementations. These tests validate that storage effects compose correctly
and handle real-world scenarios.

Pattern: Layer 4 (Workflow Tests) - Uses run_ws_program() with pytest-mock.
See docs/testing/TESTING_PATTERNS.md for comprehensive testing guidelines.

Coverage: 100% of storage workflow patterns.
"""

from collections.abc import Generator
from datetime import UTC, datetime

import pytest
from pytest_mock import MockerFixture

from effectful.algebraic.result import Err, Ok
from effectful.domain.s3_object import PutSuccess, S3Object
from effectful.effects.storage import DeleteObject, GetObject, ListObjects, PutObject
from effectful.infrastructure.storage import ObjectStorage
from effectful.interpreters.errors import StorageError
from effectful.interpreters.storage import StorageInterpreter
from effectful.programs.program_types import AllEffects, EffectResult
from effectful.programs.runners import run_ws_program


class TestBasicStorageWorkflows:
    """Tests for basic storage operations."""

    @pytest.mark.asyncio()
    async def test_put_and_get_workflow(self, mocker: MockerFixture) -> None:
        """Should put object and retrieve it successfully."""
        # Arrange - Create in-memory storage simulation
        storage_dict: dict[tuple[str, str], S3Object] = {}

        async def mock_put_object(
            bucket: str,
            key: str,
            content: bytes,
            metadata: dict[str, str] | None = None,
            content_type: str | None = None,
        ) -> PutSuccess:
            storage_dict[(bucket, key)] = S3Object(
                key=key,
                bucket=bucket,
                content=content,
                last_modified=datetime.now(UTC),
                metadata=metadata or {},
                content_type=content_type,
                size=len(content),
                version_id="v1",
            )
            return PutSuccess(key=key, bucket=bucket, version_id="v1")

        async def mock_get_object(bucket: str, key: str) -> S3Object | None:
            return storage_dict.get((bucket, key))

        # Setup mock storage
        storage = mocker.AsyncMock(spec=ObjectStorage)
        storage.put_object.side_effect = mock_put_object
        storage.get_object.side_effect = mock_get_object

        interpreter = StorageInterpreter(storage=storage)

        # Define workflow program
        def put_and_get_program() -> Generator[AllEffects, EffectResult, bytes]:
            """Put object, then get it back."""
            # Put object
            key_result = yield PutObject(
                bucket="my-bucket",
                key="data/file.txt",
                content=b"test data",
                metadata={"author": "test"},
                content_type="text/plain",
            )
            assert isinstance(key_result, str)

            # Get object back
            obj_result = yield GetObject(bucket="my-bucket", key="data/file.txt")
            assert isinstance(obj_result, S3Object)

            return obj_result.content

        # Act
        result = await run_ws_program(put_and_get_program(), interpreter)

        # Assert
        match result:
            case Ok(content):
                assert content == b"test data"
                # Verify mock interactions
                storage.put_object.assert_called_once_with(
                    "my-bucket",
                    "data/file.txt",
                    b"test data",
                    {"author": "test"},
                    "text/plain",
                )
                storage.get_object.assert_called_once_with("my-bucket", "data/file.txt")
            case Err(error):
                pytest.fail(f"Expected Ok, got Err({error})")

    @pytest.mark.asyncio()
    async def test_get_nonexistent_object(self, mocker: MockerFixture) -> None:
        """Should return None for nonexistent object."""
        # Arrange
        storage = mocker.AsyncMock(spec=ObjectStorage)
        storage.get_object.return_value = None

        interpreter = StorageInterpreter(storage=storage)

        # Define workflow
        def get_missing_program() -> Generator[AllEffects, EffectResult, bool]:
            """Try to get nonexistent object."""
            obj_result = yield GetObject(bucket="my-bucket", key="missing.txt")
            return obj_result is None

        # Act
        result = await run_ws_program(get_missing_program(), interpreter)

        # Assert
        match result:
            case Ok(is_none):
                assert is_none is True
                storage.get_object.assert_called_once_with("my-bucket", "missing.txt")
            case Err(error):
                pytest.fail(f"Expected Ok, got Err({error})")

    @pytest.mark.asyncio()
    async def test_delete_workflow(self, mocker: MockerFixture) -> None:
        """Should put, verify, delete, and verify deletion."""
        # Arrange - Stateful storage simulation
        storage_dict: dict[tuple[str, str], S3Object] = {}

        async def mock_put_object(
            bucket: str,
            key: str,
            content: bytes,
            metadata: dict[str, str] | None = None,
            content_type: str | None = None,
        ) -> PutSuccess:
            storage_dict[(bucket, key)] = S3Object(
                key=key,
                bucket=bucket,
                content=content,
                last_modified=datetime.now(UTC),
                metadata=metadata or {},
                content_type=content_type,
                size=len(content),
                version_id="v1",
            )
            return PutSuccess(key=key, bucket=bucket, version_id="v1")

        async def mock_get_object(bucket: str, key: str) -> S3Object | None:
            return storage_dict.get((bucket, key))

        async def mock_delete_object(bucket: str, key: str) -> None:
            storage_dict.pop((bucket, key), None)

        storage = mocker.AsyncMock(spec=ObjectStorage)
        storage.put_object.side_effect = mock_put_object
        storage.get_object.side_effect = mock_get_object
        storage.delete_object.side_effect = mock_delete_object

        interpreter = StorageInterpreter(storage=storage)

        # Define workflow
        def delete_workflow_program() -> Generator[AllEffects, EffectResult, bool]:
            """Put, verify exists, delete, verify deleted."""
            # Put object
            key_result = yield PutObject(
                bucket="my-bucket", key="temp.txt", content=b"temporary data"
            )
            assert isinstance(key_result, str)

            # Verify exists
            obj1 = yield GetObject(bucket="my-bucket", key="temp.txt")
            assert isinstance(obj1, S3Object)

            # Delete
            yield DeleteObject(bucket="my-bucket", key="temp.txt")

            # Verify deleted
            obj2 = yield GetObject(bucket="my-bucket", key="temp.txt")
            return obj2 is None

        # Act
        result = await run_ws_program(delete_workflow_program(), interpreter)

        # Assert
        match result:
            case Ok(was_deleted):
                assert was_deleted is True
                storage.delete_object.assert_called_once_with("my-bucket", "temp.txt")
            case Err(error):
                pytest.fail(f"Expected Ok, got Err({error})")

    @pytest.mark.asyncio()
    async def test_list_objects_workflow(self, mocker: MockerFixture) -> None:
        """Should list objects with prefix filtering."""
        # Arrange
        storage = mocker.AsyncMock(spec=ObjectStorage)
        storage.list_objects.return_value = ["data/file1.txt", "data/file2.txt"]

        interpreter = StorageInterpreter(storage=storage)

        # Define workflow
        def list_program() -> Generator[AllEffects, EffectResult, int]:
            """List objects and count them."""
            keys_result = yield ListObjects(
                bucket="my-bucket", prefix="data/", max_keys=100
            )
            assert isinstance(keys_result, list)
            return len(keys_result)

        # Act
        result = await run_ws_program(list_program(), interpreter)

        # Assert
        match result:
            case Ok(count):
                assert count == 2
                storage.list_objects.assert_called_once_with("my-bucket", "data/", 100)
            case Err(error):
                pytest.fail(f"Expected Ok, got Err({error})")


class TestStorageErrorHandling:
    """Tests for storage error scenarios."""

    @pytest.mark.asyncio()
    async def test_put_failure_quota_exceeded(self, mocker: MockerFixture) -> None:
        """Should handle quota exceeded error (retryable)."""
        # Arrange
        storage = mocker.AsyncMock(spec=ObjectStorage)
        storage.put_object.side_effect = RuntimeError("quota_exceeded")

        interpreter = StorageInterpreter(storage=storage)

        # Define workflow
        def put_program() -> Generator[AllEffects, EffectResult, str]:
            """Try to put object."""
            key = yield PutObject(bucket="my-bucket", key="file.txt", content=b"data")
            return key  # type: ignore

        # Act
        result = await run_ws_program(put_program(), interpreter)

        # Assert
        match result:
            case Err(error):
                assert isinstance(error, StorageError)
                assert "quota_exceeded" in error.storage_error
                assert error.is_retryable is True
            case Ok(value):
                pytest.fail(f"Expected Err(StorageError), got Ok({value})")

    @pytest.mark.asyncio()
    async def test_put_failure_permission_denied(self, mocker: MockerFixture) -> None:
        """Should handle permission denied error (non-retryable)."""
        # Arrange
        storage = mocker.AsyncMock(spec=ObjectStorage)
        storage.put_object.side_effect = PermissionError("access denied")

        interpreter = StorageInterpreter(storage=storage)

        # Define workflow
        def put_program() -> Generator[AllEffects, EffectResult, str]:
            """Try to put object."""
            key = yield PutObject(bucket="my-bucket", key="file.txt", content=b"data")
            return key  # type: ignore

        # Act
        result = await run_ws_program(put_program(), interpreter)

        # Assert
        match result:
            case Err(error):
                assert isinstance(error, StorageError)
                assert "access denied" in error.storage_error
                assert error.is_retryable is False
            case Ok(value):
                pytest.fail(f"Expected Err(StorageError), got Ok({value})")

    @pytest.mark.asyncio()
    async def test_put_failure_invalid_object_state(
        self, mocker: MockerFixture
    ) -> None:
        """Should handle invalid object state error (non-retryable)."""
        # Arrange
        storage = mocker.AsyncMock(spec=ObjectStorage)
        storage.put_object.side_effect = RuntimeError("invalid_object_state")

        interpreter = StorageInterpreter(storage=storage)

        # Define workflow
        def put_program() -> Generator[AllEffects, EffectResult, str]:
            """Try to put object."""
            key = yield PutObject(bucket="my-bucket", key="file.txt", content=b"data")
            return key  # type: ignore

        # Act
        result = await run_ws_program(put_program(), interpreter)

        # Assert
        match result:
            case Err(error):
                assert isinstance(error, StorageError)
                assert "invalid_object_state" in error.storage_error
                assert error.is_retryable is False
            case Ok(value):
                pytest.fail(f"Expected Err(StorageError), got Ok({value})")

    @pytest.mark.asyncio()
    async def test_get_failure_exception(self, mocker: MockerFixture) -> None:
        """Should handle get object exception."""
        # Arrange
        storage = mocker.AsyncMock(spec=ObjectStorage)
        storage.get_object.side_effect = RuntimeError("connection_timeout")

        interpreter = StorageInterpreter(storage=storage)

        # Define workflow
        def get_program() -> Generator[AllEffects, EffectResult, S3Object | None]:
            """Try to get object."""
            obj = yield GetObject(bucket="my-bucket", key="file.txt")
            return obj  # type: ignore

        # Act
        result = await run_ws_program(get_program(), interpreter)

        # Assert
        match result:
            case Err(error):
                assert isinstance(error, StorageError)
                assert "connection_timeout" in error.storage_error
                assert error.is_retryable is True
            case Ok(value):
                pytest.fail(f"Expected Err(StorageError), got Ok({value})")

    @pytest.mark.asyncio()
    async def test_delete_failure_exception(self, mocker: MockerFixture) -> None:
        """Should handle delete object exception."""
        # Arrange
        storage = mocker.AsyncMock(spec=ObjectStorage)
        storage.delete_object.side_effect = RuntimeError("service_unavailable")

        interpreter = StorageInterpreter(storage=storage)

        # Define workflow
        def delete_program() -> Generator[AllEffects, EffectResult, None]:
            """Try to delete object."""
            yield DeleteObject(bucket="my-bucket", key="file.txt")
            return None

        # Act
        result = await run_ws_program(delete_program(), interpreter)

        # Assert
        match result:
            case Err(error):
                assert isinstance(error, StorageError)
                assert "service_unavailable" in error.storage_error
                assert error.is_retryable is True
            case Ok(value):
                pytest.fail(f"Expected Err(StorageError), got Ok({value})")

    @pytest.mark.asyncio()
    async def test_list_failure_exception(self, mocker: MockerFixture) -> None:
        """Should handle list objects exception."""
        # Arrange
        storage = mocker.AsyncMock(spec=ObjectStorage)
        storage.list_objects.side_effect = RuntimeError("timeout")

        interpreter = StorageInterpreter(storage=storage)

        # Define workflow
        def list_program() -> Generator[AllEffects, EffectResult, list[str]]:
            """Try to list objects."""
            keys = yield ListObjects(bucket="my-bucket")
            return keys  # type: ignore

        # Act
        result = await run_ws_program(list_program(), interpreter)

        # Assert
        match result:
            case Err(error):
                assert isinstance(error, StorageError)
                assert "timeout" in error.storage_error
                assert error.is_retryable is True
            case Ok(value):
                pytest.fail(f"Expected Err(StorageError), got Ok({value})")


class TestComplexStorageWorkflows:
    """Tests for complex multi-step storage workflows."""

    @pytest.mark.asyncio()
    async def test_backup_workflow(self, mocker: MockerFixture) -> None:
        """Should copy object from source to backup bucket."""
        # Arrange - Stateful storage
        source_dict: dict[tuple[str, str], S3Object] = {}
        backup_dict: dict[tuple[str, str], S3Object] = {}

        # Seed source bucket
        source_dict[("source-bucket", "data.txt")] = S3Object(
            key="data.txt",
            bucket="source-bucket",
            content=b"important data",
            last_modified=datetime.now(UTC),
            metadata={},
            content_type="text/plain",
            size=14,
            version_id="v1",
        )

        async def mock_get_object(bucket: str, key: str) -> S3Object | None:
            if bucket == "source-bucket":
                return source_dict.get((bucket, key))
            return backup_dict.get((bucket, key))

        async def mock_put_object(
            bucket: str,
            key: str,
            content: bytes,
            metadata: dict[str, str] | None = None,
            content_type: str | None = None,
        ) -> PutSuccess:
            if bucket == "backup-bucket":
                backup_dict[(bucket, key)] = S3Object(
                    key=key,
                    bucket=bucket,
                    content=content,
                    last_modified=datetime.now(UTC),
                    metadata=metadata or {},
                    content_type=content_type,
                    size=len(content),
                    version_id="v2",
                )
            return PutSuccess(key=key, bucket=bucket, version_id="v2")

        storage = mocker.AsyncMock(spec=ObjectStorage)
        storage.get_object.side_effect = mock_get_object
        storage.put_object.side_effect = mock_put_object

        interpreter = StorageInterpreter(storage=storage)

        # Define workflow
        def backup_program() -> Generator[AllEffects, EffectResult, bool]:
            """Get from source, put to backup."""
            # Get from source
            obj = yield GetObject(bucket="source-bucket", key="data.txt")
            assert isinstance(obj, S3Object)

            # Put to backup
            key = yield PutObject(
                bucket="backup-bucket",
                key="data.txt",
                content=obj.content,
                metadata=obj.metadata,
                content_type=obj.content_type,
            )
            assert isinstance(key, str)

            return True

        # Act
        result = await run_ws_program(backup_program(), interpreter)

        # Assert
        match result:
            case Ok(success):
                assert success is True
                assert storage.get_object.call_count == 1
                assert storage.put_object.call_count == 1
            case Err(error):
                pytest.fail(f"Expected Ok, got Err({error})")

    @pytest.mark.asyncio()
    async def test_cleanup_old_files_workflow(self, mocker: MockerFixture) -> None:
        """Should list and delete multiple objects."""
        # Arrange
        storage = mocker.AsyncMock(spec=ObjectStorage)
        storage.list_objects.return_value = [
            "temp/file1.txt",
            "temp/file2.txt",
            "temp/file3.txt",
        ]

        interpreter = StorageInterpreter(storage=storage)

        # Define workflow
        def cleanup_program() -> Generator[AllEffects, EffectResult, int]:
            """List temp files and delete them."""
            # List files
            keys_result = yield ListObjects(bucket="my-bucket", prefix="temp/")
            assert isinstance(keys_result, list)

            # Delete each file
            deleted_count = 0
            for key in keys_result:
                assert isinstance(key, str)
                yield DeleteObject(bucket="my-bucket", key=key)
                deleted_count += 1

            return deleted_count

        # Act
        result = await run_ws_program(cleanup_program(), interpreter)

        # Assert
        match result:
            case Ok(count):
                assert count == 3
                assert storage.list_objects.call_count == 1
                assert storage.delete_object.call_count == 3
            case Err(error):
                pytest.fail(f"Expected Ok, got Err({error})")

    @pytest.mark.asyncio()
    async def test_conditional_put_workflow(self, mocker: MockerFixture) -> None:
        """Should check if object exists before putting."""
        # Arrange
        storage = mocker.AsyncMock(spec=ObjectStorage)
        storage.get_object.return_value = None  # Object doesn't exist
        storage.put_object.return_value = PutSuccess(
            key="data/new-file.txt", bucket="my-bucket", version_id="v1"
        )

        interpreter = StorageInterpreter(storage=storage)

        # Define workflow
        def conditional_put_program() -> Generator[AllEffects, EffectResult, str]:
            """Put only if object doesn't exist."""
            # Check if exists
            existing = yield GetObject(bucket="my-bucket", key="data/new-file.txt")

            if existing is not None:
                return "already_exists"

            # Doesn't exist - put it
            key = yield PutObject(
                bucket="my-bucket",
                key="data/new-file.txt",
                content=b"new content",
            )
            assert isinstance(key, str)

            return "created"

        # Act
        result = await run_ws_program(conditional_put_program(), interpreter)

        # Assert
        match result:
            case Ok(status):
                assert status == "created"
                storage.get_object.assert_called_once()
                storage.put_object.assert_called_once()
            case Err(error):
                pytest.fail(f"Expected Ok, got Err({error})")
