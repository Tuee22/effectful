# Effect Runners: The Proof Boundary Edge

**Status**: Authoritative source
**Supersedes**: none
**Referenced by**: architecture.md, dsl/intro.md, boundary_model.md, effect_patterns.md

> **Purpose**: Define the contract for effect runners—the Rust code that bridges the purity boundary (Haskell effect descriptions) and the outside world (drivers, APIs, hardware).

______________________________________________________________________

## SSoT Link Map

| Need               | Link                                              |
| ------------------ | ------------------------------------------------- |
| Effectful overview | [Effectful DSL Hub](../dsl/intro.md)              |
| Boundary model     | [Boundary Model](boundary_model.md)               |
| Standard effects   | [Standard Effects](standard_effects.md)           |
| Effect patterns    | [Effect Patterns](effect_patterns.md)             |
| Verification       | [Verification Contract](verification_contract.md) |

______________________________________________________________________

## 1. Runner Contract

### 1.1 The Core Principle

**One impure function per effect type**:

```rust
// example code
fn run_effect(effect: EffectType) -> Result<OkT, ErrT>
```

This is the ONLY pattern for effect runners.

### 1.2 Contract Requirements

| Requirement              | Description                             |
| ------------------------ | --------------------------------------- |
| **Single input**         | The pure effect value only              |
| **Result output**        | Always returns `Result<OkT, ErrT>`      |
| **No exceptions**        | All failures are typed errors           |
| **No panics**            | Runner never panics in normal operation |
| **Bounded time**         | Runner has configurable timeout         |
| **Dependency injection** | External deps injected at construction  |

### 1.3 Anti-Patterns

| Anti-Pattern        | Problem                          | Fix                         |
| ------------------- | -------------------------------- | --------------------------- |
| Multiple parameters | Breaks pure effect interface     | Bundle into effect type     |
| Returning Option    | Hides error information          | Use Result with typed error |
| Throwing exceptions | Caller can't handle exhaustively | Convert to Result           |
| Panicking           | Process dies                     | Return error variant        |
| Unbounded execution | May hang forever                 | Add timeout                 |
| Global state        | Non-deterministic                | Inject dependencies         |

______________________________________________________________________

## 2. Runner Structure

### 2.1 Anatomy of a Runner

```rust
// example code
pub struct DbRunner {
    // Dependencies injected at construction
    pool: Pool,
    timeout: Duration,
}

impl DbRunner {
    // Constructor receives dependencies
    pub fn new(pool: Pool, timeout: Duration) -> Self {
        Self { pool, timeout }
    }

    // Runner function: pure effect in, Result out
    pub async fn run(&self, effect: DbQuery) -> Result<DbRows, DbError> {
        // Timeout enforcement
        tokio::time::timeout(self.timeout, async {
            // Execute effect
            let rows = self.pool
                .query(&effect.sql, &effect.params)
                .await
                // Convert driver errors to typed errors
                .map_err(classify_db_error)?;

            Ok(to_db_rows(rows))
        })
        .await
        .map_err(|_| DbError::Timeout)?
    }
}
```

### 2.2 Key Components

| Component            | Purpose                                    |
| -------------------- | ------------------------------------------ |
| **Struct**           | Holds injected dependencies                |
| **Constructor**      | Receives dependencies, returns runner      |
| **Run method**       | Takes effect, returns Result               |
| **Timeout wrapper**  | Ensures bounded execution                  |
| **Error classifier** | Converts external errors to typed variants |

______________________________________________________________________

## 3. Effect Input

### 3.1 Pure Effect Values

Effect inputs are pure data:

```rust
#[derive(Debug, Clone)]
pub struct DbQuery {
    pub sql: String,
    pub params: Vec<Value>,
    pub mode: QueryMode,
}

#[derive(Debug, Clone)]
pub enum QueryMode {
    One,    // Expect exactly one row
    Many,   // Expect zero or more rows
    Exec,   // Execute, don't return rows
}
```

