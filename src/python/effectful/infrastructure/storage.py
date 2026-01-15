"""Infrastructure protocols for object storage operations.

This module defines protocols (interfaces) for object storage adapters. Protocols
use structural typing (duck typing with type checking) rather than inheritance.

Protocols:
    - ObjectStorage: Complete object storage interface (get, put, delete, list)

Implementations must provide async methods matching the protocol signatures.
This allows for multiple implementations (AWS S3, MinIO, GCS, fakes, etc.)
without coupling to a specific adapter.

Example:
    >>> from effectful.infrastructure.storage import ObjectStorage
    >>> from effectful.domain.s3_object import GetObjectResult, PutResult, S3Object
    >>>
    >>> class MyStorageAdapter:
    ...     async def get_object(
    ...         self, bucket: str, key: str
    ...     ) -> GetObjectResult:
    ...         # Implementation...
    ...         pass
    ...
    ...     async def put_object(
    ...         self,
    ...         bucket: str,
    ...         key: str,
    ...         content: bytes,
    ...         metadata: dict[str, str] | None,
    ...         content_type: str | None
    ...     ) -> PutResult:
    ...         # Implementation...
    ...         pass
    ...
    ...     async def delete_object(self, bucket: str, key: str) -> None:
    ...         # Implementation...
    ...         pass
    ...
    ...     async def list_objects(
    ...         self, bucket: str, prefix: str | None, max_keys: int
    ...     ) -> list[str]:
    ...         # Implementation...
    ...         pass
    >>>
    >>> # Type checker verifies MyStorageAdapter implements ObjectStorage
    >>> adapter: ObjectStorage = MyStorageAdapter()
"""

from typing import Protocol

from effectful.domain.optional_value import OptionalValue

from effectful.domain.s3_object import GetObjectResult, PutResult


class ObjectStorage(Protocol):
    """Protocol for object storage operations (AWS S3, MinIO, GCS, etc.).

    This protocol defines the interface for object storage adapters. Any class
    implementing these methods can be used as an ObjectStorage adapter.

    Methods must follow these contracts:
    - get_object: Returns S3Object if exists, ObjectNotFound if not found
    - put_object: Returns PutSuccess or PutFailure ADT
    - delete_object: Always succeeds (idempotent)
    - list_objects: Returns list of keys (empty if no matches)

    All methods are async and may raise exceptions for infrastructure failures
    (network errors, service unavailable, etc.). Domain failures (object not found,
    quota exceeded) are represented as ADTs, not exceptions.
    """

    async def get_object(self, bucket: str, key: str) -> GetObjectResult:
        """Retrieve object from storage.

        Args:
            bucket: Bucket name containing the object
            key: Object key (path) within the bucket

        Returns:
            S3Object with content and metadata if object exists.
            ObjectNotFound ADT if object does not exist (not an error).

        Raises:
            Exception: For infrastructure failures (network, permissions, etc.)

        Note:
            Object not found is NOT an exception - it returns ObjectNotFound.
            This is a domain outcome, not an error.
        """
        ...

    async def put_object(
        self,
        bucket: str,
        key: str,
        content: bytes,
        metadata: OptionalValue[dict[str, str]],
        content_type: OptionalValue[str],
    ) -> PutResult:
        """Store object in storage.

        Args:
            bucket: Bucket name to store the object
            key: Object key (path) within the bucket
            content: Object content as bytes
            metadata: Optional metadata key-value pairs
            content_type: Optional MIME type (e.g., "text/plain")

        Returns:
            PutSuccess with key, bucket, and version_id if successful.
            PutFailure with reason if failed (quota, permissions, etc.).

        Raises:
            Exception: For infrastructure failures (network, service unavailable)

        Note:
            Domain failures (quota exceeded, permission denied) return PutFailure,
            not exceptions. Only infrastructure failures raise exceptions.
        """
        ...

    async def delete_object(self, bucket: str, key: str) -> None:
        """Delete object from storage.

        Args:
            bucket: Bucket name containing the object
            key: Object key (path) to delete

        Returns:
            None (deletion is idempotent - deleting non-existent object succeeds)

        Raises:
            Exception: For infrastructure failures (network, permissions, etc.)

        Note:
            Deleting a non-existent object is NOT an error. This operation is
            idempotent and always succeeds unless there's an infrastructure failure.
        """
        ...

    async def list_objects(
        self, bucket: str, prefix: OptionalValue[str], max_keys: int = 1000
    ) -> list[str]:
        """List object keys in bucket.

        Args:
            bucket: Bucket name to list objects from
            prefix: Optional key prefix to filter results (e.g., "data/")
            max_keys: Maximum number of keys to return (default: 1000)

        Returns:
            List of object keys matching the prefix.
            Empty list if no objects match (not an error).

        Raises:
            Exception: For infrastructure failures (network, bucket not found, etc.)

        Note:
            Empty results are NOT an exception - they return an empty list.
            This allows distinguishing between "no objects" and "error listing objects".
        """
        ...
