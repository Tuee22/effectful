"""MinIO S3 fixtures for integration and e2e testing.

Provides fixtures for:
- S3 bucket creation
- Object cleanup
- S3ObjectStorage adapter
"""

import boto3
import pytest
from botocore.exceptions import ClientError

from effectful.adapters.s3_storage import S3ObjectStorage
from tests.fixtures.config import (
    MINIO_ACCESS_KEY,
    MINIO_BUCKET,
    MINIO_ENDPOINT,
    MINIO_SECRET_KEY,
)


@pytest.fixture
def s3_bucket() -> str:
    """Ensure test bucket exists and is clean.

    Returns:
        Bucket name for testing
    """
    s3_client = boto3.client(
        "s3",
        endpoint_url=f"http://{MINIO_ENDPOINT}",
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
        region_name="us-east-1",
    )
    bucket_name = MINIO_BUCKET

    # Create bucket if it doesn't exist
    try:
        s3_client.head_bucket(Bucket=bucket_name)
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "")
        if error_code in ("404", "NoSuchBucket"):
            s3_client.create_bucket(Bucket=bucket_name)

    return bucket_name


@pytest.fixture
def clean_minio(s3_bucket: str) -> str:
    """Provide a clean MinIO bucket.

    Deletes all objects in the test bucket before returning.
    Tests should upload their own objects after receiving this fixture.

    Returns:
        Name of the clean bucket
    """
    s3_client = boto3.client(
        "s3",
        endpoint_url=f"http://{MINIO_ENDPOINT}",
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
        region_name="us-east-1",
    )

    # List and delete all objects in bucket
    # NOTE: for-loop acceptable here per code_quality.md - infrastructure cleanup at I/O boundary
    try:
        response = s3_client.list_objects_v2(Bucket=s3_bucket)
        if "Contents" in response:
            for obj in response["Contents"]:
                s3_client.delete_object(Bucket=s3_bucket, Key=obj["Key"])
    except ClientError:
        # Bucket might not exist yet, that's OK
        pass

    return s3_bucket


@pytest.fixture
def object_storage(s3_bucket: str) -> S3ObjectStorage:
    """Provide object storage backed by real MinIO.

    Args:
        s3_bucket: Ensures bucket exists before creating storage

    Returns:
        S3ObjectStorage instance
    """
    client = boto3.client(
        "s3",
        endpoint_url=f"http://{MINIO_ENDPOINT}",
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
        region_name="us-east-1",
    )
    return S3ObjectStorage(client)
