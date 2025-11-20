"""Unit tests for StorageInterpreter.

Tests verify that the storage interpreter correctly handles all storage effects,
delegates to ObjectStorage protocol implementations, and converts results to
Result[EffectReturn, InterpreterError].

Coverage: 100% of storage interpreter module.
"""

import pytest
from pytest_mock import MockerFixture

from effectful.algebraic.effect_return import EffectReturn
from effectful.algebraic.result import Err, Ok
from effectful.domain.s3_object import PutFailure, PutSuccess, S3Object
from effectful.effects.base import Effect
from effectful.effects.storage import DeleteObject, GetObject, ListObjects, PutObject
from effectful.infrastructure.storage import ObjectStorage
from effectful.interpreters.errors import StorageError, UnhandledEffectError
from effectful.interpreters.storage import StorageInterpreter


class TestStorageInterpreterGetObject:
    """Tests for StorageInterpreter handling GetObject effects."""

    @pytest.mark.asyncio
    async def test_get_object_success(self, mocker: MockerFixture) -> None:
        """GetObject should return Ok with S3Object when object exists."""
        # Arrange
        effect = GetObject(bucket="my-bucket", key="data/file.txt")
        s3_object = mocker.Mock(spec=S3Object)
        s3_object.key = "data/file.txt"
        s3_object.bucket = "my-bucket"
        s3_object.content = b"test data"

        storage = mocker.AsyncMock(spec=ObjectStorage)
        storage.get_object.return_value = s3_object

        interpreter = StorageInterpreter(storage=storage)

        # Act
        result = await interpreter.interpret(effect)

        # Assert
        storage.get_object.assert_awaited_once_with("my-bucket", "data/file.txt")

        match result:
            case Ok(EffectReturn(value=obj, effect_name="GetObject")):
                from effectful.domain.s3_object import S3Object as S3Obj

                assert isinstance(obj, S3Obj)
                assert obj.key == "data/file.txt"
            case _:
                pytest.fail(f"Expected Ok with S3Object, got {result}")

    @pytest.mark.asyncio
    async def test_get_object_not_found(self, mocker: MockerFixture) -> None:
        """GetObject should return Ok with None when object does not exist."""
        # Arrange
        effect = GetObject(bucket="my-bucket", key="missing.txt")

        storage = mocker.AsyncMock(spec=ObjectStorage)
        storage.get_object.return_value = None

        interpreter = StorageInterpreter(storage=storage)

        # Act
        result = await interpreter.interpret(effect)

        # Assert
        storage.get_object.assert_awaited_once_with("my-bucket", "missing.txt")

        match result:
            case Ok(EffectReturn(value=None, effect_name="GetObject")):
                assert True  # Expected
            case _:
                pytest.fail(f"Expected Ok with None, got {result}")

    @pytest.mark.asyncio
    async def test_get_object_retryable_exception(self, mocker: MockerFixture) -> None:
        """GetObject should return Err with retryable=True for network errors."""
        # Arrange
        effect = GetObject(bucket="my-bucket", key="data/file.txt")

        storage = mocker.AsyncMock(spec=ObjectStorage)
        storage.get_object.side_effect = RuntimeError("Connection timeout")

        interpreter = StorageInterpreter(storage=storage)

        # Act
        result = await interpreter.interpret(effect)

        # Assert
        match result:
            case Err(StorageError(effect=e, storage_error=msg, is_retryable=True)):
                assert e is effect
                assert "Connection timeout" in msg
            case _:
                pytest.fail(f"Expected Err with retryable=True, got {result}")

    @pytest.mark.asyncio
    async def test_get_object_non_retryable_exception(self, mocker: MockerFixture) -> None:
        """GetObject should return Err with retryable=False for config errors."""
        # Arrange
        effect = GetObject(bucket="my-bucket", key="data/file.txt")

        storage = mocker.AsyncMock(spec=ObjectStorage)
        storage.get_object.side_effect = RuntimeError("Access denied")

        interpreter = StorageInterpreter(storage=storage)

        # Act
        result = await interpreter.interpret(effect)

        # Assert
        match result:
            case Err(StorageError(effect=e, storage_error=msg, is_retryable=False)):
                assert e is effect
                assert "Access denied" in msg
            case _:
                pytest.fail(f"Expected Err with retryable=False, got {result}")


