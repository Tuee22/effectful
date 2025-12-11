"""Pytest fixtures for integration testing.

This module imports all fixtures from tests/conftest.py.
Fixtures are now centralized in tests/fixtures/ for DRY reuse.

For integration tests, fixtures connect to real Docker services:
- PostgreSQL (asyncpg)
- Redis (redis-py async)
- MinIO S3 (boto3)
- Apache Pulsar (pulsar-client)
"""

from collections.abc import AsyncGenerator
from dataclasses import dataclass
from types import SimpleNamespace

import asyncpg
import pytest
import pytest_asyncio
from pytest_mock import MockerFixture
from redis.asyncio import Redis

from effectful.adapters.postgres import PostgresChatMessageRepository, PostgresUserRepository
from effectful.adapters.redis_cache import RedisProfileCache
from effectful.infrastructure.repositories import ChatMessageRepository, UserRepository
from effectful.infrastructure.websocket import WebSocketConnection
from effectful.interpreters.composite import CompositeInterpreter, create_composite_interpreter

# All fixtures are imported from the root conftest via tests/fixtures/
# This file only contains integration-specific composite fixtures

# =============================================================================
# Composite Clean Fixtures (Integration-specific)
# =============================================================================


@pytest_asyncio.fixture
async def clean_all(
    clean_db: asyncpg.Connection,
    clean_redis: Redis,
    clean_minio: str,
) -> AsyncGenerator[dict[str, asyncpg.Connection | Redis | str], None]:
    """Provide all infrastructure clean and ready.

    Convenience fixture that combines clean_db, clean_redis, and clean_minio.
    Use for composite workflow tests that span multiple services.

    Yields:
        Dict with keys: "db", "redis", "minio"
    """
    yield {
        "db": clean_db,
        "redis": clean_redis,
        "minio": clean_minio,
    }


# =============================================================================
# Interpreter Fixtures (reduce per-test boilerplate)
# =============================================================================


@dataclass(frozen=True)
class InterpreterDeps:
    websocket_connection: "MockWebSocketConnection"
    user_repo: UserRepository
    message_repo: ChatMessageRepository


class MockWebSocketConnection(WebSocketConnection):
    """Test double for WebSocketConnection backed by AsyncMocks."""

    def __init__(self, mocker: MockerFixture) -> None:
        self._send_text = mocker.AsyncMock()
        self._receive_text = mocker.AsyncMock()
        self._close = mocker.AsyncMock()
        self._is_open = True
        self._mock = SimpleNamespace(
            send_text=self._send_text,
            receive_text=self._receive_text,
            close=self._close,
            is_open=mocker.Mock(return_value=self._is_open),
        )

    def reset_mock(self) -> None:
        """Reset all underlying mocks to initial state."""
        self._send_text.reset_mock()
        self._receive_text.reset_mock()
        self._close.reset_mock()
        self._mock.is_open.reset_mock()
        self._is_open = True
        self._mock.is_open.return_value = True

    async def send_text(self, text: str) -> None:
        await self._send_text(text)

    async def receive_text(self) -> str:
        return await self._receive_text()

    async def close(self) -> None:
        await self._close()

    async def is_open(self) -> bool:
        return self._is_open

    @property
    def mock(self) -> SimpleNamespace:
        """Expose underlying mocks for assertions."""
        return self._mock

    def __getattr__(self, item: str) -> object:
        # Delegate attribute access (e.g., assert_called) to underlying mock
        return getattr(self._mock, item)


@pytest.fixture
def mock_interpreter_deps(mocker: MockerFixture) -> InterpreterDeps:
    """Provide mocked interpreter dependencies reused across integration tests."""
    websocket_connection = MockWebSocketConnection(mocker)
    user_repo: UserRepository = mocker.AsyncMock(spec=UserRepository)
    message_repo: ChatMessageRepository = mocker.AsyncMock(spec=ChatMessageRepository)

    return InterpreterDeps(
        websocket_connection=websocket_connection,
        user_repo=user_repo,
        message_repo=message_repo,
    )


@pytest.fixture
def interpreter_with_redis(
    mock_interpreter_deps: InterpreterDeps,
    clean_redis: Redis,
) -> tuple[CompositeInterpreter, MockWebSocketConnection]:
    """Composite interpreter with real Redis cache and mocked deps."""
    interpreter = create_composite_interpreter(
        websocket_connection=mock_interpreter_deps.websocket_connection,
        user_repo=mock_interpreter_deps.user_repo,
        message_repo=mock_interpreter_deps.message_repo,
        cache=RedisProfileCache(clean_redis),
    )
    websocket = mock_interpreter_deps.websocket_connection
    return interpreter, websocket


@pytest.fixture
def interpreter_with_postgres_and_redis(
    mock_interpreter_deps: InterpreterDeps,
    clean_db: asyncpg.Connection,
    clean_redis: Redis,
) -> tuple[CompositeInterpreter, MockWebSocketConnection]:
    """Composite interpreter with real Postgres + Redis and mocked websocket."""
    websocket = mock_interpreter_deps.websocket_connection
    interpreter = create_composite_interpreter(
        websocket_connection=websocket,
        user_repo=PostgresUserRepository(clean_db),
        message_repo=PostgresChatMessageRepository(clean_db),
        cache=RedisProfileCache(clean_redis),
    )
    return interpreter, websocket
