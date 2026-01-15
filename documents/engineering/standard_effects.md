# Standard Effect Library

**Status**: Authoritative source
**Supersedes**: none
**Referenced by**: dsl/intro.md, runner_pattern.md, effect_patterns.md

> **Purpose**: Document the language-agnostic standard effects that form the core interface between pure business logic and the impure world. Standard effects minimize the impure surface area while maximizing expressiveness.

______________________________________________________________________

## SSoT Link Map

| Need                  | Link                                  |
| --------------------- | ------------------------------------- |
| Effectful overview    | [Effectful DSL Hub](../dsl/intro.md)  |
| Runner implementation | [Runner Pattern](runner_pattern.md)   |
| Effect patterns       | [Effect Patterns](effect_patterns.md) |
| Boundary model        | [Boundary Model](boundary_model.md)   |

______________________________________________________________________

## 1. Why Standard Effects

### 1.1 The Core Principle

**Minimize the impure surface, maximize pure logic.**

Standard effects provide a small, well-defined interface to the outside world:

```typescript
// diagram
┌─────────────────────────────────────────────────────────────────────┐
│                    PURITY BOUNDARY                                   │
│  Pure business logic composes standard effects                       │
│  Effect descriptions are values, not actions                         │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ Standard effects
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    PROOF BOUNDARY                                    │
│  Small number of well-tested runners                                 │
│  Each runner implements one effect type                              │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.2 Benefits

| Benefit      | How Achieved                              |
| ------------ | ----------------------------------------- |
| Testability  | Mock standard effects, not infrastructure |
| Portability  | Same effects across platforms             |
| Verification | Small interface is tractable to verify    |
| Optimization | Optimizer can analyze effect patterns     |

______________________________________________________________________

## 2. Standard Effect Catalog

### 2.1 Database Effects

```haskell
-- Query execution
data DbQuery = DbQuery
  { sql    :: Text
  , params :: [Value]
  , mode   :: QueryMode
  }

data QueryMode = One | Many | Exec

-- Result types
data DbRows = DbRows
  { columns :: [Text]
  , rows    :: [[Value]]
  }

data DbError
  = NotFound
  | Conflict
  | Constraint Text
  | Timeout
  | Connection Text
  | Unknown Text
```

### 2.2 HTTP Effects

```haskell
-- HTTP request
data HttpRequest = HttpRequest
  { method    :: HttpMethod
  , url       :: Text
  , headers   :: [(Text, Text)]
  , body      :: Maybe ByteString
  , timeoutMs :: Int
  }

data HttpMethod = GET | POST | PUT | DELETE | PATCH

-- Response
data HttpResponse = HttpResponse
  { status  :: Int
  , headers :: [(Text, Text)]
  , body    :: ByteString
  }

data HttpError
  = NetworkFailure Text
  | Timeout
  | InvalidUrl Text
  | TlsError Text
```

### 2.3 Key-Value Store Effects

```haskell
-- Key-value operations
data KvGet = KvGet { key :: Text }
data KvSet = KvSet { key :: Text, value :: ByteString, ttlMs :: Maybe Int }
data KvDelete = KvDelete { key :: Text }

-- Results
data KvValue = KvValue ByteString | KvMissing

data KvError
  = ConnectionError Text
  | Timeout
  | QuotaExceeded
```

### 2.4 Time Effects

```haskell
-- Current time
data NowMs = NowMs

-- Result: milliseconds since epoch
type Timestamp = Int64
```

### 2.5 Randomness Effects

```haskell
-- Random bytes
data RandomBytes = RandomBytes { count :: Int }

-- Result: cryptographically secure random bytes
type Bytes = ByteString
```

### 2.6 Logging Effects

````haskell
-- Structured logging
data Log = Log
  { level   :: LogLevel
  , message :: Text
  , context :: [(Text, Value)]
  }

data LogLevel = Debug | Info | Warn | Error
```text

---

## 3. Effect Composition

### 3.1 Pure Composition

Effects compose purely:

```haskell
-- Compose database and cache
getUserCached :: UserId -> Program User
getUserCached uid = do
  cached <- yield $ KvGet { key = "user:" <> show uid }
  case cached of
    KvValue bytes -> pure (decode bytes)
    KvMissing -> do
      rows <- yield $ DbQuery
        { sql = "SELECT * FROM users WHERE id = ?"
        , params = [toValue uid]
        , mode = One
        }
      let user = rowToUser rows
      yield $ KvSet
        { key = "user:" <> show uid
        , value = encode user
        , ttlMs = Just 3600000
        }
      pure user
````

### 3.2 Repository Pattern

The repository pattern wraps standard effects with domain semantics:

````haskell
-- Domain-specific repository (pure)
class UserRepository where
  getUser :: UserId -> Program (Maybe User)
  saveUser :: User -> Program ()
  deleteUser :: UserId -> Program ()

-- Implementation using standard effects
instance UserRepository where
  getUser uid = do
    rows <- yield $ DbQuery
      { sql = "SELECT * FROM users WHERE id = ?"
      , params = [toValue uid]
      , mode = One
      }
    pure $ rowToUser <$> rows

  saveUser user = do
    yield $ DbQuery
      { sql = "INSERT INTO users ..."
      , params = userToParams user
      , mode = Exec
      }
    pure ()
```text

---

## 4. Domain Effects

### 4.1 When to Create Domain Effects

