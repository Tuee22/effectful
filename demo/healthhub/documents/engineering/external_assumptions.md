# HealthHub External Service Assumptions

**Status**: Authoritative source
**Supersedes**: none
**Referenced by**: boundary_map.md

> **Purpose**: Document all assumptions about external services that HealthHub depends on. These assumptions live outside the proof boundary and can never be formally verified. TLA+ proofs and runtime behavior depend on these assumptions being correct.
> **📖 Base Standard**: [external_assumptions.md](../../../../documents/engineering/external_assumptions.md)

______________________________________________________________________

## SSoT Link Map

| Need                   | Link                                                                  |
| ---------------------- | --------------------------------------------------------------------- |
| Boundary model         | [Boundary Model](../../../../documents/engineering/boundary_model.md) |
| HealthHub boundary map | [Boundary Map](boundary_map.md)                                       |
| Docker configuration   | [Docker](docker.md)                                                   |

______________________________________________________________________

## Deltas

This document extends the base external_assumptions.md with HealthHub's specific service assumptions inventory.

______________________________________________________________________

## 1. Assumption Documentation Format

Each external service assumption follows this template:

```python
# assumption template
ASSUMPTION: [What we assume about the service]
DEPENDS ON: [Version requirements]
TLA+ PROPERTY: [Which TLA+ properties depend on this assumption]
FAILURE MODE: [What happens if assumption is violated]
MITIGATION: [How we detect or recover from failures]
```

______________________________________________________________________

## 2. PostgreSQL Assumptions

### 2.1 SQL Semantics

```text
ASSUMPTION: PostgreSQL implements SQL semantics correctly
DEPENDS ON: PostgreSQL 15+
TLA+ PROPERTY: DataConsistency, TransactionIsolation
FAILURE MODE: Data corruption, constraint violations, incorrect query results
MITIGATION: Integration tests validate expected behavior; database health checks
```

### 2.2 ACID Guarantees

```text
ASSUMPTION: PostgreSQL transactions provide ACID guarantees
DEPENDS ON: PostgreSQL 15+ with default isolation level (READ COMMITTED)
TLA+ PROPERTY: AtomicOperations, DurableWrites
FAILURE MODE: Partial writes, phantom reads, lost updates
MITIGATION: Explicit transaction boundaries; idempotent operations where possible
```

### 2.3 SQL Parameterization

```text
ASSUMPTION: asyncpg parameterized queries prevent SQL injection
DEPENDS ON: asyncpg 0.27+
TLA+ PROPERTY: N/A (security property, not modeled in TLA+)
FAILURE MODE: SQL injection vulnerability
MITIGATION: All queries use parameterized statements; no string interpolation
```

### 2.4 Connection Pool

```text
ASSUMPTION: asyncpg connection pool handles transient connection failures
DEPENDS ON: asyncpg 0.27+ with pool configuration
TLA+ PROPERTY: ServiceAvailability
FAILURE MODE: Connection exhaustion, stale connections
MITIGATION: Pool health checks; bounded pool size; connection timeouts
```

______________________________________________________________________

## 3. Redis Assumptions

### 3.1 Pub/Sub Delivery

```text
ASSUMPTION: Redis pub/sub delivers messages at-most-once to connected subscribers
DEPENDS ON: Redis 7+
TLA+ PROPERTY: NotificationDelivery (eventual, not guaranteed)
FAILURE MODE: Message loss if subscriber disconnected
MITIGATION: Audit log provides durable fallback; notifications are non-critical
```

### 3.2 Cache Semantics

```text
ASSUMPTION: Redis GET/SET operations are atomic
DEPENDS ON: Redis 7+
TLA+ PROPERTY: CacheConsistency
FAILURE MODE: Race conditions in read-modify-write patterns
MITIGATION: Use Redis atomic commands (SETNX, INCR); avoid patterns requiring multi-command atomicity
```

### 3.3 TTL Behavior

