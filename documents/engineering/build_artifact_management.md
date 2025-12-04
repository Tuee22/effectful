# Build Artifact Management

**Status**: SSoT  
**Last Updated**: 2025-12-03  

> **Purpose**: Authoritative rules for what counts as a build artifact, where it lives, and why it must never be versioned or copied out of the container.  
> **📖 See**: [Documentation Standards](../documentation_standards.md) for SSoT/linking rules.

---

## Executive Summary

- **Build artifacts are never versioned**. They are regenerated deterministically from source.
- **All build outputs live under `/opt` inside containers** and **stay there** (not copied back to the host or image layers beyond `/opt`).
- **Lockfiles (`poetry.lock`, `package-lock.json`) are treated as build artifacts in this repo**: they are not tracked in git and are excluded from Docker contexts.

---

## Doctrine

### Core Principle
**Only source-of-truth files are versioned. Everything produced by a build step is an artifact and must be ignored.**

### Locations
- **Container-only outputs**: `/opt/**` (backend + frontend build products). These remain inside the container; do not copy them into the final image or host.
- **Lockfiles as artifacts**: `poetry.lock`, `package-lock.json` are regenerated as part of dependency resolution and are not versioned.

### Rationale
1. **Reproducibility**: Deterministic builds from `pyproject.toml`/`package.json` without stale lockfiles.
2. **Security**: Prevent leaking secrets embedded in compiled outputs or npm/yarn caches.
3. **Repo health**: Avoid churn/bloat from compiled assets or lockfile drift.
4. **CI parity**: CI regenerates artifacts exactly as local Docker builds do.

---

## What Is Versioned (Sources)
- `pyproject.toml`, `package.json`, source code, schemas, docs.
- Minimal config needed to run deterministic builds inside containers.

## What Is Not Versioned (Artifacts)
- **Lockfiles**: `poetry.lock`, `package-lock.json` (regenerated during builds).
- **Container build outputs**: Anything under `/opt/**` created during Docker builds.
- **Caches/binaries**: `__pycache__/`, `.mypy_cache/`, `.pytest_cache/`, `dist/`, `build/`, `*.egg-info/`.

---

## Ignore Policy

### .gitignore (host)
- **Exclude**: `poetry.lock`, `package-lock.json`, build/caches (`dist/`, `build/`, `*.egg-info/`, `__pycache__/`, `.mypy_cache/`, `.pytest_cache/`).
- **Comment rules**: Every new pattern must state what/why/how to regenerate (see [Documentation Standards](../documentation_standards.md#gitignore-and-dockerignore-rules)).

### .dockerignore (build context)
- **Exclude**: `poetry.lock`, `package-lock.json`, host caches/build outputs (`dist/`, `build/`, `*.egg-info/`, `__pycache__/`, `.mypy_cache/`, `.pytest_cache/`).
- **Include**: Only source-of-truth inputs required to rebuild artifacts inside the container.

---

## Regeneration Workflow

Backend (inside container):
```bash
docker compose -f docker/docker-compose.yml exec effectful poetry install
docker compose -f docker/docker-compose.yml exec healthhub poetry install
```

Frontend (inside container):
```bash
docker compose -f demo/healthhub/docker/docker-compose.yml exec healthhub npm ci
docker compose -f demo/healthhub/docker/docker-compose.yml exec healthhub npm run build
```

Artifacts produced in these steps stay under `/opt/**` in the container; do not copy them to the host or commit them.

---

## Verification

- **Check gitignore**:
  ```bash
  git check-ignore -v poetry.lock package-lock.json dist/ build/
  ```
- **Check docker context**:
  ```bash
  docker build --progress=plain . | grep -E "poetry.lock|package-lock.json"
  # Expect: excluded from context
  ```
- **No artifacts in git**:
  ```bash
  git status --short | grep -E "poetry.lock|package-lock.json|dist/|build/" && echo "Artifacts present (fix ignore rules)"
  ```

---

## Cross-References

- Upstream doctrine: [Documentation Standards](../documentation_standards.md) — SSoT/link hygiene and ignore file commentary.
- Build workflows: [Docker Workflow](docker_workflow.md) — container-only development contract.
- Frontend build: [demo/healthhub/documents/engineering/frontend_architecture.md](/demo/healthhub/documents/engineering/frontend_architecture.md) — build stage copies and `/opt` output rules.
- Code quality gates: [Code Quality](code_quality.md) — enforcement pipeline that regenerates artifacts.

---

## Maintenance

- Update this doc when:
  - New artifact types or build locations are introduced.
  - Ignore rules change materially.
  - Build pipelines add new stages affecting `/opt/**` outputs or lockfile handling.

---

**SSoT**: This file supersedes any other guidance on build artifact handling in this repository. All other docs must link here when referring to artifact/versioning rules.
