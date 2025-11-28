# Docker Development Doctrine

## Core Principle

**ALL development commands MUST run inside the Docker container. NEVER run commands directly on the host machine.**

This doctrine applies to:
- Type checking (mypy)
- Code formatting (black)
- Testing (pytest)
- Package management (poetry)
- Python execution
- Any development-related command

## Rationale

### Why Docker-Only Development?

1. **Environment Consistency**: Everyone uses the exact same Python version, dependencies, and system libraries
2. **No Local Setup Required**: Contributors don't need to manage Python versions or virtual environments locally
3. **Infrastructure Parity**: Tests run against the same PostgreSQL, Redis, MinIO, and Pulsar versions as production
4. **Reproducible Builds**: Build artifacts are identical regardless of host OS (macOS, Linux, Windows)
5. **Clean Host Machine**: No Poetry, no virtualenvs, no Python version conflicts on your machine

### Why NOT Local Development?

1. **Dependency Hell**: Different Python versions cause subtle bugs
2. **Missing Infrastructure**: Local tests can't connect to PostgreSQL/Redis/MinIO/Pulsar/Prometheus
3. **False Confidence**: Tests pass locally but fail in CI due to environment differences
4. **Onboarding Friction**: New contributors spend hours setting up local environments

## Command Patterns

### Correct Pattern

All commands follow this structure:

```bash
docker compose -f docker/docker-compose.yml exec effectful poetry run <command>
```

### Examples

| Task | Correct Command |
|------|-----------------|
| Type check | `docker compose -f docker/docker-compose.yml exec effectful poetry run check-code` |
| All tests | `docker compose -f docker/docker-compose.yml exec effectful poetry run pytest` |
| Unit tests | `docker compose -f docker/docker-compose.yml exec effectful poetry run pytest tests/unit` |
| Integration tests | `docker compose -f docker/docker-compose.yml exec effectful poetry run pytest tests/integration` |
| Python shell | `docker compose -f docker/docker-compose.yml exec effectful poetry run python` |
| Add dependency | `docker compose -f docker/docker-compose.yml exec effectful poetry add <package>` |
| Add dev dependency | `docker compose -f docker/docker-compose.yml exec effectful poetry add --group dev <package>` |

### Shell Alias (Optional)

For convenience, add to your shell profile:

```bash
alias eff='docker compose -f docker/docker-compose.yml exec effectful poetry run'
```

Then use: `eff pytest`, `eff check-code`, etc.

## Forbidden Practices

### NEVER Do This

```bash
# FORBIDDEN - Running pytest locally
pytest tests/

# FORBIDDEN - Running poetry locally
poetry run pytest
poetry add some-package
poetry install

# FORBIDDEN - Running mypy locally
mypy effectful/

# FORBIDDEN - Installing packages locally
pip install effectful
pip install -r requirements.txt

# FORBIDDEN - Running Python scripts locally
python examples/01_hello_world.py
```

### Why These Are Forbidden

1. **Local pytest**: Won't have access to PostgreSQL, Redis, MinIO, Pulsar
2. **Local poetry**: Creates local virtualenvs, causes version mismatches
3. **Local mypy**: May use different Python version, give false positives/negatives
4. **Local pip**: Pollutes global Python, causes conflicts

## Development Workflow

### Initial Setup

```bash
# Start all services (effectful + infrastructure)
docker compose -f docker/docker-compose.yml up -d

# Verify services are running
docker compose -f docker/docker-compose.yml ps
```

### Daily Development

```bash
# 1. Make code changes in your editor (host machine)
# 2. Run type checker
docker compose -f docker/docker-compose.yml exec effectful poetry run check-code

# 3. Run tests
docker compose -f docker/docker-compose.yml exec effectful poetry run pytest

# 4. Iterate
```

### Viewing Logs

```bash
# All services
docker compose -f docker/docker-compose.yml logs -f

# Just the effectful container
docker compose -f docker/docker-compose.yml logs -f effectful
```

### Stopping Services

```bash
# Stop but keep data
docker compose -f docker/docker-compose.yml stop

# Stop and remove containers (keeps volumes)
docker compose -f docker/docker-compose.yml down

# Stop and remove everything including data
docker compose -f docker/docker-compose.yml down -v
```

## Container Services

The effectful Docker Compose stack includes multiple services that work together to provide a complete development environment.

### Service Overview

| Service | Purpose | Ports | Data Persistence |
|---------|---------|-------|------------------|
| `effectful` | Main Python container | - | Code bind-mounted from host |
| `postgres` | PostgreSQL 15+ | 5432 | Named volume `pgdata` |
| `redis` | Redis 7+ cache | 6379 | Named volume `redisdata` |
| `minio` | S3-compatible storage | 9000 (API), 9001 (Console) | Named volume `miniodata` |
| `pulsar` | Apache Pulsar messaging | 6650 (broker), 8080 (HTTP) | Named volume `pulsardata` |
| `prometheus` | Metrics collection | 9090 | Named volume `prometheusdata` |
| `grafana` | Metrics visualization | 3000 | Named volume `grafanadata` |

