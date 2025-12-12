# Claude Code Patterns for HealthHub

## Project Overview

**HealthHub** is a comprehensive healthcare management portal demonstrating the **Effectful** pure functional effect system library. It showcases real-world complexity: patient management, appointment scheduling, prescriptions with medication interaction checking, lab results, and HIPAA-compliant audit logging.

**Parent Library**: This application is built on `effectful` (local path dependency at `../../`).

## 🏗️ Architecture

> **📖 Base**: [Effectful CLAUDE.md](../../CLAUDE.md) | [Architecture SSoT](../../documents/engineering/architecture.md)

HealthHub follows the base effectful 5-layer architecture with healthcare-specific additions:

**HealthHub-Specific Stack**: FastAPI + PostgreSQL + Redis + Apache Pulsar + MinIO S3

**Specialized Layer 4 Interpreters**:

- `HealthcareInterpreter` - Patient/doctor/appointment/prescription operations
- `NotificationInterpreter` - HIPAA-compliant audit logging and notifications

**Healthcare Domain Patterns**:

- ADT Authorization: `PatientAuthorized | DoctorAuthorized | AdminAuthorized | Unauthorized`
- State Machine: Appointment status transitions (Requested → Confirmed → InProgress → Completed)
- HIPAA Compliance: Audit logging for all PHI access

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

