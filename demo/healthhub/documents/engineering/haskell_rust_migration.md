# HealthHub Migration Guide: Python to Haskell/Rust

**Status**: Authoritative source
**Supersedes**: none
**Referenced by**: boundary_map.md

> **Purpose**: Demonstrate how HealthHub's Python code translates to the target Haskell/Rust architecture. Each boundary has different migration characteristics.
> **📖 Base Standard**: [haskell_rust_migration.md](../../../../documents/engineering/haskell_rust_migration.md)

______________________________________________________________________

## SSoT Link Map

| Need                   | Link                                                                                |
| ---------------------- | ----------------------------------------------------------------------------------- |
| Boundary model         | [Boundary Model](../../../../documents/engineering/boundary_model.md)               |
| Language architecture  | [Language Architecture](../../../../documents/engineering/language_architecture.md) |
| JIT compilation        | [JIT Compilation](../../../../documents/dsl/jit.md)                                 |
| HealthHub boundary map | [Boundary Map](boundary_map.md)                                                     |

______________________________________________________________________

## Deltas

This document extends the base haskell_rust_migration.md with concrete HealthHub code translation examples.

______________________________________________________________________

## 1. Migration Overview

### 1.1 Language Mapping

| Python (Current) | Target     | Rationale                                   |
| ---------------- | ---------- | ------------------------------------------- |
| Purity boundary  | Haskell    | Pure functional, compute graph optimization |
| Proof boundary   | Rust       | Memory-safe, TLA+ verifiable                |
| Outside boundary | Rust + FFI | Driver communication, external APIs         |

### 1.2 What Changes, What Stays

**Changes**:

- Language syntax and semantics
- Concurrency model (generators → algebraic effects)
- Type system (Python typing → Haskell/Rust types)

**Stays**:

- Domain model structure (ADTs remain ADTs)
- Effect pattern (yield → do-notation)
- Boundary responsibilities

______________________________________________________________________

## 2. Purity Boundary: Python → Haskell

### 2.1 Domain Models

**Python (current):**

```python
# backend/app/domain/appointment.py
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

@dataclass(frozen=True)
class Requested:
    """Appointment requested, awaiting confirmation."""
    requested_at: datetime

@dataclass(frozen=True)
class Confirmed:
    """Appointment confirmed by doctor."""
    confirmed_at: datetime
    scheduled_time: datetime

@dataclass(frozen=True)
class InProgress:
    """Appointment in progress."""
    started_at: datetime

@dataclass(frozen=True)
class Completed:
    """Appointment completed."""
    completed_at: datetime
    notes: str

@dataclass(frozen=True)
class Cancelled:
    """Appointment cancelled."""
    cancelled_at: datetime
    reason: str

type AppointmentStatus = Requested | Confirmed | InProgress | Completed | Cancelled
```

**Haskell (target):**

```haskell
-- Domain/Appointment.hs
module Domain.Appointment where

import Data.Time (UTCTime)
import Data.Text (Text)
import Data.UUID (UUID)
import GHC.Generics (Generic)

data AppointmentStatus
  = Requested { requestedAt :: UTCTime }
  | Confirmed { confirmedAt :: UTCTime, scheduledTime :: UTCTime }
  | InProgress { startedAt :: UTCTime }
  | Completed { completedAt :: UTCTime, notes :: Text }
  | Cancelled { cancelledAt :: UTCTime, reason :: Text }
  deriving (Eq, Show, Generic)

data Appointment = Appointment
  { appointmentId :: UUID
  , patientId :: UUID
  , doctorId :: UUID
  , status :: AppointmentStatus
  , reason :: Text
  , createdAt :: UTCTime
  , updatedAt :: UTCTime
  }
  deriving (Eq, Show, Generic)
```

**Translation rules:**

- `@dataclass(frozen=True)` → Haskell data type (immutable by default)
- Python `type X = A | B | C` → Haskell `data X = A | B | C`
- Python `UUID` → Haskell `Data.UUID.UUID`
- Python `datetime` → Haskell `Data.Time.UTCTime`
- Python `str` → Haskell `Data.Text.Text`

### 2.2 Effect Descriptions

