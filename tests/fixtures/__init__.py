"""Pytest fixtures for integration and e2e testing.

This module provides reusable fixtures for all infrastructure services:
- PostgreSQL (database.py)
- Redis (cache.py)
- MinIO S3 (storage.py)
- Apache Pulsar (messaging.py)
- Auth service (auth.py)
- Base state seeding (base_state.py)

Fixtures are designed for DRY usage across integration and e2e tests.
"""

# Re-export environment config
from tests.fixtures.config import (
    JWT_SECRET,
    MINIO_ACCESS_KEY,
    MINIO_BUCKET,
    MINIO_ENDPOINT,
    MINIO_SECRET_KEY,
    POSTGRES_DB,
    POSTGRES_HOST,
    POSTGRES_PASSWORD,
    POSTGRES_PORT,
    POSTGRES_USER,
    PULSAR_URL,
    REDIS_HOST,
    REDIS_PORT,
)

__all__ = [
    # Environment config
    "POSTGRES_HOST",
    "POSTGRES_PORT",
    "POSTGRES_DB",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "REDIS_HOST",
    "REDIS_PORT",
    "MINIO_ENDPOINT",
    "MINIO_ACCESS_KEY",
    "MINIO_SECRET_KEY",
    "MINIO_BUCKET",
    "PULSAR_URL",
    "JWT_SECRET",
]
