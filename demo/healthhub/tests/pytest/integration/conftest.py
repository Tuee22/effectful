"""Integration test configuration."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import asyncpg
import redis.asyncio as redis
from app.interpreters.composite_interpreter import CompositeInterpreter
from app.interpreters.notification_interpreter import NotificationInterpreter
from app.protocols.observability import ObservabilityInterpreter


@pytest.fixture(autouse=True)
async def _clean_state(clean_healthhub_state: None) -> AsyncIterator[None]:
    """Ensure deterministic DB/Redis state for every integration test."""
    yield


@pytest.fixture
def composite_interpreter(
    db_pool: asyncpg.Pool[asyncpg.Record],
    redis_client: redis.Redis[bytes],
    observability_interpreter: ObservabilityInterpreter,
) -> CompositeInterpreter:
    """Provide a CompositeInterpreter with real Postgres/Redis."""
    return CompositeInterpreter(
        pool=db_pool,
        redis_client=redis_client,
        observability_interpreter=observability_interpreter,
    )


@pytest.fixture
def notification_interpreter(
    db_pool: asyncpg.Pool[asyncpg.Record],
    redis_client: redis.Redis[bytes],
) -> NotificationInterpreter:
    """Provide a NotificationInterpreter with real Postgres/Redis."""
    return NotificationInterpreter(db_pool, redis_client)
