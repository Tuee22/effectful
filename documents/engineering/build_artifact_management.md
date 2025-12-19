# Build Artifact Management

**Status**: Authoritative source\
**Supersedes**: none\
**Referenced by**: engineering/README.md

> **Purpose**: Authoritative rules for what counts as a build artifact, where it lives, and why it must never be versioned or copied out of the container.

______________________________________________________________________

## Executive Summary

- **Build artifacts are never versioned**. They are regenerated deterministically from source.
- **All build outputs live under `/opt` inside containers** and **stay there** (not copied back to the host or image layers beyond `/opt`).
- **Lockfiles (`poetry.lock`, `package-lock.json`) are treated as build artifacts in this repo**: they are not tracked in git and are excluded from Docker contexts.

______________________________________________________________________

## Doctrine

### Core Principle

**Only source-of-truth files are versioned. Everything produced by a build step is an artifact and must be ignored.**

### Locations

- **Container-only outputs**: `/opt/**` (backend + frontend build products **including caches**). These remain inside the container; do not copy them into the final image or host, and do not map them back through bind mounts.
- **Lockfiles as artifacts**: `poetry.lock`, `package-lock.json` are regenerated as part of dependency resolution and are not versioned.

### Rationale

1. **Reproducibility**: Deterministic builds from `pyproject.toml`/`package.json` without stale lockfiles.
1. **Security**: Prevent leaking secrets embedded in compiled outputs or npm/yarn caches.
1. **Repo health**: Avoid churn/bloat from compiled assets or lockfile drift.
1. **CI parity**: CI regenerates artifacts exactly as local Docker builds do.

______________________________________________________________________

## What Is Versioned (Sources)

- `pyproject.toml`, `package.json`, source code, schemas, docs.
- **Generated documentation that is part of the SSoT (e.g., `documents/engineering/functional_catalogue.md`) stays in git alongside other docs**; it must carry the auto-generated banner (`<!-- AUTO-GENERATED FILE. DO NOT EDIT BY HAND. -->`) and be regenerated via `check-code`.
- Minimal config needed to run deterministic builds inside containers.

## What Is Not Versioned (Artifacts)

- **Lockfiles**: `poetry.lock`, `package-lock.json` (regenerated during builds).
- **Container build outputs**: Anything under `/opt/**` created during Docker builds.
- **Caches/binaries**: `__pycache__/`, `.mypy_cache/`, `.pytest_cache/`, `.ruff_cache/`, `dist/`, `build/`, `*.egg-info/`.
  - **Placement rule**: All cache-style artifacts (`__pycache__`, `.mypy_cache`, `.pytest_cache`, `.ruff_cache`) must reside under `/opt/**` inside containers so they never appear in bind-mounted source trees.

### Cache placement contract

- **Location**: All runtime/tooling caches live under `/opt/**` with project namespacing (e.g., `/opt/effectful/mypy_cache`, `/opt/effectful/pytest_cache`, `/opt/effectful/ruff_cache`, `/opt/pycache` for Python bytecode).
- **Propagation**: These caches must not be bind-mounted back to the host; they are container-only artifacts.
- **Configuration**: Cache locations are controlled exclusively by environment variables set in `docker/Dockerfile` (SSoT policy).

**Effectful Namespace** (`/opt/effectful/`):
- `MYPY_CACHE_DIR=/opt/effectful/mypy_cache` - MyPy type checker cache
- `PYTEST_CACHE_DIR=/opt/effectful/pytest_cache` - Pytest cache
- `RUFF_CACHE_DIR=/opt/effectful/ruff_cache` - Ruff linter cache
- `XDG_CACHE_HOME=/opt/effectful/cache` - General tool cache

**Shared** (not namespaced):
- `PYTHONPYCACHEPREFIX=/opt/pycache` - Python bytecode cache (shared across containers)

📖 **See**: [docker.md](docker.md#environment-variables) for complete environment variable documentation.

______________________________________________________________________

## Ignore Policy

### .gitignore (host)

- **Exclude**: `poetry.lock`, `package-lock.json`, build/caches (`dist/`, `build/`, `*.egg-info/`, `__pycache__/`, `.mypy_cache/`, `.pytest_cache/`).
- **Comment rules**: Every new pattern must state what/why/how to regenerate (see [Documentation Standards](../documentation_standards.md#gitignore-and-dockerignore-rules)).

### .dockerignore (build context)

- **Exclude**: `poetry.lock`, `package-lock.json`, host caches/build outputs (`dist/`, `build/`, `*.egg-info/`, `__pycache__/`, `.mypy_cache/`, `.pytest_cache/`).
- **Include**: Only source-of-truth inputs required to rebuild artifacts inside the container.

______________________________________________________________________

## Regeneration Workflow

Backend (inside container):

```bash
# snippet
docker compose -f docker/docker-compose.yml exec effectful poetry install
docker compose -f demo/healthhub/docker/docker-compose.yml exec healthhub poetry install
```

Frontend (inside container):

```bash
# snippet
docker compose -f demo/healthhub/docker/docker-compose.yml exec healthhub npm ci
docker compose -f demo/healthhub/docker/docker-compose.yml exec healthhub npm run build
```

Artifacts produced in these steps stay under `/opt/**` in the container; do not copy them to the host or commit them.

______________________________________________________________________

## Verification

- **Check gitignore**:
  ```bash
  # verify gitignore catches common build artifacts
  git check-ignore -v poetry.lock package-lock.json dist/ build/
  ```
- **Check docker context**:
  ```bash
  # ensure docker build context excludes lockfiles
  docker build --progress=plain . | grep -E "poetry.lock|package-lock.json"
  # Expect: excluded from context
  ```
- **No artifacts in git**:
  ```bash
  # detect generated artifacts checked into git
  git status --short | grep -E "poetry.lock|package-lock.json|dist/|build/" && echo "Artifacts present (fix ignore rules)"
  ```

______________________________________________________________________

## Maintenance

- Update this doc when:
  - New artifact types or build locations are introduced.
  - Ignore rules change materially.
  - Build pipelines add new stages affecting `/opt/**` outputs or lockfile handling.

______________________________________________________________________

## Cross-References

- 📖 [Docker & Environment Variables](docker.md) — Environment variable SSoT, cache directory policy, and namespacing
- 📖 [Docker Workflow](docker_workflow.md) — Container-only development contract and daily patterns
- 📖 [Documentation Standards](../documentation_standards.md) — SSoT/link hygiene and ignore file commentary
- 📖 [Code Quality](code_quality.md) — Enforcement pipeline that regenerates artifacts

______________________________________________________________________

**SSoT**: This file supersedes any other guidance on build artifact handling in this repository. All other docs must link here when referring to artifact/versioning rules.
