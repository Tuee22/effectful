# Claude Code Patterns for Effectful

## Project Overview

**Effectful** is a pure functional effect system library for Python that brings algebraic data types, explicit error handling, and composable programs to async Python applications.

**Core Philosophy**: Make invalid states unrepresentable through the type system.

**Architecture**: Pure Python library (no web framework) with Docker-managed development environment for integration testing against real infrastructure (PostgreSQL, Redis, MinIO S3, Apache Pulsar).

## 🏗️ Architecture

**Stack**: Python 3.12+ | Poetry | asyncpg | Redis | WebSockets | Docker

**Library Structure**:
- `effectful/` - Main library package (renamed from functional_effects)
- `effectful/algebraic/` - Result[T, E], EffectReturn types
- `effectful/domain/` - Business domain models (User, Message, Profile, Token, etc.)
- `effectful/effects/` - Immutable effect definitions (WebSocket, Database, Cache, Messaging, Storage, Auth)
- `effectful/interpreters/` - Effect handlers (execution layer)
- `effectful/programs/` - Program execution runners
- `effectful/adapters/` - Real infrastructure implementations (PostgreSQL, Redis, S3, Pulsar)
- `effectful/infrastructure/` - Protocol definitions (interfaces)
- `effectful/testing/` - Testing matchers and utilities
- `tests/` - Comprehensive test suite (329+ tests)
- `examples/` - Working example programs
- `documents/` - Tutorials and API reference

**5-Layer Architecture**:
```
Layer 1: Application (User programs as generators)
    ↓
Layer 2: Program Runner (run_ws_program - effect execution loop)
    ↓
Layer 3: Composite Interpreter (Effect routing)
    ↓
Layer 4: Specialized Interpreters (WebSocket, Database, Cache, Messaging, Storage, Auth)
    ↓
Layer 5: Infrastructure Layer (PostgreSQL, Redis, S3, Pulsar, or test doubles)
```

## 📋 Command Reference

**All commands run inside Docker**: `docker compose -f docker/docker-compose.yml exec effectful poetry run <command>`

**Important**: Poetry is NOT set up as a virtual environment. Running `poetry install` outside the container should not create a `.venv` directory. All development happens inside Docker.

| Task | Command |
|------|---------|
| Start services | `docker compose -f docker/docker-compose.yml up -d` |
| View logs | `docker compose -f docker/docker-compose.yml logs -f effectful` |
| Check code quality | `docker compose -f docker/docker-compose.yml exec effectful poetry run check-code` |
| Test all | `docker compose -f docker/docker-compose.yml exec effectful poetry run test-all` |
| Test unit | `docker compose -f docker/docker-compose.yml exec effectful poetry run test-unit` |
| Test integration | `docker compose -f docker/docker-compose.yml exec effectful poetry run test-integration` |
| Python shell | `docker compose -f docker/docker-compose.yml exec effectful poetry run python` |
| Build package | `docker compose -f docker/docker-compose.yml exec effectful poetry build` |

**Entrypoints**:
- `check-code` - Black formatter + MyPy strict type checking
- `test-unit` - Unit tests only (pytest-mock, no I/O)
- `test-integration` - Integration tests (real PostgreSQL, Redis, MinIO, Pulsar)
- `test-all` - Complete test suite

**Test Isolation**: Each test is responsible for creating reproducible starting conditions (e.g., TRUNCATE + seed in fixtures).

**With output capture**: Add `> /tmp/test-output.txt 2>&1` to any test command (see Test Output Management).

## 📊 Test Statistics

| Category | Test Count | Duration | Infrastructure |
|----------|-----------|----------|----------------|
| Unit Tests | 200+ tests | ~0.5s | pytest-mock only |
| Integration | 27+ tests | ~1.1s | Real PostgreSQL/Redis/MinIO |
| Full suite | **329 tests** | **~1.6s** | Mixed |
| Coverage | 69% overall | - | Adapters/infrastructure excluded from measurement |

**Test Organization**:
- `tests/test_algebraic/` - Result, EffectReturn type tests
- `tests/test_domain/` - Domain model tests
- `tests/test_effects/` - Effect definition tests
- `tests/test_interpreters/` - Individual interpreter tests (pytest-mock)
- `tests/test_programs/` - Program runner tests
- `tests/test_integration/` - Multi-effect workflows (real infrastructure)
- `tests/test_demo/` - Demo program tests

## ✅ Universal Success Criteria

