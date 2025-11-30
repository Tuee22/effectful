"""Root pytest configuration for all tests.

This conftest imports fixtures from tests/fixtures/ to make them available
to all test modules (integration, e2e).

Fixtures are organized by service:
- database.py: PostgreSQL fixtures
- cache.py: Redis fixtures
- storage.py: MinIO S3 fixtures
- messaging.py: Pulsar fixtures
- auth.py: Auth service fixtures
- base_state.py: E2E test seeding
"""

from uuid import uuid4

import pytest

# Import all fixtures from fixtures module to make them available
# Database fixtures
from tests.fixtures.database import (
    clean_db,
    message_repo,
    postgres_connection,
    user_repo,
)

# Cache fixtures
from tests.fixtures.cache import (
    clean_redis,
    profile_cache,
    redis_client,
)

# Storage fixtures
from tests.fixtures.storage import (
    clean_minio,
    object_storage,
    s3_bucket,
)

# Messaging fixtures
from tests.fixtures.messaging import (
    clean_pulsar,
    pulsar_client,
    pulsar_consumer,
    pulsar_producer,
)

# Auth fixtures
from tests.fixtures.auth import auth_service

# Base state for e2e tests
from tests.fixtures.base_state import base_state

# Re-export all fixtures so pytest can discover them
__all__ = [
    # Database
    "postgres_connection",
    "clean_db",
    "user_repo",
    "message_repo",
    # Cache
    "redis_client",
    "clean_redis",
    "profile_cache",
    # Storage
    "s3_bucket",
    "clean_minio",
    "object_storage",
    # Messaging
    "pulsar_client",
    "pulsar_producer",
    "pulsar_consumer",
    "clean_pulsar",
    # Auth
    "auth_service",
    # Base state
    "base_state",
    # Common
    "test_user_id",
]


# =============================================================================
# Common Fixtures
# =============================================================================


@pytest.fixture
def test_user_id() -> str:
    """Provide a unique user ID for testing.

    Returns:
        New UUID as string
    """
    return str(uuid4())
