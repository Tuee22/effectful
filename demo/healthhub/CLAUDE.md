# Claude Code Patterns for HealthHub

## Project Overview

**HealthHub** is a comprehensive healthcare management portal demonstrating the **Effectful** pure functional effect system library. It showcases real-world complexity: patient management, appointment scheduling, prescriptions with medication interaction checking, lab results, and HIPAA-compliant audit logging.

**Parent Library**: This application is built on `effectful` (local path dependency at `../../`).

## 🏗️ Architecture

**Stack**: Python 3.12 | FastAPI | PostgreSQL | Redis | Apache Pulsar | MinIO S3 | Effectful Effect System

**5-Layer Architecture**:
```
Layer 1: Application (FastAPI routes, request handling)
    ↓
Layer 2: Program Runner (effect execution loop, generator protocol)
    ↓
Layer 3: Composite Interpreter (effect routing via pattern matching)
    ↓
Layer 4: Specialized Interpreters (HealthcareInterpreter, NotificationInterpreter)
    ↓
Layer 5: Infrastructure (PostgreSQL, Redis, Pulsar, MinIO)
```

**Key Patterns**:
- ✅ **Effect Programs**: Business logic as generators yielding immutable effect descriptions
- ✅ **ADT Authorization**: `PatientAuthorized | DoctorAuthorized | AdminAuthorized | Unauthorized`
- ✅ **State Machine**: Appointment status (Requested → Confirmed → InProgress → Completed)
- ✅ **Result Types**: Explicit error handling with `Ok[T] | Err[E]`
- ✅ **Immutability**: All domain models are frozen dataclasses

**Structure**:
- `backend/app/`: Main application
  - `domain/`: Healthcare domain models (Patient, Doctor, Appointment, Prescription, etc.)
  - `effects/`: Immutable effect descriptions (HealthcareEffect, NotificationEffect)
  - `interpreters/`: Effect handlers (execution layer)
  - `programs/`: Effect programs (pure business logic as generators)
  - `api/`: FastAPI routers
  - `auth/`: JWT authentication, bcrypt hashing
  - `repositories/`: asyncpg data access
  - `infrastructure/`: Database connection management
- `docker/`: Container configuration
- `tools/`: Build and test utilities
- `tests/`: Test suite (pytest/ backend and integration)
- `documents/`: Comprehensive documentation suite

## 📋 Command Reference

**Base pattern**: `docker compose -f docker/docker-compose.yml exec healthhub poetry run <command>`

| Task | Command |
|------|---------|
| Start services | `docker compose -f docker/docker-compose.yml up -d` |
| View logs | `docker compose -f docker/docker-compose.yml logs -f healthhub` |
| Check code quality | `docker compose -f docker/docker-compose.yml exec healthhub poetry run check-code` |
| Test all | `docker compose -f docker/docker-compose.yml exec healthhub poetry run test-all` |
| Test backend | `docker compose -f docker/docker-compose.yml exec healthhub poetry run test-backend` |
| Test integration | `docker compose -f docker/docker-compose.yml exec healthhub poetry run test-integration` |
| API server (dev) | `docker compose -f docker/docker-compose.yml exec healthhub poetry run api-dev` |
| Python shell | `docker compose -f docker/docker-compose.yml exec healthhub poetry run python` |
| Rebuild with frontend | `docker compose -f docker/docker-compose.yml build healthhub && docker compose -f docker/docker-compose.yml up -d` |

**With output capture**: Add `> /tmp/test-output.txt 2>&1` to any test command.

## 🐳 Docker Development Policy

**CRITICAL**: All development happens inside Docker containers. Poetry is configured to NOT create virtual environments via `poetry.toml`.

**Do NOT run `poetry install` locally** - it will fail.

See parent [Docker Doctrine](../../documents/core/docker_doctrine.md) for complete policy.

**Why Docker-Only**:
- Consistent environment (Python 3.12, PostgreSQL 15, Redis 7)
- Access to real infrastructure for integration tests
- Matches production environment
- No local Python version conflicts
- No virtualenv mismatches (enforced by `poetry.toml`)

## 📊 Test Statistics

| Category | Test Count | Duration | Infrastructure |
|----------|-----------|----------|----------------|
| Backend Unit | 100+ tests | ~0.5s | pytest-mock only |
| Integration | 24 tests | ~1.5s | Real PostgreSQL/Redis/Pulsar |
| **Full suite** | **124+ tests** | **~2s** | Mixed |

**Test Organization**:
- `tests/pytest/backend/` - Unit tests (pytest-mock, no I/O)
- `tests/pytest/integration/` - Integration tests (real infrastructure)