All code changes must meet these requirements:
- ✅ Exit code 0 (all operations complete successfully)
- ✅ **Zero MyPy errors** (mypy --strict mandatory)
- ✅ Zero stderr output
- ✅ Zero console warnings/errors
- ✅ **Zero skipped tests** (pytest.skip() forbidden)
- ✅ 100% test pass rate
- ✅ **Zero `Any`, `cast()`, or `# type: ignore`** (escape hatches forbidden)
- ✅ **Minimum 45% code coverage** (adapters excluded)
- ✅ **Integration tests cover all features** (conceptual coverage)

Referenced by: Testing Doctrine, Type Safety Doctrine, Code Quality checks, Contributing Checklist.

## 🐳 Docker Development

### Container Services

**Main Services** (docker-compose.yml):
- `effectful` - Python 3.12 + Poetry container with two entrypoints:
  - **Main**: Library development and unit tests
  - **Mock Client**: Separate process for integration testing
- `postgres` - PostgreSQL 15+ (asyncpg repository testing)
- `redis` - Redis 7+ (cache and auth testing)
- `minio` - S3-compatible storage (storage effect testing)
- `pulsar` - Apache Pulsar (messaging effect testing)

### Data Persistence

**Named Volumes (Recommended)**:
- PostgreSQL: `pgdata:/var/lib/postgresql/data`
- Redis: `redisdata:/data`
- MinIO: `miniodata:/data`
- Pulsar: `pulsardata:/pulsar/data`
- ✅ Automatic correct file ownership (no permission issues)
- ✅ Cross-platform compatible (macOS, Linux, Windows)
- ✅ Remove with: `docker compose -f docker/docker-compose.yml down -v`

**Why Not Bind Mounts?**:
- ❌ Docker Desktop for Mac has permission conflicts with PostgreSQL
- ❌ Bind mounts cause "Permission denied" errors during TRUNCATE operations
- ❌ Random test failures in integration suite
- ✅ Named volumes solve all these issues

### Package Management
- Poetry manages all Python dependencies via `pyproject.toml`
- No manual pip/pipx usage - all dependencies declared in pyproject.toml
- Use: `poetry add <package>` for runtime deps, `poetry add --group dev <package>` for dev deps

### 🚫 FORBIDDEN: Local Development Commands

**NEVER run these commands directly on the host machine:**

```bash
# ❌ FORBIDDEN - Running pytest locally
pytest tests/
python -m pytest

# ❌ FORBIDDEN - Running poetry locally
poetry run pytest
poetry run check-code
poetry install
poetry add some-package

# ❌ FORBIDDEN - Running mypy locally
mypy effectful/

# ❌ FORBIDDEN - Installing packages locally
pip install effectful
pip install -r requirements.txt

# ❌ FORBIDDEN - Running Python scripts locally
python examples/01_hello_world.py
```

**Why These Are Forbidden:**
- Tests can't access PostgreSQL, Redis, MinIO, Pulsar infrastructure
- Local Python version may differ from container
- Creates local virtualenvs that cause version mismatches
- Mypy results won't match CI environment

**Always use the Docker prefix:**
```bash
docker compose -f docker/docker-compose.yml exec effectful poetry run <command>
```

See `documents/core/docker_doctrine.md` for complete policy.

## 🧪 Testing Philosophy

**Core Principle**: Tests exist to find problems, not provide false confidence.

**Test Pyramid Strategy**:
```
        /\
       /E2\      E2E/Demo (Few) - Real infrastructure, full workflows
      /----\
     / Intg \    Integration (Some) - Real DB/Redis/MinIO, mocked WebSocket
    /--------\
   /   Unit   \  Unit (Many) - pytest-mock only, no I/O, fast (<1s)
  /------------\
```

Success criteria: See Universal Success Criteria section above.

### Test Output Management

**CRITICAL - Output Truncation**: Bash tool truncates at 30,000 characters. Large test suites can exceed this.

**REQUIRED Pattern**:

```bash
# Step 1: Run tests with output redirection
docker compose -f docker/docker-compose.yml exec effectful poetry run pytest > /tmp/test-output.txt 2>&1

# Step 2: Read complete output using Read tool on /tmp/test-output.txt

# Step 3: Analyze ALL failures, not just visible ones
```

**Why This Matters**: Truncated output hides failures, making diagnosis impossible. File-based approach ensures complete output is always available. Read tool has no size limits.

**For all test categories**: Use pattern above with `pytest`, `test-integration`, or specific test paths.

**Forbidden Practices**:
- ❌ `Bash(command="...pytest...", timeout=60000)` - Kills tests mid-run, truncates output
- ❌ `Bash(command="...pytest...", run_in_background=True)` - Loses real-time failure visibility
- ❌ Reading partial output with `head -n 100` or similar truncation
- ❌ Checking test status before completion (polling BashOutput prematurely)
- ❌ Running tests via Bash tool and analyzing truncated stdout
- ❌ Drawing conclusions without seeing complete output
- ❌ Creating fix plans based on partial failure information

