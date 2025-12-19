# Docker & Environment Variables

**Status**: Authoritative source
**Supersedes**: None
**Referenced by**: [docker_workflow.md](docker_workflow.md), [build_artifact_management.md](build_artifact_management.md), [testing.md](testing.md), [command_reference.md](command_reference.md)

> **Purpose**: Prescribe Docker container standards, environment variable policy, and build artifact management for Effectful library development.

## TL;DR

- All development happens inside Docker containers (no local Python/Poetry installation)
- Environment variables are the Single Source of Truth - defined exclusively in `docker/Dockerfile`
- Build artifacts live under `/opt/effectful/` namespace (cache directories)
- Python bytecode cache in `/opt/pycache` (shared across projects)
- Direct pytest execution blocked - use `poetry run test-*` commands only
- All containers run as root for simplicity and cross-platform compatibility (macOS/Linux/Windows)
- See [docker_workflow.md](docker_workflow.md) for daily development patterns and command reference

## Environment Variables

All environment variables are defined in `docker/Dockerfile`. This section documents each variable's purpose and rationale.

### Python Runtime

#### PYTHONUNBUFFERED=1

Forces Python to run in unbuffered mode for immediate output visibility.

- **Purpose**: Print statements and logs appear immediately instead of being buffered
- **Rationale**: Critical for Docker containers so logs appear in real-time via `docker logs`
- **Default without it**: Python buffers output, causing delays in log visibility

### Python Package Management

#### PIP_NO_CACHE_DIR=1

Disables pip's download cache to reduce Docker image size.

- **Purpose**: Prevents pip from storing cached packages
- **Rationale**: Docker image optimization - caches aren't needed across builds
- **Default without it**: Pip caches downloads in `~/.cache/pip`, increasing image size

#### PIP_DISABLE_PIP_VERSION_CHECK=1

Stops pip from checking for newer versions on every command.

- **Purpose**: Speeds up pip operations slightly
- **Rationale**: Version checking is unnecessary in controlled container environment
- **Default without it**: Pip checks PyPI for updates on every invocation, adding latency

#### PIP_BREAK_SYSTEM_PACKAGES=1

Allows pip to install packages system-wide outside virtual environments.

- **Purpose**: Permits pip to modify system Python installation
- **Rationale**: In containers, we control the entire Python environment - no isolation needed
- **Default without it**: Python 3.11+ blocks system-wide pip installs to prevent conflicts

### Poetry Configuration

#### POETRY_NO_INTERACTION=1

Runs Poetry in non-interactive mode, never prompting for user input.

- **Purpose**: Ensures Poetry never waits for keyboard input
- **Rationale**: Essential for automated environments (CI/CD, Docker builds)
- **Default without it**: Poetry may prompt for confirmation, hanging builds

#### POETRY_HOME=/usr/local

Sets where Poetry itself is installed.

- **Purpose**: Installs Poetry in standard system location
- **Rationale**: Makes Poetry accessible to all users, follows Unix conventions
- **Default without it**: Poetry installs to user home directory (`~/.local`)

### Python Path Configuration

#### PATH="/usr/local/bin:${PATH}"

Prepends `/usr/local/bin` to system PATH.

- **Purpose**: Ensures Poetry and other tools in `/usr/local/bin` take precedence
- **Rationale**: Standard Unix convention for user-installed binaries
- **Default without it**: System binaries in `/usr/bin` would take precedence

#### PYTHONPATH="/app"

Tells Python where to find importable modules.

- **Purpose**: Allows `from effectful import ...` style imports from `/app` directory
- **Rationale**: Maps to application root for clean imports
- **Default without it**: Python can't find effectful modules without relative imports

#### PYTHONPYCACHEPREFIX="/opt/pycache"

Centralizes Python bytecode (`.pyc`) files in a single directory outside the source tree.

- **Purpose**: Improves Python import performance by enabling bytecode compilation and caching
- **Rationale**: Keeps source directories clean, enables performance optimization
- **Location**: `/opt/pycache` contains all compiled Python modules (shared across containers)
- **Default without it**: `.pyc` files scattered in `__pycache__/` throughout source tree

