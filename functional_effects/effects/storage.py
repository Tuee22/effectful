"""Storage effects for object storage operations (AWS S3).

This module defines effects for interacting with object storage systems like AWS S3.
All effects are frozen dataclasses representing declarative operations to be interpreted.

Effects:
    - GetObject: Retrieve an object from storage
    - PutObject: Store an object in storage
    - DeleteObject: Remove an object from storage
    - ListObjects: List objects in a bucket/prefix

All effects follow the functional_effects patterns:
- Frozen dataclasses (immutable)
- No side effects (data only)
- Interpreted by StorageInterpreter

Example:
    >>> from functional_effects import GetObject, PutObject
    >>>
    >>> def store_data() -> Generator[AllEffects, EffectResult, str]:
    ...     # Put object in storage
    ...     object_key = yield PutObject(
    ...         bucket="my-bucket",
    ...         key="data/file.txt",
    ...         content=b"Hello World",
    ...         metadata={"content-type": "text/plain"}
    ...     )
    ...     assert isinstance(object_key, str)
    ...
    ...     # Retrieve object
    ...     s3_object = yield GetObject(bucket="my-bucket", key="data/file.txt")
    ...     assert isinstance(s3_object, S3Object)
    ...
    ...     return s3_object.key
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class GetObject:
    """Retrieve an object from storage.

    This effect retrieves an object's content and metadata from object storage (S3).

    Attributes:
        bucket: Bucket name containing the object
        key: Object key (path) within the bucket

    Returns:
        S3Object with content and metadata if object exists.
        None if object does not exist.

    Raises:
        StorageError: If retrieval fails (permission denied, network error, etc.)

    Example:
        >>> def download_file() -> Generator[AllEffects, EffectResult, bytes]:
        ...     obj = yield GetObject(bucket="my-bucket", key="data/file.txt")
        ...
        ...     match obj:
        ...         case None:
        ...             yield SendText(text="File not found")
        ...             return b""
        ...         case S3Object(content=content):
        ...             yield SendText(text="File downloaded")
        ...             return content
    """

    bucket: str
    key: str


@dataclass(frozen=True)
class PutObject:
    """Store an object in storage.

    This effect stores content with metadata in object storage (S3).

    Attributes:
        bucket: Bucket name to store the object
        key: Object key (path) within the bucket
        content: Object content as bytes
        metadata: Optional metadata key-value pairs
        content_type: Optional MIME type (e.g., "text/plain", "application/json")

    Returns:
        str: Object key that was stored.

    Raises:
        StorageError: If storage fails (quota exceeded, permission denied, etc.)

    Example:
        >>> def upload_file(data: bytes) -> Generator[AllEffects, EffectResult, str]:
        ...     object_key = yield PutObject(
        ...         bucket="my-bucket",
        ...         key="data/file.txt",
        ...         content=data,
        ...         metadata={"uploaded-by": "user-123"},
        ...         content_type="text/plain"
        ...     )
        ...     assert isinstance(object_key, str)
        ...     yield SendText(text=f"Uploaded: {object_key}")
        ...     return object_key
    """

    bucket: str
    key: str
    content: bytes
    metadata: dict[str, str] | None = None
    content_type: str | None = None


@dataclass(frozen=True)
class DeleteObject:
    """Remove an object from storage.

    This effect deletes an object from object storage (S3). Deleting a non-existent
    object is not an error (idempotent operation).

    Attributes:
        bucket: Bucket name containing the object
        key: Object key (path) to delete

    Returns:
        None (deletion always succeeds)

    Raises:
        StorageError: If deletion fails (permission denied, network error, etc.)

    Example:
        >>> def cleanup_file() -> Generator[AllEffects, EffectResult, bool]:
        ...     yield DeleteObject(bucket="my-bucket", key="temp/file.txt")
        ...     yield SendText(text="File deleted")
        ...     return True
    """

    bucket: str
    key: str


@dataclass(frozen=True)
class ListObjects:
    """List objects in a bucket with optional prefix filter.

    This effect lists objects in a bucket, optionally filtered by prefix.
    Results may be paginated for large result sets.

    Attributes:
        bucket: Bucket name to list objects from
        prefix: Optional key prefix to filter results (e.g., "data/" lists only "data/*")
        max_keys: Optional maximum number of keys to return (default: 1000)

    Returns:
        list[str]: List of object keys matching the prefix.

    Raises:
        StorageError: If listing fails (permission denied, bucket not found, etc.)

    Example:
        >>> def list_data_files() -> Generator[AllEffects, EffectResult, int]:
        ...     # List all objects under "data/" prefix
        ...     keys = yield ListObjects(
        ...         bucket="my-bucket",
        ...         prefix="data/",
        ...         max_keys=100
        ...     )
        ...     assert isinstance(keys, list)
        ...
        ...     yield SendText(text=f"Found {len(keys)} files")
        ...     return len(keys)
    """

    bucket: str
    prefix: str | None = None
    max_keys: int = 1000


# Type alias for all storage effects
type StorageEffect = GetObject | PutObject | DeleteObject | ListObjects