**Required Practices**:
- ✅ Always redirect to /tmp/, then read complete output
- ✅ Verify you have seen ALL test results before creating fix plans
- ✅ If output is truncated, STOP and re-run with file redirection
- ✅ Let tests complete naturally (integration tests may take 1-2 seconds - patience required!)
- ✅ Review ALL stdout/stderr output before drawing conclusions

### Testing Strategy: Mocks vs Integration

**Unit Tests** (200+ tests, <1s):
- Use `pytest-mock` with `mocker.AsyncMock(spec=Protocol)`
- **No real infrastructure** - pure logic testing
- Test interpreters, domain models, effects, algebraic types
- Type-safe mocking: `spec=` parameter ensures correct interface

**Integration Tests** (27+ tests, ~1s):
- **Real PostgreSQL, Redis, MinIO** via Docker sidecars
- Mocked WebSocket (no real client needed for most tests)
- Test multi-effect workflows end-to-end
- Validates actual database queries, cache operations, S3 storage

**Mock Client Service**:
- Separate entrypoint in same Docker container
- Used for integration tests that need WebSocket client behavior
- Simulates real client connections without browser automation

## 🔍 Code Quality: check-code Command

**Usage**: `docker compose -f docker/docker-compose.yml exec effectful poetry run check-code` (see Command Reference)

### Black + MyPy Workflow

Runs Black (formatter) → MyPy (strict type checker) with fail-fast behavior.

**Behavior**:
1. **Black**: Auto-formats Python code (line-length=100)
2. **MyPy**: Strict type checking with 30+ strict settings, disallow_any_explicit=true
3. **Fail-fast**: Exits on first failure

Must meet Universal Success Criteria (exit code 0, Black formatting applied, zero MyPy errors).

## 🛡️ Type Safety Doctrines

For complete type safety policy, patterns, and examples, see **`documents/core/type_safety_doctrine.md`**.

**Core Principle**: Make invalid states unrepresentable through the type system.

**Eight Doctrines** (enforced via `mypy --strict`):
1. NO Escape Hatches (Any, cast, type:ignore forbidden)
2. ADTs Over Optional Types
3. Result Type for Error Handling
4. Immutability by Default (frozen dataclasses)
5. Exhaustive Pattern Matching
6. Type Narrowing for Union Types
7. Generic Type Parameters
8. PEP 695 Type Aliases

**Enforcement**: `mypy --strict` with `disallow_any_explicit = true` in pyproject.toml

## 🧹 Purity Enforcement

For complete purity doctrine and patterns, see **`documents/core/purity.md`** and **`documents/core/purity_patterns.md`**.

**Core Principle**: Expressions over statements. Comprehensions over loops. Trampolines over recursion.

**Six Purity Doctrines**:
1. No Loops (`for`, `while` forbidden - use comprehensions/trampolines)
2. Effects as Data (immutable descriptions, not execution)
3. Yield Don't Call (programs yield effects, never call infrastructure)
4. Interpreters Isolate Impurity (all I/O at boundary)
5. Immutability by Default (frozen dataclasses everywhere)
6. Exhaustive Pattern Matching (all cases handled with `unreachable()`)

**Banned Patterns**:
- ❌ `for` loops - use list/dict/set comprehensions
- ❌ `while` loops - use trampoline pattern
- ❌ `+=`, `-=` accumulation - use `functools.reduce`
- ❌ `.append()`, `.extend()` - use tuple spread or comprehension
- ❌ `del dict[key]` - use dict comprehension to filter
- ❌ Variable reassignment - use expression-based flow

**Acceptable Exceptions**:
- ✅ Single `while True` in trampoline driver
- ✅ Mutable connection state in adapters (I/O boundary)
- ✅ Imperative patterns in tests for setup/assertions

**Trampoline Module**: `effectful/algebraic/trampoline.py` - Use for any recursive patterns.

## 🚫 Test Anti-Patterns

For complete list of 22 test anti-patterns with examples, see **`documents/core/testing_doctrine.md`**.

**Key Anti-Patterns to Avoid:**
- Tests that pass when features are broken
- Using pytest.skip() (NEVER allowed)
- Testing with real infrastructure in unit tests
- Not testing error paths
- Incomplete assertions
- Docker bind mount permission issues

**Core Principle**: Tests exist to find problems, not provide false confidence.

## 🚫 Implementation Anti-Patterns

