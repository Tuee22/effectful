"""Tests for Storage interpreter.

This module tests the StorageInterpreter using pytest mocks (via pytest-mock).
Tests cover:
- GetObject (success, not found, infrastructure errors)
- PutObject (success, domain failures, infrastructure errors)
- DeleteObject (success, infrastructure errors)
- ListObjects (success, empty results, infrastructure errors)
- Unhandled effects
- Immutability
- Retryable error detection
"""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest
from pytest_mock import MockerFixture

from effectful.algebraic.effect_return import EffectReturn
from effectful.algebraic.result import Err, Ok
from effectful.domain.s3_object import PutFailure, PutSuccess, S3Object
from effectful.effects.storage import DeleteObject, GetObject, ListObjects, PutObject
from effectful.effects.websocket import SendText
from effectful.infrastructure.storage import ObjectStorage
from effectful.interpreters.errors import StorageError, UnhandledEffectError
from effectful.interpreters.storage import StorageInterpreter


class TestGetObject:
    """Tests for GetObject effect handling."""

    @pytest.mark.asyncio()
    async def test_get_object_success(self, mocker: MockerFixture) -> None:
        """Interpreter should return S3Object when object exists."""
        # Setup
        s3_object = S3Object(
            key="data/file.txt",
            bucket="my-bucket",
            content=b"Hello World",
            last_modified=datetime.now(UTC),
            metadata={"uploaded-by": "test"},
            content_type="text/plain",
            size=11,
            version_id="v1",
        )
        mock_storage = mocker.AsyncMock(spec=ObjectStorage)
        mock_storage.get_object.return_value = s3_object

        interpreter = StorageInterpreter(storage=mock_storage)

        effect = GetObject(bucket="my-bucket", key="data/file.txt")
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Ok(EffectReturn(value=obj, effect_name="GetObject")):
                assert obj == s3_object
            case _:
                pytest.fail(f"Expected Ok with S3Object, got {result}")

        # Verify mock was called correctly
        mock_storage.get_object.assert_called_once_with("my-bucket", "data/file.txt")

    @pytest.mark.asyncio()
    async def test_get_object_not_found(self, mocker: MockerFixture) -> None:
        """Interpreter should return None when object does not exist."""
        # Setup
        mock_storage = mocker.AsyncMock(spec=ObjectStorage)
        mock_storage.get_object.return_value = None

        interpreter = StorageInterpreter(storage=mock_storage)

        effect = GetObject(bucket="my-bucket", key="nonexistent.txt")
        result = await interpreter.interpret(effect)

        # Verify result - not found returns None (not an error)
        match result:
            case Ok(EffectReturn(value=None, effect_name="GetObject")):
                pass  # Success
            case _:
                pytest.fail(f"Expected Ok with None, got {result}")

        # Verify mock was called correctly
        mock_storage.get_object.assert_called_once_with("my-bucket", "nonexistent.txt")

    @pytest.mark.asyncio()
    async def test_get_object_infrastructure_error(self, mocker: MockerFixture) -> None:
        """Interpreter should return StorageError on infrastructure failure."""
        # Setup
        mock_storage = mocker.AsyncMock(spec=ObjectStorage)
        mock_storage.get_object.side_effect = Exception("Connection timeout")

        interpreter = StorageInterpreter(storage=mock_storage)

        effect = GetObject(bucket="my-bucket", key="data/file.txt")
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Err(StorageError(effect=e, storage_error="Connection timeout", is_retryable=True)):
                assert e == effect
            case _:
                pytest.fail(f"Expected StorageError, got {result}")