class TestStorageInterpreterPutObject:
    """Tests for StorageInterpreter handling PutObject effects."""

    @pytest.mark.asyncio
    async def test_put_object_success(self, mocker: MockerFixture) -> None:
        """PutObject should return Ok with key when put succeeds."""
        # Arrange
        effect = PutObject(
            bucket="my-bucket",
            key="data/file.txt",
            content=b"test data",
            metadata={"uploaded-by": "user-123"},
            content_type="text/plain",
        )

        storage = mocker.AsyncMock(spec=ObjectStorage)
        storage.put_object.return_value = PutSuccess(
            key="data/file.txt", bucket="my-bucket", version_id="v1"
        )

        interpreter = StorageInterpreter(storage=storage)

        # Act
        result = await interpreter.interpret(effect)

        # Assert
        storage.put_object.assert_awaited_once_with(
            "my-bucket",
            "data/file.txt",
            b"test data",
            {"uploaded-by": "user-123"},
            "text/plain",
        )

        match result:
            case Ok(EffectReturn(value=key, effect_name="PutObject")):
                assert key == "data/file.txt"
            case _:
                pytest.fail(f"Expected Ok with key, got {result}")

    @pytest.mark.asyncio
    async def test_put_object_with_metadata(self, mocker: MockerFixture) -> None:
        """PutObject should pass metadata to storage implementation."""
        # Arrange
        effect = PutObject(
            bucket="bucket",
            key="key",
            content=b"data",
            metadata={"key1": "value1", "key2": "value2"},
            content_type=None,
        )

        storage = mocker.AsyncMock(spec=ObjectStorage)
        storage.put_object.return_value = PutSuccess(
            key="key", bucket="bucket", version_id="v1"
        )

        interpreter = StorageInterpreter(storage=storage)

        # Act
        result = await interpreter.interpret(effect)

        # Assert
        storage.put_object.assert_awaited_once_with(
            "bucket", "key", b"data", {"key1": "value1", "key2": "value2"}, None
        )

        match result:
            case Ok(EffectReturn(value="key", effect_name="PutObject")):
                assert True  # Expected
            case _:
                pytest.fail(f"Expected Ok, got {result}")

    @pytest.mark.asyncio
    async def test_put_object_failure_quota_exceeded(self, mocker: MockerFixture) -> None:
        """PutObject should return Err with retryable=True for quota_exceeded."""
        # Arrange
        effect = PutObject(bucket="bucket", key="key", content=b"data")

        storage = mocker.AsyncMock(spec=ObjectStorage)
        storage.put_object.return_value = PutFailure(
            key="key", bucket="bucket", reason="quota_exceeded"
        )

        interpreter = StorageInterpreter(storage=storage)

        # Act
        result = await interpreter.interpret(effect)

        # Assert
        match result:
            case Err(StorageError(effect=e, storage_error=msg, is_retryable=True)):
                assert e is effect
                assert "quota_exceeded" in msg
            case _:
                pytest.fail(f"Expected Err with retryable=True, got {result}")

    @pytest.mark.asyncio
    async def test_put_object_failure_permission_denied(
        self, mocker: MockerFixture
    ) -> None:
        """PutObject should return Err with retryable=False for permission_denied."""
        # Arrange
        effect = PutObject(bucket="bucket", key="key", content=b"data")

        storage = mocker.AsyncMock(spec=ObjectStorage)
        storage.put_object.return_value = PutFailure(
            key="key", bucket="bucket", reason="permission_denied"
        )

        interpreter = StorageInterpreter(storage=storage)

        # Act
        result = await interpreter.interpret(effect)

        # Assert
        match result:
            case Err(StorageError(effect=e, storage_error=msg, is_retryable=False)):
                assert e is effect
                assert "permission_denied" in msg
            case _:
                pytest.fail(f"Expected Err with retryable=False, got {result}")

    @pytest.mark.asyncio
    async def test_put_object_failure_invalid_object_state(
        self, mocker: MockerFixture
    ) -> None:
        """PutObject should return Err with retryable=True for invalid_object_state."""
        # Arrange
        effect = PutObject(bucket="bucket", key="key", content=b"data")

        storage = mocker.AsyncMock(spec=ObjectStorage)
        storage.put_object.return_value = PutFailure(
            key="key", bucket="bucket", reason="invalid_object_state"
        )

        interpreter = StorageInterpreter(storage=storage)

        # Act
        result = await interpreter.interpret(effect)

        # Assert
        match result:
            case Err(StorageError(effect=e, storage_error=msg, is_retryable=True)):
                assert e is effect
                assert "invalid_object_state" in msg
            case _:
                pytest.fail(f"Expected Err with retryable=True, got {result}")

    @pytest.mark.asyncio
    async def test_put_object_exception(self, mocker: MockerFixture) -> None:
        """PutObject should return Err when storage raises exception."""
        # Arrange
        effect = PutObject(bucket="bucket", key="key", content=b"data")

        storage = mocker.AsyncMock(spec=ObjectStorage)
        storage.put_object.side_effect = RuntimeError("Network error")

        interpreter = StorageInterpreter(storage=storage)

        # Act
        result = await interpreter.interpret(effect)

        # Assert
        match result:
            case Err(StorageError(effect=e, storage_error=msg, is_retryable=True)):
                assert e is effect
                assert "Network error" in msg
            case _:
                pytest.fail(f"Expected Err, got {result}")