## ✅ Universal Success Criteria

All code changes must meet:
- ✅ Exit code 0 (all operations complete successfully)
- ✅ **Zero MyPy errors** (mypy --strict mandatory)
- ✅ Zero stderr output
- ✅ Zero console warnings/errors
- ✅ **Zero skipped tests** (pytest.skip() forbidden)
- ✅ 100% test pass rate
- ✅ **Zero `Any`, `cast()`, or `# type: ignore`** (escape hatches forbidden)

## 🐳 Docker Development

### Container Services

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| healthhub | Python 3.12 + Poetry | 8851 | FastAPI application + React frontend |
| postgres | postgres:15-alpine | 5433 | Patient/appointment data |
| redis | redis:7-alpine | 6380 | Notifications, cache |
| pulsar | apachepulsar/pulsar:3.0.0 | 6651 | Durable messaging |
| minio | minio/minio:latest | 9001 | S3-compatible storage |

### Named Volumes (Required)

- PostgreSQL: `healthhub_pgdata:/var/lib/postgresql/data`
- Redis: `healthhub_redisdata:/data`
- Remove with: `docker compose -f docker/docker-compose.yml down -v`

### Effectful Library Access

The Docker build makes the parent `effectful` library available:
- Build context: effectful root (`../../..`)
- Volume mount: `effectful` mounted read-only
- PYTHONPATH: Includes both effectful and healthhub

**Importing effectful in healthhub**:
```python
from effectful.algebraic.result import Ok, Err, Result
from effectful.domain.user import User
from effectful.effects.database import GetUserById
```

### Frontend Architecture

**Pattern**: FastAPI serves React frontend using StaticFiles mount.

**Build Process**:
- Frontend built during `docker build` step
- Output: `/opt/healthhub/frontend-build/build/`
- Served by FastAPI on port 8851

**Routing**:
- `/api/*` - API routes (FastAPI routers)
- `/static/*` - Static assets (JS, CSS, images)
- `/*` - React app (index.html served for client-side routing)

**Development Workflow**:
- **Backend changes**: Volume mounts enable hot reload (uvicorn --reload)
- **Frontend changes**: Rebuild Docker image OR run `npm run dev` locally at http://localhost:5173

**See also**: [documents/engineering/frontend_architecture.md](documents/engineering/frontend_architecture.md)

## 🧪 Testing Philosophy

**Core Principle**: Tests exist to find problems, not provide false confidence.

### Test Pyramid
```
        /\
       /  \      Integration (24) - Real PostgreSQL/Redis/Pulsar
      /----\
     /      \    Unit (100+) - pytest-mock only, no I/O
    /--------\
```

### Test Output Management

**CRITICAL**: Bash tool truncates at 30,000 chars.

**Required Pattern**:
```bash
docker compose -f docker/docker-compose.yml exec healthhub poetry run test-all > /tmp/test-output.txt 2>&1
# Then read /tmp/test-output.txt with Read tool
```

### Generator Testing Pattern

Effect programs are tested by stepping through the generator:
```python
def test_appointment_program() -> None:
    gen = schedule_appointment_program(patient_id, doctor_id, time)

    # Step 1: Expect GetPatientById effect
    effect1 = next(gen)
    assert isinstance(effect1, GetPatientById)

    # Send mock result, get next effect
    effect2 = gen.send(mock_patient)
    assert isinstance(effect2, GetDoctorById)

    # Continue until StopIteration with final result
```

## 🔍 Code Quality

**check-code**: Runs Black (formatter) → MyPy (strict type checker), fail-fast.

Must meet Universal Success Criteria.

## 🚫 Anti-Patterns

### Healthcare Domain Anti-Patterns

1. **String-Based Authorization** - ❌ `if user.role == "doctor"` | ✅ ADT pattern matching
2. **String-Based Status** - ❌ `appointment.status = "confirmed"` | ✅ ADT variants with context
3. **Missing Type Narrowing** - ❌ Using effect result without isinstance | ✅ Always narrow union types
4. **Direct Infrastructure Calls** - ❌ `await db.query(...)` in programs | ✅ Yield effects
5. **Unlogged PHI Access** - ❌ Accessing patient data without audit | ✅ Log every PHI access
6. **Success-Only Logging** - ❌ Only logging successful operations | ✅ Log all attempts
7. **Mutable Domain Models** - ❌ Dataclasses without frozen=True | ✅ All models immutable

### Test Anti-Patterns