```text
ASSUMPTION: Redis TTL expires keys at approximately the specified time
DEPENDS ON: Redis 7+
TLA+ PROPERTY: SessionExpiry (eventual)
FAILURE MODE: Keys may persist slightly longer than TTL; clock skew
MITIGATION: Do not rely on exact TTL timing; treat as "at least" not "exactly"
```

______________________________________________________________________

## 4. Apache Pulsar Assumptions

### 4.1 Message Delivery

```text
ASSUMPTION: Pulsar provides at-least-once delivery with acknowledgment
DEPENDS ON: Apache Pulsar 3.0+
TLA+ PROPERTY: DurableMessageDelivery
FAILURE MODE: Duplicate messages (expected); message loss (unexpected)
MITIGATION: Idempotent consumers; deduplication by message ID
```

### 4.2 Ordering Guarantees

```text
ASSUMPTION: Pulsar preserves message ordering within a partition
DEPENDS ON: Apache Pulsar 3.0+ with single-partition topics
TLA+ PROPERTY: MessageOrdering (per-partition)
FAILURE MODE: Out-of-order processing
MITIGATION: Use single partition for ordering-sensitive topics; accept eventual consistency for others
```

### 4.3 Persistence

```text
ASSUMPTION: Pulsar persists acknowledged messages to configured retention
DEPENDS ON: Apache Pulsar 3.0+ with BookKeeper
TLA+ PROPERTY: MessageDurability
FAILURE MODE: Message loss on cluster failure
MITIGATION: Configure appropriate replication factor; async backup
```

______________________________________________________________________

## 5. MinIO/S3 Assumptions

### 5.1 S3 API Compatibility

```text
ASSUMPTION: MinIO implements AWS S3 API correctly
DEPENDS ON: MinIO latest
TLA+ PROPERTY: ObjectStorageSemantics
FAILURE MODE: API incompatibility, upload failures
MITIGATION: Integration tests against MinIO; fallback error handling
```

### 5.2 Object Durability

```text
ASSUMPTION: Uploaded objects are durable once PUT returns success
DEPENDS ON: MinIO with local storage
TLA+ PROPERTY: ObjectDurability
FAILURE MODE: Object loss, corruption
MITIGATION: Verify uploads with HEAD; retry on failure
```

### 5.3 Eventual Consistency

```text
ASSUMPTION: S3 listings may be eventually consistent
DEPENDS ON: MinIO behavior (stronger than AWS S3)
TLA+ PROPERTY: N/A (consistency model varies)
FAILURE MODE: Recently uploaded objects may not appear in LIST
MITIGATION: Do not rely on LIST for verification; use direct GET
```

______________________________________________________________________

## 6. FastAPI/Starlette Assumptions

### 6.1 Request Handling

```text
ASSUMPTION: FastAPI correctly routes requests to handlers
DEPENDS ON: FastAPI 0.100+, Starlette 0.27+
TLA+ PROPERTY: RequestRouting
FAILURE MODE: Misrouted requests, handler not invoked
MITIGATION: Integration tests for all endpoints
```

### 6.2 Dependency Injection

```text
ASSUMPTION: FastAPI Depends() provides correct instances per-request
DEPENDS ON: FastAPI 0.100+
TLA+ PROPERTY: N/A (framework behavior)
FAILURE MODE: Wrong dependency injected, stale instance
MITIGATION: Explicit typing; integration tests
```

### 6.3 ASGI Lifecycle

```text
ASSUMPTION: ASGI lifespan events fire correctly
DEPENDS ON: Uvicorn 0.22+, Starlette 0.27+
TLA+ PROPERTY: ServiceLifecycle
FAILURE MODE: Resources not initialized/cleaned up
MITIGATION: Health checks verify initialization; graceful shutdown
```

______________________________________________________________________

## 7. Cryptographic Assumptions

### 7.1 JWT Signing

```text
ASSUMPTION: PyJWT correctly implements JWT RS256/HS256 signing
DEPENDS ON: PyJWT 2.8+
TLA+ PROPERTY: TokenIntegrity
FAILURE MODE: Invalid signatures accepted, valid signatures rejected
MITIGATION: Unit tests with known test vectors; library version pinning
```