### 3.2 Effect Design Rules

| Rule               | Rationale                             |
| ------------------ | ------------------------------------- |
| **Immutable**      | Can be inspected without side effects |
| **Clone-able**     | Can be passed to multiple consumers   |
| **Debug-able**     | Can be logged for debugging           |
| **Serializable**   | Can be transmitted across processes   |
| **Self-contained** | No references to external state       |

______________________________________________________________________

## 4. Result Output

### 4.1 Result Type

Runners always return `Result<OkT, ErrT>`:

```rust
// Success type: domain-specific
pub struct DbRows {
    pub columns: Vec<String>,
    pub rows: Vec<Vec<Value>>,
}

// Error type: exhaustive ADT
pub enum DbError {
    NotFound,
    Conflict,
    Constraint(String),
    Timeout,
    Connection(String),
    Unknown(String),
}
```

### 4.2 Error Type Requirements

| Requirement      | Description                                 |
| ---------------- | ------------------------------------------- |
| **Exhaustive**   | Covers all possible failures                |
| **Typed**        | Each variant has specific meaning           |
| **Informative**  | Contains enough detail for handling         |
| **No panic**     | Even "impossible" states are error variants |
| **Serializable** | Can be returned to caller                   |

______________________________________________________________________

## 5. Dependency Injection

### 5.1 What Gets Injected

| Dependency Type          | Examples                      |
| ------------------------ | ----------------------------- |
| **Connection pools**     | Database, Redis, HTTP clients |
| **Configuration**        | Timeouts, retry policies      |
| **Credentials**          | API keys, certificates        |
| **Mock implementations** | For testing                   |

### 5.2 Injection Pattern

```rust
// Production
let db_runner = DbRunner::new(
    production_pool,
    Duration::from_secs(30),
);

// Testing
let db_runner = DbRunner::new(
    mock_pool,
    Duration::from_secs(1),
);

// Both use the same run() interface
let result = db_runner.run(query).await;
```

### 5.3 Injection Benefits

| Benefit       | How Achieved              |
| ------------- | ------------------------- |
| Testability   | Inject mocks              |
| Flexibility   | Swap implementations      |
| Configuration | Inject different settings |
| Isolation     | Each runner has own deps  |

______________________________________________________________________

## 6. Error Handling

### 6.1 Error Conversion

Runners are the ONLY place where exceptions become typed errors:

```rust
// example code
impl DbRunner {
    fn classify_error(e: DriverError) -> DbError {
        match e.code() {
            "23505" => DbError::Conflict,
            "23503" => DbError::Constraint(e.message()),
            "57014" => DbError::Timeout,
            "08006" => DbError::Connection(e.message()),
            _ if e.is_not_found() => DbError::NotFound,
            _ => DbError::Unknown(e.to_string()),
        }
    }
}
```

### 6.2 Error Conversion Rules

| Rule                      | Rationale                         |
| ------------------------- | --------------------------------- |
| **Classify by semantics** | Map to domain-meaningful errors   |
| **Preserve information**  | Include details in error variants |
| **Never lose errors**     | Unknown case catches everything   |
| **Never panic**           | Even unexpected errors are typed  |

______________________________________________________________________

## 7. Timeout Enforcement

### 7.1 Why Timeouts Are Mandatory

Runners must not hang forever:

- Network calls may never return
- Database queries may lock
- External services may be down
- Deadlocks may occur

### 7.2 Timeout Pattern

```rust
// example code
pub async fn run(&self, effect: Effect) -> Result<T, Error> {
    tokio::time::timeout(self.timeout, self.execute(effect))
        .await
        .map_err(|_| Error::Timeout)?
}

async fn execute(&self, effect: Effect) -> Result<T, Error> {
    // Actual execution without timeout wrapper
}
```

### 7.3 Timeout Configuration

| Context         | Typical Timeout |
| --------------- | --------------- |
| Database query  | 30 seconds      |
| HTTP request    | 60 seconds      |
| File operation  | 10 seconds      |
| Cache operation | 1 second        |

