"""Environment configuration for test fixtures.

All environment variables for Docker services are centralized here.
"""

import os

# PostgreSQL configuration
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "effectful_test")
POSTGRES_USER = os.getenv("POSTGRES_USER", "effectful")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "effectful_pass")

# Redis configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

# MinIO S3 configuration
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "effectful-test")

# Apache Pulsar configuration
PULSAR_URL = os.getenv("PULSAR_URL", "pulsar://localhost:6650")

# JWT configuration for auth testing
JWT_SECRET = os.getenv("JWT_SECRET", "test-secret-key-for-integration-tests")
