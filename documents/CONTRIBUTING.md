# Contributing to Effectful

**Status**: Reference only  
**Supersedes**: none  
**Referenced by**: README.md

> **Purpose**: Contributor guide for Effectful, including prerequisites and core development commands.
> **📖 Authoritative Reference**: [Repository README](../README.md)

Welcome to the effectful project! We're excited to have you contribute.

## Prerequisites

All development happens inside Docker containers. See [Docker Workflow](engineering/docker_workflow.md) for complete policy.

**CRITICAL**: Poetry is configured to NOT create virtual environments (`poetry.toml`). Do NOT run `poetry install` locally.

```bash
# Start development environment
docker compose -f docker/docker-compose.yml up -d

# Run tests
docker compose -f docker/docker-compose.yml exec effectful poetry run pytest

# Type check
docker compose -f docker/docker-compose.yml exec effectful poetry run check-code
```

## Quick Links

**Before contributing, read these engineering standards**:

| Standard | Purpose |
|----------|---------|
| [Engineering Standards](engineering/README.md) | Master index of all standards |
| [Architecture](engineering/architecture.md) | 5-layer architecture design |
| [Code Quality](engineering/code_quality.md) | Type safety + purity doctrines and anti-pattern routing |
| [Testing](engineering/testing.md) | Testing standards and 22 anti-patterns |
| [Docker Workflow](engineering/docker_workflow.md) | All development in Docker |

## Contributing Checklist

All contributions must meet the **Universal Success Criteria**:

- ✅ Exit code 0 (all operations complete successfully)
- ✅ **Zero MyPy errors** (mypy --strict mandatory)
- ✅ Zero stderr output
- ✅ No skipped tests
- ✅ Lint + doc link verification passed
- ✅ Documentation updated (links + SSoT alignment)

## How to Contribute

1. Fork the repository and create a branch for your change
2. Ensure Docker services are running (`docker compose -f docker/docker-compose.yml up -d`)
3. Run `docker compose -f docker/docker-compose.yml exec effectful poetry run check-code`
4. Run relevant test suites (`... pytest tests/unit` or `... pytest`)
5. Update documentation and links if you add or move modules
6. Open a PR with a concise description and a list of commands you ran

## Code of Conduct

Be respectful and inclusive. Follow the community guidelines in the project tracker.