### Effectful Container

**Purpose**: Runs the effectful Python library code with all development tools.

**Key Features**:
- Python 3.12 with Poetry for dependency management
- Two entrypoints: main (library development) and mock-client (integration testing)
- Bind-mounted source code (`./effectful:/app/effectful`, `./tests:/app/tests`)
- Connects to all infrastructure services

**Environment Variables**:
```bash
POSTGRES_HOST=postgres
REDIS_HOST=redis
MINIO_ENDPOINT=minio:9000
PULSAR_URL=pulsar://pulsar:6650
PROMETHEUS_URL=http://prometheus:9090
```

### PostgreSQL Container

**Purpose**: Database backend for repository pattern testing.

**Version**: PostgreSQL 15+

**Data Persistence**: Named volume ensures data survives container restarts.

**Why Named Volumes?**: Bind mounts cause permission issues on Docker Desktop for Mac. Named volumes have correct ownership automatically.

### Redis Container

**Purpose**: Caching and session storage for cache effect testing.

**Version**: Redis 7+

**Data Persistence**: Named volume `redisdata`.

### MinIO Container

**Purpose**: S3-compatible object storage for storage effect testing.

**Version**: MinIO latest

**Access**:
- API: http://localhost:9000
- Console: http://localhost:9001
- Credentials: `minioadmin` / `minioadmin`

**Data Persistence**: Named volume `miniodata`.

### Apache Pulsar Container

**Purpose**: Pub/sub messaging for messaging effect testing.

**Version**: Pulsar latest

**Access**:
- Broker: pulsar://localhost:6650
- HTTP: http://localhost:8080

**Data Persistence**: Named volume `pulsardata`.

### Prometheus Container

**Purpose**: Metrics collection and time-series database for observability.

**Version**: Prometheus latest

**Configuration**:
- Config file: `docker/prometheus/prometheus.yml`
- Alert rules: `docker/prometheus/alerts.yml`
- Scrape interval: 15 seconds (default)

**Access**: http://localhost:9090

**Key Features**:
- Scrapes `/metrics` endpoint from effectful applications
- Evaluates alert rules defined in `alerts.yml`
- Forwards alerts to Alertmanager (if configured)
- Time-series data stored in named volume

**Data Persistence**: Named volume `prometheusdata`.

**See Also**: `documents/core/observability_doctrine.md` for metrics philosophy.

### Grafana Container

**Purpose**: Metrics visualization, dashboards, and alerting UI.

**Version**: Grafana latest

**Access**: http://localhost:3000

**Default Credentials**: `admin` / `admin` (change on first login)

**Key Features**:
- Pre-configured Prometheus datasource
- Dashboard provisioning from `docker/grafana/dashboards/`
- Alert notification channels (Slack, PagerDuty, Email)
- Query builder for PromQL expressions

**Data Persistence**: Named volume `grafanadata`.

**See Also**: `documents/tutorials/15_grafana_dashboards.md` for dashboard creation.

## IDE Integration

### VS Code

The devcontainer support allows VS Code to run inside the Docker container:

1. Install "Dev Containers" extension
2. Open command palette: "Dev Containers: Reopen in Container"
3. VS Code now runs all commands inside Docker automatically

### PyCharm

Configure a remote Python interpreter pointing to the Docker container:

1. Settings > Project > Python Interpreter
2. Add Interpreter > Docker Compose
3. Select `docker/docker-compose.yml` and service `effectful`

### Other Editors

Edit files on host, run commands via Docker exec as shown above.

## Troubleshooting

### "Container not running"

```bash
# Start the containers
docker compose -f docker/docker-compose.yml up -d
```

### "Permission denied"

```bash
# Reset volumes (loses data)
docker compose -f docker/docker-compose.yml down -v
docker compose -f docker/docker-compose.yml up -d
```

### "Poetry install failed"

```bash
# Rebuild the container
docker compose -f docker/docker-compose.yml build --no-cache effectful
docker compose -f docker/docker-compose.yml up -d
```

### "Tests can't connect to postgres/redis"

Ensure all infrastructure services are running:

```bash
docker compose -f docker/docker-compose.yml ps
# Should show: effectful, postgres, redis, minio, pulsar, prometheus, grafana all "Up"
```

## References

- **Command Reference**: See `CLAUDE.md` for complete command table
- **Testing**: See `documents/core/testing_doctrine.md` for test organization
- **Observability**: See `documents/core/observability_doctrine.md` for Prometheus/Grafana integration
- **Contributing**: See `CONTRIBUTING.md` for contribution workflow

---

**Remember**: If you're typing `poetry run` or `pytest` without the Docker prefix, you're doing it wrong.
