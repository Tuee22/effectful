"""Protocol definitions for dependency injection."""

from app.protocols.database import DatabasePool
from app.protocols.observability import ObservabilityInterpreter
from app.protocols.redis import RedisClient

__all__ = ["DatabasePool", "ObservabilityInterpreter", "RedisClient"]
