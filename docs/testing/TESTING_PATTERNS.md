# Testing Patterns for functional-effects

This document defines the comprehensive testing patterns for the functional-effects library. Following these patterns ensures consistency, maintainability, and type safety across the entire test suite.

## Table of Contents
- [Architecture Overview](#architecture-overview)
- [Testing Philosophy](#testing-philosophy)
- [Four Testing Layers](#four-testing-layers)
- [Pattern Decision Tree](#pattern-decision-tree)
- [Complete Examples](#complete-examples)
- [Common Pitfalls](#common-pitfalls)
- [Migration Guide](#migration-guide)

## Architecture Overview

The functional-effects library has a clean 4-layer architecture:

```
┌─────────────────────────────────────────────────────────┐
│ Layer 4: Workflow Tests (Integration)                   │
│ - Complete end-to-end scenarios                         │
│ - Multiple effects composed together                    │
│ - Pattern: run_ws_program() + pytest-mock              │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│ Layer 3: Program Tests (Unit)                           │
│ - Business logic in generators                          │
│ - Effect sequencing and data flow                       │
│ - Pattern: Manual generator stepping (next/send)       │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│ Layer 2: Interpreter Tests (Unit)                       │
│ - Effect execution against infrastructure              │
│ - Error handling and Result types                       │
│ - Pattern: Direct interpreter calls + pytest-mock      │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│ Layer 1: Effect Tests (Unit)                            │
│ - Dataclass structure validation                        │
│ - Immutability and type safety                          │
│ - Pattern: Simple instantiation tests                   │
└─────────────────────────────────────────────────────────┘
```

## Testing Philosophy

### Core Principles

1. **Each layer tests ONE concern**: Effects test structure, interpreters test execution, programs test logic, workflows test integration
2. **Type safety everywhere**: Use `spec` parameter in pytest-mock to catch interface mismatches
3. **No test doubles library**: Use pytest-mock's `AsyncMock` with `side_effect` for stateful behavior
4. **Explicit error handling**: Always test both `Ok` and `Err` cases using pattern matching
5. **100% coverage, 100% pass rate**: Zero skipped tests (pytest.skip is forbidden)

### Why This Architecture?

**Separation of Concerns**: Each layer has distinct responsibilities:
- Effects = **WHAT** to do (pure data)
- Interpreters = **HOW** to do it (execution)
- Programs = **WHEN** to do it (sequencing)
- Workflows = **WHY** to do it (business scenarios)

**Testability**: Each layer can be tested independently:
- Effects: No dependencies, just dataclass validation
- Interpreters: Mock infrastructure, focus on execution logic
- Programs: Mock effect results, focus on sequencing
- Workflows: Real interpreters + mocked infrastructure, focus on integration

## Four Testing Layers

### Layer 1: Effect Tests (Unit)

**Location**: `tests/test_effects/`

**Purpose**: Validate effect dataclass structure, immutability, and type safety.

**Pattern**: Simple instantiation and assertion.

```python
from functional_effects.effects.database import GetUserById

def test_get_user_by_id_structure():
    """Effect should be immutable with correct fields."""
    effect = GetUserById(user_id=uuid4())

    assert isinstance(effect, GetUserById)
    assert effect.user_id is not None

    # Verify immutability
    with pytest.raises(FrozenInstanceError):
        effect.user_id = uuid4()
```

**When to use**: Testing effect dataclass definitions.

**Do NOT**: Use interpreters or generators in effect tests.

### Layer 2: Interpreter Tests (Unit)

**Location**: `tests/test_interpreters/`

**Purpose**: Test effect execution against mocked infrastructure. Verify Result types, error handling, and retryability.

**Pattern**: Direct interpreter method calls with pytest-mock.

```python
from pytest_mock import MockerFixture
from functional_effects.interpreters.database import DatabaseInterpreter
from functional_effects.infrastructure.repositories import UserRepository

@pytest.mark.asyncio()
async def test_get_user_by_id_success(mocker: MockerFixture) -> None:
    """GetUserById with existing user should return Ok(EffectReturn(user))."""
    # Arrange - Mock infrastructure
    user = User(id=uuid4(), email="alice@example.com", name="Alice")
    mock_repo = mocker.AsyncMock(spec=UserRepository)
    mock_repo.get_by_id.return_value = user

    interpreter = DatabaseInterpreter(user_repo=mock_repo)
    effect = GetUserById(user_id=user.id)

    # Act
    result = await interpreter.interpret(effect)

    # Assert - Pattern match on Result
    match result:
        case Ok(EffectReturn(value=returned_user, effect_name="GetUserById")):
            assert returned_user == user
        case _:
            pytest.fail(f"Expected Ok(EffectReturn(user)), got {result}")

    # Verify mock interactions
    mock_repo.get_by_id.assert_awaited_once_with(user.id)
```

**Key points**:
- Use `mocker.AsyncMock(spec=Protocol)` for type safety
- Test both success (`Ok`) and error (`Err`) paths
- Verify retryability for errors
- Use pattern matching for Result validation
- Assert mock call counts and arguments

**When to use**: Testing individual interpreter implementations.

**Do NOT**: Use generators or run_ws_program in interpreter tests.

### Layer 3: Program Tests (Unit)

**Location**: `tests/test_demo/`

**Purpose**: Test program logic (effect sequencing, data transformations, conditional flows) in isolation.

**Pattern**: Manual generator stepping with `next()` and `gen.send()`.

```python
from demo.programs.user_programs import get_user_program

def test_get_user_program_success(mocker: MockerFixture) -> None:
    """Program should yield GetUserById and return Ok(user)."""
    # Arrange
    user_id = uuid4()
    user = User(id=user_id, email="alice@example.com", name="Alice")

    # Act - Step through program
    gen = get_user_program(user_id=user_id)

    # Step 1: Program yields GetUserById effect
    effect = next(gen)
    assert effect.__class__.__name__ == "GetUserById"
    assert effect.user_id == user_id

    # Step 2: Send mock user result, program completes
    try:
        gen.send(user)
        pytest.fail("Expected StopIteration")
    except StopIteration as e:
        result = e.value

    # Assert final result
    match result:
        case Ok(returned_user):
            assert returned_user == user
        case _:
            pytest.fail(f"Expected Ok(user), got {result}")
```

**Key points**:
- Programs are generators: use `next(gen)` to get next effect
- Use `gen.send(value)` to provide mock results
- Catch `StopIteration` to extract final return value
- Test effect sequencing and conditional logic
- NO interpreters - we're testing program logic only

**When to use**: Testing program business logic without infrastructure.

**Do NOT**: Use interpreters or run_ws_program in program tests.

### Layer 4: Workflow Tests (Integration)

**Location**: `tests/test_integration/`

**Purpose**: Test complete end-to-end workflows with interpreters executing against mocked infrastructure.

**Pattern**: `run_ws_program()` with pytest-mock infrastructure.

```python
from functional_effects.programs.runners import run_ws_program
from functional_effects.interpreters.composite import CompositeInterpreter

@pytest.mark.asyncio()
async def test_complete_user_workflow(mocker: MockerFixture) -> None:
    """Complete workflow: get user, update profile, verify update."""
    # Arrange - Mock infrastructure
    user_id = uuid4()
    user = User(id=user_id, email="alice@example.com", name="Alice")
    updated_user = User(id=user_id, email="alice@example.com", name="Alice Updated")

    mock_user_repo = mocker.AsyncMock(spec=UserRepository)
    mock_user_repo.get_by_id.return_value = user
    mock_user_repo.update.return_value = updated_user

    # Create interpreter with mocked infrastructure
    db_interpreter = DatabaseInterpreter(user_repo=mock_user_repo)
    interpreter = CompositeInterpreter(interpreters=[db_interpreter])

    # Define workflow program
    def update_user_workflow() -> Generator[AllEffects, EffectResult, User]:
        """Get user, update name, return updated user."""
        # Get existing user
        user_result = yield GetUserById(user_id=user_id)
        assert isinstance(user_result, User)

        # Update user name
        updated_result = yield UpdateUser(
            user_id=user_id,
            name="Alice Updated"
        )
        assert isinstance(updated_result, User)

        return updated_result

    # Act - Run complete workflow
    result = await run_ws_program(update_user_workflow(), interpreter)

    # Assert - Verify final result
    match result:
        case Ok(final_user):
            assert final_user.name == "Alice Updated"
            # Verify all infrastructure calls
            mock_user_repo.get_by_id.assert_awaited_once_with(user_id)
            mock_user_repo.update.assert_awaited_once()
        case Err(error):
            pytest.fail(f"Expected Ok(user), got Err({error})")
```

**Key points**:
- Use `run_ws_program(program(), interpreter)` - it handles all generator iteration
- Create interpreters with mocked infrastructure (pytest-mock with spec)
- Test complete multi-effect workflows
- Verify all mock interactions
- Test both success and error propagation paths

**When to use**: Testing complete business scenarios that compose multiple effects.

**Do NOT**: Manually step through generators (no `next()`/`gen.send()`) - let `run_ws_program` do it.

## Pattern Decision Tree

```
What are you testing?
│
├─ Effect dataclass structure?
│  └─ Use Layer 1: Effect Tests
│     - Simple instantiation
│     - No mocks, no async
│
├─ Interpreter execution logic?
│  └─ Use Layer 2: Interpreter Tests
│     - await interpreter.interpret(effect)
│     - Mock infrastructure with pytest-mock
│     - Verify Result types
│
├─ Program sequencing/logic?
│  └─ Use Layer 3: Program Tests
│     - Manual generator stepping (next/send)
│     - Mock effect results
│     - No interpreters
│
└─ Complete workflow integration?
   └─ Use Layer 4: Workflow Tests
      - run_ws_program(program(), interpreter)
      - Mock infrastructure
      - Verify end-to-end behavior
```

## Complete Examples

### Example 1: Testing a New Database Effect

**Step 1: Effect Test** (`tests/test_effects/test_database_effects.py`)
```python
def test_delete_user_effect():
    """DeleteUser effect should be immutable."""
    user_id = uuid4()
    effect = DeleteUser(user_id=user_id)

    assert effect.user_id == user_id
    with pytest.raises(FrozenInstanceError):
        effect.user_id = uuid4()
```

**Step 2: Interpreter Test** (`tests/test_interpreters/test_database.py`)
```python
@pytest.mark.asyncio()
async def test_delete_user_success(mocker: MockerFixture) -> None:
    """DeleteUser should return Ok(None) on success."""
    mock_repo = mocker.AsyncMock(spec=UserRepository)
    mock_repo.delete.return_value = None

    interpreter = DatabaseInterpreter(user_repo=mock_repo)
    effect = DeleteUser(user_id=uuid4())

    result = await interpreter.interpret(effect)

    match result:
        case Ok(EffectReturn(value=None, effect_name="DeleteUser")):
            assert True  # Expected
        case _:
            pytest.fail(f"Expected Ok(None), got {result}")
```

**Step 3: Program Test** (`tests/test_demo/test_user_programs.py`)
```python
def test_delete_user_program():
    """Program should verify user exists before deleting."""
    user_id = uuid4()
    user = User(id=user_id, email="alice@example.com", name="Alice")

    gen = delete_user_program(user_id=user_id)

    # Step 1: Verify user exists
    effect1 = next(gen)
    assert effect1.__class__.__name__ == "GetUserById"

    # Step 2: Delete user
    effect2 = gen.send(user)
    assert effect2.__class__.__name__ == "DeleteUser"

    # Step 3: Program completes
    try:
        gen.send(None)
        pytest.fail("Expected StopIteration")
    except StopIteration as e:
        assert e.value == Ok(None)
```

**Step 4: Workflow Test** (`tests/test_integration/test_user_workflow.py`)
```python
@pytest.mark.asyncio()
async def test_delete_user_workflow(mocker: MockerFixture) -> None:
    """Complete delete workflow: verify exists, delete, verify deleted."""
    user_id = uuid4()
    user = User(id=user_id, email="alice@example.com", name="Alice")

    mock_repo = mocker.AsyncMock(spec=UserRepository)
    mock_repo.get_by_id.side_effect = [user, None]  # Exists, then deleted
    mock_repo.delete.return_value = None

    interpreter = DatabaseInterpreter(user_repo=mock_repo)

    def delete_workflow():
        user_result = yield GetUserById(user_id=user_id)
        yield DeleteUser(user_id=user_id)
        verify_result = yield GetUserById(user_id=user_id)
        return verify_result is None  # Should be deleted

    result = await run_ws_program(delete_workflow(), interpreter)

    match result:
        case Ok(True):
            mock_repo.delete.assert_awaited_once_with(user_id)
        case _:
            pytest.fail(f"Expected Ok(True), got {result}")
```

## Common Pitfalls

### Pitfall 1: Manual Iterator Loops in Workflow Tests ❌

**WRONG - Causes infinite loops:**
```python
# ❌ DO NOT DO THIS IN WORKFLOW TESTS
gen = my_program()
result = await interpreter.interpret(next(gen))

while True:  # This can hang indefinitely!
    try:
        match result:
            case Ok(EffectReturn(value=value)):
                result = await interpreter.interpret(gen.send(value))
            case Err(error):
                pytest.fail(f"Error: {error}")
    except StopIteration as e:
        final_result = e.value
        break
```

**Correct - Use run_ws_program:**
```python
# ✅ CORRECT - Let the runner handle iteration
result = await run_ws_program(my_program(), interpreter)
match result:
    case Ok(value): ...
    case Err(error): ...
```

**Why**: The manual loop doesn't handle all edge cases (generators that don't raise StopIteration, errors in pattern matching, etc.). The runner is battle-tested and handles all cases correctly.

### Pitfall 2: Using Interpreters in Program Tests ❌

**WRONG:**
```python
# ❌ DO NOT DO THIS IN PROGRAM TESTS
def test_user_program(mocker: MockerFixture):
    mock_repo = mocker.AsyncMock(spec=UserRepository)
    interpreter = DatabaseInterpreter(user_repo=mock_repo)  # Don't use interpreter!
    result = await run_ws_program(get_user_program(), interpreter)
```

**Correct:**
```python
# ✅ CORRECT - Manual stepping, no interpreter
def test_user_program():
    gen = get_user_program(user_id=uuid4())
    effect = next(gen)
    # Test effect sequencing, not execution
```

**Why**: Program tests should focus on business logic (effect sequencing, conditionals, data transformations), not infrastructure execution.

### Pitfall 3: Missing spec Parameter in Mocks ❌

**WRONG:**
```python
# ❌ NO TYPE SAFETY - Catches nothing at test time
mock_repo = mocker.AsyncMock()  # No spec!
mock_repo.get_user.return_value = user  # Typo: should be get_by_id
```

**Correct:**
```python
# ✅ TYPE SAFE - Fails if method doesn't exist
mock_repo = mocker.AsyncMock(spec=UserRepository)
mock_repo.get_by_id.return_value = user
```

**Why**: The `spec` parameter ensures mocks match the actual interface, catching typos and interface changes at test time.

### Pitfall 4: Not Testing Error Paths ❌

**WRONG:**
```python
# ❌ ONLY TESTS SUCCESS PATH
@pytest.mark.asyncio()
async def test_get_user(mocker: MockerFixture):
    mock_repo = mocker.AsyncMock(spec=UserRepository)
    mock_repo.get_by_id.return_value = user
    # ... only tests when user exists
```

**Correct:**
```python
# ✅ TESTS BOTH PATHS
@pytest.mark.asyncio()
async def test_get_user_success(mocker: MockerFixture):
    # Test success case
    pass

@pytest.mark.asyncio()
async def test_get_user_not_found(mocker: MockerFixture):
    mock_repo = mocker.AsyncMock(spec=UserRepository)
    mock_repo.get_by_id.return_value = None
    # Test error case
    pass
```

**Why**: Effect systems make error handling explicit via Result types. Both `Ok` and `Err` paths must be tested.

### Pitfall 5: Using pytest.skip() ❌

**WRONG:**
```python
# ❌ FORBIDDEN - Hides incomplete implementation
@pytest.mark.skip(reason="Not implemented yet")
def test_complex_workflow():
    pass
```

**Correct:**
```python
# ✅ EITHER IMPLEMENT OR DELETE
def test_complex_workflow():
    # Implement the test
    pass
```

**Why**: Skipped tests create false confidence. Either implement the test or delete it until you're ready to implement.

## Migration Guide

### From Fake-Based Testing to pytest-mock

**Before (with fakes):**
```python
from functional_effects.testing import FakeUserRepository

def test_with_fake():
    fake_repo = FakeUserRepository()
    fake_repo.add_user(user)
    interpreter = DatabaseInterpreter(user_repo=fake_repo)
```

**After (with pytest-mock):**
```python
from pytest_mock import MockerFixture

def test_with_mock(mocker: MockerFixture):
    mock_repo = mocker.AsyncMock(spec=UserRepository)
    mock_repo.get_by_id.return_value = user
    interpreter = DatabaseInterpreter(user_repo=mock_repo)
```

### From Manual Stepping to run_ws_program

**Before (manual iteration):**
```python
gen = my_program()
result = await interpreter.interpret(next(gen))
while True:
    try:
        match result:
            case Ok(EffectReturn(value=v)):
                result = await interpreter.interpret(gen.send(v))
            case Err(e):
                break
    except StopIteration as e:
        final_result = e.value
        break
```

**After (use runner):**
```python
result = await run_ws_program(my_program(), interpreter)
match result:
    case Ok(value): ...
    case Err(error): ...
```

## Summary

**Four layers, four patterns**:
1. **Effects**: Simple instantiation tests
2. **Interpreters**: Direct calls with pytest-mock
3. **Programs**: Manual generator stepping (next/send)
4. **Workflows**: run_ws_program with interpreters

**Golden rules**:
- ✅ Use `spec` parameter for type safety
- ✅ Test both Ok and Err paths
- ✅ Use `run_ws_program` for workflow tests
- ✅ Manual stepping only for program tests
- ❌ Never use pytest.skip()
- ❌ Never use manual loops in workflow tests
- ❌ Never use interpreters in program tests

Following these patterns ensures consistent, maintainable, and type-safe tests across the entire functional-effects library.