**Python (current):**

```python
# backend/app/effects/healthcare.py
from dataclasses import dataclass
from uuid import UUID

@dataclass(frozen=True)
class GetPatientById:
    """Effect: Fetch patient by ID."""
    patient_id: UUID

@dataclass(frozen=True)
class CreateAppointment:
    """Effect: Create new appointment request."""
    patient_id: UUID
    doctor_id: UUID
    requested_time: OptionalValue[datetime]
    reason: str

type HealthcareEffect = GetPatientById | CreateAppointment | ...
```

**Haskell (target):**

```haskell
-- Effects/Healthcare.hs
module Effects.Healthcare where

import Data.UUID (UUID)
import Data.Time (UTCTime)
import Data.Text (Text)

data HealthcareEffect result where
  GetPatientById :: UUID -> HealthcareEffect (Maybe Patient)
  CreateAppointment
    :: UUID           -- patientId
    -> UUID           -- doctorId
    -> Maybe UTCTime  -- requestedTime
    -> Text           -- reason
    -> HealthcareEffect Appointment

-- Using GADTs for type-safe effect results
```

**Translation rules:**

- Python effect dataclass → Haskell GADT constructor
- Effect's `Returns:` docstring → GADT result type
- `OptionalValue[T]` → Haskell `Maybe T`

### 2.3 Effect Programs (Generators → Do-Notation)

**Python (current):**

```python
# backend/app/programs/appointment_programs.py
from collections.abc import Generator
from effectful.algebraic.result import Result, Ok, Err

def schedule_appointment_program(
    patient_id: UUID,
    doctor_id: UUID,
    requested_time: datetime | None,
    reason: str,
) -> Generator[HealthcareEffect, object, Result[Appointment, str]]:
    """Pure program to schedule an appointment."""

    # Yield effect, receive result
    patient_result = yield GetPatientById(patient_id=patient_id)

    match patient_result:
        case PatientMissingById():
            return Err("Patient not found")
        case PatientFound(patient=patient):
            pass  # Continue

    doctor_result = yield GetDoctorById(doctor_id=doctor_id)

    match doctor_result:
        case DoctorMissingById():
            return Err("Doctor not found")
        case DoctorFound(doctor=doctor):
            pass  # Continue

    # Create appointment
    appointment = yield CreateAppointment(
        patient_id=patient_id,
        doctor_id=doctor_id,
        requested_time=to_optional_value(requested_time),
        reason=reason,
    )

    return Ok(appointment)
```

**Haskell (target):**

```haskell
-- Programs/Appointment.hs
module Programs.Appointment where

import Control.Monad.Freer (Eff, Member, send)
import Data.UUID (UUID)
import Data.Time (UTCTime)
import Data.Text (Text)

scheduleAppointmentProgram
  :: Member HealthcareEffect effs
  => UUID           -- patientId
  -> UUID           -- doctorId
  -> Maybe UTCTime  -- requestedTime
  -> Text           -- reason
  -> Eff effs (Either Text Appointment)
scheduleAppointmentProgram patientId doctorId requestedTime reason = do
  -- Send effect, receive result
  maybePatient <- send (GetPatientById patientId)

  case maybePatient of
    Nothing -> pure (Left "Patient not found")
    Just patient -> do
      maybeDoctor <- send (GetDoctorById doctorId)

      case maybeDoctor of
        Nothing -> pure (Left "Doctor not found")
        Just doctor -> do
          -- Create appointment
          appointment <- send (CreateAppointment patientId doctorId requestedTime reason)
          pure (Right appointment)
```

**Translation rules:**

- Python `Generator[Effect, Result, Return]` → Haskell `Eff effs Return`
- Python `yield EffectType(...)` → Haskell `send (EffectType ...)`
- Python `Result[Ok, Err]` → Haskell `Either err ok`
- Python `match` → Haskell `case`

______________________________________________________________________

## 3. Proof Boundary: Python → Rust

### 3.1 Effect Runner

**Python (current):**

