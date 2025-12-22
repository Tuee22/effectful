# Tutorial 05: Production Deployment

**Status**: Authoritative source
**Supersedes**: none
**Referenced by**: README.md, documents/readme.md, examples/README.md, documents/api/interpreters.md, documents/tutorials/quickstart.md, documents/tutorials/adts_and_results.md, documents/tutorials/advanced_composition.md, documents/tutorials/00_library_deltas/production_deployment.md, demo/healthhub/documents/tutorials/00_library_deltas/README.md, demo/healthhub/documents/tutorials/00_library_deltas/production_deployment.md, demo/healthhub/documents/tutorials/01_journeys/advanced_journey.md

> **Purpose**: Tutorial for deploying effectful programs to production with proper infrastructure configuration.

## SSoT Link Map

| Need                    | Link                                                                                         |
| ----------------------- | -------------------------------------------------------------------------------------------- |
| Infrastructure topology | [Architecture](../engineering/architecture.md#infrastructure-topology)                       |
| Interpreters API        | [Interpreters API](../api/interpreters.md)                                                   |
| Advanced composition    | [Advanced Composition](advanced_composition.md)                                              |
| Configuration lifecycle | [Code Quality](../engineering/code_quality.md#doctrine-7-configuration-lifecycle-management) |

## Prerequisites

- Completed previous tutorials (01-04)
- Familiarity with FastAPI
- Basic knowledge of PostgreSQL and Redis
- Understanding of async Python

## Learning Objectives

By the end of this tutorial, you will:

- Configure production infrastructure (PostgreSQL, Redis, WebSocket)
- Use connection pooling for scalability
- Implement error monitoring and logging
- Configure timeouts and retries
- Deploy with Docker

______________________________________________________________________

## Step 1: Settings boundary (single injection point)

Create a frozen Pydantic settings class and instantiate it **only** inside the FastAPI lifespan. All downstream assembly flows derive from this instance.

```python
# config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(frozen=True, extra="ignore")

    postgres_host: str
    postgres_port: int
    postgres_db: str
    postgres_user: str
    postgres_password: str
    redis_host: str
    redis_port: int
    redis_db: int = 0

    app_name: str = "Effectful Demo"
    app_env: str = "production"
    api_prefix: str = "/api"
    cors_origins: list[str] = ["http://localhost:8000"]
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = ["*"]
    cors_allow_headers: list[str] = ["*"]
```

______________________________________________________________________

## Step 2: Pure startup/shutdown programs

Use the core runtime effects to model middleware, routing, static mounts, observability, and infrastructure handles as pure data. Programs return opaque handles (`ResourceHandle`) on success.

```python
# programs/startup.py
from collections.abc import Generator
from dataclasses import dataclass
from effectful.effects.runtime import (
    CloseDatabasePool,
    CloseRedisClientFactory,
    ConfigureCors,
    CreateDatabasePool,
    CreateRedisClientFactory,
    IncludeRouter,
    MountStatic,
    RegisterHttpRoute,
    ResourceHandle,
    RuntimeEffect,
    SetAppMetadata,
)
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, REGISTRY, generate_latest

@dataclass(frozen=True)
class RouterSpec:
    router: object
    prefix: str
    tags: tuple[str, ...]

@dataclass(frozen=True)
class StaticMountSpec:
    path: str
    directory: str
    name: str

@dataclass(frozen=True)
class StartupAssembly:
    app: ResourceHandle[object]
    db_pool: ResourceHandle[object]
    redis_factory: ResourceHandle[object]

async def _metrics() -> Response:
    return Response(content=generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)

def startup_program(
    settings: Settings,
    app_handle: ResourceHandle[object],
    routers: tuple[RouterSpec, ...],
    static_mounts: tuple[StaticMountSpec, ...],
) -> Generator[RuntimeEffect, ResourceHandle[object], StartupAssembly]:
    yield SetAppMetadata(
        app=app_handle,
        title=settings.app_name,
        description="Effectful production deployment",
        version="1.0.0",
    )
    yield ConfigureCors(
        app=app_handle,
        allow_origins=tuple(settings.cors_origins),
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=tuple(settings.cors_allow_methods),
        allow_headers=tuple(settings.cors_allow_headers),
    )
    for spec in routers:
        yield IncludeRouter(app=app_handle, router=spec.router, prefix=spec.prefix, tags=spec.tags)
    for mount in static_mounts:
        yield MountStatic(app=app_handle, path=mount.path, directory=mount.directory, name=mount.name)

    yield RegisterHttpRoute(
        app=app_handle,
        path="/metrics",
        endpoint=_metrics,
        methods=("GET",),
        include_in_schema=False,
        response_model=None,
    )

    redis_handle = yield CreateRedisClientFactory(
        host=settings.redis_host, port=settings.redis_port, db=settings.redis_db
    )
    pool_handle = yield CreateDatabasePool(
        host=settings.postgres_host,
        port=settings.postgres_port,
        database=settings.postgres_db,
        user=settings.postgres_user,
        password=settings.postgres_password,
        min_size=5,
        max_size=20,
        command_timeout=60.0,
    )
    return StartupAssembly(app=app_handle, db_pool=pool_handle, redis_factory=redis_handle)

def shutdown_program(startup: StartupAssembly) -> Generator[RuntimeEffect, object, None]:
    yield CloseRedisClientFactory(handle=startup.redis_factory)
    yield CloseDatabasePool(handle=startup.db_pool)
```

______________________________________________________________________

## Step 3: Interpreter + FastAPI lifespan

Keep I/O confined to the interpreter. Lifespan constructs settings, runs the pure program with `run_ws_program`, stores handles on `app.state`, and runs teardown on shutdown.

```python
# main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.routing import APIRouter
from fastapi.staticfiles import StaticFiles
import asyncpg
import redis.asyncio as redis

from effectful.algebraic.result import Err, Ok
from effectful.effects.runtime import (
    CreateDatabasePool,
    CreateRedisClientFactory,
    MountStatic,
    ResourceHandle,
)
from effectful.interpreters.runtime import RuntimeInterpreter
from effectful.programs.runners import run_ws_program

from config import Settings
from programs.startup import RouterSpec, StaticMountSpec, startup_program, shutdown_program

async def _create_asyncpg_pool(effect: CreateDatabasePool) -> ResourceHandle[asyncpg.Pool]:
    pool = await asyncpg.create_pool(
        host=effect.host,
        port=effect.port,
        database=effect.database,
        user=effect.user,
        password=effect.password,
        min_size=effect.min_size,
        max_size=effect.max_size,
        command_timeout=effect.command_timeout,
    )
    return ResourceHandle(kind="database_pool", resource=pool)

class RedisFactory:
    def __init__(self, host: str, port: int, db: int) -> None:
        self._host, self._port, self._db = host, port, db
    def create(self) -> redis.Redis[bytes]:
        return redis.Redis(host=self._host, port=self._port, db=self._db, decode_responses=False)
    async def close(self) -> None:  # matches CloseRedisClientFactory expectation
        return None
    async def managed(self):
        client = self.create()
        try:
            yield client
        finally:
            await client.aclose()

async def _create_redis_factory(
    effect: CreateRedisClientFactory,
) -> ResourceHandle[RedisFactory]:
    factory = RedisFactory(effect.host, effect.port, effect.db)
    return ResourceHandle(kind="redis_factory", resource=factory)

async def _mount_static(effect: MountStatic) -> None:
    app: FastAPI = effect.app.resource
    app.mount(effect.path, StaticFiles(directory=effect.directory), name=effect.name)

runtime_interpreter = RuntimeInterpreter(
    create_db_pool=_create_asyncpg_pool,
    close_db_pool=lambda eff: eff.handle.resource.close(),
    create_redis_factory=_create_redis_factory,
    close_redis_factory=lambda eff: eff.handle.resource.close(),
    mount_static=_mount_static,
    # include_router, configure_cors, set_app_metadata, register_route can rely on FastAPI defaults
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = Settings()
    app_handle = ResourceHandle(kind="fastapi_app", resource=app)

    routers = (RouterSpec(router=APIRouter(), prefix=f"{settings.api_prefix}/health", tags=("health",)),)
    static_dir = "/opt/frontend-build/static"
    static_mounts = (
        StaticMountSpec(path="/static", directory=static_dir, name="static"),
    )

    startup_result = await run_ws_program(
        startup_program(settings, app_handle=app_handle, routers=routers, static_mounts=static_mounts),
        runtime_interpreter,
    )
    match startup_result:
        case Ok(startup):
            app.state.startup = startup
        case Err(error):
            raise RuntimeError(f"Startup failed: {error}")
    app.state.settings = settings
    yield

    shutdown_result = await run_ws_program(shutdown_program(app.state.startup), runtime_interpreter)
    match shutdown_result:
        case Ok():
            pass
        case Err(error):
            raise RuntimeError(f"Shutdown failed: {error}")

app = FastAPI(lifespan=lifespan)
```

This pattern satisfies the Purity Migration Plan: settings are the only injected input, interpreters own all I/O, and startup/shutdown flows are pure effect programs returning handles. Any demo overlays should link back to `architecture.md#pure-interpreter-assembly-doctrine` and describe deltas only.

## Step 3: Error monitoring

### Logging Configuration

```python
# file: examples/05_production_deployment.py
# src/logging_config.py
import logging
import sys

def setup_logging(level: str = "INFO") -> None:
    """Configure application logging."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("app.log"),
        ],
    )

    # Configure library loggers
    logging.getLogger("asyncpg").setLevel(logging.WARNING)
    logging.getLogger("redis").setLevel(logging.WARNING)
```

### Sentry Integration

**Install Dependencies**:

```bash
# snippet
poetry add sentry-sdk
```

**Configuration**:

```python
# file: examples/05_production_deployment.py
# src/monitoring.py
import sentry_sdk
from sentry_sdk.integrations.asyncio import AsyncioIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

def init_sentry(dsn: str, environment: str = "production") -> None:
    """Initialize Sentry error monitoring."""
    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        integrations=[
            AsyncioIntegration(),
            LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
        ],
        traces_sample_rate=0.1,  # 10% of transactions
        profiles_sample_rate=0.1,  # 10% of transactions
    )
```

**Error Reporting**:

```python
# file: examples/05_production_deployment.py
from effectful import run_ws_program, Err
import sentry_sdk

result = await run_ws_program(my_program(), interpreter)

match result:
    case Err(error):
        # Report error to Sentry
        sentry_sdk.capture_exception(Exception(str(error)))
        logger.error(f"Program failed: {error}")
    case Ok(value):
        logger.info(f"Program succeeded: {value}")
```

______________________________________________________________________

## Step 4: Environment configuration

### Settings Management

```python
# file: examples/05_production_deployment.py
# src/settings.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings from environment variables."""

    # Database
    database_url: str
    database_pool_min_size: int = 5
    database_pool_max_size: int = 20

    # Redis
    redis_url: str
    redis_max_connections: int = 10

    # Application
    environment: str = "production"
    log_level: str = "INFO"
    program_timeout_seconds: float = 300.0

    # Monitoring
    sentry_dsn: str | None = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
```

**Environment File (.env)**:

```bash
# Database
DATABASE_URL=postgresql://user:password@db:5432/mydb
DATABASE_POOL_MIN_SIZE=5
DATABASE_POOL_MAX_SIZE=20

# Redis
REDIS_URL=redis://redis:6379/0
REDIS_MAX_CONNECTIONS=10

# Application
ENVIRONMENT=production
LOG_LEVEL=INFO
PROGRAM_TIMEOUT_SECONDS=300.0

# Monitoring
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project
```

______________________________________________________________________

## Step 5: Docker deployment

### Dockerfile

```dockerfile
# file: examples/05_production_deployment.Dockerfile
# Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install Poetry
RUN pip install poetry==1.7.0

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-dev --no-interaction --no-ansi

# Copy application code
COPY src ./src

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose

```yaml
# file: configs/05_production_deployment.yaml
# docker-compose.yml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/mydb
      - REDIS_URL=redis://redis:6379/0
      - ENVIRONMENT=production
      - LOG_LEVEL=INFO
    depends_on:
      - db
      - redis

  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=mydb
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

**Start Services**:

```bash
# snippet
docker-compose up -d
```

______________________________________________________________________

## Step 6: Performance tuning

### Connection Pool Sizing

**Formula**: `connections = (core_count * 2) + effective_spindle_count`

For web application:

```python
# file: examples/05_production_deployment.py
# 4 CPU cores
min_size = 5
max_size = (4 * 2) + 1 = 9
```

### Timeout Configuration

```python
# file: examples/05_production_deployment.py
# Program execution timeout
PROGRAM_TIMEOUT = 300.0  # 5 minutes

# Database query timeout
DATABASE_TIMEOUT = 60.0  # 1 minute

# Redis operation timeout
REDIS_TIMEOUT = 5.0  # 5 seconds
```

### Caching Strategy

```python
# file: examples/05_production_deployment.py
# Cache TTL by data type
CACHE_TTL_PROFILE = 600     # 10 minutes
CACHE_TTL_SESSION = 3600    # 1 hour
CACHE_TTL_STATIC = 86400    # 24 hours
```

______________________________________________________________________

## Step 7: Health checks

### Endpoint Implementation

```python
# file: examples/05_production_deployment.py
from fastapi import status
from fastapi.responses import JSONResponse

@app.get("/health")
async def health_check() -> JSONResponse:
    """Health check endpoint for load balancers."""
    checks = {}

    # Check database
    try:
        async with get_db_connection() as conn:
            await conn.fetchval("SELECT 1")
        checks["database"] = "healthy"
    except Exception as e:
        checks["database"] = f"unhealthy: {e}"

    # Check Redis
    try:
        redis = get_redis()
        await redis.ping()
        checks["redis"] = "healthy"
    except Exception as e:
        checks["redis"] = f"unhealthy: {e}"

    # Overall status
    is_healthy = all(v == "healthy" for v in checks.values())
    status_code = status.HTTP_200_OK if is_healthy else status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        content={
            "status": "healthy" if is_healthy else "unhealthy",
            "checks": checks,
        },
        status_code=status_code,
    )
```

______________________________________________________________________

## Step 8: Deployment checklist

### Pre-Deployment

- [ ] All tests passing (unit, integration, E2E)
- [ ] Type checking passes (`mypy --strict`)
- [ ] Code quality checks pass (Black, Ruff)
- [ ] Environment variables configured
- [ ] Database migrations applied
- [ ] Connection pools configured
- [ ] Timeouts configured
- [ ] Error monitoring configured (Sentry)
- [ ] Health checks implemented
- [ ] Logging configured

### Post-Deployment

- [ ] Health check returns 200 OK
- [ ] Metrics dashboard shows normal traffic
- [ ] Error rate < 1%
- [ ] P95 latency < 500ms
- [ ] Database connection pool utilization < 80%
- [ ] Redis connection pool utilization < 80%
- [ ] No memory leaks (stable memory usage)
- [ ] CPU usage < 70%

______________________________________________________________________

## Best Practices

### ✅ DO

1. **Use Pure Startup Programs for Pools/Infra**

   ```python
   # file: examples/05_production_deployment.py
   from pathlib import Path
   from fastapi import APIRouter, FastAPI
   from effectful.algebraic.result import Err, Ok
   from effectful.effects.runtime import ResourceHandle
   from effectful.programs.runners import run_ws_program
   from app.config import Settings
   from app.interpreters.runtime_interpreter import build_runtime_interpreter
   from app.programs.startup import RouterSpec, StaticMountSpec, startup_program

   app = FastAPI()
   router = APIRouter()
   runtime = build_runtime_interpreter()
   settings = Settings()
   app_handle = ResourceHandle(kind="fastapi_app", resource=app)

   match await run_ws_program(
       startup_program(
           settings,
           app_handle=app_handle,
           routers=(RouterSpec(router=router, prefix="/api", tags=("api",)),),
           static_mounts=(StaticMountSpec(path="/static", directory="/opt/frontend", name="static"),),
           frontend_build_path=Path("/opt/frontend"),
       ),
       runtime,
   ):
       case Ok(assembly):
           db_pool = assembly.database_pool.resource
           redis_factory = assembly.redis_factory.resource
       case Err(error):
           raise RuntimeError(f"Startup failed: {error}")
   ```

   (Pure program describes wiring; interpreter owns I/O. See `documents/engineering/architecture.md#pure-interpreter-assembly-doctrine`.)

1. **Configure Timeouts**

   ```python
   # file: examples/05_production_deployment.py
   result = await asyncio.wait_for(run_ws_program(...), timeout=300.0)
   ```

1. **Monitor Errors**

   ```python
   # file: examples/05_production_deployment.py
   sentry_sdk.capture_exception(Exception(str(error)))
   ```

1. **Validate Health**

   ```python
   # file: examples/05_production_deployment.py
   @app.get("/health")
   async def health_check() -> JSONResponse: ...
   ```

1. **Use Environment Variables**

   ```python
   # file: examples/05_production_deployment.py
   settings = Settings()  # Loads from .env
   ```

### ❌ DON'T

1. **Don't Create Connections Per Request or Outside Interpreters**

   ```python
   # file: examples/05_production_deployment.py
   # ❌ Imperative wiring that bypasses the pure interpreter boundary
   conn = await asyncpg.connect(DATABASE_URL)
   ```

1. **Don't Skip Error Monitoring**

   ```python
   # file: examples/05_production_deployment.py
   # ❌ Silent failures
   match result:
       case Err(_): pass
   ```

1. **Don't Use Hardcoded Secrets**

   ```python
   # file: examples/05_production_deployment.py
   # ❌ Security risk
   DATABASE_URL = "postgresql://user:password@localhost/db"
   ```

______________________________________________________________________

## Next Steps

- Read [Tutorial 06: Advanced Composition](./advanced_composition.md) for complex workflows
- Explore production examples in `examples/`
- Read [API Reference: Interpreters](../api/interpreters.md) for configuration options

## Summary

You learned how to:

- ✅ Configure production infrastructure (PostgreSQL, Redis)
- ✅ Use connection pooling for scalability
- ✅ Integrate with FastAPI and WebSocket
- ✅ Monitor errors with Sentry
- ✅ Deploy with Docker
- ✅ Implement health checks

Your application is production-ready! 🚀

______________________________________________________________________

## Cross-References

- [Documentation Standards](../documentation_standards.md)
- [Engineering Standards](../engineering/README.md)
