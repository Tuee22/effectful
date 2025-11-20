# Examples

This directory contains complete, runnable examples demonstrating **effectful** patterns.

## Running Examples

All examples can be run as Python modules:

```bash
# From the project root
python -m examples.01_hello_world
python -m examples.02_user_greeting
python -m examples.03_caching_workflow
python -m examples.04_error_handling
```

Or run individual files:

```bash
cd examples
python 01_hello_world.py
```

## Example Programs

### 01_hello_world.py

**Minimal effect program** demonstrating basic WebSocket communication.

**Concepts:**
- Basic effect program structure
- Yielding effects
- Running programs with `run_ws_program`
- Pattern matching on Result type

**Output:**
```
Running hello_world program...
✓ Success: Message sent successfully
```

---

### 02_user_greeting.py

**Database + WebSocket workflow** with user lookup and message saving.

**Concepts:**
- Multiple effect types (GetUserById, SendText, SaveChatMessage)
- Pattern matching on domain results
- Type narrowing with `isinstance()`
- Sequential effect execution

**Output:**
```
Running greet_user program for user ...
✓ Success: success

Messages sent:
  1. Hello Alice!
  2. Message saved with ID: ...

Messages saved: 1
  - Hello Alice! (ID: ...)
```

---

### 03_caching_workflow.py

**Cache-aside pattern** with database fallback.

**Concepts:**
- Cache effects (GetCachedProfile, PutCachedProfile)
- Cache miss handling
- Profile caching with TTL
- Comparing cache hit vs miss behavior

**Output:**
```
=== First Request (expect cache miss) ===
✓ Result: cache_miss
  → Cache miss - querying database...
  → Profile: Bob (bob@example.com) [from database]

=== Second Request (expect cache hit) ===
✓ Result: cache_hit
  → Profile: Bob (bob@example.com) [from cache]

=== Cache State ===
Cached profiles: 1
  - ...: Bob (bob@example.com)
```

---

### 04_error_handling.py

**Comprehensive error handling** patterns.

**Concepts:**
- Handling user not found (None case)
- Database failures (DatabaseError)
- Fail-fast semantics
- Batch processing with mixed results
- Using FailingUserRepository for error testing

**Output:**
```
=== Demo 1: User Not Found ===
✓ Program completed: not_found
  → User not found - please check the ID

=== Demo 2: Database Failure ===
✓ Caught database error: Connection timeout
  Retryable: True
  → Could implement retry logic here

=== Demo 3: Success Case ===
✓ Program completed: success
  → Found user: Charlie (charlie@example.com)

=== Demo 4: Batch Processing ===
✓ Batch complete: {'found': 3, 'not_found': 2}
  Messages sent:
    → Found: User 1
    → Found: User 3
    → Found: User 5
    → Lookup complete: 3 found, 2 not found
```

---

## Common Patterns

### Basic Program Structure

```python
from collections.abc import Generator
from effectful import AllEffects, EffectResult

def my_program() -> Generator[AllEffects, EffectResult, str]:
    # Yield effects
    result = yield SomeEffect(...)

    # Pattern match on result
    match result:
        case SomeType(value=value):
            return "success"
        case _:
            return "failure"
```

### Running Programs

```python
from effectful import run_ws_program
from effectful.testing import create_test_interpreter

async def main():
    interpreter = create_test_interpreter()
    result = await run_ws_program(my_program(), interpreter)

    match result:
        case Ok(value):
            print(f"Success: {value}")
        case Err(error):
            print(f"Error: {error}")
```

### Setting Up Test Data

```python
from effectful.testing import (
    FakeUserRepository,
    FakeProfileCache,
    create_test_interpreter,
)

# Setup test data
fake_repo = FakeUserRepository()
fake_cache = FakeProfileCache()

user_id = uuid4()
fake_repo._users[user_id] = User(...)

# Create interpreter
interpreter = create_test_interpreter(
    user_repo=fake_repo,
    cache=fake_cache,
)
```

### Error Handling

```python
# Testing database failures
from effectful.testing import FailingUserRepository

failing_repo = FailingUserRepository(error_message="Connection timeout")
interpreter = create_test_interpreter(user_repo=failing_repo)

result = await run_ws_program(program(), interpreter)

match result:
    case Err(DatabaseError(db_error=error, is_retryable=True)):
        # Handle retryable error
        ...
    case Err(error):
        # Handle other errors
        ...
```

## Next Steps

After exploring these examples:

1. **Read the tutorials** - [documents/tutorials/](../documents/tutorials/)
2. **Study the architecture** - [ARCHITECTURE.md](../ARCHITECTURE.md)
3. **Review type safety guidelines** - [effectful/CLAUDE.md](../effectful/CLAUDE.md)
4. **Write your own programs** - See [CONTRIBUTING.md](../CONTRIBUTING.md)

## Testing Examples

All examples use test fakes (in-memory implementations). For production:

```python
from effectful import create_composite_interpreter

# Replace fakes with real infrastructure
interpreter = create_composite_interpreter(
    websocket_connection=real_fastapi_websocket,
    user_repo=real_postgres_repo,
    message_repo=real_postgres_repo,
    cache=real_redis_cache,
)
```

See [Tutorial 05: Production Deployment](../documents/tutorials/05_production_deployment.md) for details.

---

**Happy effect programming!**