class TestPutObject:
    """Tests for PutObject effect handling."""

    @pytest.mark.asyncio()
    async def test_put_object_success(self, mocker: MockerFixture) -> None:
        """Interpreter should return object key on successful put."""
        # Setup
        mock_storage = mocker.AsyncMock(spec=ObjectStorage)
        mock_storage.put_object.return_value = PutSuccess(
            key="data/file.txt", bucket="my-bucket", version_id="v2"
        )

        interpreter = StorageInterpreter(storage=mock_storage)

        effect = PutObject(
            bucket="my-bucket",
            key="data/file.txt",
            content=b"Hello World",
            metadata={"author": "test"},
            content_type="text/plain",
        )
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Ok(EffectReturn(value="data/file.txt", effect_name="PutObject")):
                pass  # Success
            case _:
                pytest.fail(f"Expected Ok with key, got {result}")

        # Verify mock was called correctly
        mock_storage.put_object.assert_called_once_with(
            "my-bucket",
            "data/file.txt",
            b"Hello World",
            {"author": "test"},
            "text/plain",
        )

    @pytest.mark.asyncio()
    async def test_put_object_with_none_metadata(self, mocker: MockerFixture) -> None:
        """Interpreter should handle None metadata correctly."""
        # Setup
        mock_storage = mocker.AsyncMock(spec=ObjectStorage)
        mock_storage.put_object.return_value = PutSuccess(key="data/file.txt", bucket="my-bucket")

        interpreter = StorageInterpreter(storage=mock_storage)

        effect = PutObject(
            bucket="my-bucket",
            key="data/file.txt",
            content=b"data",
            metadata=None,
            content_type=None,
        )
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Ok(EffectReturn(value="data/file.txt", effect_name="PutObject")):
                pass  # Success
            case _:
                pytest.fail(f"Expected Ok, got {result}")

        # Verify mock was called with None
        mock_storage.put_object.assert_called_once_with(
            "my-bucket", "data/file.txt", b"data", None, None
        )

    @pytest.mark.asyncio()
    async def test_put_object_quota_exceeded_failure(self, mocker: MockerFixture) -> None:
        """Interpreter should return StorageError on quota exceeded."""
        # Setup
        mock_storage = mocker.AsyncMock(spec=ObjectStorage)
        mock_storage.put_object.return_value = PutFailure(
            key="data/file.txt", bucket="my-bucket", reason="quota_exceeded"
        )

        interpreter = StorageInterpreter(storage=mock_storage)

        effect = PutObject(bucket="my-bucket", key="data/file.txt", content=b"large data")
        result = await interpreter.interpret(effect)

        # Verify result - quota_exceeded is retryable
        match result:
            case Err(StorageError(effect=e, storage_error=err_msg, is_retryable=True)):
                assert e == effect
                assert "quota_exceeded" in err_msg
            case _:
                pytest.fail(f"Expected StorageError with retryable=True, got {result}")

    @pytest.mark.asyncio()
    async def test_put_object_permission_denied_failure(self, mocker: MockerFixture) -> None:
        """Interpreter should return StorageError on permission denied."""
        # Setup
        mock_storage = mocker.AsyncMock(spec=ObjectStorage)
        mock_storage.put_object.return_value = PutFailure(
            key="data/file.txt", bucket="my-bucket", reason="permission_denied"
        )

        interpreter = StorageInterpreter(storage=mock_storage)

        effect = PutObject(bucket="my-bucket", key="data/file.txt", content=b"data")
        result = await interpreter.interpret(effect)

        # Verify result - permission_denied is NOT retryable
        match result:
            case Err(StorageError(effect=e, storage_error=err_msg, is_retryable=False)):
                assert e == effect
                assert "permission_denied" in err_msg
            case _:
                pytest.fail(f"Expected StorageError with retryable=False, got {result}")

    @pytest.mark.asyncio()
    async def test_put_object_invalid_object_state_failure(self, mocker: MockerFixture) -> None:
        """Interpreter should return StorageError on invalid object state."""
        # Setup
        mock_storage = mocker.AsyncMock(spec=ObjectStorage)
        mock_storage.put_object.return_value = PutFailure(
            key="data/file.txt", bucket="my-bucket", reason="invalid_object_state"
        )

        interpreter = StorageInterpreter(storage=mock_storage)

        effect = PutObject(bucket="my-bucket", key="data/file.txt", content=b"data")
        result = await interpreter.interpret(effect)

        # Verify result - invalid_object_state is retryable (lock may be released)
        match result:
            case Err(StorageError(effect=e, storage_error=err_msg, is_retryable=True)):
                assert e == effect
                assert "invalid_object_state" in err_msg
            case _:
                pytest.fail(f"Expected StorageError with retryable=True, got {result}")

    @pytest.mark.asyncio()
    async def test_put_object_infrastructure_error(self, mocker: MockerFixture) -> None:
        """Interpreter should return StorageError on infrastructure failure."""
        # Setup
        mock_storage = mocker.AsyncMock(spec=ObjectStorage)
        mock_storage.put_object.side_effect = Exception("Network error")

        interpreter = StorageInterpreter(storage=mock_storage)

        effect = PutObject(bucket="my-bucket", key="data/file.txt", content=b"data")
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Err(StorageError(effect=e, storage_error="Network error", is_retryable=True)):
                assert e == effect
            case _:
                pytest.fail(f"Expected StorageError, got {result}")