### 1. Using `Any` Types
- ❌ Function parameters or return types with `Any`
- ✅ Explicit types always (see Type Safety Doctrines)

### 2. Mutable Domain Models
- ❌ Dataclasses without `frozen=True`
- ✅ All domain models immutable: `@dataclass(frozen=True)`

### 3. Optional for Domain Logic
- ❌ Returning `Optional[User]` from domain methods
- ✅ ADT types: `UserLookupResult = UserFound | UserNotFound`

### 4. Exceptions for Expected Errors
- ❌ Raising exceptions for expected failure cases
- ✅ Result type: `Result[Success, Error]`

### 5. Imperative Effect Execution
- ❌ Directly calling infrastructure in programs: `await db.query(...)`
- ✅ Yield effects: `user = yield GetUserById(user_id=user_id)`

**Reference**: See `documents/core/purity.md` for complete purity doctrine and functional programming rules.

Impact: Breaks separation of concerns, makes testing difficult, couples business logic to infrastructure.

## Effect Program Patterns

For complete purity rules and functional programming patterns, see **`documents/core/purity.md`**.

### 1. Generator-Based DSL

```python
from collections.abc import Generator
from effectful import (
    AllEffects,
    EffectResult,
    GetUserById,
    SendText,
    SaveChatMessage,
)

def greet_user(user_id: UUID) -> Generator[AllEffects, EffectResult, bool]:
    """Effect program that looks up user and sends personalized greeting."""

    # Yield effect, receive result
    user = yield GetUserById(user_id=user_id)

    # Type narrowing
    if not isinstance(user, User):
        yield SendText(text="Error: User not found")
        return False

    # Use narrowed type
    greeting = f"Hello {user.name}!"
    yield SendText(text=greeting)

    # Type narrowing for next effect
    message = yield SaveChatMessage(user_id=user_id, text=greeting)
    assert isinstance(message, ChatMessage)

    yield SendText(text=f"Message saved with ID: {message.id}")
    return True
```

**Pattern**: `result = yield Effect(...)` - Yield effect, receive typed result.

### 2. Fail-Fast Error Propagation

```python
from effectful import run_ws_program

async def execute() -> None:
    result = await run_ws_program(greet_user(user_id), interpreter)

    # run_ws_program returns Err immediately on first effect failure
    match result:
        case Ok(success):
            print(f"Program completed: {success}")
        case Err(error):
            print(f"Program failed: {error}")
            # error is one of: DatabaseError | WebSocketClosedError | CacheError | etc.
```

**Pattern**: First effect that returns Err short-circuits the entire program.

### 3. Composing Programs

```python
def lookup_and_cache_profile(
    user_id: UUID
) -> Generator[AllEffects, EffectResult, ProfileData | None]:
    """Reusable program: lookup user, create profile, cache it."""
    user = yield GetUserById(user_id=user_id)

    if not isinstance(user, User):
        return None

    profile = ProfileData(id=str(user.id), name=user.name, email=user.email)
    yield PutCachedProfile(user_id=user.id, profile_data=profile, ttl_seconds=300)
    return profile

def greet_with_caching(user_id: UUID) -> Generator[AllEffects, EffectResult, str]:
    """Compose smaller programs into larger workflows."""

    # Check cache first
    cached = yield GetCachedProfile(user_id=user_id)
    if isinstance(cached, ProfileData):
        greeting = f"Hello {cached.name} (from cache)!"
    else:
        # Cache miss - lookup and cache
        profile = yield from lookup_and_cache_profile(user_id)
        if profile is None:
            return "User not found"
        greeting = f"Hello {profile.name}!"

    yield SendText(text=greeting)
    return greeting
```

**Pattern**: Use `yield from` to delegate to sub-programs.

## 🗄️ Database

**Schema**: Integration tests use real PostgreSQL with schema migrations
**Test Data**: Auto-seeded before each integration test (with TRUNCATE for isolation)
**Reset**: `docker compose -f docker/docker-compose.yml down -v && docker compose -f docker/docker-compose.yml up -d`

## 🔒 Git Workflow Policy

**Critical Rule**: Claude Code is NOT authorized to commit or push changes.

### Forbidden Git Operations
- ❌ **NEVER** run `git commit` (including `--amend`, `--no-verify`, etc.)
- ❌ **NEVER** run `git push` (including `--force`, `--force-with-lease`, etc.)
- ❌ **NEVER** run `git add` followed by commit operations
- ❌ **NEVER** create commits under any circumstances

### Required Workflow
- ✅ Make all code changes as requested
- ✅ Run tests and validation (see Command Reference)
- ✅ Leave ALL changes as **uncommitted** working directory changes
- ✅ User reviews changes using `git status` and `git diff`
- ✅ User manually commits and pushes when satisfied