```python
# backend/app/programs/runner.py
from effectful.algebraic.result import Result, Ok, Err

@dataclass(frozen=True)
class InterpreterFailure:
    """Interpreter raised unexpectedly while executing an effect."""
    effect: AllEffects
    message: str

async def run_program(
    program: Generator[AllEffects, object, T],
    interpreter: InterpreterProtocol,
) -> Result[T, InterpreterFailure]:
    """Execute an effect program to completion."""
    effect_result: object = None

    try:
        while True:
            effect = program.send(effect_result)

            try:
                effect_result = await interpreter.handle(effect)
            except Exception as exc:
                return Err(InterpreterFailure(effect=effect, message=str(exc)))

    except StopIteration as stop:
        result: T = stop.value
        return Ok(result)
```

**Rust (target):**

```rust
// src/programs/runner.rs
use std::error::Error;

/// Interpreter raised unexpectedly while executing an effect.
#[derive(Debug)]
pub struct InterpreterFailure {
    pub effect_type: String,
    pub message: String,
}

/// Execute an effect program to completion.
pub async fn run_program<T, E, P, I>(
    mut program: P,
    interpreter: &I,
) -> Result<T, InterpreterFailure>
where
    P: EffectProgram<T, E>,
    I: Interpreter<E>,
    E: Effect,
{
    loop {
        match program.resume() {
            EffectState::Yield(effect) => {
                let result = interpreter
                    .handle(effect)
                    .await
                    .map_err(|e| InterpreterFailure {
                        effect_type: std::any::type_name::<E>().to_string(),
                        message: e.to_string(),
                    })?;
                program.send(result);
            }
            EffectState::Done(value) => return Ok(value),
        }
    }
}
```

**Translation rules:**

- Python `Generator` → Rust trait implementing resume/send
- Python `async def` → Rust `async fn`
- Python `Result[T, E]` → Rust `Result<T, E>`
- Python exception handling → Rust `?` operator with `map_err`

### 3.2 Composite Interpreter (Routing)

**Python (current):**

```python
# backend/app/interpreters/composite_interpreter.py
class CompositeInterpreter:
    """Routes effects to appropriate handlers."""

    def __init__(
        self,
        healthcare_interpreter: HealthcareInterpreterProtocol,
        notification_interpreter: NotificationInterpreterProtocol,
    ) -> None:
        self._healthcare = healthcare_interpreter
        self._notification = notification_interpreter

    async def handle(self, effect: AllEffects) -> object:
        match effect:
            case GetPatientById() | CreateAppointment() | ...:
                return await self._healthcare.handle(effect)
            case SendNotification() | ...:
                return await self._notification.handle(effect)
```

**Rust (target):**

````rust
// src/interpreters/composite.rs
pub struct CompositeInterpreter<H, N>
where
    H: HealthcareInterpreter,
    N: NotificationInterpreter,
{
    healthcare: H,
    notification: N,
}

impl<H, N> CompositeInterpreter<H, N>
where
    H: HealthcareInterpreter,
    N: NotificationInterpreter,
{
    pub fn new(healthcare: H, notification: N) -> Self {
        Self { healthcare, notification }
    }
}

impl<H, N> Interpreter<AllEffects> for CompositeInterpreter<H, N>
where
    H: HealthcareInterpreter,
    N: NotificationInterpreter,
{
    async fn handle(&self, effect: AllEffects) -> Result<Box<dyn Any>, InterpreterError> {
        match effect {
            AllEffects::Healthcare(e) => self.healthcare.handle(e).await,
            AllEffects::Notification(e) => self.notification.handle(e).await,
        }
    }
}
```text

---

## 4. Outside Boundary: Python → Rust + FFI

### 4.1 Database Interpreter

**Python (current):**
```python
# backend/app/interpreters/healthcare_interpreter.py
"""Healthcare effect interpreter.

Boundary: OUTSIDE_PROOF
Target-Language: N/A (assumed correct)

Assumptions:
- [Library] asyncpg correctly implements PostgreSQL wire protocol
- [Service] PostgreSQL server enforces ACID guarantees
"""

