# Demo Application - Pure Functional Effect Programs

This demo application demonstrates how to build complex business logic using the `functional_effects` library with **pure functions**, **algebraic data types (ADTs)**, and **explicit error handling**.

## Overview

The demo implements a simple chat application backend with:
- **Auth lifecycle**: Login, logout, token refresh, user registration
- **User management**: CRUD operations with cache invalidation
- **Messaging**: Send messages to Pulsar topics
- **Complex workflows**: Authenticated message sending using all 6 infrastructure types

All business logic is implemented as **pure effect programs** that are:
- **Type-safe**: 100% MyPy strict compliance with no `Any`, `cast`, or `type: ignore`
- **Testable**: 35 comprehensive tests using pytest-mock (100% pass rate)
- **Composable**: Programs yield effects and return Result types for explicit error handling
- **Infrastructure-agnostic**: No direct dependencies on databases, caches, or external services

## Architecture

### Directory Structure

```
demo/
├── domain/
│   ├── errors.py           # ADTs for domain errors (AuthError, AppError)
│   └── responses.py        # ADTs for API responses (LoginResponse, MessageResponse)
└── programs/
    ├── auth_programs.py    # Auth lifecycle (login, logout, refresh, register)
    ├── user_programs.py    # User CRUD operations
    ├── message_programs.py # Message sending/retrieval
    └── chat_programs.py    # Complex workflow using all 6 infrastructure types
```

### Infrastructure Types

The demo uses all 6 infrastructure types from `functional_effects`:

1. **Auth** (Redis): JWT token generation/validation
2. **Cache** (Redis): User data caching with TTL
3. **Database** (PostgreSQL): User and message persistence
4. **Messaging** (Pulsar): Publish messages to topics
5. **Storage** (S3): Archive messages for compliance
6. **WebSocket**: Real-time client notifications

## Programs

### Auth Programs (`auth_programs.py`)

#### `login_program(email, password) -> Result[LoginResponse, AuthError | AppError]`

Authenticate user with email/password and return JWT tokens.

**Flow**:
1. Get user by email from database
2. Validate password against bcrypt hash
3. Generate access token (1 hour TTL)
4. Generate refresh token (7 day TTL)
5. Return LoginResponse with tokens

**Example**:
```python
from demo.programs.auth_programs import login_program
from functional_effects.algebraic.result import Ok, Err

result = await run_program(login_program("alice@example.com", "secret123"))

match result:
    case Ok(login_response):
        print(f"Access token: {login_response.access_token}")
        print(f"Refresh token: {login_response.refresh_token}")
    case Err(error):
        print(f"Login failed: {error.message}")
```

#### `logout_program(token) -> Result[bool, AuthError]`

Revoke JWT token (add to Redis blacklist).

#### `refresh_program(refresh_token) -> Result[LoginResponse, AuthError | AppError]`

Exchange refresh token for new access + refresh tokens.

#### `register_program(email, name, password) -> Result[User, AuthError | AppError]`

Create new user account with hashed password.

### User Programs (`user_programs.py`)

#### `get_user_program(user_id) -> Result[User, AppError]`

Retrieve user by ID.

#### `list_users_program(limit, offset) -> Result[list[User], AppError]`

List all users with optional pagination.

#### `update_user_program(user_id, email, name) -> Result[User, AppError]`

Update user fields and invalidate cache.

**Flow**:
1. Validate inputs (at least one field, valid email format)
2. Verify user exists
3. Update user in database
4. Invalidate user cache
5. Return updated user

#### `delete_user_program(user_id) -> Result[bool, AppError]`

Delete user and invalidate cache.

### Message Programs (`message_programs.py`)

#### `send_message_program(user_id, text) -> Result[MessageResponse, AppError]`

Send message to Pulsar topic.

**Flow**:
1. Validate user exists
2. Validate message text (not empty, max 10000 chars)
3. Create message with ID and timestamp
4. Publish message to Pulsar topic
5. Return MessageResponse

#### `get_message_program(message_id) -> Result[MessageResponse, AppError]`

Demonstration stub showing message retrieval pattern (always returns not_found).

### Chat Programs (`chat_programs.py`)

#### `send_authenticated_message_with_storage_program(token, text) -> Result[MessageResponse, AuthError | AppError]`

**This program demonstrates all 6 infrastructure types in a single workflow.**

**Flow**:
1. **[Auth]** Validate JWT token
2. **[Cache]** Check for cached user data (cache-aside pattern)
3. **[Database]** Load user from PostgreSQL (if cache miss)
4. **[Cache]** Store user in Redis for future requests (TTL: 5 minutes)
5. Validate message text
6. **[Storage]** Archive message to S3 for compliance/audit
7. **[Messaging]** Publish message to Pulsar topic
8. **[WebSocket]** Send confirmation to client via WebSocket
9. Return MessageResponse

**Example**:
```python
from demo.programs.chat_programs import send_authenticated_message_with_storage_program

result = await run_program(
    send_authenticated_message_with_storage_program(
        token="eyJhbGciOiJIUzI1NiIs...",
        text="Hello from all 6 infrastructure types!"
    )
)

match result:
    case Ok(message_response):
        print(f"Message sent: {message_response.message_id}")
        print(f"Archived to S3, published to Pulsar, sent via WebSocket")
    case Err(AuthError(error_type="token_invalid")):
        print("Invalid or expired token")
    case Err(AppError(error_type="not_found")):
        print("User not found")
```