class TestStorageInterpreterDeleteObject:
    """Tests for StorageInterpreter handling DeleteObject effects."""

    @pytest.mark.asyncio
    async def test_delete_object_success(self, mocker: MockerFixture) -> None:
        """DeleteObject should return Ok with None when delete succeeds."""
        # Arrange
        effect = DeleteObject(bucket="my-bucket", key="data/file.txt")

        storage = mocker.AsyncMock(spec=ObjectStorage)
        storage.delete_object.return_value = None

        interpreter = StorageInterpreter(storage=storage)

        # Act
        result = await interpreter.interpret(effect)

        # Assert
        storage.delete_object.assert_awaited_once_with("my-bucket", "data/file.txt")

        match result:
            case Ok(EffectReturn(value=None, effect_name="DeleteObject")):
                assert True  # Expected
            case _:
                pytest.fail(f"Expected Ok with None, got {result}")

    @pytest.mark.asyncio
    async def test_delete_object_exception(self, mocker: MockerFixture) -> None:
        """DeleteObject should return Err when storage raises exception."""
        # Arrange
        effect = DeleteObject(bucket="bucket", key="key")

        storage = mocker.AsyncMock(spec=ObjectStorage)
        storage.delete_object.side_effect = RuntimeError("Access denied")

        interpreter = StorageInterpreter(storage=storage)

        # Act
        result = await interpreter.interpret(effect)

        # Assert
        match result:
            case Err(StorageError(effect=e, storage_error=msg, is_retryable=False)):
                assert e is effect
                assert "Access denied" in msg
            case _:
                pytest.fail(f"Expected Err, got {result}")


class TestStorageInterpreterListObjects:
    """Tests for StorageInterpreter handling ListObjects effects."""

    @pytest.mark.asyncio
    async def test_list_objects_success(self, mocker: MockerFixture) -> None:
        """ListObjects should return Ok with list of keys when list succeeds."""
        # Arrange
        effect = ListObjects(bucket="my-bucket", prefix=None, max_keys=1000)

        storage = mocker.AsyncMock(spec=ObjectStorage)
        storage.list_objects.return_value = ["file1.txt", "file2.txt", "data/file3.txt"]

        interpreter = StorageInterpreter(storage=storage)

        # Act
        result = await interpreter.interpret(effect)

        # Assert
        storage.list_objects.assert_awaited_once_with("my-bucket", None, 1000)

        match result:
            case Ok(EffectReturn(value=keys, effect_name="ListObjects")):
                assert keys == ["file1.txt", "file2.txt", "data/file3.txt"]
            case _:
                pytest.fail(f"Expected Ok with list, got {result}")

    @pytest.mark.asyncio
    async def test_list_objects_with_prefix(self, mocker: MockerFixture) -> None:
        """ListObjects should pass prefix to storage implementation."""
        # Arrange
        effect = ListObjects(bucket="my-bucket", prefix="data/", max_keys=1000)

        storage = mocker.AsyncMock(spec=ObjectStorage)
        storage.list_objects.return_value = ["data/file1.txt", "data/file2.txt"]

        interpreter = StorageInterpreter(storage=storage)

        # Act
        result = await interpreter.interpret(effect)

        # Assert
        storage.list_objects.assert_awaited_once_with("my-bucket", "data/", 1000)

        match result:
            case Ok(EffectReturn(value=keys, effect_name="ListObjects")):
                assert keys == ["data/file1.txt", "data/file2.txt"]
            case _:
                pytest.fail(f"Expected Ok with list, got {result}")

    @pytest.mark.asyncio
    async def test_list_objects_empty(self, mocker: MockerFixture) -> None:
        """ListObjects should return Ok with empty list when no objects found."""
        # Arrange
        effect = ListObjects(bucket="my-bucket", prefix="missing/", max_keys=1000)

        storage = mocker.AsyncMock(spec=ObjectStorage)
        storage.list_objects.return_value = []

        interpreter = StorageInterpreter(storage=storage)

        # Act
        result = await interpreter.interpret(effect)

        # Assert
        match result:
            case Ok(EffectReturn(value=[], effect_name="ListObjects")):
                assert True  # Expected
            case _:
                pytest.fail(f"Expected Ok with empty list, got {result}")

    @pytest.mark.asyncio
    async def test_list_objects_exception(self, mocker: MockerFixture) -> None:
        """ListObjects should return Err when storage raises exception."""
        # Arrange
        effect = ListObjects(bucket="bucket", prefix=None, max_keys=1000)

        storage = mocker.AsyncMock(spec=ObjectStorage)
        storage.list_objects.side_effect = RuntimeError("Bucket not found")

        interpreter = StorageInterpreter(storage=storage)

        # Act
        result = await interpreter.interpret(effect)

        # Assert
        match result:
            case Err(StorageError(effect=e, storage_error=msg, is_retryable=False)):
                assert e is effect
                assert "Bucket not found" in msg
            case _:
                pytest.fail(f"Expected Err, got {result}")


