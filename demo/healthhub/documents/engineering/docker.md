# Docker & Environment Variables (HealthHub Overlay)

**Status**: Demo overlay (delta-only)
**Base**: [Effectful docker.md](../../../../documents/engineering/docker.md)
**Referenced by**: [docker_workflow.md](../../../../documents/engineering/docker_workflow.md), [build_artifact_management.md](build_artifact_management.md), [README.md](README.md), [CLAUDE.md](../../CLAUDE.md)

> **Pattern**: This document contains ONLY HealthHub-specific deltas. For shared patterns, see base effectful documentation.

---

## Environment Variables (HealthHub-Specific)

**Base environment variables**: See [effectful docker.md](../../../../documents/engineering/docker.md#environment-variables) for complete Python runtime, pip, Poetry, and tool-specific cache directories documentation.

### HealthHub-Specific Additions

#### Application Paths

**PYTHONPATH=/app/effectful-root:/app/effectful-root/demo/healthhub:/app/effectful-root/demo/healthhub/backend**

- **Purpose**: Enables importing both effectful parent library AND healthhub application
- **Rationale**: HealthHub depends on effectful as local path dependency (`../../`)
- **Components**:
  - `/app/effectful-root` - Enables `from effectful import ...`
  - `/app/effectful-root/demo/healthhub` - Enables `from backend import ...`
  - `/app/effectful-root/demo/healthhub/backend` - Direct backend module access
- **Default without it**: ImportError for effectful or backend modules

### Tool-Specific Cache Directories

**HealthHub namespace** (`/opt/healthhub/`):

- `MYPY_CACHE_DIR=/opt/healthhub/mypy_cache` - MyPy type checker cache
- `PYTEST_CACHE_DIR=/opt/healthhub/pytest_cache` - Pytest cache (set in pyproject.toml)
- `RUFF_CACHE_DIR=/opt/healthhub/ruff_cache` - Ruff linter cache
- `XDG_CACHE_HOME=/opt/healthhub/cache` - General tool cache
- `PYTHONPYCACHEPREFIX=/opt/healthhub/pycache` - Python bytecode cache

**Why separate namespace from effectful?** Prevents cache conflicts when both containers run simultaneously during integration validation (Phase 6).

**See also**: [Base docker.md - Environment Variables](../../../../documents/engineering/docker.md#environment-variables) for complete cache directory documentation and enforcement pattern.

---

## Build Directory Structure (HealthHub-Specific)

**Base structure**: See [effectful docker.md](../../../../documents/engineering/docker.md#build-directory-structure) for shared patterns.

### HealthHub Namespace

**HealthHub Namespace** (`/opt/healthhub/`):

- `/opt/healthhub/cache` - General cache (XDG_CACHE_HOME)
- `/opt/healthhub/mypy_cache` - MyPy type checker cache
- `/opt/healthhub/pytest_cache` - Pytest cache
- `/opt/healthhub/ruff_cache` - Ruff linter cache
- `/opt/healthhub/pycache` - Python bytecode cache (HealthHub-specific, NOT shared)
- `/opt/healthhub/frontend-build` - React frontend build output (vite build)
- `/opt/healthhub/backend-build` - Reserved for backend artifacts

**Why `/opt/healthhub/` namespace?**

- Prevents conflicts when both effectful and healthhub containers run simultaneously
- Clear ownership of cache directories
- Follows ShipNorth production-hardened pattern

**Why separate pycache from effectful?**

- HealthHub imports both effectful AND backend modules
- Different PYTHONPATH means different bytecode cache requirements
- Prevents cache invalidation issues during integration validation

---

## Testing Policy Enforcement (HealthHub-Specific)

**Base pattern**: See [effectful docker.md](../../../../documents/engineering/docker.md#testing-policy-enforcement) for pytest wrapper pattern and rationale.

### HealthHub Pytest Wrapper

HealthHub uses an inline pytest wrapper (not a separate file) configured in Dockerfile:

```dockerfile
RUN if [ -f /usr/local/bin/pytest ]; then mv /usr/local/bin/pytest /usr/local/bin/pytest.real; fi && \
    echo '#!/bin/sh\necho "❌ ERROR: Direct pytest forbidden"\necho "✅ USE: poetry run test-<category> (test-all, test-backend, test-integration, test-e2e)"\nexit 1' > /usr/local/bin/pytest && \
    chmod +x /usr/local/bin/pytest
```

**Why inline instead of separate file?**

- HealthHub has 4 test categories (test-all, test-backend, test-integration, test-e2e) vs effectful's 3
- Simpler to maintain enforcement message in Dockerfile where test categories are visible
- Follows effectful pattern but adapted for HealthHub's test organization

**Required commands**:

```bash
# ✅ CORRECT - Use Poetry test commands
docker compose -f docker/docker-compose.yml exec healthhub poetry run test-all
docker compose -f docker/docker-compose.yml exec healthhub poetry run test-backend
docker compose -f docker/docker-compose.yml exec healthhub poetry run test-integration
docker compose -f docker/docker-compose.yml exec healthhub poetry run test-e2e
```

**Emergency override** (debugging enforcement only):

```bash
/usr/local/bin/pytest.real tests/
```

**See**: [testing.md](../../../../documents/engineering/testing.md#pytest-enforcement) for complete enforcement rationale.

---

## Frontend Build Management

**Critical difference from effectful**: HealthHub includes a React frontend that must be built during Docker image build.

### Build Process

**Build location**: `/opt/healthhub/frontend-build/`

**Build steps** (in Dockerfile):

1. Copy frontend source (`package.json`, `src/`, `index.html`, vite config, TypeScript config)
2. Run `npm install --quiet` (regenerates package-lock.json in container)
3. Run `BUILD_PATH=build npm run build` (vite build output to `build/`)
4. Verify `build/index.html` exists

**Why in Dockerfile, not at runtime?**

- Frontend is static assets (HTML, JS, CSS) - doesn't need hot reload
- Docker image contains built frontend ready to serve
- Reduces container startup time (no build step at runtime)

### Frontend Rebuild Workflow

**Backend changes**: Volume mounts enable hot reload (no rebuild needed)

**Frontend changes**: Rebuild Docker image

```bash
docker compose -f docker/docker-compose.yml build healthhub
docker compose -f docker/docker-compose.yml up -d healthhub
```

**Alternative** (local development only): Run `npm run dev` locally

```bash
cd demo/healthhub/frontend
npm install
npm run dev
```

Frontend available at http://localhost:5173 with hot reload.

**See also**: [frontend_architecture.md](frontend_architecture.md) for complete frontend architecture and routing patterns.

---

## SSoT Link Map

| Topic                          | SSoT                                                                                                   |
| ------------------------------ | ------------------------------------------------------------------------------------------------------ |
| Environment variables (shared) | [Effectful docker.md](../../../../documents/engineering/docker.md#environment-variables)              |
| Environment variable policy    | [Effectful docker.md](../../../../documents/engineering/docker.md#environment-variable-policy)        |
| Build directory structure      | [Effectful docker.md](../../../../documents/engineering/docker.md#build-directory-structure)          |
| Testing policy enforcement     | [Effectful docker.md](../../../../documents/engineering/docker.md#testing-policy-enforcement)         |
| HealthHub-specific caches      | This document                                                                                          |
| Frontend build management      | This document                                                                                          |
| Pytest wrapper (HealthHub)     | This document                                                                                          |
| Cache placement contract       | [build_artifact_management.md](build_artifact_management.md#cache-placement-contract)                 |
| Docker workflow                | [docker_workflow.md](../../../../documents/engineering/docker_workflow.md)                            |
| Test execution                 | [testing.md](../../../../documents/engineering/testing.md)                                            |
| Command reference              | [command_reference.md](../../../../documents/engineering/command_reference.md)                        |
| Development workflow           | [development_workflow.md](../../../../documents/engineering/development_workflow.md)                  |
| Build artifact management      | [build_artifact_management.md](../../../../documents/engineering/build_artifact_management.md)        |
| Architecture                   | [architecture.md](../../../../documents/engineering/architecture.md)                                  |
| Code quality                   | [code_quality.md](../../../../documents/engineering/code_quality.md)                                  |
| HealthHub overview             | [CLAUDE.md](../../CLAUDE.md)                                                                          |
| Engineering standards index    | [Engineering README](../../../../documents/engineering/README.md)                                     |
| Frontend architecture          | [frontend_architecture.md](frontend_architecture.md)                                                  |
