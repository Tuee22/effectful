"""Application container for dependency injection.

Replaces module-level singleton globals with explicit container stored in app.state.
Container is frozen (immutable) and created once at application startup.
"""

from dataclasses import dataclass
from app.protocols.database import DatabasePool
from app.protocols.observability import ObservabilityInterpreter
from app.protocols.redis_factory import RedisClientFactory
from app.protocols.interpreter_factory import InterpreterFactory


@dataclass(frozen=True)
class ApplicationContainer:
    """Container holding application-scoped resources.

    Stored in FastAPI app.state, created during lifespan startup.
    All resources implement protocols, making lifecycle invisible to consumers.

    Resources:
        database_pool: Application-scoped PostgreSQL connection pool
        observability_interpreter: Metrics recording and instrumentation
        redis_factory: Factory for creating per-request Redis clients
        interpreter_factory: Factory for creating interpreters with managed Redis lifecycle

    Testing: Override via app.dependency_overrides with pytest-mock mocks
    """

    database_pool: DatabasePool
    observability_interpreter: ObservabilityInterpreter
    redis_factory: RedisClientFactory
    interpreter_factory: InterpreterFactory
