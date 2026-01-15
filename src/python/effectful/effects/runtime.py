"""Runtime assembly effect DSL.

These effects describe infrastructure assembly steps (e.g., creating and
closing connection pools) as pure data. Interpreters perform the I/O and
return opaque handles.
"""

from dataclasses import dataclass
from typing import Generic, TypeVar

T_co = TypeVar("T_co", covariant=True)


@dataclass(frozen=True)
class ResourceHandle(Generic[T_co]):
    """Opaque handle to an external resource.

    Attributes:
        kind: Descriptive kind for debugging/metrics (e.g., "database_pool")
        resource: Underlying resource instance (interpreter-owned)
    """

    kind: str
    resource: T_co


@dataclass(frozen=True)
class CreateDatabasePool:
    """Effect: Create a database connection pool."""

    host: str
    port: int
    database: str
    user: str
    password: str
    min_size: int
    max_size: int
    command_timeout: float | None = None


@dataclass(frozen=True)
class CloseDatabasePool(Generic[T_co]):
    """Effect: Close a database connection pool."""

    handle: ResourceHandle[T_co]


@dataclass(frozen=True)
class CloseRedisClientFactory(Generic[T_co]):
    """Effect: Close a Redis client factory."""

    handle: ResourceHandle[T_co]


@dataclass(frozen=True)
class CloseObservabilityInterpreter(Generic[T_co]):
    """Effect: Close an observability interpreter."""

    handle: ResourceHandle[T_co]


@dataclass(frozen=True)
class SetAppMetadata:
    """Effect: Set metadata on an HTTP application."""

    app: ResourceHandle[object]
    title: str
    description: str
    version: str


@dataclass(frozen=True)
class ConfigureCors:
    """Effect: Configure CORS middleware for an HTTP application."""

    app: ResourceHandle[object]
    allow_origins: tuple[str, ...]
    allow_credentials: bool
    allow_methods: tuple[str, ...]
    allow_headers: tuple[str, ...]


@dataclass(frozen=True)
class IncludeRouter:
    """Effect: Include a router in an HTTP application."""

    app: ResourceHandle[object]
    router: object
    prefix: str
    tags: tuple[str, ...]


@dataclass(frozen=True)
class MountStatic:
    """Effect: Mount a static files directory."""

    app: ResourceHandle[object]
    path: str
    directory: str
    name: str


@dataclass(frozen=True)
class CreateRedisClientFactory:
    """Effect: Create a Redis client factory."""

    host: str
    port: int
    db: int


@dataclass(frozen=True)
class CreateObservabilityInterpreter:
    """Effect: Create an observability interpreter handle.

    Carries optional registry bindings so pure programs can describe
    observability configuration without impure defaults.
    """

    metrics_registry: object | None = None
    collector_registry: object | None = None


@dataclass(frozen=True)
class RegisterHttpRoute:
    """Effect: Register an HTTP route on the application.

    The endpoint field is typed as `object` rather than a callable Protocol
    because HTTP handlers have varying signatures (zero args, path params,
    Request, etc.) and async return types. The interpreter handles the
    actual callable registration with FastAPI's route system.
    """

    app: ResourceHandle[object]
    path: str
    endpoint: object  # Callable - typed as object to accept all valid signatures
    methods: tuple[str, ...]
    include_in_schema: bool = True
    response_model: object | None = None


# ADT of runtime assembly effects
type RuntimeEffect = (
    CreateDatabasePool
    | CloseDatabasePool[object]
    | CloseRedisClientFactory[object]
    | CloseObservabilityInterpreter[object]
    | SetAppMetadata
    | ConfigureCors
    | IncludeRouter
    | MountStatic
    | CreateRedisClientFactory
    | CreateObservabilityInterpreter
    | RegisterHttpRoute
)