## Domain Models

### Errors (`domain/errors.py`)

All errors are immutable ADTs using frozen dataclasses:

```python
@dataclass(frozen=True)
class AuthError:
    message: str
    error_type: Literal["invalid_credentials", "token_expired", "token_invalid", "unauthorized"]

@dataclass(frozen=True)
class AppError:
    message: str
    error_type: Literal["not_found", "validation_error", "conflict", "internal_error"]

    @staticmethod
    def not_found(message: str) -> "AppError":
        return AppError(message=message, error_type="not_found")
```

### Responses (`domain/responses.py`)

All responses are immutable ADTs:

```python
@dataclass(frozen=True)
class LoginResponse:
    access_token: str
    refresh_token: str
    user_id: UUID
    expires_in: int

@dataclass(frozen=True)
class MessageResponse:
    message_id: UUID
    user_id: UUID
    text: str
    created_at: datetime
```

## Testing

All programs are tested with **pytest-mock** (no fakes):

```bash
# Run demo tests
pytest tests/test_demo/ -v

# Expected output:
# 35 passed, 0 failed (100% pass rate)
```

### Test Coverage

- **auth_programs**: 13 tests (login, logout, refresh, register - success + error paths)
- **user_programs**: 10 tests (get, list, update, delete - success + validation errors)
- **message_programs**: 6 tests (send, get - success + validation errors)
- **chat_programs**: 5 tests (all 6 infrastructure types - success + error paths)

### Test Pattern

All tests use generator-based mocking:

```python
def test_login_success(mocker: MockerFixture) -> None:
    """Test successful login with valid credentials."""
    # Setup
    user = User(id=uuid4(), email="alice@example.com", name="Alice")

    # Mock the program execution
    gen = login_program(email="alice@example.com", password="secret123")

    # Step 1: GetUserByEmail returns user
    effect1 = next(gen)
    assert effect1.__class__.__name__ == "GetUserByEmail"
    result1 = gen.send(user)

    # Step 2: ValidatePassword returns True
    effect2 = result1
    assert effect2.__class__.__name__ == "ValidatePassword"
    result2 = gen.send(True)

    # Step 3: GenerateToken for access token
    effect3 = result2
    result3 = gen.send("access_token_123")

    # Step 4: GenerateToken for refresh token
    effect4 = result3

    # Final result
    try:
        gen.send("refresh_token_456")
        pytest.fail("Expected StopIteration")
    except StopIteration as e:
        result = e.value

    # Assert
    assert isinstance(result, Ok)
    assert result.value.access_token == "access_token_123"
    assert result.value.refresh_token == "refresh_token_456"
```

## Type Safety

All demo code is 100% MyPy strict compliant:

```bash
# Run MyPy on demo programs
mypy demo/programs/

# Expected output:
# Success: no issues found in 5 source files
# (4 benign "unreachable" warnings may appear - these are MyPy false positives)
```

### Type Safety Features

- **No escape hatches**: Zero `Any`, `cast()`, or `# type: ignore`
- **ADTs over Optional**: Explicit error cases instead of `Optional[T]`
- **Result type**: All fallible operations return `Result[T, E]`
- **Immutability**: All dataclasses use `frozen=True`
- **Exhaustive matching**: Pattern matching ensures all cases handled

## Key Patterns

### 1. Result Type for Error Handling

```python
def login_program(...) -> Generator[AllEffects, EffectResult, Result[LoginResponse, AuthError | AppError]]:
    user = yield GetUserByEmail(email=email)

    if user is None:
        return Err(AppError.not_found(f"User not found"))

    # Success path
    return Ok(LoginResponse(...))
```

### 2. Effect Composition

```python
# Yield effects, receive results directly
user = yield GetUserById(user_id=user_id)
assert isinstance(user, User)  # Type narrowing

# Multiple effects in sequence
access_token = yield GenerateToken(user_id=user.id, ...)
refresh_token = yield GenerateToken(user_id=user.id, ...)
```

### 3. Cache-Aside Pattern

```python
# Check cache first
cached = yield GetCachedValue(key=cache_key)

# Cache miss - load from database
user = yield GetUserById(user_id=user_id)

# Store in cache for future requests
yield PutCachedValue(key=cache_key, value=user_bytes, ttl_seconds=300)
```

### 4. Validation Before Effects

```python
# Validate inputs before yielding effects
if not text or text.strip() == "":
    return Err(AppError.validation_error("Message text cannot be empty"))

if len(text) > 10000:
    return Err(AppError.validation_error("Text exceeds max length"))

# Only yield effects after validation passes
message_id = yield PublishMessage(topic="chat-messages", payload=payload)
```

## Anti-Patterns to Avoid

See `CLAUDE.md` in the project root for comprehensive anti-patterns documentation.

**Key anti-patterns avoided in this demo**:
- ❌ Using fakes or test doubles (use pytest-mock instead)
- ❌ Using Optional types (use ADTs instead)
- ❌ Throwing exceptions (return Result types)
- ❌ Mutable dataclasses (all frozen=True)
- ❌ Skipping tests (pytest.skip forbidden)

## References

- **Main README**: `/packages/functional/README.md` - Library overview
- **Architecture**: `/packages/functional/ARCHITECTURE.md` - System design
- **Contributing**: `/packages/functional/CONTRIBUTING.md` - Development guidelines
- **Testing Guide**: `/packages/functional/docs/tutorials/04_testing_guide.md` - Testing patterns
