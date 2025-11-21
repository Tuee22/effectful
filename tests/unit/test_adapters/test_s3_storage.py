"""Unit tests for S3 storage adapter.

Tests S3ObjectStorage using pytest-mock with MagicMock for boto3 client.
"""

from datetime import UTC, datetime

import pytest
from botocore.exceptions import ClientError
from pytest_mock import MockerFixture

from effectful.adapters.s3_storage import S3ObjectStorage
from effectful.domain.s3_object import PutFailure, PutSuccess, S3Object


class TestS3ObjectStorageGetObject:
    """Tests for S3ObjectStorage.get_object."""

    @pytest.mark.asyncio
    async def test_get_object_returns_s3_object_when_found(self, mocker: MockerFixture) -> None:
        """Test successful object retrieval returns S3Object."""
        # Setup
        bucket = "test-bucket"
        key = "data/file.txt"
        content = b"Hello, World!"
        last_modified = datetime.now(UTC)

        mock_body = mocker.MagicMock()
        mock_body.read.return_value = content

        mock_response = {
            "Body": mock_body,
            "Metadata": {"uploaded-by": "user-123"},
            "ContentType": "text/plain",
            "LastModified": last_modified,
            "VersionId": "v1",
            "ContentLength": len(content),
        }

        mock_client = mocker.MagicMock()
        mock_client.get_object.return_value = mock_response

        storage = S3ObjectStorage(mock_client)

        # Execute
        result = await storage.get_object(bucket, key)

        # Assert
        assert isinstance(result, S3Object)
        assert result.key == key
        assert result.bucket == bucket
        assert result.content == content
        assert result.metadata == {"uploaded-by": "user-123"}
        assert result.content_type == "text/plain"
        assert result.version_id == "v1"
        assert result.size == len(content)

        # Verify S3 call
        mock_client.get_object.assert_called_once_with(Bucket=bucket, Key=key)

    @pytest.mark.asyncio
    async def test_get_object_returns_none_when_not_found(self, mocker: MockerFixture) -> None:
        """Test object retrieval returns None for NoSuchKey."""
        # Setup
        mock_client = mocker.MagicMock()

        error_response = {"Error": {"Code": "NoSuchKey", "Message": "Not found"}}
        mock_client.get_object.side_effect = ClientError(error_response, "GetObject")

        storage = S3ObjectStorage(mock_client)

        # Execute
        result = await storage.get_object("test-bucket", "nonexistent.txt")

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_get_object_raises_on_permission_error(self, mocker: MockerFixture) -> None:
        """Test object retrieval raises exception for permission errors."""
        # Setup
        mock_client = mocker.MagicMock()

        error_response = {"Error": {"Code": "AccessDenied", "Message": "Access denied"}}
        mock_client.get_object.side_effect = ClientError(error_response, "GetObject")

        storage = S3ObjectStorage(mock_client)

        # Execute & Assert
        with pytest.raises(ClientError):
            await storage.get_object("test-bucket", "secret.txt")

    @pytest.mark.asyncio
    async def test_get_object_handles_missing_optional_fields(self, mocker: MockerFixture) -> None:
        """Test object retrieval handles missing optional metadata."""
        # Setup
        mock_body = mocker.MagicMock()
        mock_body.read.return_value = b"content"

        mock_response = {
            "Body": mock_body,
            # Missing Metadata, ContentType, VersionId
            "LastModified": datetime.now(UTC),
            "ContentLength": 7,
        }

        mock_client = mocker.MagicMock()
        mock_client.get_object.return_value = mock_response

        storage = S3ObjectStorage(mock_client)

        # Execute
        result = await storage.get_object("bucket", "key")

        # Assert
        assert isinstance(result, S3Object)
        assert result.metadata == {}
        assert result.content_type is None
        assert result.version_id is None


class TestS3ObjectStoragePutObject:
    """Tests for S3ObjectStorage.put_object."""

    @pytest.mark.asyncio
    async def test_put_object_returns_success_with_version(self, mocker: MockerFixture) -> None:
        """Test successful object storage returns PutSuccess."""
        # Setup
        bucket = "test-bucket"
        key = "data/file.txt"
        content = b"Hello, World!"
        metadata = {"source": "test"}
        content_type = "text/plain"

        mock_client = mocker.MagicMock()
        mock_client.put_object.return_value = {"VersionId": "v2"}

        storage = S3ObjectStorage(mock_client)

        # Execute
        result = await storage.put_object(bucket, key, content, metadata, content_type)

        # Assert
        assert isinstance(result, PutSuccess)
        assert result.key == key
        assert result.bucket == bucket
        assert result.version_id == "v2"

        # Verify S3 call
        mock_client.put_object.assert_called_once_with(
            Bucket=bucket,
            Key=key,
            Body=content,
            Metadata=metadata,
            ContentType=content_type,
        )

    @pytest.mark.asyncio
    async def test_put_object_returns_failure_for_quota_exceeded(
        self, mocker: MockerFixture
    ) -> None:
        """Test storage returns PutFailure for quota exceeded."""
        # Setup
        mock_client = mocker.MagicMock()

        error_response = {"Error": {"Code": "SlowDown", "Message": "Reduce request rate"}}
        mock_client.put_object.side_effect = ClientError(error_response, "PutObject")

        storage = S3ObjectStorage(mock_client)

        # Execute
        result = await storage.put_object("bucket", "key", b"data", None, None)

        # Assert
        assert isinstance(result, PutFailure)
        assert result.key == "key"
        assert result.bucket == "bucket"
        assert result.reason == "quota_exceeded"

    @pytest.mark.asyncio
    async def test_put_object_returns_failure_for_permission_denied(
        self, mocker: MockerFixture
    ) -> None:
        """Test storage returns PutFailure for access denied."""
        # Setup
        mock_client = mocker.MagicMock()

        error_response = {"Error": {"Code": "AccessDenied", "Message": "Access denied"}}
        mock_client.put_object.side_effect = ClientError(error_response, "PutObject")

        storage = S3ObjectStorage(mock_client)

        # Execute
        result = await storage.put_object("bucket", "key", b"data", None, None)

        # Assert
        assert isinstance(result, PutFailure)
        assert result.reason == "permission_denied"

    @pytest.mark.asyncio
    async def test_put_object_raises_for_unknown_errors(self, mocker: MockerFixture) -> None:
        """Test storage raises exception for unknown errors."""
        # Setup
        mock_client = mocker.MagicMock()

        error_response = {"Error": {"Code": "InternalError", "Message": "Server error"}}
        mock_client.put_object.side_effect = ClientError(error_response, "PutObject")

        storage = S3ObjectStorage(mock_client)

        # Execute & Assert
        with pytest.raises(ClientError):
            await storage.put_object("bucket", "key", b"data", None, None)


