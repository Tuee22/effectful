# Tutorial 05: Production Deployment

This tutorial guides you through deploying effectful programs to production with proper infrastructure configuration.

> **Core Doctrine**: For the complete infrastructure topology and architecture diagrams, see [architecture.md](../engineering/architecture.md#infrastructure-topology).

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

---

## Part 1: Infrastructure Setup

### PostgreSQL Configuration

**Install Dependencies**:
```bash
# For library users adding effectful to YOUR application
poetry add asyncpg

# For effectful contributors (inside Docker)
docker compose -f docker/docker-compose.yml exec effectful poetry add asyncpg
```

**Connection Pool Setup**:
```python
# src/infrastructure/database.py
import asyncpg
from contextlib import asynccontextmanager
from typing import AsyncIterator

DATABASE_URL = "postgresql://user:password@localhost:5432/mydb"

# Create connection pool
db_pool: asyncpg.Pool | None = None

async def init_database_pool() -> None:
    """Initialize PostgreSQL connection pool."""
    global db_pool
    db_pool = await asyncpg.create_pool(
        dsn=DATABASE_URL,
        min_size=5,          # Minimum connections
        max_size=20,         # Maximum connections
        command_timeout=60.0, # Query timeout (seconds)
        max_inactive_connection_lifetime=300.0,  # 5 minutes
    )

async def close_database_pool() -> None:
    """Close PostgreSQL connection pool."""
    global db_pool
    if db_pool is not None:
        await db_pool.close()

@asynccontextmanager
async def get_db_connection() -> AsyncIterator[asyncpg.Connection]:
    """Get a database connection from the pool."""
    if db_pool is None:
        raise RuntimeError("Database pool not initialized")

    async with db_pool.acquire() as connection:
        yield connection
```

### Redis Configuration

**Install Dependencies**:
```bash
# For library users adding effectful to YOUR application
poetry add redis[hiredis]

# For effectful contributors (inside Docker)
docker compose -f docker/docker-compose.yml exec effectful poetry add redis[hiredis]
```

**Connection Pool Setup**:
```python
# src/infrastructure/cache.py
import redis.asyncio as aioredis

REDIS_URL = "redis://localhost:6379/0"

# Create Redis connection pool
redis_pool: aioredis.Redis | None = None

async def init_redis_pool() -> None:
    """Initialize Redis connection pool."""
    global redis_pool
    redis_pool = await aioredis.from_url(
        REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
        max_connections=10,
    )

async def close_redis_pool() -> None:
    """Close Redis connection pool."""
    global redis_pool
    if redis_pool is not None:
        await redis_pool.close()

def get_redis() -> aioredis.Redis:
    """Get Redis connection from pool."""
    if redis_pool is None:
        raise RuntimeError("Redis pool not initialized")
    return redis_pool
```

---

## Part 2: FastAPI Integration

### Application Lifespan

```python
# src/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket
from effectful import run_ws_program, create_composite_interpreter

from src.infrastructure.database import init_database_pool, close_database_pool
from src.infrastructure.cache import init_redis_pool, close_redis_pool

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan: startup and shutdown."""
    # Startup
    await init_database_pool()
    await init_redis_pool()
    yield
    # Shutdown
    await close_database_pool()
    await close_redis_pool()

app = FastAPI(lifespan=lifespan)
```

### WebSocket Endpoint

```python
from fastapi import WebSocket, WebSocketDisconnect
from effectful.adapters.postgres import PostgresUserRepository, PostgresChatMessageRepository
from effectful.adapters.redis_cache import RedisProfileCache
from effectful.adapters.websocket_connection import FastAPIWebSocketConnection

from src.programs.chat import chat_program

@app.websocket("/ws/chat")
async def websocket_chat_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint for chat application."""
    await websocket.accept()

    try:
        # Create infrastructure connections
        async with get_db_connection() as db_conn:
            # Create repositories
            user_repo = PostgresUserRepository(connection=db_conn)
            message_repo = PostgresChatMessageRepository(connection=db_conn)
            cache = RedisProfileCache(redis=get_redis())

            # Create WebSocket connection wrapper
            ws_conn = FastAPIWebSocketConnection(websocket)

            # Create interpreter
            interpreter = create_composite_interpreter(
                websocket_connection=ws_conn,
                user_repo=user_repo,
                message_repo=message_repo,
                cache=cache,
            )

            # Run program with timeout
            result = await asyncio.wait_for(
                run_ws_program(chat_program(), interpreter),
                timeout=300.0  # 5 minutes max
            )

            # Handle result
            match result:
                case Ok(_):
                    logger.info("Chat program completed successfully")
                case Err(error):
                    logger.error(f"Chat program failed: {error}")

    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except asyncio.TimeoutError:
        logger.error("Chat program timeout")
        await websocket.close(code=1008, reason="Timeout")
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        await websocket.close(code=1011, reason="Internal error")
```

---

## Part 3: Error Monitoring

### Logging Configuration

```python
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
poetry add sentry-sdk
```

**Configuration**:
```python
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

---

## Part 4: Environment Configuration

### Settings Management

```python
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

settings = Settings()
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

---

## Part 5: Docker Deployment

### Dockerfile

```dockerfile
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
docker-compose up -d
```

---

## Part 6: Performance Tuning

### Connection Pool Sizing

**Formula**: `connections = (core_count * 2) + effective_spindle_count`

For web application:
```python
# 4 CPU cores
min_size = 5
max_size = (4 * 2) + 1 = 9
```

### Timeout Configuration

```python
# Program execution timeout
PROGRAM_TIMEOUT = 300.0  # 5 minutes

# Database query timeout
DATABASE_TIMEOUT = 60.0  # 1 minute

# Redis operation timeout
REDIS_TIMEOUT = 5.0  # 5 seconds
```

### Caching Strategy

```python
# Cache TTL by data type
CACHE_TTL_PROFILE = 600     # 10 minutes
CACHE_TTL_SESSION = 3600    # 1 hour
CACHE_TTL_STATIC = 86400    # 24 hours
```

---

## Part 7: Health Checks

### Endpoint Implementation

```python
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

---

## Part 8: Deployment Checklist

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

---

## Best Practices

### ✅ DO

1. **Use Connection Pools**
   ```python
   db_pool = await asyncpg.create_pool(dsn=DATABASE_URL, min_size=5, max_size=20)
   ```

2. **Configure Timeouts**
   ```python
   result = await asyncio.wait_for(run_ws_program(...), timeout=300.0)
   ```

3. **Monitor Errors**
   ```python
   sentry_sdk.capture_exception(Exception(str(error)))
   ```

4. **Validate Health**
   ```python
   @app.get("/health")
   async def health_check() -> JSONResponse: ...
   ```

5. **Use Environment Variables**
   ```python
   settings = Settings()  # Loads from .env
   ```

### ❌ DON'T

1. **Don't Create Connections Per Request**
   ```python
   # ❌ Creates new connection every request
   conn = await asyncpg.connect(DATABASE_URL)
   ```

2. **Don't Skip Error Monitoring**
   ```python
   # ❌ Silent failures
   match result:
       case Err(_): pass
   ```

3. **Don't Use Hardcoded Secrets**
   ```python
   # ❌ Security risk
   DATABASE_URL = "postgresql://user:password@localhost/db"
   ```

---

## Next Steps

- Read [Tutorial 06: Advanced Composition](./06_advanced_composition.md) for complex workflows
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
