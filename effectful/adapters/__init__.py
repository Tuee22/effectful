"""Infrastructure adapters for functional-effects.

This module provides production-ready implementations of the infrastructure protocols:
- PostgreSQL repositories using asyncpg
- Redis cache using redis-py
- WebSocket connections using websockets library

These adapters are the "real" implementations that connect to actual infrastructure.
For testing, use pytest mocks (mocker.AsyncMock) instead of custom fakes.
"""

from effectful.adapters.postgres import (
    PostgresChatMessageRepository,
    PostgresUserRepository,
)
from effectful.adapters.redis_cache import RedisProfileCache
from effectful.adapters.websocket_connection import RealWebSocketConnection

__all__ = [
    "PostgresUserRepository",
    "PostgresChatMessageRepository",
    "RedisProfileCache",
    "RealWebSocketConnection",
]
