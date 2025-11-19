# Changelog

All notable changes to **functional_effects** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-01-XX

### Added

#### Core Features
- **Effect System** - Generator-based DSL for composable programs
- **Result Type** - Explicit error handling (`Ok[T] | Err[E]`)
- **Algebraic Data Types** - Type-safe domain modeling
- **run_ws_program** - Effect program runner with fail-fast semantics
- **CompositeInterpreter** - Unified interpreter for all effect types

#### Effects
- **WebSocket Effects**: `SendText`, `ReceiveText`, `Close`
- **Database Effects**: `GetUserById`, `SaveChatMessage`
- **Cache Effects**: `GetCachedProfile`, `PutCachedProfile`

#### Domain Models
- **User** - User entity (`id`, `email`, `name`)
- **ChatMessage** - Chat message entity (`id`, `user_id`, `text`, `created_at`)
- **ProfileData** - Cached profile data (`id`, `name`, `email`)
- **UserLookupResult** - ADT for user lookup (`UserFound | UserNotFound`)
- **CacheLookupResult** - ADT for cache lookup (`CacheHit | CacheMiss`)

#### Interpreters
- **WebSocketInterpreter** - Handles WebSocket effects
- **DatabaseInterpreter** - Handles database effects
- **CacheInterpreter** - Handles cache effects
- **CompositeInterpreter** - Routes effects to specialized interpreters

#### Error Types
- **DatabaseError** - Database operation failures
- **WebSocketClosedError** - WebSocket connection closed
- **CacheError** - Cache access failures
- **UnhandledEffectError** - Effect type not recognized

#### Testing Utilities
- **Fakes**: `FakeWebSocketConnection`, `FakeUserRepository`, `FakeChatMessageRepository`, `FakeProfileCache`
- **Failing Fakes**: `FailingUserRepository`, `FailingChatMessageRepository`, `FailingProfileCache`
- **Fixtures**: pytest fixtures for all fakes (`test_interpreter`, `fake_websocket`, etc.)
- **Matchers**: `assert_ok`, `assert_err`, `unwrap_ok`, `unwrap_err`, `assert_ok_value`, `assert_err_message`
- **Factory**: `create_test_interpreter()` for quick test setup

#### Documentation
- **README.md** - Complete library overview with examples
- **ARCHITECTURE.md** - Design rationale and patterns
- **CONTRIBUTING.md** - Development workflow and standards
- **functional_effects/CLAUDE.md** - Type safety guidelines
- **docs/tutorials/01_quickstart.md** - Getting started guide
- **docs/tutorials/02_effect_types.md** - Complete effect reference
- **docs/tutorials/03_adts_and_results.md** - Type safety deep dive

#### Infrastructure
- **Public API** (`functional_effects/__init__.py`) - ~50 exports
- **Testing API** (`functional_effects/testing/__init__.py`) - 24 testing utilities
- **Type Checking** - 100% mypy --strict compliance
- **Test Coverage** - 29 tests with zero mypy errors

### Technical Details

#### Type Safety
- Zero `Any` types
- Zero `cast()` calls
- Zero `# type: ignore` comments
- All dataclasses `frozen=True`
- Exhaustive pattern matching enforced
- Generic type parameters fully specified

#### Testing
- 29 tests across unit, integration, and import categories
- 10 tests for run_ws_program
- 5 integration tests for multi-effect workflows
- 14 import tests validating public API
- Zero skipped tests (pytest.skip() forbidden)
- Fakes for all infrastructure (no mocking framework)

#### Code Quality
- Black formatting (line-length=100)
- Ruff linting
- MyPy strict mode
- Immutability by default
- PEP 695 type syntax (Python 3.12+)

### Philosophy

This release establishes the core architecture:

1. **Make invalid states unrepresentable** - ADTs over Optional
2. **Errors in signatures** - Result type over exceptions
3. **Immutability** - Frozen dataclasses eliminate temporal coupling
4. **Exhaustive matching** - Type checker enforces handling all cases
5. **Testability** - Swap real infrastructure for fakes

### Migration Notes

This is the initial release. No migration needed.

### Known Limitations

- **Effect types limited** - WebSocket, Database, Cache only
- **No parallel effects** - All effects execute sequentially
- **No effect retries** - Manual retry logic required
- **No effect timeouts** - Manual timeout handling required
- **No structured logging** - Manual logging in interpreters

These limitations are intentional for v0.1.0. Future releases will add:
- Parallel effect execution (`Parallel([effect1, effect2])`)
- Retry semantics (`Retry(effect, max_attempts=3)`)
- Timeout wrappers (`Timeout(effect, seconds=5.0)`)
- Structured logging middleware

### Dependencies

**Runtime**:
- Python 3.12+

**Development**:
- pytest >= 7.0
- pytest-asyncio >= 0.21
- mypy >= 1.0
- black >= 23.0
- ruff >= 0.1.0

### Breaking Changes

None (initial release).

---

## [Unreleased]

### Planned for 0.2.0

- [ ] Parallel effect execution
- [ ] Effect retry semantics
- [ ] Effect timeout wrappers
- [ ] Structured logging middleware
- [ ] HTTP effects (GET, POST, PUT, DELETE)
- [ ] File I/O effects (Read, Write, Delete)
- [ ] Example programs in `examples/` directory
- [ ] Complete API reference documentation
- [ ] Performance benchmarks
- [ ] py.typed marker for PEP 561 compliance

### Planned for 0.3.0

- [ ] Effect cancellation
- [ ] Effect streaming (async generators)
- [ ] Effect batching
- [ ] Effect memoization/caching
- [ ] Effect tracing/debugging
- [ ] Effect visualization tools

---

## Release Checklist

Before each release:

- [ ] All tests pass (100% coverage)
- [ ] Zero mypy --strict errors
- [ ] Black formatting applied
- [ ] Ruff linting passed
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] Version bumped in pyproject.toml
- [ ] Git tag created (`vX.Y.Z`)
- [ ] Package built (`poetry build`)
- [ ] Package published (`poetry publish`)

---

[Unreleased]: https://github.com/your-org/functional_effects/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/your-org/functional_effects/releases/tag/v0.1.0