Domain effects extend standard effects for app-specific operations:

| Use Case | Standard Effect | Domain Effect |
|----------|-----------------|---------------|
| SQL query | `DbQuery` | - |
| Get user by email | `DbQuery` | `GetUserByEmail` |
| Complex transaction | Multiple `DbQuery` | `TransferFunds` |
| Third-party API | `HttpRequest` | `SendNotification` |

### 4.2 Domain Effect Rules

| Rule | Rationale |
|------|-----------|
| Built on standard effects | Reuse runners |
| Domain-specific types | Type safety |
| High-level semantics | Business meaning |
| Pure implementation | Testable |

### 4.3 Example: Payment Domain

```haskell
-- Domain effect
data ChargeCard = ChargeCard
  { card   :: CardToken
  , amount :: Money
  , idempotencyKey :: Text
  }

data ChargeResult
  = ChargeSucceeded ReceiptId
  | ChargeFailed PaymentError

-- Implementation in terms of standard effects
chargeCard :: ChargeCard -> Program ChargeResult
chargeCard charge = do
  response <- yield $ HttpRequest
    { method = POST
    , url = "https://payments.example.com/charge"
    , headers = [("Authorization", apiKey)]
    , body = Just (encode charge)
    , timeoutMs = 30000
    }
  case response.status of
    200 -> pure $ ChargeSucceeded (decode response.body)
    402 -> pure $ ChargeFailed PaymentDeclined
    _   -> pure $ ChargeFailed (UnexpectedError response)
```text

---

## 5. Effect Semantics

### 5.1 Language-Agnostic

Standard effects have the same semantics across all languages:

| Effect | Semantics |
|--------|-----------|
| `DbQuery sql params One` | Execute SQL, return exactly one row or NotFound |
| `DbQuery sql params Many` | Execute SQL, return zero or more rows |
| `DbQuery sql params Exec` | Execute SQL, return affected row count |
| `HttpRequest ...` | Execute HTTP request, return response |
| `KvGet key` | Read value at key, return value or missing |
| `KvSet key value ttl` | Write value at key with optional TTL |
| `NowMs` | Return current timestamp in milliseconds |
| `RandomBytes n` | Return n cryptographically secure random bytes |
| `Log level message ctx` | Write structured log entry |

### 5.2 Runner Contracts

Every runner must implement identical semantics:

```rust
// Rust runner
fn run_db_query(effect: DbQuery) -> Result<DbRows, DbError>

// Python runner (legacy)
async def run_db_query(effect: DbQuery) -> Result[DbRows, DbError]

// TypeScript runner (legacy)
async function runDbQuery(effect: DbQuery): Promise<Result<DbRows, DbError>>
```text

---

## 6. Testing Standard Effects

### 6.1 Mock Runners

For unit tests, use mock runners:

```haskell
-- Mock runner for testing
mockRunner :: Effect -> IO Result
mockRunner (DbQuery sql _ One) =
  if sql == "SELECT * FROM users WHERE id = ?"
    then pure $ Ok mockUserRow
    else pure $ Err NotFound

-- Test with mock
testGetUser = do
  result <- runWith mockRunner (getUser userId)
  assertEqual (Just expectedUser) result
````

### 6.2 Integration Tests

For integration tests, use real runners:

````haskell
-- example code
testGetUserIntegration = do
  -- Setup: insert test user
  runWith realRunner $ insertUser testUser

  -- Test: retrieve user
  result <- runWith realRunner $ getUser testUser.id

  -- Assert
  assertEqual (Just testUser) result

  -- Cleanup
  runWith realRunner $ deleteUser testUser.id
```text

---

## 7. Effect Optimization

### 7.1 Batching

The optimizer can batch similar effects:

```haskell
-- Before optimization: 3 separate queries
users <- sequence [getUser u1, getUser u2, getUser u3]

-- After optimization: 1 batch query
users <- getBatchUsers [u1, u2, u3]
````

### 7.2 Caching

The optimizer can insert caching:

```haskell
-- Original: always hits database
user <- getUser uid

-- Optimized: check cache first
user <- getUserCached uid
```

### 7.3 Parallelization

Independent effects can run in parallel:

```haskell
-- Sequential (unnecessary)
user <- getUser uid
settings <- getSettings uid
notifications <- getNotifications uid

-- Parallel (optimized)
(user, settings, notifications) <- parallel3
  (getUser uid)
  (getSettings uid)
  (getNotifications uid)
```

______________________________________________________________________

## 8. Adding New Standard Effects

### 8.1 Criteria

New standard effects must be:

| Criterion | Description                              |
| --------- | ---------------------------------------- |
| General   | Useful across many applications          |
| Minimal   | Cannot be composed from existing effects |
| Portable  | Implementable on all target platforms    |
| Testable  | Can be mocked without infrastructure     |

### 8.2 Process

1. Propose effect with rationale
1. Define types (effect, result, error)
1. Specify semantics precisely
1. Implement runners for all platforms
1. Add conformance tests
1. Document in this file

______________________________________________________________________

## Cross-References

- [dsl/intro.md](../dsl/intro.md) — Effectful language overview
- [runner_pattern.md](runner_pattern.md) — How to implement runners
- [effect_patterns.md](effect_patterns.md) — Effect composition patterns
- [boundary_model.md](boundary_model.md) — Where effects fit in architecture
- [verification_contract.md](verification_contract.md) — Testing effect semantics
