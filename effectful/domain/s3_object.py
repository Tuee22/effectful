"""Domain models for S3 objects and storage operations.

This module defines domain types for AWS S3 object storage using algebraic data types.
All models are frozen dataclasses (immutable) following effectful patterns.

Domain Models:
    - S3Object: Object content and metadata from S3
    - PutSuccess: Successful object storage
    - PutFailure: Failed object storage with reason
    - PutResult: ADT combining success and failure cases

All models use ADTs instead of Optional to make all outcomes explicit.

Example:
    >>> from effectful.domain.s3_object import S3Object, PutSuccess, PutFailure
    >>>
    >>> # Success case
    >>> success = PutSuccess(key="data/file.txt", bucket="my-bucket", version_id="v1")
    >>>
    >>> # Failure case
    >>> failure = PutFailure(
    ...     key="data/file.txt",
    ...     bucket="my-bucket",
    ...     reason="quota_exceeded"
    ... )
    >>>
    >>> # Pattern match on result
    >>> match result:
    ...     case PutSuccess(key=key, version_id=vid):
    ...         print(f"Stored {key} version {vid}")
    ...     case PutFailure(key=key, reason=reason):
    ...         print(f"Failed to store {key}: {reason}")
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from effectful.domain.optional_value import (
    Absent,
    OptionalValue,
    Provided,
    to_optional_value,
)


def _normalize_optional_value(value: str | OptionalValue[str] | None) -> OptionalValue[str]:
    """Convert plain values into OptionalValue ADT without escape hatches."""
    if isinstance(value, (Provided, Absent)):
        return value
    return to_optional_value(value)


@dataclass(frozen=True, init=False)
class S3Object:
    """Object retrieved from S3 storage.

    This model represents an object's content and metadata retrieved from S3.
    All objects have a key, bucket, content, and last modified time. Metadata
    and content type are optional.

    Attributes:
        key: Object key (path) in the bucket
        bucket: Bucket name containing the object
        content: Object content as bytes
        last_modified: Timestamp of last modification
        metadata: Optional metadata key-value pairs
        content_type: Optional MIME type (e.g., "text/plain")
        size: Content size in bytes
        version_id: Optional version ID (if bucket versioning enabled)

    Example:
        >>> obj = S3Object(
        ...     key="data/file.txt",
        ...     bucket="my-bucket",
        ...     content=b"Hello World",
        ...     last_modified=datetime.now(UTC),
        ...     metadata={"uploaded-by": "user-123"},
        ...     content_type="text/plain",
        ...     size=11,
        ...     version_id="v1"
        ... )
        >>>
        >>> # Pattern match on object
        >>> match obj:
        ...     case S3Object(key=key, content=content, content_type="text/plain"):
        ...         text = content.decode("utf-8")
        ...         print(f"{key}: {text}")
    """

    key: str
    bucket: str
    content: bytes
    last_modified: datetime
    metadata: dict[str, str]
    content_type: OptionalValue[str]
    size: int
    version_id: OptionalValue[str]

    def __init__(
        self,
        key: str,
        bucket: str,
        content: bytes,
        last_modified: datetime,
        metadata: dict[str, str] | None = None,
        content_type: str | OptionalValue[str] | None = None,
        size: int = 0,
        version_id: str | OptionalValue[str] | None = None,
    ) -> None:
        object.__setattr__(self, "key", key)
        object.__setattr__(self, "bucket", bucket)
        object.__setattr__(self, "content", content)
        object.__setattr__(self, "last_modified", last_modified)
        object.__setattr__(self, "metadata", metadata or {})
        object.__setattr__(self, "content_type", _normalize_optional_value(content_type))
        object.__setattr__(self, "size", size)
        object.__setattr__(self, "version_id", _normalize_optional_value(version_id))


@dataclass(frozen=True)
class ObjectNotFound:
    """Object lookup result when the key does not exist.

    This ADT replaces None to make the "not found" state explicit and
    pattern-matchable.

    Attributes:
        bucket: Bucket that was queried
        key: Object key that was requested
    """

    bucket: str
    key: str


@dataclass(frozen=True, init=False)
class PutSuccess:
    """Successful object storage operation.

    This model represents a successful PutObject operation. It contains the key,
    bucket, and optional version ID of the stored object.

    Attributes:
        key: Object key that was stored
        bucket: Bucket where object was stored
        version_id: Optional version ID (if bucket versioning enabled)

    Example:
        >>> success = PutSuccess(
        ...     key="data/file.txt",
        ...     bucket="my-bucket",
        ...     version_id="v2"
        ... )
        >>>
        >>> match success:
        ...     case PutSuccess(key=key, version_id=vid):
        ...         print(f"Stored {key} as version {vid}")
    """

    key: str
    bucket: str
    version_id: OptionalValue[str]

    def __init__(
        self,
        key: str,
        bucket: str,
        version_id: str | OptionalValue[str] | None = None,
    ) -> None:
        object.__setattr__(self, "key", key)
        object.__setattr__(self, "bucket", bucket)
        object.__setattr__(self, "version_id", _normalize_optional_value(version_id))


@dataclass(frozen=True)
class PutFailure:
    """Failed object storage operation.

    This model represents a failed PutObject operation with a specific reason.
    The reason is constrained to a known set of failure modes.

    Attributes:
        key: Object key that failed to store
        bucket: Bucket where storage was attempted
        reason: Failure reason (see below)

    Failure Reasons:
        - quota_exceeded: Storage quota limit reached
        - permission_denied: Insufficient permissions to write
        - invalid_object_state: Object in invalid state (e.g., locked)

    Example:
        >>> failure = PutFailure(
        ...     key="data/file.txt",
        ...     bucket="my-bucket",
        ...     reason="quota_exceeded"
        ... )
        >>>
        >>> match failure:
        ...     case PutFailure(key=key, reason="quota_exceeded"):
        ...         print(f"Quota exceeded storing {key}")
        ...     case PutFailure(key=key, reason="permission_denied"):
        ...         print(f"Permission denied storing {key}")
    """

    key: str
    bucket: str
    reason: Literal["quota_exceeded", "permission_denied", "invalid_object_state"]


# ADT: PutResult can be either success or failure (not Optional)
type PutResult = PutSuccess | PutFailure

# ADT: GetObjectResult is either the object or an explicit not-found marker
type GetObjectResult = S3Object | ObjectNotFound
