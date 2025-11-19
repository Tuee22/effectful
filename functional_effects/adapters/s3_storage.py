"""AWS S3 implementations of storage protocols.

This module provides production implementations of ObjectStorage using the AWS SDK
for Python (boto3).

Implementations:
    - S3ObjectStorage: Production S3 storage adapter using boto3

Dependencies:
    Requires boto3 library:
    pip install boto3

Type Safety:
    All implementations follow protocol contracts strictly. Domain failures return
    ADTs (PutSuccess/PutFailure), not exceptions.
"""

from datetime import UTC, datetime

try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    raise ImportError(
        "S3 support requires boto3 library. " "Install with: pip install boto3"
    )

from functional_effects.domain.s3_object import (
    PutFailure,
    PutResult,
    PutSuccess,
    S3Object,
)
from functional_effects.infrastructure.storage import ObjectStorage


class S3ObjectStorage(ObjectStorage):
    """AWS S3-based object storage.

    This implementation uses the boto3 library to interact with AWS S3.
    It implements the ObjectStorage protocol for get, put, delete, and list operations.

    Attributes:
        _s3_client: boto3 S3 client instance

    Example:
        >>> import boto3
        >>> s3_client = boto3.client(
        ...     "s3",
        ...     aws_access_key_id="your-key",
        ...     aws_secret_access_key="your-secret",
        ...     region_name="us-east-1"
        ... )
        >>> storage = S3ObjectStorage(s3_client)
        >>>
        >>> result = await storage.put_object(
        ...     bucket="my-bucket",
        ...     key="data/file.txt",
        ...     content=b"Hello World",
        ...     metadata={"uploaded-by": "user-123"},
        ...     content_type="text/plain"
        ... )
        >>>
        >>> match result:
        ...     case PutSuccess(key=key, version_id=vid):
        ...         print(f"Stored {key} version {vid}")
    """

    def __init__(self, s3_client: "boto3.client") -> None:
        """Initialize storage with boto3 S3 client.

        Args:
            s3_client: boto3.client('s3') instance with credentials configured
        """
        self._s3_client = s3_client

    async def get_object(self, bucket: str, key: str) -> S3Object | None:
        """Retrieve object from S3.

        Args:
            bucket: Bucket name containing the object
            key: Object key (path) within the bucket

        Returns:
            S3Object with content and metadata if object exists.
            None if object does not exist (404 - not an error).

        Raises:
            Exception: For infrastructure failures (network, permissions, etc.)
        """
        try:
            response = self._s3_client.get_object(Bucket=bucket, Key=key)

            # Extract metadata
            metadata = response.get("Metadata", {})
            content_type = response.get("ContentType")
            last_modified = response.get("LastModified")
            version_id = response.get("VersionId")
            content_length = response.get("ContentLength", 0)

            # Read content
            content = response["Body"].read()

            return S3Object(
                key=key,
                bucket=bucket,
                content=content,
                last_modified=last_modified.astimezone(UTC)
                if last_modified
                else datetime.now(UTC),
                metadata=metadata,
                content_type=content_type,
                size=content_length,
                version_id=version_id,
            )
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")

            if error_code == "NoSuchKey":
                # Object not found - not an error, return None
                return None

            # Other client errors (permission denied, etc.) - raise
            raise

    async def put_object(
        self,
        bucket: str,
        key: str,
        content: bytes,
        metadata: dict[str, str] | None = None,
        content_type: str | None = None,
    ) -> PutResult:
        """Store object in S3.

        Args:
            bucket: Bucket name to store the object
            key: Object key (path) within the bucket
            content: Object content as bytes
            metadata: Optional metadata key-value pairs
            content_type: Optional MIME type

        Returns:
            PutSuccess with key, bucket, and version_id if successful.
            PutFailure with reason if failed (quota, permissions, etc.).

        Note:
            Domain failures (quota exceeded, permission denied) return PutFailure.
            Infrastructure failures (network errors) raise exceptions.
        """
        try:
            # Prepare put_object parameters
            put_params: dict[str, str | bytes | dict[str, str]] = {
                "Bucket": bucket,
                "Key": key,
                "Body": content,
            }

            if metadata is not None:
                put_params["Metadata"] = metadata

            if content_type is not None:
                put_params["ContentType"] = content_type

            # Put object
            response = self._s3_client.put_object(**put_params)

            # Extract version ID if versioning enabled
            version_id = response.get("VersionId")

            return PutSuccess(key=key, bucket=bucket, version_id=version_id)

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")

            # Map S3 errors to PutFailure reasons
            match error_code:
                case "SlowDown" | "ServiceUnavailable":
                    # Throttling - quota exceeded
                    return PutFailure(key=key, bucket=bucket, reason="quota_exceeded")
                case "AccessDenied" | "InvalidAccessKeyId" | "SignatureDoesNotMatch":
                    # Permission denied
                    return PutFailure(key=key, bucket=bucket, reason="permission_denied")
                case "ObjectLockConfigurationNotFoundError" | "InvalidObjectState":
                    # Object state issues
                    return PutFailure(
                        key=key, bucket=bucket, reason="invalid_object_state"
                    )
                case _:
                    # Unknown error - raise for infrastructure layer to handle
                    raise

    async def delete_object(self, bucket: str, key: str) -> None:
        """Delete object from S3.

        Args:
            bucket: Bucket name containing the object
            key: Object key (path) to delete

        Returns:
            None (deletion is idempotent)

        Raises:
            Exception: For infrastructure failures (network, permissions, etc.)

        Note:
            Deleting a non-existent object is NOT an error. S3 delete is idempotent
            and returns success even if the object doesn't exist.
        """
        try:
            self._s3_client.delete_object(Bucket=bucket, Key=key)
            # S3 delete is idempotent - no error if object doesn't exist
        except ClientError as e:
            # Only raise for non-404 errors
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code != "NoSuchKey":
                raise

    async def list_objects(
        self, bucket: str, prefix: str | None = None, max_keys: int = 1000
    ) -> list[str]:
        """List object keys in S3 bucket.

        Args:
            bucket: Bucket name to list objects from
            prefix: Optional key prefix to filter results
            max_keys: Maximum number of keys to return (default: 1000)

        Returns:
            List of object keys matching the prefix.
            Empty list if no objects match (not an error).

        Raises:
            Exception: For infrastructure failures (network, bucket not found, etc.)
        """
        try:
            # Prepare list_objects_v2 parameters
            list_params: dict[str, str | int] = {
                "Bucket": bucket,
                "MaxKeys": max_keys,
            }

            if prefix is not None:
                list_params["Prefix"] = prefix

            response = self._s3_client.list_objects_v2(**list_params)

            # Extract keys from response
            if "Contents" in response:
                return [obj["Key"] for obj in response["Contents"]]
            else:
                # No objects found - return empty list
                return []

        except ClientError:
            # Bucket not found, permission denied, etc. - raise
            raise
