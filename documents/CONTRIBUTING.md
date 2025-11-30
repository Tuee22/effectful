# Contributing to Effectful

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
| [Type Safety](engineering/type_safety.md) | Eight type safety doctrines |
| [Purity](engineering/purity.md) | Six purity doctrines |
| [Testing](engineering/testing.md) | Testing standards and 22 anti-patterns |
| [Docker Workflow](engineering/docker_workflow.md) | All development in Docker |

## Contributing Checklist

All contributions must meet the **Universal Success Criteria**:

- ✅ Exit code 0 (all operations complete successfully)
- ✅ **Zero MyPy errors** (mypy --strict mandatory)
- ✅ Zero stderr output
- ✅ Zero console warnings/errors
- ✅ **Zero skipped tests** (pytest.skip() forbidden)
- ✅ 100% test pass rate
- ✅ **Zero `Any`, `cast()`, or `# type: ignore`** (escape hatches forbidden)
- ✅ **Minimum 45% code coverage** (adapters excluded)
- ✅ **Integration tests cover all features** (conceptual coverage)

**Detailed checklist**:

- [ ] Code quality: `poetry run check-code` exits 0
- [ ] Tests for all features (unit + integration)
- [ ] No forbidden constructs (Any/cast/type:ignore)
- [ ] No anti-patterns (see [Forbidden Patterns](engineering/forbidden_patterns.md))
- [ ] All dataclasses frozen (`frozen=True`)
- [ ] ADTs used instead of Optional for domain logic
- [ ] Result type used for all fallible operations
- [ ] Exhaustive pattern matching (all cases handled)
- [ ] Type narrowing for union types
- [ ] Generic type parameters specified
- [ ] Integration tests use real infrastructure
- [ ] Unit tests use pytest-mock only
- [ ] Changes left uncommitted (see Git Workflow below)

See [Code Quality](engineering/code_quality.md) for complete standards.

## Development Workflow

1. **Start Docker services**:
   ```bash
   docker compose -f docker/docker-compose.yml up -d
   ```

2. **Make code changes** following [Engineering Standards](engineering/README.md)

3. **Run code quality checks**:
   ```bash
   docker compose -f docker/docker-compose.yml exec effectful poetry run check-code
   ```

4. **Run tests**:
   ```bash
   docker compose -f docker/docker-compose.yml exec effectful poetry run test-all
   ```

5. **Leave changes uncommitted** (see Git Workflow below)

See [Development Workflow](engineering/development_workflow.md) for detailed procedures.

## Git Workflow

**Critical Rule**: Do NOT commit changes yourself. Leave all changes as uncommitted working directory changes for human review.

**Rationale**: All changes must be human-reviewed before entering version control. This ensures code quality, prevents automated mistakes, and maintains clear authorship.

## Adding New Features

### Adding New Effects

See [Development Workflow](engineering/development_workflow.md) for the 9-step procedure:

1. Define immutable effect dataclass
2. Add to AllEffects union
3. Update EffectResult union
4. Create specialized interpreter
5. Register interpreter
6. Create real adapter
7. Write unit tests
8. Write integration tests
9. Update documentation

### Adding New Domain Models

See [Development Workflow](engineering/development_workflow.md) for the 5-step procedure:

1. Create ADT types (frozen dataclasses)
2. Update EffectResult
3. Write exhaustive pattern matching examples
4. Add tests
5. Update API documentation

## Testing Requirements

**Test Pyramid**:
- **Unit tests** (Many): pytest-mock only, no I/O, fast (<1s)
- **Integration tests** (Some): Real PostgreSQL/Redis/MinIO/Pulsar
- **E2E tests** (Few): Full workflows with real infrastructure

**Forbidden test anti-patterns**:
- Tests that pass when features are broken
- Using pytest.skip() (NEVER allowed)
- Testing with real infrastructure in unit tests
- Not testing error paths
- Incomplete assertions

See [Testing](engineering/testing.md) for complete testing doctrine with 22 anti-patterns.

## Documentation

All new features require documentation updates:

- **API Reference**: Update `documents/api/` with function signatures
- **Tutorials**: Add step-by-step guides to `documents/tutorials/` if complex
- **Engineering Standards**: Update `documents/engineering/` if new patterns introduced

Follow [Documentation Guidelines](engineering/documentation_guidelines.md) for SSoT, DRY, and mermaid best practices.

## Code Quality Standards

**Type Safety** (enforced via mypy --strict):
- Zero `Any` types
- Zero `cast()` calls
- Zero `# type: ignore` comments
- ADTs over Optional types
- Result type for error handling
- Exhaustive pattern matching

**Purity** (enforced via code review):
- No loops (use comprehensions/trampolines)
- Effects as data (immutable descriptions)
- Yield don't call (never call infrastructure)
- Immutability by default (frozen dataclasses)

**See**:
- [Type Safety](engineering/type_safety.md) - Eight type safety doctrines
- [Purity](engineering/purity.md) - Six purity doctrines
- [Forbidden Patterns](engineering/forbidden_patterns.md) - Anti-patterns to avoid

## Questions or Issues?

- **Questions?** Open a [discussion](https://github.com/your-org/effectful/discussions)
- **Bug reports?** File an [issue](https://github.com/your-org/effectful/issues)
- **Documentation unclear?** File an issue or submit a pull request

## Philosophy

> Make invalid states unrepresentable through the type system.

All engineering decisions flow from this principle. Every standard, pattern, and anti-pattern serves to eliminate entire classes of bugs at compile time rather than runtime.

Thank you for contributing to effectful!

---

**See Also**:
- [Engineering Standards](engineering/README.md) - Master index
- [Architecture](engineering/architecture.md) - System design
- [Type Safety](engineering/type_safety.md) - Type safety doctrines
- [Testing](engineering/testing.md) - Testing standards
- [Documentation Hub](README.md) - Complete documentation index