class HealthcareInterpreter:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def handle(self, effect: HealthcareEffect) -> object:
        match effect:
            case GetPatientById(patient_id=patient_id):
                return await self._get_patient_by_id(patient_id)
            # ... other cases

    async def _get_patient_by_id(self, patient_id: UUID) -> PatientLookupResult:
        row = await self._pool.fetchrow(
            "SELECT * FROM patients WHERE id = $1",
            patient_id,
        )
        if row is None:
            return PatientMissingById(patient_id=patient_id)
        return PatientFound(patient=_row_to_patient(row))
````

**Rust (target):**

```rust
// src/interpreters/healthcare.rs
//! Healthcare effect interpreter.
//!
//! Boundary: OUTSIDE_PROOF
//! Target-Language: N/A (assumed correct)
//!
//! Assumptions:
//! - [Library] sqlx correctly implements PostgreSQL wire protocol
//! - [Service] PostgreSQL server enforces ACID guarantees

use sqlx::PgPool;
use uuid::Uuid;

pub struct HealthcareInterpreter {
    pool: PgPool,
}

impl HealthcareInterpreter {
    pub fn new(pool: PgPool) -> Self {
        Self { pool }
    }

    pub async fn handle(&self, effect: HealthcareEffect) -> Result<Box<dyn Any>, DbError> {
        match effect {
            HealthcareEffect::GetPatientById(patient_id) => {
                let result = self.get_patient_by_id(patient_id).await?;
                Ok(Box::new(result))
            }
            // ... other cases
        }
    }

    async fn get_patient_by_id(&self, patient_id: Uuid) -> Result<PatientLookupResult, DbError> {
        // ASSUMPTION: sqlx correctly implements PostgreSQL wire protocol
        let row = sqlx::query_as!(
            PatientRow,
            "SELECT * FROM patients WHERE id = $1",
            patient_id
        )
        .fetch_optional(&self.pool)
        .await?;

        Ok(match row {
            None => PatientLookupResult::Missing { patient_id },
            Some(row) => PatientLookupResult::Found(row.into()),
        })
    }
}
```

**Key difference**: Rust version explicitly documents assumptions in doc comments, which can be extracted for the assumption inventory.

______________________________________________________________________

## 5. Migration Checklist

### 5.1 Per-File Migration

For each HealthHub file:

1. [ ] Identify boundary classification (PURITY, PROOF, OUTSIDE)
1. [ ] Add boundary annotation to current Python
1. [ ] Determine target language (Haskell, Rust, or keep as Rust+FFI)
1. [ ] Document assumptions (for OUTSIDE boundary)
1. [ ] Write target implementation (when Effectful compiler is ready)
1. [ ] Verify behavior equivalence via tests

### 5.2 Domain Model Migration Order

1. **Primitives** (`OptionalValue`, `Result`)
1. **Domain entities** (`Patient`, `Doctor`, `Appointment`)
1. **Domain ADTs** (`AppointmentStatus`, `AuthorizationState`)
1. **Lookup results** (`PatientLookupResult`, etc.)

### 5.3 Effect Migration Order

1. **Effect definitions** (pure data descriptions)
1. **Programs** (pure logic using effects)
1. **Runner** (execution loop)
1. **Interpreters** (handlers)

______________________________________________________________________

## 6. What Cannot Be Migrated

### 6.1 Stays in OUTSIDE Boundary

The following will always remain outside the proof boundary:

- **External service clients**: asyncpg → sqlx, but still assumes PostgreSQL correctness
- **HTTP framework glue**: FastAPI → whatever Rust HTTP framework, still assumes correct routing
- **Cryptographic operations**: bcrypt, JWT libraries

### 6.2 Assumption Documentation Remains Critical

Even after migration to Haskell/Rust, the assumption documentation in [External Assumptions](external_assumptions.md) remains necessary. The boundary model is about **verification scope**, not language choice.

______________________________________________________________________

## Cross-References

- [Boundary Model](../../../../documents/engineering/boundary_model.md) - Verification boundaries
- [Language Architecture](../../../../documents/engineering/language_architecture.md) - Why Haskell + Rust
- [JIT Compilation](../../../../documents/dsl/jit.md) - Haskell → Rust compilation
- [Boundary Map](boundary_map.md) - Component classifications
- [External Assumptions](external_assumptions.md) - What can never be proven