class TestDeleteObject:
    """Tests for DeleteObject effect handling."""

    @pytest.mark.asyncio()
    async def test_delete_object_success(self, mocker: MockerFixture) -> None:
        """Interpreter should return None on successful delete."""
        # Setup
        mock_storage = mocker.AsyncMock(spec=ObjectStorage)

        interpreter = StorageInterpreter(storage=mock_storage)

        effect = DeleteObject(bucket="my-bucket", key="data/file.txt")
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Ok(EffectReturn(value=None, effect_name="DeleteObject")):
                pass  # Success
            case _:
                pytest.fail(f"Expected Ok with None, got {result}")

        # Verify mock was called correctly
        mock_storage.delete_object.assert_called_once_with("my-bucket", "data/file.txt")

    @pytest.mark.asyncio()
    async def test_delete_object_idempotent(self, mocker: MockerFixture) -> None:
        """Interpreter should succeed when deleting non-existent object."""
        # Setup - delete is idempotent, always succeeds
        mock_storage = mocker.AsyncMock(spec=ObjectStorage)

        interpreter = StorageInterpreter(storage=mock_storage)

        effect = DeleteObject(bucket="my-bucket", key="nonexistent.txt")
        result = await interpreter.interpret(effect)

        # Verify result - should still succeed
        match result:
            case Ok(EffectReturn(value=None, effect_name="DeleteObject")):
                pass  # Success
            case _:
                pytest.fail(f"Expected Ok with None, got {result}")

    @pytest.mark.asyncio()
    async def test_delete_object_infrastructure_error(self, mocker: MockerFixture) -> None:
        """Interpreter should return StorageError on infrastructure failure."""
        # Setup
        mock_storage = mocker.AsyncMock(spec=ObjectStorage)
        mock_storage.delete_object.side_effect = Exception("Service unavailable")

        interpreter = StorageInterpreter(storage=mock_storage)

        effect = DeleteObject(bucket="my-bucket", key="data/file.txt")
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Err(
                StorageError(effect=e, storage_error="Service unavailable", is_retryable=True)
            ):
                assert e == effect
            case _:
                pytest.fail(f"Expected StorageError, got {result}")


class TestListObjects:
    """Tests for ListObjects effect handling."""

    @pytest.mark.asyncio()
    async def test_list_objects_success(self, mocker: MockerFixture) -> None:
        """Interpreter should return list of keys."""
        # Setup
        keys = ["data/file1.txt", "data/file2.txt", "data/file3.txt"]
        mock_storage = mocker.AsyncMock(spec=ObjectStorage)
        mock_storage.list_objects.return_value = keys

        interpreter = StorageInterpreter(storage=mock_storage)

        effect = ListObjects(bucket="my-bucket", prefix="data/", max_keys=100)
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Ok(EffectReturn(value=result_keys, effect_name="ListObjects")):
                assert result_keys == keys
            case _:
                pytest.fail(f"Expected Ok with keys, got {result}")

        # Verify mock was called correctly
        mock_storage.list_objects.assert_called_once_with("my-bucket", "data/", 100)

    @pytest.mark.asyncio()
    async def test_list_objects_empty_result(self, mocker: MockerFixture) -> None:
        """Interpreter should return empty list when no objects match."""
        # Setup
        mock_storage = mocker.AsyncMock(spec=ObjectStorage)
        mock_storage.list_objects.return_value = []

        interpreter = StorageInterpreter(storage=mock_storage)

        effect = ListObjects(bucket="my-bucket", prefix="nonexistent/", max_keys=100)
        result = await interpreter.interpret(effect)

        # Verify result - empty list is not an error
        match result:
            case Ok(EffectReturn(value=result_keys, effect_name="ListObjects")):
                assert result_keys == []
            case _:
                pytest.fail(f"Expected Ok with empty list, got {result}")

    @pytest.mark.asyncio()
    async def test_list_objects_with_none_prefix(self, mocker: MockerFixture) -> None:
        """Interpreter should handle None prefix correctly."""
        # Setup
        keys = ["file1.txt", "file2.txt"]
        mock_storage = mocker.AsyncMock(spec=ObjectStorage)
        mock_storage.list_objects.return_value = keys

        interpreter = StorageInterpreter(storage=mock_storage)

        effect = ListObjects(bucket="my-bucket", prefix=None, max_keys=1000)
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Ok(EffectReturn(value=result_keys, effect_name="ListObjects")):
                assert result_keys == keys
            case _:
                pytest.fail(f"Expected Ok, got {result}")

        # Verify mock was called with None prefix
        mock_storage.list_objects.assert_called_once_with("my-bucket", None, 1000)

    @pytest.mark.asyncio()
    async def test_list_objects_infrastructure_error(self, mocker: MockerFixture) -> None:
        """Interpreter should return StorageError on infrastructure failure."""
        # Setup
        mock_storage = mocker.AsyncMock(spec=ObjectStorage)
        mock_storage.list_objects.side_effect = Exception("Bucket not found 404")

        interpreter = StorageInterpreter(storage=mock_storage)

        effect = ListObjects(bucket="nonexistent-bucket", prefix=None, max_keys=100)
        result = await interpreter.interpret(effect)

        # Verify result - 404 is not retryable
        match result:
            case Err(StorageError(effect=e, storage_error=err_msg, is_retryable=False)):
                assert e == effect
                assert "404" in err_msg
            case _:
                pytest.fail(f"Expected StorageError with retryable=False, got {result}")