class TestS3ObjectStorageDeleteObject:
    """Tests for S3ObjectStorage.delete_object."""

    @pytest.mark.asyncio
    async def test_delete_object_succeeds(self, mocker: MockerFixture) -> None:
        """Test successful object deletion."""
        # Setup
        mock_client = mocker.MagicMock()
        mock_client.delete_object.return_value = {}

        storage = S3ObjectStorage(mock_client)

        # Execute
        await storage.delete_object("bucket", "key")

        # Assert
        mock_client.delete_object.assert_called_once_with(Bucket="bucket", Key="key")

    @pytest.mark.asyncio
    async def test_delete_object_handles_nonexistent_key(self, mocker: MockerFixture) -> None:
        """Test deletion of nonexistent object doesn't raise."""
        # Setup
        mock_client = mocker.MagicMock()

        error_response = {"Error": {"Code": "NoSuchKey", "Message": "Not found"}}
        mock_client.delete_object.side_effect = ClientError(error_response, "DeleteObject")

        storage = S3ObjectStorage(mock_client)

        # Execute - should not raise
        await storage.delete_object("bucket", "nonexistent")

    @pytest.mark.asyncio
    async def test_delete_object_raises_for_other_errors(self, mocker: MockerFixture) -> None:
        """Test deletion raises for non-404 errors."""
        # Setup
        mock_client = mocker.MagicMock()

        error_response = {"Error": {"Code": "AccessDenied", "Message": "Access denied"}}
        mock_client.delete_object.side_effect = ClientError(error_response, "DeleteObject")

        storage = S3ObjectStorage(mock_client)

        # Execute & Assert
        with pytest.raises(ClientError):
            await storage.delete_object("bucket", "key")


class TestS3ObjectStorageListObjects:
    """Tests for S3ObjectStorage.list_objects."""

    @pytest.mark.asyncio
    async def test_list_objects_returns_keys(self, mocker: MockerFixture) -> None:
        """Test listing objects returns list of keys."""
        # Setup
        mock_client = mocker.MagicMock()
        mock_client.list_objects_v2.return_value = {
            "Contents": [
                {"Key": "file1.txt"},
                {"Key": "file2.txt"},
                {"Key": "data/file3.txt"},
            ]
        }

        storage = S3ObjectStorage(mock_client)

        # Execute
        result = await storage.list_objects("bucket", prefix="")

        # Assert
        assert result == ["file1.txt", "file2.txt", "data/file3.txt"]

        # Verify call
        mock_client.list_objects_v2.assert_called_once_with(
            Bucket="bucket",
            MaxKeys=1000,
            Prefix="",
        )

    @pytest.mark.asyncio
    async def test_list_objects_with_prefix(self, mocker: MockerFixture) -> None:
        """Test listing objects with prefix filter."""
        # Setup
        mock_client = mocker.MagicMock()
        mock_client.list_objects_v2.return_value = {
            "Contents": [
                {"Key": "data/file1.txt"},
                {"Key": "data/file2.txt"},
            ]
        }

        storage = S3ObjectStorage(mock_client)

        # Execute
        result = await storage.list_objects("bucket", prefix="data/", max_keys=100)

        # Assert
        assert result == ["data/file1.txt", "data/file2.txt"]

        # Verify call
        mock_client.list_objects_v2.assert_called_once_with(
            Bucket="bucket",
            MaxKeys=100,
            Prefix="data/",
        )

    @pytest.mark.asyncio
    async def test_list_objects_returns_empty_list_when_no_contents(
        self, mocker: MockerFixture
    ) -> None:
        """Test listing returns empty list when no objects found."""
        # Setup
        mock_client = mocker.MagicMock()
        mock_client.list_objects_v2.return_value = {}  # No Contents key

        storage = S3ObjectStorage(mock_client)

        # Execute
        result = await storage.list_objects("bucket")

        # Assert
        assert result == []

    @pytest.mark.asyncio
    async def test_list_objects_raises_for_errors(self, mocker: MockerFixture) -> None:
        """Test listing raises for bucket errors."""
        # Setup
        mock_client = mocker.MagicMock()

        error_response = {"Error": {"Code": "NoSuchBucket", "Message": "Bucket not found"}}
        mock_client.list_objects_v2.side_effect = ClientError(error_response, "ListObjectsV2")

        storage = S3ObjectStorage(mock_client)

        # Execute & Assert
        with pytest.raises(ClientError):
            await storage.list_objects("nonexistent-bucket")