8. **Real Infrastructure in Unit Tests** - ❌ Connecting to DB in unit tests | ✅ pytest-mock only
9. **Missing Error Path Tests** - ❌ Only testing happy path | ✅ Test all error cases
10. **Incomplete State Machine Tests** - ❌ Not testing all transitions | ✅ Full coverage
11. **Using pytest.skip()** - ❌ **NEVER** skip tests | ✅ Fix or delete
12. **Truncated Output Analysis** - ❌ Drawing conclusions from partial output | ✅ Read complete file

### Effect Program Anti-Patterns

13. **Silent Effect Failures** - ❌ Ignoring None results | ✅ Handle all cases
14. **Imperative Loops** - ❌ `for` loops in programs | ✅ Comprehensions/trampolines
15. **Missing Transition Validation** - ❌ Allowing invalid state changes | ✅ validate_transition()
16. **Blocking on Notification Failure** - ❌ Failing workflow on notification error | ✅ Fire-and-forget

## 🛡️ Type Safety

**Core Rules**:
- ❌ NO `Any`, `cast()`, `# type: ignore`
- ✅ All domain models: `@dataclass(frozen=True)`
- ✅ ADTs over Optional: `AuthorizationState = PatientAuthorized | ... | Unauthorized`
- ✅ Result type: `Result[Success, Error]` not exceptions
- ✅ Exhaustive pattern matching

**Config**: `strict = true`, `disallow_any_explicit = true`

## 🏥 Healthcare Domain

### Domain Models

| Model | Purpose |
|-------|---------|
| Patient | Demographics, medical history |
| Doctor | Credentials, specialization, can_prescribe flag |
| Appointment | Status (state machine), timestamps, notes |
| Prescription | Medications, dosage, interaction results |
| LabResult | Test results, critical value alerts |
| Invoice | Billing, line items, payment status |

### Authorization ADT

```python
type AuthorizationState = (
    PatientAuthorized    # user_id, patient_id, email, role="patient"
    | DoctorAuthorized   # user_id, doctor_id, email, specialization, can_prescribe
    | AdminAuthorized    # user_id, email, role="admin"
    | Unauthorized       # reason, detail
)
```

### Appointment State Machine

```
Requested → Confirmed → InProgress → Completed
    ↓           ↓           ↓
 Cancelled  Cancelled   Cancelled
```

## 🗄️ Database

**Schema**: `backend/scripts/init_db.sql` (9 tables with indexes)
**Demo Data**: `backend/scripts/seed_data.sql` (2 admins, 4 doctors, 5 patients)
**Reset**: `docker compose -f docker/docker-compose.yml down -v && docker compose -f docker/docker-compose.yml up -d`

## 🔒 Git Workflow Policy

**Critical Rule**: Claude Code is NOT authorized to commit or push changes.

- ❌ **NEVER** run `git commit`, `git push`, or `git add` followed by commit
- ✅ Make code changes, run tests, leave changes **uncommitted**
- ✅ User reviews with `git status`/`git diff`, then commits manually

## 🔧 Development Workflow

1. `docker compose -f docker/docker-compose.yml up -d`
2. Make code changes
3. `poetry run check-code`
4. `poetry run test-all`
5. Leave changes uncommitted

## 📊 Configuration

**Environment Variables**:
```bash
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=healthhub
POSTGRES_USER=healthhub
POSTGRES_PASSWORD=healthhub_pass

REDIS_HOST=redis
REDIS_PORT=6379

PULSAR_URL=pulsar://pulsar:6650

MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin

JWT_SECRET_KEY=healthhub-secret
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
```

## 🤝 Contributing Checklist

- [ ] `poetry run check-code` exits 0
- [ ] Tests for all features (unit + integration)
- [ ] No forbidden constructs (Any/cast/type:ignore)
- [ ] No anti-patterns (1-16)
- [ ] All dataclasses frozen (`frozen=True`)
- [ ] ADTs used instead of Optional for domain logic
- [ ] Result type used for all fallible operations
- [ ] Effect programs yield effects, don't call infrastructure
- [ ] HIPAA audit logging for PHI access
- [ ] Changes left uncommitted

## 📚 References

- **Parent Library**: `../../effectful/` (effectful effect system)
- **Documentation**: `documents/` (comprehensive 24-document suite)
- **API Reference**: `documents/product/api_reference.md`
- **Architecture**: `documents/product/architecture_overview.md`
- **Authorization**: `documents/product/authorization_system.md`
- **State Machine**: `documents/product/appointment_state_machine.md`

---

**Status**: Backend feature-complete | 3,948 LOC | 124+ tests passing
**Architecture**: Pure functional effect system demonstrating effectful library
**Philosophy**: Make invalid states unrepresentable through the type system
