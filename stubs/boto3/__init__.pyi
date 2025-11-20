"""Type stubs for boto3.

Minimal stubs for the boto3 library to satisfy mypy strict mode.
Only includes types actually used by effectful.
"""

from typing import Protocol
from datetime import datetime
from botocore.exceptions import ClientError as ClientError

class StreamingBody(Protocol):
    """Protocol for S3 object body."""

    def read(self) -> bytes: ...

class S3GetObjectResponse(Protocol):
    """Protocol for S3 get_object response."""

    def get(self, key: str, default: object = None) -> object: ...
    def __getitem__(self, key: str) -> StreamingBody: ...

class S3PutObjectResponse(Protocol):
    """Protocol for S3 put_object response."""

    def get(self, key: str, default: str | None = None) -> str | None: ...

class S3ListObjectsResponse(Protocol):
    """Protocol for S3 list_objects_v2 response."""

    def __contains__(self, key: str) -> bool: ...
    def __getitem__(self, key: str) -> list[dict[str, str]]: ...

class S3Client(Protocol):
    """Protocol for boto3 S3 client."""

    def get_object(self, *, Bucket: str, Key: str) -> S3GetObjectResponse: ...
    def put_object(
        self,
        *,
        Bucket: str,
        Key: str,
        Body: bytes,
        Metadata: dict[str, str] | None = None,
        ContentType: str | None = None,
    ) -> S3PutObjectResponse: ...
    def delete_object(self, *, Bucket: str, Key: str) -> None: ...
    def list_objects_v2(
        self,
        *,
        Bucket: str,
        MaxKeys: int = 1000,
        Prefix: str | None = None,
    ) -> S3ListObjectsResponse: ...
    def head_bucket(self, *, Bucket: str) -> None: ...
    def create_bucket(self, *, Bucket: str) -> None: ...

def client(
    service_name: str,
    *,
    region_name: str | None = None,
    aws_access_key_id: str | None = None,
    aws_secret_access_key: str | None = None,
    endpoint_url: str | None = None,
) -> S3Client: ...