**Rationale**: All changes must be human-reviewed before entering version control. This ensures code quality, prevents automated commit mistakes, and maintains clear authorship.

## 🔧 Development Workflow

1. `docker compose -f docker/docker-compose.yml up -d`
2. Make code changes
3. `poetry run check-code` (see Code Quality section)
4. `poetry run pytest` (see Command Reference)
5. Leave changes uncommitted (see Git Workflow Policy)

### Adding New Effects

1. Define immutable effect dataclass in `effectful/effects/`
   - Use `@dataclass(frozen=True)`
   - Include all parameters needed for execution
2. Add effect to `AllEffects` union type in `effectful/programs/program_types.py`
3. Update `EffectResult` union type if effect returns new type
4. Create specialized interpreter in `effectful/interpreters/`
   - Inherit from `BaseInterpreter`
   - Implement `handle()` method returning `Result[T, E]`
5. Register interpreter in `CompositeInterpreter`
6. Create real adapter in `effectful/adapters/` (if needed)
7. Write unit tests with pytest-mock (see Testing Antipatterns)
8. Write integration tests with real infrastructure
9. Update documentation in `documents/`

### Adding New Domain Models

1. Create ADT types in `effectful/domain/`
   - All dataclasses `frozen=True`
   - Use union types for variants: `type Result = Success | Failure`
2. Update `EffectResult` if model is returned from effects
3. Write exhaustive pattern matching examples
4. Add tests for domain model validation
5. Update API documentation

## 📊 Configuration

**Environment Variables**:
```bash
# PostgreSQL (integration tests)
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=effectful_test
POSTGRES_USER=effectful
POSTGRES_PASSWORD=effectful_pass

# Redis (integration tests)
REDIS_HOST=redis
REDIS_PORT=6379

# MinIO S3 (integration tests)
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=effectful-test

# Pulsar (integration tests)
PULSAR_URL=pulsar://pulsar:6650
```

## 🤝 Contributing Checklist

All items must meet Universal Success Criteria (see above).

- [ ] Code quality: `poetry run check-code` exits 0
- [ ] Tests for all features (unit + integration)
- [ ] No forbidden constructs (Any/cast/type:ignore)
- [ ] No anti-patterns (1-22)
- [ ] All dataclasses frozen (`frozen=True`)
- [ ] ADTs used instead of Optional for domain logic
- [ ] Result type used for all fallible operations
- [ ] Exhaustive pattern matching (all cases handled)
- [ ] Type narrowing for union types
- [ ] Generic type parameters specified
- [ ] Integration tests use real infrastructure
- [ ] Unit tests use pytest-mock only
- [ ] Changes left uncommitted (see Git Workflow Policy)

## 📚 References

### Core Doctrines (SSoT)
- **Purity Doctrine**: `documents/core/purity.md`
- **Purity Patterns**: `documents/core/purity_patterns.md`
- **Testing Doctrine**: `documents/core/testing_doctrine.md`
- **Type Safety Doctrine**: `documents/core/type_safety_doctrine.md`
- **Architecture**: `documents/core/architecture.md`

### Code References
- **Trampoline Module**: `effectful/algebraic/trampoline.py`
- **Result Type**: `effectful/algebraic/result.py`
- **ADT Examples**: `effectful/domain/user.py`, `effectful/domain/profile.py`
- **Type Aliases**: `effectful/programs/program_types.py`

### Testing
- **Testing Utilities**: `effectful/testing/__init__.py` (6 Result matchers)
- **Testing Doctrine**: `documents/core/testing_doctrine.md` (SSoT for all testing)
- **Testing Tutorial**: `documents/tutorials/04_testing_guide.md`
- **Test Suite Audit**: `documents/testing/test_suite_audit.md`

### Other
- **Effect Programs**: `tests/test_integration/test_chat_workflow.py`
- **Contributing Guide**: `CONTRIBUTING.md`

### Examples
- **Hello World**: `examples/01_hello_world.py`
- **User Greeting**: `examples/02_user_greeting.py`
- **Caching Workflow**: `examples/03_caching_workflow.py`
- **Error Handling**: `examples/04_error_handling.py`
- **Messaging Workflow**: `examples/05_messaging_workflow.py`

---

**Status**: Library foundation complete | Docker infrastructure ready | 329 tests passing
**Philosophy**: If the type checker passes, the program is correct. Make the type system work for you, not against you.
**Architecture**: Pure functional effect system with 5-layer architecture (Application -> Runner -> Composite -> Interpreters -> Infrastructure)