### XDG Standards

#### XDG_CACHE_HOME="/opt/effectful/cache"

Follows the XDG Base Directory specification for tool cache storage.

- **Purpose**: Centralizes cache files for development and testing tools
- **Rationale**: Explicit control over cache location, namespaced to `/opt/effectful/`
- **Tools**: mypy, pytest, ruff, and other XDG-compliant applications
- **Location**: `/opt/effectful/cache` for effectful-specific tool caches
- **Default without it**: Tools default to `~/.cache/`, less predictable

### Tool-Specific Cache Directories

#### MYPY_CACHE_DIR=/opt/effectful/mypy_cache

Dedicated cache directory for MyPy type checker.

- **Purpose**: Speeds up incremental type checking by caching previous runs
- **Rationale**: Namespaced to `/opt/effectful/` for isolation from other projects
- **Default without it**: MyPy uses `.mypy_cache/` in current directory

#### RUFF_CACHE_DIR=/opt/effectful/ruff_cache

Dedicated cache directory for Ruff linter.

- **Purpose**: Speeds up incremental linting by caching previous runs
- **Rationale**: Namespaced to `/opt/effectful/` for isolation
- **Default without it**: Ruff uses default cache location (less predictable)

#### PYTEST_CACHE_DIR=/opt/effectful/pytest_cache

Dedicated cache directory for pytest.

- **Purpose**: Stores pytest cache data (test failures, profiling info)
- **Rationale**: Namespaced to `/opt/effectful/` for isolation
- **Default without it**: pytest uses `.pytest_cache/` in current directory

### Build Configuration

#### DOCKER_CONTAINER=1

Custom flag indicating code is running in Docker.

- **Purpose**: Application code and tools can check this if needed
- **Rationale**: Allows conditional behavior for container vs local development
- **Default without it**: No built-in way to detect Docker environment

## Environment Variable Policy

**Critical Rule**: All environment variables are set exclusively in `docker/Dockerfile`.

### Prohibited Practices

❌ **NEVER** set or override environment variables in:

- Python scripts (`effectful_tools/*.py`)
- Shell scripts
- Poetry scripts in `pyproject.toml`
- Test configuration files
- CI/CD pipeline files
- `docker-compose.yaml` (except for secrets/host-specific values)

### Rationale

1. **Single Source of Truth**: Dockerfile is the canonical definition of the container environment
1. **Predictability**: Same environment in development, testing, and CI
1. **Simplicity**: No conditional logic based on environment type
1. **Debuggability**: Environment is defined in one place, easy to audit
1. **Immutability**: Container behavior doesn't change based on how it's invoked

### Allowed Exception

The ONLY exception is runtime secrets that cannot be baked into images:

- Database passwords (PostgreSQL, Redis)
- API keys for external services
- Service credentials (MinIO, Pulsar)

These may be set via `docker-compose.yaml` or runtime configuration, but ONLY for security-sensitive values.

### What This Means

- Build tools must NOT set environment variables
- Test runners must NOT modify `PYTHONPATH`, cache directories, or Python configuration
- All builds use identical configuration regardless of context (dev, CI, production)
- Build tools must NOT hardcode paths like `/opt/effectful/*` - use environment variables instead
- All build artifact paths must be read via `os.environ[]` (no fallbacks)

### Enforcement

Code review must reject any PRs that set environment variables outside Dockerfile (except allowed exceptions above).

Use fail-fast pattern in Python code:

```python
# ✅ CORRECT - Use os.environ[] without fallbacks
cache_dir = Path(os.environ["MYPY_CACHE_DIR"])

# ❌ WRONG - Fallback defeats enforcement
cache_dir = Path(os.getenv("MYPY_CACHE_DIR", "/default"))
```

If different behavior is needed for different contexts, use:

1. **Feature flags**: Application-level configuration
1. **Build arguments**: Docker ARG (compile-time only, not runtime)
1. **Configuration files**: Explicit config files read by application

Do NOT use environment variables for context-dependent behavior.

## Build Directory Structure

All build artifacts live under `/opt/` hierarchy with project namespacing:

