# effectful_tools Package

This package contains the development and build tools for the Effectful project. It ships with the library and is invoked via Poetry scripts.

## Overview

All tools are designed to be run via Poetry scripts defined in `pyproject.toml` **inside the effectful Docker container**. This ensures:

- Consistent execution environment
- Proper dependency isolation
- Clear entrypoints for CI/CD

## Available Tools

### Code Quality

#### check_code.py

Runs type checking, formatting, and linting in sequence with fail-fast behavior.

**Usage:**

```bash
docker compose -f docker/docker-compose.yml exec effectful poetry run check-code
```

**Steps:**

1. **MyPy --strict**: Zero-tolerance type checking
1. **Black**: Code formatting (auto-formats)
1. **Ruff**: Linting with 100+ rules

**Exit codes:**

- `0`: All checks passed
- Non-zero: At least one check failed (see output for details)

### Testing

#### test_runner.py

Orchestrates test execution across different test categories.

**Usage:**

```bash
# Run all tests
docker compose -f docker/docker-compose.yml exec effectful poetry run test-all

# Run unit tests only (pytest-mock, <1s)
docker compose -f docker/docker-compose.yml exec effectful poetry run test-unit

# Run integration tests only (real infrastructure, 1-2s)
docker compose -f docker/docker-compose.yml exec effectful poetry run test-integration
```

**Test Categories:**

- **Unit**: Fast tests using pytest-mock only, no I/O
- **Integration**: Tests against real PostgreSQL, Redis, MinIO, Pulsar
- **All**: Complete test suite (329+ tests)

## Development Pattern

All tools follow a consistent pattern:

```python
#!/usr/bin/env python3
"""Module docstring explaining the tool's purpose."""

import subprocess
import sys


def main() -> int:
    """Main entrypoint - returns exit code."""
    # Implementation
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

**Key principles:**

1. **Function-based entrypoints**: Each function can be called independently
1. **Explicit return codes**: Functions return `int` (0 for success, non-zero for failure)
1. **Type hints**: All parameters and return types explicitly annotated
1. **Documentation**: Module and function docstrings explain purpose and behavior
1. **Fail-fast behavior**: Early returns on first failure, no silent failures
1. **Emoji logging**: Visual feedback (✅/❌) for quick status recognition

## Adding New Tools

To add a new tool:

1. **Create the script** in `effectful_tools/` following the pattern above
1. **Add docstrings** explaining purpose, usage, and behavior
1. **Add Poetry script** in `pyproject.toml`:
   ```toml
   [tool.poetry.scripts]
   my-tool = "effectful_tools.my_tool:main"
   ```
1. **Update this README** with tool description and usage
1. **Update CLAUDE.md** command reference if user-facing

## References

- Poetry scripts documentation: https://python-poetry.org/docs/pyproject/#scripts
- Effectful development guide: `../CLAUDE.md`
