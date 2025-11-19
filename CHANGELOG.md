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
- **Auth Effects**: `ValidateToken`, `GenerateToken`, `RefreshToken`, `RevokeToken`, `GetUserByEmail`, `ValidatePassword`, `HashPassword`
- **Cache Effects**: `GetCachedProfile`, `PutCachedProfile`
- **Database Effects**: `GetUserById`, `SaveChatMessage`
- **Messaging Effects**: `PublishMessage`, `ConsumeMessage`, `AcknowledgeMessage`, `NegativeAcknowledge`
- **Storage Effects**: `GetObject`, `PutObject`, `DeleteObject`, `ListObjects`
- **WebSocket Effects**: `SendText`, `ReceiveText`, `Close`

#### Domain Models
- **User** - User entity (`id`, `email`, `name`)
- **ChatMessage** - Chat message entity (`id`, `user_id`, `text`, `created_at`)
- **ProfileData** - Cached profile data (`id`, `name`, `email`)
- **UserLookupResult** - ADT for user lookup (`UserFound | UserNotFound`)
- **CacheLookupResult** - ADT for cache lookup (`CacheHit | CacheMiss`)
- **TokenValidationResult** - ADT for token validation (`TokenValid | TokenExpired | TokenInvalid`)
- **PublishResult** - ADT for message publishing (`PublishSuccess | PublishFailure`)
- **MessageEnvelope** - Message container with metadata
- **PutResult** - ADT for object storage (`PutSuccess | PutFailure`)
- **S3Object** - Stored object with content and metadata

#### Interpreters
- **AuthInterpreter** - Handles JWT authentication effects
- **CacheInterpreter** - Handles cache effects
- **DatabaseInterpreter** - Handles database effects
- **MessagingInterpreter** - Handles Pulsar messaging effects
- **StorageInterpreter** - Handles S3 storage effects
- **WebSocketInterpreter** - Handles WebSocket effects
- **CompositeInterpreter** - Routes effects to specialized interpreters

#### Error Types
- **AuthError** - Authentication/JWT operation failures
- **CacheError** - Cache access failures
- **DatabaseError** - Database operation failures
- **MessagingError** - Messaging/Pulsar operation failures
- **StorageError** - Storage/S3 operation failures
- **WebSocketClosedError** - WebSocket connection closed
- **UnhandledEffectError** - Effect type not recognized

#### Testing Utilities
- **Matchers**: `assert_ok`, `assert_err`, `unwrap_ok`, `unwrap_err`, `assert_ok_value`, `assert_err_message`
- **Testing Pattern Docs**: `docs/testing/TESTING_PATTERNS.md` - Comprehensive 4-layer testing guide
- **Test Suite Audit**: `docs/testing/TEST_SUITE_AUDIT.md` - Systematic review of all 27 test files
- **pytest-mock Integration**: Type-safe mocking using `mocker.AsyncMock(spec=Protocol)`

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
- 329 tests across unit, integration, and import categories
- 10 tests for run_ws_program
- 27 integration tests for multi-effect workflows
- 14 import tests validating public API
- Zero skipped tests (pytest.skip() forbidden)
- pytest-mock for type-safe mocking with spec parameter

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

- **Adapters not included** - Real implementations for S3, Pulsar, Redis require external setup
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

### Changed

#### Testing Infrastructure - BREAKING CHANGE

**Major refactoring**: Replaced custom fake infrastructure with pytest-mock for cleaner, more maintainable tests.

**Before (Custom Fakes)**:
- Required maintaining 8 fake classes (`FakeWebSocketConnection`, `FakeUserRepository`, etc.)
- Required maintaining 3 failing fake variants
- Required maintaining pytest fixtures for all fakes
- Required maintaining factory function `create_test_interpreter()`
- Total overhead: ~500+ lines of test infrastructure code

**After (pytest-mock)**:
```python
from pytest_mock import MockerFixture

def test_workflow(mocker: MockerFixture) -> None:
    # Type-safe mocks using spec parameter
    mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
    mock_user_repo = mocker.AsyncMock(spec=UserRepository)

    # Configure behavior
    mock_user_repo.get_by_id.return_value = UserFound(user=user, source="database")

    # Use in test
    interpreter = create_composite_interpreter(
        websocket_connection=mock_ws,
        user_repo=mock_user_repo,
        ...
    )
```

**Benefits**:
- **Less code**: Eliminated 500+ lines of fake infrastructure
- **Type safety**: `spec=Protocol` provides compile-time type checking
- **Flexibility**: Configure behavior per-test, no shared state
- **Standard tooling**: pytest-mock is industry standard
- **Better errors**: Clear assertion messages from pytest-mock

**Migration Guide**:
1. Replace `from functional_effects.testing import ...` with `from pytest_mock import MockerFixture`
2. Replace fake fixtures with `mocker: MockerFixture` parameter
3. Create mocks using `mocker.AsyncMock(spec=Protocol)`
4. Configure behavior using `.return_value` or `.side_effect`
5. See `docs/testing/TESTING_PATTERNS.md` for complete examples

**Documentation Added**:
- **docs/testing/TESTING_PATTERNS.md** (650+ lines) - Comprehensive testing guide
  - Four-layer testing architecture (Effects → Interpreters → Programs → Workflows)
  - Pattern decision tree for choosing correct approach
  - Complete examples for each layer
  - Common pitfalls and how to avoid them
  - Migration guide from old patterns
- **docs/testing/TEST_SUITE_AUDIT.md** - Systematic review of all 27 test files
  - Categorized by testing layer
  - Verification that all tests follow documented patterns
  - Test execution results (329 tests, 100% pass rate)

**Test Suite Status**:
- **Total tests**: 329 (up from 29)
- **Pass rate**: 100% (0 failures, 0 skipped)
- **Duration**: 1.64 seconds
- **Coverage**: 69% (expected - adapters not tested with real infrastructure)
  - Tested modules: 96-99% coverage (interpreters, runners, effects, domain)
  - Untested adapters: 0-57% coverage (postgres, pulsar, redis, s3)

**Breaking Changes**:
- **Removed**: All fake classes from `functional_effects/testing/fakes.py`
- **Removed**: All failing fake variants
- **Removed**: `create_test_interpreter()` factory function
- **Removed**: Fake-related pytest fixtures
- **Removed**: `functional_effects/testing/__init__.py` exports for fakes
- **Kept**: Testing matchers (`assert_ok`, `unwrap_ok`, etc.) - still useful

**If your tests break**:
- You were using the testing fake infrastructure (now removed)
- Follow migration guide above to switch to pytest-mock
- All 329 tests in this library have been migrated successfully
- See `tests/test_integration/` for working examples

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