> **📖 Base**: [Effectful CLAUDE.md](../../CLAUDE.md#quick-reference) | [Command Reference SSoT](../../documents/engineering/command_reference.md)

HealthHub commands follow the base pattern `docker compose -f docker/docker-compose.yml exec healthhub poetry run <command>`. HealthHub-specific additions: `test-backend`, `test-integration`, `api-dev` (FastAPI development server), and frontend rebuild. See [Command Reference](../../documents/engineering/command_reference.md) for complete table.

## 🐳 Docker Development Policy

> **📖 Base**: [Effectful CLAUDE.md](../../CLAUDE.md) | [Docker Workflow SSoT](../../documents/engineering/docker_workflow.md)

HealthHub follows base Docker-only policy. HealthHub-specific: requires real infrastructure services (PostgreSQL, Redis, Pulsar, MinIO) for integration tests. See [Docker Workflow](../../documents/engineering/docker_workflow.md) for complete policy.

## 📊 Test Statistics

| Category       | Test Count     | Duration | Infrastructure               |
| -------------- | -------------- | -------- | ---------------------------- |
| Backend Unit   | 100+ tests     | ~0.5s    | pytest-mock only             |
| Integration    | 24 tests       | ~1.5s    | Real PostgreSQL/Redis/Pulsar |
| **Full suite** | **124+ tests** | **~2s**  | Mixed                        |

**Test Organization**:

- `tests/pytest/backend/` - Unit tests (pytest-mock, no I/O)
- `tests/pytest/integration/` - Integration tests (real infrastructure)

## ✅ Universal Success Criteria

> **📖 Base**: [Effectful CLAUDE.md](../../CLAUDE.md#universal-success-criteria) | [Code Quality SSoT](../../documents/engineering/code_quality.md#universal-success-criteria)

HealthHub follows base Universal Success Criteria with no additional requirements. See [Code Quality](../../documents/engineering/code_quality.md#universal-success-criteria) for complete list.

## 🐳 Docker Development

### Container Services

| Service   | Image                     | Port | Purpose                              |
| --------- | ------------------------- | ---- | ------------------------------------ |
| healthhub | Python 3.12 + Poetry      | 8851 | FastAPI application + React frontend |
| postgres  | postgres:15-alpine        | 5433 | Patient/appointment data             |
| redis     | redis:7-alpine            | 6380 | Notifications, cache                 |
| pulsar    | apachepulsar/pulsar:3.0.0 | 6651 | Durable messaging                    |
| minio     | minio/minio:latest        | 9001 | S3-compatible storage                |

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

> **📖 Base**: [Effectful CLAUDE.md](../../CLAUDE.md#test-output-management-pattern) | [Command Reference SSoT](../../documents/engineering/command_reference.md#test-output-management)

HealthHub follows base test output management pattern. Always redirect to `/tmp/test-output.txt 2>&1` and read complete file. See [Command Reference](../../documents/engineering/command_reference.md#test-output-management) for complete pattern.

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
1. **String-Based Status** - ❌ `appointment.status = "confirmed"` | ✅ ADT variants with context
1. **Missing Type Narrowing** - ❌ Using effect result without isinstance | ✅ Always narrow union types
1. **Direct Infrastructure Calls** - ❌ `await db.query(...)` in programs | ✅ Yield effects
1. **Unlogged PHI Access** - ❌ Accessing patient data without audit | ✅ Log every PHI access
1. **Success-Only Logging** - ❌ Only logging successful operations | ✅ Log all attempts
1. **Mutable Domain Models** - ❌ Dataclasses without frozen=True | ✅ All models immutable

### Test Anti-Patterns

8. **Real Infrastructure in Unit Tests** - ❌ Connecting to DB in unit tests | ✅ pytest-mock only
1. **Missing Error Path Tests** - ❌ Only testing happy path | ✅ Test all error cases
1. **Incomplete State Machine Tests** - ❌ Not testing all transitions | ✅ Full coverage
1. **Using pytest.skip()** - ❌ **NEVER** skip tests | ✅ Fix or delete
1. **Truncated Output Analysis** - ❌ Drawing conclusions from partial output | ✅ Read complete file

### Effect Program Anti-Patterns

13. **Silent Effect Failures** - ❌ Ignoring None results | ✅ Handle all cases
01. **Imperative Loops** - ❌ `for` loops in programs | ✅ Comprehensions/trampolines
01. **Missing Transition Validation** - ❌ Allowing invalid state changes | ✅ validate_transition()
01. **Blocking on Notification Failure** - ❌ Failing workflow on notification error | ✅ Fire-and-forget

### API Layer Anti-Patterns

17. **Inline Interpreter Construction** - ❌ Manually creating db_manager, pool, redis_client, observability_interpreter, base_interpreter, and AuditedCompositeInterpreter in each endpoint | ✅ Use `Depends(get_audited_composite_interpreter)` dependency injection

### Configuration Anti-Patterns

> **📖 See**: [Configuration Lifecycle Management (Doctrine 7)](../../documents/engineering/code_quality.md#doctrine-7-configuration-lifecycle-management)

18. **Module-Level Settings Singleton** - ❌ `settings = Settings()` at module level | ✅ Create Settings in lifespan context manager only
01. **Settings in Effect Programs** - ❌ Yielding GetSettings effect or passing Settings to programs | ✅ Settings injected to infrastructure constructors only
01. **Mutable Settings Object** - ❌ Settings without frozen=True | ✅ Pydantic BaseSettings with frozen=True in model_config

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

| Model        | Purpose                                         |
| ------------ | ----------------------------------------------- |
| Patient      | Demographics, medical history                   |
| Doctor       | Credentials, specialization, can_prescribe flag |
| Appointment  | Status (state machine), timestamps, notes       |
| Prescription | Medications, dosage, interaction results        |
| LabResult    | Test results, critical value alerts             |
| Invoice      | Billing, line items, payment status             |

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

> **📖 Base**: [Effectful CLAUDE.md](../../CLAUDE.md#git-workflow-policy) | [Development Workflow SSoT](../../documents/engineering/development_workflow.md#git-workflow-policy)

HealthHub follows base Git workflow policy with no exceptions. See [Development Workflow](../../documents/engineering/development_workflow.md#git-workflow-policy) for complete policy.

## 🔧 Development Workflow

1. `docker compose -f docker/docker-compose.yml up -d`
1. Make code changes
1. `poetry run check-code`
1. `poetry run test-all`
1. Leave changes uncommitted

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
- [ ] No anti-patterns (1-20, including configuration anti-patterns)
- [ ] All dataclasses frozen (`frozen=True`)
- [ ] ADTs used instead of Optional for domain logic
- [ ] Result type used for all fallible operations
- [ ] Effect programs yield effects, don't call infrastructure
- [ ] API endpoints use dependency injection for interpreters
- [ ] Settings created ONLY in lifespan context manager (Doctrine 7)
- [ ] HIPAA audit logging for PHI access
- [ ] Changes left uncommitted

## 📚 References

- **Parent Library**: `../../effectful/` (effectful effect system)
- **Documentation**: `documents/` (comprehensive 24-document suite)
- **API Reference**: `documents/api/README.md`
- **Architecture**: `documents/engineering/architecture.md`
- **Authorization**: `documents/engineering/authentication.md`
- **State Machine**: `documents/engineering/effect_patterns.md#state-machines`

______________________________________________________________________

**Status**: Backend feature-complete | 3,948 LOC | 124+ tests passing
**Architecture**: Pure functional effect system demonstrating effectful library
**Philosophy**: Make invalid states unrepresentable through the type system