**Effectful Namespace** (`/opt/effectful/`):

- `/opt/effectful/cache` - General cache (XDG_CACHE_HOME)
- `/opt/effectful/mypy_cache` - MyPy type checker cache
- `/opt/effectful/pytest_cache` - Pytest cache
- `/opt/effectful/ruff_cache` - Ruff linter cache

**Shared** (not namespaced):

- `/opt/pycache` - Python bytecode cache (PYTHONPYCACHEPREFIX)
  - Shared across all Python containers for performance
  - Lives outside project namespace to enable cross-project sharing

**Rationale**: Namespacing prevents conflicts when multiple containers run simultaneously. Effectful uses `/opt/effectful/` while demo applications (like HealthHub) use their own namespaces (e.g., `/opt/healthhub/`).

## Testing Policy Enforcement

### Pytest Wrapper

Direct pytest execution is blocked in containers. This enforces:

1. Test output redirection pattern (required for Claude Code compatibility)
1. Use of Poetry test commands (standardization)
1. Consistent test execution across all environments

**Blocked**:

```bash
# ❌ BLOCKED - These commands are forbidden
pytest tests/
python -m pytest
```

**Required**:

```bash
# ✅ REQUIRED - Use these Poetry commands
poetry run test-all
poetry run test-unit
poetry run test-integration
```

**Rationale**:

- **Output Management**: Ensures `/tmp/test-output.txt` pattern is followed (Bash tool truncates at 30,000 chars)
- **Command Consistency**: Everyone uses same commands regardless of environment
- **Claude Code Safety**: Prevents common anti-patterns that violate engineering standards

**Override** (Emergency Only):

```bash
# Emergency override to bypass pytest wrapper
/usr/local/bin/pytest.real tests/
```

This should only be used for debugging the enforcement mechanism itself.

## Infrastructure Services

Effectful development requires real infrastructure for integration testing:

| Service    | Image                      | Port | Purpose                          |
| ---------- | -------------------------- | ---- | -------------------------------- |
| effectful  | Ubuntu 22.04 + Python 3.12 | N/A  | Library development              |
| postgres   | postgres:15-alpine         | 5432 | PostgreSQL integration tests     |
| redis      | redis:7-alpine             | 6379 | Redis integration tests          |
| pulsar     | apachepulsar/pulsar:3.0.0  | 6650 | Pulsar messaging tests           |
| minio      | minio/minio:latest         | 9000 | S3-compatible storage tests      |
| prometheus | prom/prometheus:latest     | 9090 | Metrics collection (optional)    |
| grafana    | grafana/grafana:latest     | 3000 | Metrics visualization (optional) |

**Named Volumes** (required for macOS):

- PostgreSQL: `effectful_pgdata:/var/lib/postgresql/data`
- Redis: `effectful_redisdata:/data`
- Remove with: `docker compose -f docker/docker-compose.yml down -v`

**Note**: No service ports are published to host by default. Services communicate via Docker internal networking.

## Success Criteria

- [ ] No environment variables set outside Dockerfile (except secrets in docker-compose.yaml)
- [ ] `docker compose ps` shows no port conflicts
- [ ] All cache directories created under `/opt/effectful/`
- [ ] Python bytecode cache in `/opt/pycache`
- [ ] Pytest wrapper blocks direct pytest execution
- [ ] `poetry run test-all` passes
- [ ] `poetry run check-code` passes

## Security Hardening

- **Non-root users**: Containers run as root for development simplicity (no production deployment)
- **Secrets management**: Never commit credentials to Dockerfile - use docker-compose.yaml
- **Named volumes**: Prefer named volumes over bind mounts for data persistence
- **Minimal base images**: Ubuntu 22.04 LTS provides security updates and stability

## Cross-References

- 📖 [Docker Workflow](docker_workflow.md) — Daily development patterns and container management
- 📖 [Build Artifact Management](build_artifact_management.md) — Build output, cache policies, and .gitignore patterns
- 📖 [Testing](testing.md) — Test execution, output management, and pytest wrapper enforcement
- 📖 [Command Reference](command_reference.md) — Complete command table for Docker-based development