______________________________________________________________________

## 8. Safe vs Unsafe Rust

### 8.1 Safe Rust by Default

All runners use safe Rust unless explicitly justified:

```rust
// Good: Safe Rust
pub async fn run(&self, effect: Effect) -> Result<T, Error> {
    let result = self.client.execute(effect).await?;
    Ok(result)
}
```

### 8.2 Unsafe Rust Policy

Unsafe is permitted only when:

1. Safe Rust cannot achieve required performance
1. The unsafe block is documented as an assumption
1. The code is reviewed and approved

### 8.3 Unsafe Documentation

````rust
// ASSUMPTION: GPU driver correctly implements CUDA memcpy
// DEPENDS ON: CUDA driver version >= 12.0
// TLA+ PROPERTY: MemcpyPreservesData
// FAILURE MODE: Silent data corruption
// MITIGATION: Checksum validation on critical paths
unsafe {
    cuda_memcpy(dst, src, len);
}
```text

---

## 9. Testing Runners

### 9.1 Unit Testing

Mock dependencies for isolation:

```rust
#[test]
async fn test_db_runner_success() {
    let mock_pool = MockPool::returning(vec![row1, row2]);
    let runner = DbRunner::new(mock_pool, Duration::from_secs(1));

    let result = runner.run(query).await;

    assert!(result.is_ok());
    assert_eq!(result.unwrap().rows.len(), 2);
}
````

### 9.2 Integration Testing

Test against real dependencies:

```rust
#[test]
async fn test_db_runner_integration() {
    let pool = create_test_pool().await;
    let runner = DbRunner::new(pool, Duration::from_secs(30));

    let result = runner.run(query).await;

    assert!(result.is_ok());
}
```

### 9.3 Property Testing

Test error handling exhaustively:

````rust
#[proptest]
fn test_error_classification(error_code: String) {
    let db_error = DbRunner::classify_error(mock_error(error_code));
    // All codes must map to some variant
    assert!(matches!(db_error, DbError::NotFound | DbError::Conflict | ...));
}
```text

---

## 10. Runner Lifecycle

### 10.1 Creation

```rust
// Create once at startup
let runner = DbRunner::new(pool, timeout);
````

### 10.2 Use

```rust
// Use many times
for effect in effects {
    let result = runner.run(effect).await;
    handle_result(result)?;
}
```

### 10.3 Cleanup

````rust
// Cleanup happens through dependency Drop
// Runner struct has no cleanup logic
drop(runner);
```text

---

## 11. Runner Registry

### 11.1 Central Registration

```rust
pub struct RunnerRegistry {
    db: DbRunner,
    http: HttpRunner,
    cache: CacheRunner,
    // ...
}

impl RunnerRegistry {
    pub async fn run(&self, effect: Effect) -> Result<Value, Error> {
        match effect {
            Effect::Db(e) => self.db.run(e).await.map(Value::from),
            Effect::Http(e) => self.http.run(e).await.map(Value::from),
            Effect::Cache(e) => self.cache.run(e).await.map(Value::from),
        }
    }
}
````

### 11.2 Registry Benefits

| Benefit                | Description                     |
| ---------------------- | ------------------------------- |
| Single dispatch point  | All effects go through registry |
| Uniform error handling | Consistent result wrapping      |
| Easy testing           | Swap entire registry            |
| Configuration          | All runners configured together |

______________________________________________________________________

## Cross-References

- [dsl/intro.md](../dsl/intro.md) — Effectful language overview
- [dsl/jit.md](../dsl/jit.md) — JIT-generated runners
- [boundary_model.md](boundary_model.md) — Where runners fit in architecture
- [standard_effects.md](standard_effects.md) — Standard effect types
- [effect_patterns.md](effect_patterns.md) — Effect composition patterns
- [verification_contract.md](verification_contract.md) — Runner conformance testing