class TestStorageInterpreterUnhandledEffects:
    """Tests for StorageInterpreter handling unhandled effects."""

    @pytest.mark.asyncio
    async def test_unhandled_effect(self, mocker: MockerFixture) -> None:
        """Interpreter should return UnhandledEffectError for non-storage effects."""
        # Arrange
        # Create a mock effect that is not a storage effect
        effect = mocker.Mock(spec=Effect)

        storage = mocker.AsyncMock(spec=ObjectStorage)
        interpreter = StorageInterpreter(storage=storage)

        # Act
        result = await interpreter.interpret(effect)

        # Assert
        match result:
            case Err(
                UnhandledEffectError(
                    effect=e, available_interpreters=["StorageInterpreter"]
                )
            ):
                assert e is effect
            case _:
                pytest.fail(f"Expected UnhandledEffectError, got {result}")


class TestStorageInterpreterRetryability:
    """Tests for StorageInterpreter retryability detection logic."""

    @pytest.mark.asyncio
    async def test_retryable_connection_error(self, mocker: MockerFixture) -> None:
        """Connection errors should be retryable."""
        # Arrange
        effect = GetObject(bucket="bucket", key="key")

        storage = mocker.AsyncMock(spec=ObjectStorage)
        storage.get_object.side_effect = RuntimeError("Connection reset by peer")

        interpreter = StorageInterpreter(storage=storage)

        # Act
        result = await interpreter.interpret(effect)

        # Assert
        match result:
            case Err(StorageError(is_retryable=True)):
                assert True  # Expected
            case _:
                pytest.fail(f"Expected retryable error, got {result}")

    @pytest.mark.asyncio
    async def test_retryable_timeout_error(self, mocker: MockerFixture) -> None:
        """Timeout errors should be retryable."""
        # Arrange
        effect = GetObject(bucket="bucket", key="key")

        storage = mocker.AsyncMock(spec=ObjectStorage)
        storage.get_object.side_effect = RuntimeError("Request timeout")

        interpreter = StorageInterpreter(storage=storage)

        # Act
        result = await interpreter.interpret(effect)

        # Assert
        match result:
            case Err(StorageError(is_retryable=True)):
                assert True  # Expected
            case _:
                pytest.fail(f"Expected retryable error, got {result}")

    @pytest.mark.asyncio
    async def test_retryable_unavailable_error(self, mocker: MockerFixture) -> None:
        """Service unavailable errors should be retryable."""
        # Arrange
        effect = GetObject(bucket="bucket", key="key")

        storage = mocker.AsyncMock(spec=ObjectStorage)
        storage.get_object.side_effect = RuntimeError("Service unavailable")

        interpreter = StorageInterpreter(storage=storage)

        # Act
        result = await interpreter.interpret(effect)

        # Assert
        match result:
            case Err(StorageError(is_retryable=True)):
                assert True  # Expected
            case _:
                pytest.fail(f"Expected retryable error, got {result}")

    @pytest.mark.asyncio
    async def test_retryable_throttling_error(self, mocker: MockerFixture) -> None:
        """Throttling errors should be retryable."""
        # Arrange
        effect = GetObject(bucket="bucket", key="key")

        storage = mocker.AsyncMock(spec=ObjectStorage)
        storage.get_object.side_effect = RuntimeError("Rate limit exceeded")

        interpreter = StorageInterpreter(storage=storage)

        # Act
        result = await interpreter.interpret(effect)

        # Assert
        match result:
            case Err(StorageError(is_retryable=True)):
                assert True  # Expected
            case _:
                pytest.fail(f"Expected retryable error, got {result}")

    @pytest.mark.asyncio
    async def test_retryable_500_error(self, mocker: MockerFixture) -> None:
        """HTTP 500 errors should be retryable."""
        # Arrange
        effect = GetObject(bucket="bucket", key="key")

        storage = mocker.AsyncMock(spec=ObjectStorage)
        storage.get_object.side_effect = RuntimeError("HTTP 500 Internal Server Error")

        interpreter = StorageInterpreter(storage=storage)

        # Act
        result = await interpreter.interpret(effect)

        # Assert
        match result:
            case Err(StorageError(is_retryable=True)):
                assert True  # Expected
            case _:
                pytest.fail(f"Expected retryable error, got {result}")

    @pytest.mark.asyncio
    async def test_non_retryable_access_denied(self, mocker: MockerFixture) -> None:
        """Access denied errors should not be retryable."""
        # Arrange
        effect = GetObject(bucket="bucket", key="key")

        storage = mocker.AsyncMock(spec=ObjectStorage)
        storage.get_object.side_effect = RuntimeError("Access denied")

        interpreter = StorageInterpreter(storage=storage)

        # Act
        result = await interpreter.interpret(effect)

        # Assert
        match result:
            case Err(StorageError(is_retryable=False)):
                assert True  # Expected
            case _:
                pytest.fail(f"Expected non-retryable error, got {result}")

    @pytest.mark.asyncio
    async def test_non_retryable_authentication_error(self, mocker: MockerFixture) -> None:
        """Authentication errors should not be retryable."""
        # Arrange
        effect = GetObject(bucket="bucket", key="key")

        storage = mocker.AsyncMock(spec=ObjectStorage)
        storage.get_object.side_effect = RuntimeError("Authentication failed")

        interpreter = StorageInterpreter(storage=storage)

        # Act
        result = await interpreter.interpret(effect)

        # Assert
        match result:
            case Err(StorageError(is_retryable=False)):
                assert True  # Expected
            case _:
                pytest.fail(f"Expected non-retryable error, got {result}")

    @pytest.mark.asyncio
    async def test_non_retryable_bucket_not_found(self, mocker: MockerFixture) -> None:
        """Bucket not found errors should not be retryable."""
        # Arrange
        effect = GetObject(bucket="bucket", key="key")

        storage = mocker.AsyncMock(spec=ObjectStorage)
        storage.get_object.side_effect = RuntimeError("Bucket not found")

        interpreter = StorageInterpreter(storage=storage)

        # Act
        result = await interpreter.interpret(effect)

        # Assert
        match result:
            case Err(StorageError(is_retryable=False)):
                assert True  # Expected
            case _:
                pytest.fail(f"Expected non-retryable error, got {result}")

    @pytest.mark.asyncio
    async def test_non_retryable_invalid_request(self, mocker: MockerFixture) -> None:
        """Invalid request errors should not be retryable."""
        # Arrange
        effect = GetObject(bucket="bucket", key="key")

        storage = mocker.AsyncMock(spec=ObjectStorage)
        storage.get_object.side_effect = RuntimeError("Invalid request")

        interpreter = StorageInterpreter(storage=storage)

        # Act
        result = await interpreter.interpret(effect)

        # Assert
        match result:
            case Err(StorageError(is_retryable=False)):
                assert True  # Expected
            case _:
                pytest.fail(f"Expected non-retryable error, got {result}")

    @pytest.mark.asyncio
    async def test_default_unknown_error_is_retryable(self, mocker: MockerFixture) -> None:
        """Unknown errors should default to retryable."""
        # Arrange
        effect = GetObject(bucket="bucket", key="key")

        storage = mocker.AsyncMock(spec=ObjectStorage)
        storage.get_object.side_effect = RuntimeError("Unknown error xyz123")

        interpreter = StorageInterpreter(storage=storage)

        # Act
        result = await interpreter.interpret(effect)

        # Assert
        match result:
            case Err(StorageError(is_retryable=True)):
                assert True  # Expected - unknown errors default to retryable
            case _:
                pytest.fail(f"Expected retryable error (default), got {result}")