### 7.2 Password Hashing

```text
ASSUMPTION: bcrypt provides secure password hashing with work factor 12
DEPENDS ON: bcrypt 4.0+
TLA+ PROPERTY: PasswordSecurity (not formally modeled)
FAILURE MODE: Weak hashes, timing attacks
MITIGATION: Use constant-time comparison; adequate work factor
```

______________________________________________________________________

## 8. Python Runtime Assumptions

### 8.1 asyncio Event Loop

```text
ASSUMPTION: asyncio correctly schedules coroutines
DEPENDS ON: Python 3 (Ubuntu 24.04 system Python via apt)
TLA+ PROPERTY: ConcurrencyModel
FAILURE MODE: Deadlocks, race conditions, starvation
MITIGATION: Avoid blocking calls in async code; use async primitives
```

### 8.2 Generator Protocol

```text
ASSUMPTION: Python generators correctly implement send/yield/return
DEPENDS ON: Python 3 (Ubuntu 24.04 system Python via apt)
TLA+ PROPERTY: EffectExecution
FAILURE MODE: Lost values, incorrect sequencing
MITIGATION: Core to effect system; extensively tested
```

### 8.3 Dataclass Semantics

```text
ASSUMPTION: frozen=True dataclasses are truly immutable
DEPENDS ON: Python 3 (Ubuntu 24.04 system Python via apt)
TLA+ PROPERTY: Immutability
FAILURE MODE: Mutation of "immutable" objects
MITIGATION: Use __slots__ where needed; avoid object.__setattr__ escapes
```

______________________________________________________________________

## 9. Network Assumptions

### 9.1 Docker Networking

```text
ASSUMPTION: Docker Compose networking provides reliable inter-container communication
DEPENDS ON: Docker Compose v2+
TLA+ PROPERTY: ServiceConnectivity
FAILURE MODE: DNS resolution failure, network partition
MITIGATION: Health checks; retry with backoff; circuit breakers
```

### 9.2 TCP Reliability

```text
ASSUMPTION: TCP provides reliable, ordered delivery
DEPENDS ON: OS TCP stack
TLA+ PROPERTY: ReliableTransport
FAILURE MODE: Connection drops, data corruption (extremely rare)
MITIGATION: Application-level acknowledgments; checksums
```

______________________________________________________________________

## 10. Assumption Validation Strategy

### 10.1 Integration Tests

Integration tests validate that assumptions hold in the test environment:

| Assumption Category | Test Location                                    | Frequency    |
| ------------------- | ------------------------------------------------ | ------------ |
| PostgreSQL          | `tests/pytest/integration/test_repositories.py`  | Every CI run |
| Redis               | `tests/pytest/integration/test_notifications.py` | Every CI run |
| Pulsar              | `tests/pytest/integration/test_messaging.py`     | Every CI run |
| FastAPI             | `tests/pytest/integration/test_api.py`           | Every CI run |

### 10.2 Production Monitoring

| Assumption      | Monitoring Approach          |
| --------------- | ---------------------------- |
| Database ACID   | Transaction rollback metrics |
| Redis pub/sub   | Message delivery lag         |
| Pulsar delivery | Consumer lag, retry counts   |
| S3 durability   | Upload success rates         |

### 10.3 Assumption Violation Response

When an assumption is violated in production:

1. **Detect**: Monitoring alerts on anomaly
1. **Classify**: Is this assumption violation or application bug?
1. **Mitigate**: Apply documented mitigation
1. **Document**: Update assumption documentation if behavior differs from expectation
1. **Escalate**: If mitigation fails, escalate to infrastructure team

______________________________________________________________________

## Cross-References

- [Boundary Model](../../../../documents/engineering/boundary_model.md) - Assumption documentation requirements
- [Boundary Map](boundary_map.md) - Component-to-boundary mapping
- [Verification Strategy](verification_strategy.md) - How testing maps to verification
- [Docker Configuration](docker.md) - Service versions and configuration