class TestUnhandledEffect:
    """Tests for unhandled effect handling."""

    @pytest.mark.asyncio()
    async def test_unhandled_effect(self, mocker: MockerFixture) -> None:
        """Interpreter should return UnhandledEffectError for non-Storage effects."""
        # Setup
        mock_storage = mocker.AsyncMock(spec=ObjectStorage)

        interpreter = StorageInterpreter(storage=mock_storage)

        effect = SendText(text="hello")
        result = await interpreter.interpret(effect)

        # Verify result
        match result:
            case Err(UnhandledEffectError(effect=e, available_interpreters=["StorageInterpreter"])):
                assert e == effect
            case _:
                pytest.fail(f"Expected UnhandledEffectError, got {result}")

        # Verify no storage methods were called
        mock_storage.get_object.assert_not_called()
        mock_storage.put_object.assert_not_called()
        mock_storage.delete_object.assert_not_called()
        mock_storage.list_objects.assert_not_called()


class TestStorageInterpreterImmutability:
    """Tests for StorageInterpreter immutability."""

    def test_interpreter_is_immutable(self, mocker: MockerFixture) -> None:
        """StorageInterpreter should be frozen."""
        mock_storage = mocker.AsyncMock(spec=ObjectStorage)
        interpreter = StorageInterpreter(storage=mock_storage)

        with pytest.raises(FrozenInstanceError):
            interpreter.storage = mocker.AsyncMock(spec=ObjectStorage)  # type: ignore[misc]


class TestIsRetryableError:
    """Tests for _is_retryable_error helper method."""

    def test_detects_retryable_patterns(self, mocker: MockerFixture) -> None:
        """_is_retryable_error should detect retryable error patterns."""
        mock_storage = mocker.AsyncMock(spec=ObjectStorage)
        interpreter = StorageInterpreter(storage=mock_storage)

        assert interpreter._is_retryable_error(Exception("Connection timeout"))
        assert interpreter._is_retryable_error(Exception("Service unavailable"))
        assert interpreter._is_retryable_error(Exception("Network error"))
        assert interpreter._is_retryable_error(Exception("Throttling 503"))
        assert interpreter._is_retryable_error(Exception("Rate limit exceeded"))
        assert interpreter._is_retryable_error(Exception("500 Internal Server Error"))

    def test_detects_non_retryable_patterns(self, mocker: MockerFixture) -> None:
        """_is_retryable_error should detect non-retryable error patterns."""
        mock_storage = mocker.AsyncMock(spec=ObjectStorage)
        interpreter = StorageInterpreter(storage=mock_storage)

        assert not interpreter._is_retryable_error(Exception("Bucket not found 404"))
        assert not interpreter._is_retryable_error(Exception("Access denied 403"))
        assert not interpreter._is_retryable_error(Exception("Invalid request 400"))
        assert not interpreter._is_retryable_error(Exception("Authentication failed"))
        assert not interpreter._is_retryable_error(Exception("Authorization error"))
        assert not interpreter._is_retryable_error(Exception("Configuration error"))


class TestIsRetryablePutFailure:
    """Tests for _is_retryable_put_failure helper method."""

    def test_quota_exceeded_is_retryable(self, mocker: MockerFixture) -> None:
        """_is_retryable_put_failure should return True for quota_exceeded."""
        mock_storage = mocker.AsyncMock(spec=ObjectStorage)
        interpreter = StorageInterpreter(storage=mock_storage)

        assert interpreter._is_retryable_put_failure("quota_exceeded")

    def test_permission_denied_is_not_retryable(self, mocker: MockerFixture) -> None:
        """_is_retryable_put_failure should return False for permission_denied."""
        mock_storage = mocker.AsyncMock(spec=ObjectStorage)
        interpreter = StorageInterpreter(storage=mock_storage)

        assert not interpreter._is_retryable_put_failure("permission_denied")

    def test_invalid_object_state_is_retryable(self, mocker: MockerFixture) -> None:
        """_is_retryable_put_failure should return True for invalid_object_state."""
        mock_storage = mocker.AsyncMock(spec=ObjectStorage)
        interpreter = StorageInterpreter(storage=mock_storage)

        assert interpreter._is_retryable_put_failure("invalid_object_state")
