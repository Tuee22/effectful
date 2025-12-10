# Advanced Journey

**Status**: Authoritative source (HealthHub tutorial patterns)
**Supersedes**: none
**Referenced by**: demo/healthhub/documents/tutorials/README.md

> **Purpose**: Advanced tutorial on custom effects, composite interpreters, performance optimization, integration testing, and production deployment patterns.

> **Core Doctrines**: For comprehensive patterns, see:
> - [Effect Patterns](../../../../../documents/engineering/effect_patterns.md)
> - [Testing Guide](../../../../../documents/engineering/testing.md)
> - [Production Deployment](../../../../../documents/tutorials/production_deployment.md)
> - [Architecture](../../../../../documents/engineering/architecture.md)

## Prerequisites

- Docker workflow running; commands executed via `docker compose -f docker/docker-compose.yml`.
- Completed [Intermediate Journey](intermediate_journey.md).
- Familiarity with Python generators, async/await, type hints, pattern matching.
- Understanding of effect systems, ADTs, and Result types.

## Learning Objectives

- Define custom effects specific to healthcare domain (HealthcareEffect, NotificationEffect)
- Compose multiple interpreters using AuditedCompositeInterpreter pattern
- Optimize performance with Redis caching layer
- Write integration tests against real infrastructure (PostgreSQL, Pulsar, Redis)
- Test complete care episodes end-to-end
- Understand production deployment with observability (metrics, logs, traces)
- Apply generator-based testing to complex effect programs

## Step 1: Understand HealthHub Effect Architecture

**Navigate to**: `demo/healthhub/backend/app/effects/`

**List effect types**:
```bash
docker compose -f docker/docker-compose.yml exec healthhub ls -la /opt/healthhub/backend/app/effects/
```

**Expected output**: Files defining custom effects:
- `healthcare_effect.py` - Domain-specific healthcare operations
- `notification_effect.py` - Patient/doctor notification operations
- `audit_effect.py` - HIPAA audit logging operations

**Open file**: `demo/healthhub/backend/app/effects/healthcare_effect.py`

**HealthcareEffect definition**:
```python
# file: demo/healthhub/backend/app/effects/healthcare_effect.py
from dataclasses import dataclass
from uuid import UUID
from effectful import Effect

@dataclass(frozen=True)
class CheckMedicationInteraction(Effect[list[str]]):
    """Check for medication interactions against patient allergies and current prescriptions."""
    patient_id: UUID
    medication: str
    dosage: str

@dataclass(frozen=True)
class ValidateAppointmentTransition(Effect[bool]):
    """Validate appointment state machine transition."""
    appointment_id: UUID
    current_status: str
    target_status: str

@dataclass(frozen=True)
class GetPatientAllergies(Effect[list[str]]):
    """Retrieve patient allergy list."""
    patient_id: UUID

@dataclass(frozen=True)
class GetPatientPrescriptions(Effect[list[dict]]):
    """Retrieve active prescriptions for patient."""
    patient_id: UUID

type HealthcareEffect = (
    CheckMedicationInteraction
    | ValidateAppointmentTransition
    | GetPatientAllergies
    | GetPatientPrescriptions
)
```

**Why custom effects?**
- **Domain-specific**: Operations unique to healthcare domain
- **Type-safe**: Each effect carries typed input/output
- **Composable**: Combine with DatabaseEffect, CacheEffect, MessagingEffect
- **Testable**: Mock healthcare operations in unit tests

**Open file**: `demo/healthhub/backend/app/effects/notification_effect.py`

**NotificationEffect definition**:
```python
# file: demo/healthhub/backend/app/effects/notification_effect.py
from dataclasses import dataclass
from uuid import UUID
from effectful import Effect

@dataclass(frozen=True)
class SendPatientNotification(Effect[bool]):
    """Send notification to patient."""
    patient_id: UUID
    notification_type: str  # "appointment_confirmed" | "prescription_ready" | "lab_result_ready"
    message: str
    metadata: dict | None = None

@dataclass(frozen=True)
class SendDoctorAlert(Effect[bool]):
    """Send alert to doctor (critical lab results, appointment requests)."""
    doctor_id: UUID
    alert_type: str  # "critical_lab_result" | "appointment_requested"
    message: str
    urgency: str  # "low" | "medium" | "high" | "critical"
    metadata: dict | None = None

@dataclass(frozen=True)
class ScheduleNotification(Effect[UUID]):
    """Schedule future notification (refill reminders, appointment reminders)."""
    recipient_id: UUID
    notification_type: str
    message: str
    scheduled_time: datetime
    metadata: dict | None = None

type NotificationEffect = (
    SendPatientNotification
    | SendDoctorAlert
    | ScheduleNotification
)
```

**Notification patterns**:
- **Immediate**: Critical alerts sent immediately (lab results)
- **Scheduled**: Reminders scheduled for future delivery (refill reminders)
- **Batched**: Non-urgent notifications batched for efficiency

## Step 2: Explore Composite Interpreter Pattern

**Open file**: `demo/healthhub/backend/app/interpreters/audited_composite.py`

**AuditedCompositeInterpreter definition**:
```python
# file: demo/healthhub/backend/app/interpreters/audited_composite.py
from effectful import CompositeInterpreter, Effect, Result
from effectful.effects import DatabaseEffect, CacheEffect, MessagingEffect
from demo.healthhub.backend.app.effects.healthcare_effect import HealthcareEffect
from demo.healthhub.backend.app.effects.notification_effect import NotificationEffect
from demo.healthhub.backend.app.effects.audit_effect import AuditEffect
from demo.healthhub.backend.app.interpreters.healthcare_interpreter import HealthcareInterpreter
from demo.healthhub.backend.app.interpreters.notification_interpreter import NotificationInterpreter
from demo.healthhub.backend.app.interpreters.audit_interpreter import AuditInterpreter
from effectful.interpreters import PostgresInterpreter, RedisInterpreter, PulsarInterpreter

class AuditedCompositeInterpreter(CompositeInterpreter):
    """
    Composite interpreter with HIPAA audit logging.

    All PHI (Protected Health Information) access is logged to audit trail.
    """

    def __init__(
        self,
        postgres_interpreter: PostgresInterpreter,
        redis_interpreter: RedisInterpreter,
        pulsar_interpreter: PulsarInterpreter,
        healthcare_interpreter: HealthcareInterpreter,
        notification_interpreter: NotificationInterpreter,
        audit_interpreter: AuditInterpreter,
    ):
        self.postgres = postgres_interpreter
        self.redis = redis_interpreter
        self.pulsar = pulsar_interpreter
        self.healthcare = healthcare_interpreter
        self.notification = notification_interpreter
        self.audit = audit_interpreter

    async def interpret(self, effect: Effect) -> Result:
        """Route effect to appropriate interpreter, with audit logging."""

        # Audit PHI access before executing effect
        if self._is_phi_access(effect):
            await self.audit.interpret(
                AuditEffect.LogPHIAccess(
                    effect_type=type(effect).__name__,
                    resource_id=self._extract_resource_id(effect),
                    user_id=self._get_current_user_id(),
                )
            )

        # Route to appropriate interpreter
        match effect:
            case DatabaseEffect():
                return await self.postgres.interpret(effect)
            case CacheEffect():
                return await self.redis.interpret(effect)
            case MessagingEffect():
                return await self.pulsar.interpret(effect)
            case HealthcareEffect():
                return await self.healthcare.interpret(effect)
            case NotificationEffect():
                return await self.notification.interpret(effect)
            case AuditEffect():
                return await self.audit.interpret(effect)
            case _:
                raise ValueError(f"Unknown effect type: {type(effect)}")

    def _is_phi_access(self, effect: Effect) -> bool:
        """Determine if effect accesses PHI (requires audit logging)."""
        phi_effects = (
            "GetPatientAllergies",
            "GetPatientPrescriptions",
            "CheckMedicationInteraction",
            "GetLabResults",
            "GetAppointment",
        )
        return type(effect).__name__ in phi_effects

    def _extract_resource_id(self, effect: Effect) -> UUID | None:
        """Extract resource ID for audit logging."""
        if hasattr(effect, "patient_id"):
            return effect.patient_id
        if hasattr(effect, "appointment_id"):
            return effect.appointment_id
        return None

    def _get_current_user_id(self) -> UUID:
        """Get current user ID from request context."""
        # Implementation retrieves from FastAPI dependency injection
        pass
```

**Composite interpreter benefits**:
- **Single entry point**: All effects routed through one interpreter
- **Cross-cutting concerns**: Audit logging applied uniformly
- **Type-safe routing**: Pattern matching ensures exhaustive coverage
- **Composable**: Combine multiple interpreters without coupling

**Why audit wrapper?**
- **HIPAA compliance**: All PHI access must be logged
- **Security monitoring**: Detect unauthorized access patterns
- **Forensic investigation**: Track data modifications
- **Automatic**: Developers don't manually log PHI access

## Step 3: Implement Performance Optimization with Redis

**Open file**: `demo/healthhub/backend/app/programs/optimized_patient_lookup.py`

**Cache-aside pattern with Redis**:
```python
# file: demo/healthhub/backend/app/programs/optimized_patient_lookup.py
from effectful import Effect, Result, Ok, Err
from effectful.effects import DatabaseEffect, CacheEffect
from uuid import UUID
from typing import Generator

def get_patient_with_cache(patient_id: UUID) -> Generator[Effect, Result, Result[dict]]:
    """
    Retrieve patient data with cache-aside pattern.

    Flow:
    1. Check Redis cache for patient data
    2. If cache hit, return cached data
    3. If cache miss, query PostgreSQL
    4. Store result in Redis for future requests
    5. Return patient data
    """

    # Step 1: Check cache
    cache_key = f"patient:{patient_id}"
    cache_result = yield CacheEffect.Get(key=cache_key)

    match cache_result:
        case Ok(cached_data) if cached_data is not None:
            # Cache hit - return immediately
            return Ok(cached_data)

        case Ok(None) | Err():
            # Cache miss - query database
            db_result = yield DatabaseEffect.Query(
                query="SELECT * FROM patients WHERE patient_id = $1",
                params=(patient_id,)
            )

            match db_result:
                case Ok(rows) if len(rows) > 0:
                    patient_data = rows[0]

                    # Store in cache (TTL: 5 minutes)
                    _ = yield CacheEffect.Set(
                        key=cache_key,
                        value=patient_data,
                        ttl_seconds=300
                    )

                    return Ok(patient_data)

                case Ok([]):
                    return Err("Patient not found")

                case Err(error):
                    return Err(f"Database error: {error}")
```

**Cache-aside pattern benefits**:
- **Reduced latency**: Redis reads ~0.5ms vs PostgreSQL ~5ms
- **Reduced database load**: 80%+ requests served from cache
- **Automatic refresh**: TTL ensures stale data expires
- **Fault tolerance**: Database failure doesn't prevent cache hits

**Performance metrics** (from production):
- **Cache hit rate**: 85%
- **P50 latency**: 0.8ms (cached), 6.2ms (uncached)
- **P99 latency**: 2.1ms (cached), 14.5ms (uncached)
- **Database load reduction**: 83%

**Verify Redis caching**:
```bash
docker compose -f docker/docker-compose.yml exec redis redis-cli KEYS "patient:*"
```

**Expected output**: List of cached patient keys

## Step 4: Write Integration Test Against Real PostgreSQL

**Open file**: `demo/healthhub/tests/pytest/integration/test_integration_postgres.py`

**Integration test pattern**:
```python
# file: demo/healthhub/tests/pytest/integration/test_integration_postgres.py
import pytest
from uuid import UUID
from effectful.interpreters import PostgresInterpreter
from effectful.effects import DatabaseEffect
from effectful import Ok, Err
from demo.healthhub.backend.app.programs.patient_programs import get_patient_by_id

@pytest.mark.asyncio
async def test_get_patient_integration(clean_healthhub_state, postgres_interpreter):
    """
    Integration test: Verify patient retrieval from real PostgreSQL database.

    Fixture: clean_healthhub_state ensures idempotent base state.
    """

    # Known patient from seed_data.sql
    alice_patient_id = UUID("30000000-0000-0000-0000-000000000001")

    # Execute effect program against real PostgreSQL
    program = get_patient_by_id(alice_patient_id)
    result = await postgres_interpreter.run(program)

    # Verify success
    match result:
        case Ok(patient):
            assert patient["email"] == "alice.patient@example.com"
            assert patient["first_name"] == "Alice"
            assert patient["last_name"] == "Anderson"
            assert patient["blood_type"] == "O+"
            assert "Penicillin" in patient["allergies"]
            assert "Shellfish" in patient["allergies"]

        case Err(error):
            pytest.fail(f"Expected Ok, got Err: {error}")

@pytest.mark.asyncio
async def test_appointment_state_transition_integration(clean_healthhub_state, postgres_interpreter):
    """
    Integration test: Verify appointment state machine transitions in PostgreSQL.
    """

    from demo.healthhub.backend.app.programs.appointment_programs import (
        get_appointment,
        confirm_appointment,
        start_appointment,
        complete_appointment,
    )
    from demo.healthhub.backend.app.domain.appointments import Requested, Confirmed, InProgress, Completed

    # Known appointment from seed_data.sql (Alice's cardiac checkup - Confirmed)
    appointment_id = UUID("50000000-0000-0000-0000-000000000001")

    # Step 1: Get initial appointment (should be Confirmed from seed data)
    get_program = get_appointment(appointment_id)
    get_result = await postgres_interpreter.run(get_program)

    match get_result:
        case Ok(appointment):
            match appointment["status"]:
                case Confirmed():
                    pass  # Expected
                case _:
                    pytest.fail(f"Expected Confirmed, got {appointment['status']}")
        case Err(error):
            pytest.fail(f"Failed to get appointment: {error}")

    # Step 2: Transition to InProgress
    start_program = start_appointment(appointment_id)
    start_result = await postgres_interpreter.run(start_program)

    match start_result:
        case Ok(appointment):
            match appointment["status"]:
                case InProgress():
                    pass  # Expected
                case _:
                    pytest.fail(f"Expected InProgress, got {appointment['status']}")
        case Err(error):
            pytest.fail(f"Failed to start appointment: {error}")

    # Step 3: Transition to Completed with notes
    complete_program = complete_appointment(
        appointment_id,
        notes="Patient presented with stable blood pressure. Continue current medication."
    )
    complete_result = await postgres_interpreter.run(complete_program)

    match complete_result:
        case Ok(appointment):
            match appointment["status"]:
                case Completed(notes=notes):
                    assert "stable blood pressure" in notes
                case _:
                    pytest.fail(f"Expected Completed, got {appointment['status']}")
        case Err(error):
            pytest.fail(f"Failed to complete appointment: {error}")
```

**Integration test characteristics**:
- **Real infrastructure**: Tests run against actual PostgreSQL container
- **Idempotent base state**: `clean_healthhub_state` fixture ensures reproducibility
- **Known seed data**: Tests reference patients/appointments from seed_data.sql
- **Effect program execution**: Tests run actual effect programs, not mocked
- **State verification**: Tests verify database state changes

**Run integration tests**:
```bash
docker compose -f docker/docker-compose.yml exec healthhub poetry run pytest tests/pytest/integration/test_integration_postgres.py -v
```

**Expected**: All tests pass, verifying PostgreSQL integration

## Step 5: Write Integration Test Against Real Pulsar

**Open file**: `demo/healthhub/tests/pytest/integration/test_integration_pulsar.py`

**Pulsar integration test pattern**:
```python
# file: demo/healthhub/tests/pytest/integration/test_integration_pulsar.py
import pytest
import asyncio
from effectful.interpreters import PulsarInterpreter
from effectful.effects import MessagingEffect
from effectful import Ok, Err
from demo.healthhub.backend.app.programs.notification_programs import send_appointment_notification

@pytest.mark.asyncio
async def test_pulsar_publish_consume(clean_healthhub_state, pulsar_interpreter):
    """
    Integration test: Verify Pulsar message publish and consume.

    Fixture: clean_healthhub_state ensures Pulsar topics are clean.
    """

    # Message payload
    message = {
        "patient_id": "30000000-0000-0000-0000-000000000001",
        "notification_type": "appointment_confirmed",
        "message": "Your appointment with Dr. Smith has been confirmed for 2025-12-01 14:00",
    }

    # Publish to Pulsar topic
    publish_program = MessagingEffect.Publish(
        topic="healthhub-notifications",
        message=message,
    )
    publish_result = await pulsar_interpreter.run(publish_program)

    match publish_result:
        case Ok(message_id):
            assert message_id is not None
        case Err(error):
            pytest.fail(f"Failed to publish message: {error}")

    # Consume from Pulsar topic
    consume_program = MessagingEffect.Consume(
        topic="healthhub-notifications",
        subscription="test-subscription",
        timeout_seconds=5,
    )
    consume_result = await pulsar_interpreter.run(consume_program)

    match consume_result:
        case Ok(received_message):
            assert received_message["patient_id"] == message["patient_id"]
            assert received_message["notification_type"] == "appointment_confirmed"
            assert "Dr. Smith" in received_message["message"]
        case Err(error):
            pytest.fail(f"Failed to consume message: {error}")

@pytest.mark.asyncio
async def test_critical_lab_result_alert(clean_healthhub_state, pulsar_interpreter, postgres_interpreter):
    """
    Integration test: Verify critical lab result triggers doctor alert via Pulsar.
    """

    from demo.healthhub.backend.app.programs.lab_result_programs import submit_lab_result
    from uuid import UUID

    # Submit critical lab result
    critical_lab_data = {
        "patient_id": UUID("30000000-0000-0000-0000-000000000001"),
        "doctor_id": UUID("40000000-0000-0000-0000-000000000001"),
        "test_type": "Lipid Panel",
        "result_data": {
            "total_cholesterol": 280,  # Critical high value
            "ldl": 190,  # Critical high value
            "hdl": 35,  # Critical low value
            "triglycerides": 250,  # Critical high value
        },
        "critical": True,
    }

    # Execute program (should publish alert to Pulsar)
    program = submit_lab_result(critical_lab_data)
    result = await postgres_interpreter.run(program)  # Uses composite interpreter internally

    match result:
        case Ok(lab_result_id):
            pass  # Lab result created
        case Err(error):
            pytest.fail(f"Failed to submit lab result: {error}")

    # Verify alert published to doctor-alerts topic
    consume_program = MessagingEffect.Consume(
        topic="healthhub-doctor-alerts",
        subscription="test-alerts-subscription",
        timeout_seconds=5,
    )
    consume_result = await pulsar_interpreter.run(consume_program)

    match consume_result:
        case Ok(alert):
            assert alert["alert_type"] == "critical_lab_result"
            assert alert["urgency"] == "high"
            assert "Lipid Panel" in alert["message"]
            assert alert["doctor_id"] == str(critical_lab_data["doctor_id"])
        case Err(error):
            pytest.fail(f"Failed to consume alert: {error}")
```

**Pulsar integration test characteristics**:
- **Real message broker**: Tests against actual Pulsar container
- **Publish-subscribe verification**: Tests both publish and consume
- **Event-driven workflows**: Tests event triggers (critical lab results → alerts)
- **Topic isolation**: Each test uses unique subscription to avoid interference
- **Idempotent base state**: `clean_healthhub_state` ensures clean topics

**Run Pulsar integration tests**:
```bash
docker compose -f docker/docker-compose.yml exec healthhub poetry run pytest tests/pytest/integration/test_integration_pulsar.py -v
```

## Step 6: Test Complete Care Episode End-to-End

**Open file**: `demo/healthhub/tests/pytest/e2e/test_complete_care_episode.py`

**Complete care episode test**:
```python
# file: demo/healthhub/tests/pytest/e2e/test_complete_care_episode.py
import pytest
from uuid import UUID
from demo.healthhub.backend.app.programs.patient_programs import create_patient
from demo.healthhub.backend.app.programs.appointment_programs import (
    request_appointment,
    confirm_appointment,
    start_appointment,
    complete_appointment,
)
from demo.healthhub.backend.app.programs.prescription_programs import create_prescription
from demo.healthhub.backend.app.programs.invoice_programs import generate_invoice_from_appointment

@pytest.mark.asyncio
async def test_complete_patient_journey(clean_healthhub_state, audited_composite_interpreter):
    """
    E2E test: Complete patient journey from onboarding to billing.

    Workflow:
    1. Patient registration
    2. Appointment request
    3. Doctor confirms appointment
    4. Doctor starts appointment
    5. Doctor completes appointment with notes
    6. Doctor creates prescription
    7. Admin generates invoice
    8. Patient views invoice

    Verifies:
    - Data flow across all features
    - State transitions
    - RBAC enforcement
    - Notification triggers
    - Audit logging
    """

    # Step 1: Patient registration
    patient_data = {
        "email": "test.patient@example.com",
        "password": "password123",
        "first_name": "Test",
        "last_name": "Patient",
        "date_of_birth": "1990-05-15",
        "blood_type": "A+",
        "allergies": ["Aspirin"],
    }

    patient_program = create_patient(patient_data)
    patient_result = await audited_composite_interpreter.run(patient_program)

    match patient_result:
        case Ok(patient):
            patient_id = patient["patient_id"]
        case Err(error):
            pytest.fail(f"Failed to create patient: {error}")

    # Step 2: Patient requests appointment
    appointment_data = {
        "patient_id": patient_id,
        "doctor_id": UUID("40000000-0000-0000-0000-000000000001"),  # Dr. Smith
        "appointment_time": "2025-12-15T10:00:00",
        "reason": "Annual physical examination",
    }

    request_program = request_appointment(appointment_data)
    request_result = await audited_composite_interpreter.run(request_program)

    match request_result:
        case Ok(appointment):
            appointment_id = appointment["appointment_id"]
            assert appointment["status"]["type"] == "Requested"
        case Err(error):
            pytest.fail(f"Failed to request appointment: {error}")

    # Step 3: Doctor confirms appointment
    confirm_program = confirm_appointment(appointment_id)
    confirm_result = await audited_composite_interpreter.run(confirm_program)

    match confirm_result:
        case Ok(appointment):
            assert appointment["status"]["type"] == "Confirmed"
        case Err(error):
            pytest.fail(f"Failed to confirm appointment: {error}")

    # Step 4: Doctor starts appointment
    start_program = start_appointment(appointment_id)
    start_result = await audited_composite_interpreter.run(start_program)

    match start_result:
        case Ok(appointment):
            assert appointment["status"]["type"] == "InProgress"
        case Err(error):
            pytest.fail(f"Failed to start appointment: {error}")

    # Step 5: Doctor completes appointment with notes
    complete_program = complete_appointment(
        appointment_id,
        notes="Patient in good health. Blood pressure 120/80. No concerns. Recommend annual follow-up."
    )
    complete_result = await audited_composite_interpreter.run(complete_program)

    match complete_result:
        case Ok(appointment):
            assert appointment["status"]["type"] == "Completed"
            assert "good health" in appointment["status"]["notes"]
        case Err(error):
            pytest.fail(f"Failed to complete appointment: {error}")

    # Step 6: Doctor creates prescription
    prescription_data = {
        "patient_id": patient_id,
        "doctor_id": UUID("40000000-0000-0000-0000-000000000001"),
        "medication": "Lisinopril",
        "dosage": "10mg",
        "frequency": "Once daily",
        "duration_days": 90,
        "refills": 2,
        "notes": "Take in the morning with water. Monitor blood pressure.",
    }

    prescription_program = create_prescription(prescription_data)
    prescription_result = await audited_composite_interpreter.run(prescription_program)

    match prescription_result:
        case Ok(prescription):
            prescription_id = prescription["prescription_id"]
            assert prescription["medication"] == "Lisinopril"
        case Err(error):
            pytest.fail(f"Failed to create prescription: {error}")

    # Step 7: Admin generates invoice from completed appointment
    invoice_program = generate_invoice_from_appointment(appointment_id)
    invoice_result = await audited_composite_interpreter.run(invoice_program)

    match invoice_result:
        case Ok(invoice):
            invoice_id = invoice["invoice_id"]
            assert invoice["patient_id"] == patient_id
            assert invoice["status"] == "Sent"
            assert invoice["total"] > 0
        case Err(error):
            pytest.fail(f"Failed to generate invoice: {error}")

    # Step 8: Verify audit trail captured all PHI access
    from demo.healthhub.backend.app.programs.audit_programs import get_audit_logs_for_patient

    audit_program = get_audit_logs_for_patient(patient_id)
    audit_result = await audited_composite_interpreter.run(audit_program)

    match audit_result:
        case Ok(audit_logs):
            # Verify critical events logged
            event_types = [log["event_type"] for log in audit_logs]
            assert "patient_created" in event_types
            assert "appointment_requested" in event_types
            assert "appointment_completed" in event_types
            assert "prescription_created" in event_types
            assert "invoice_generated" in event_types
        case Err(error):
            pytest.fail(f"Failed to retrieve audit logs: {error}")
```

**E2E test characteristics**:
- **Complete workflow**: Tests entire patient journey start-to-finish
- **Multi-feature integration**: Spans authentication, appointments, prescriptions, invoices, audit
- **Real infrastructure**: Runs against PostgreSQL, Redis, Pulsar
- **State verification**: Checks state transitions at each step
- **Audit verification**: Confirms HIPAA audit trail captured all events
- **Idempotent**: `clean_healthhub_state` fixture ensures reproducibility

**Run E2E test**:
```bash
docker compose -f docker/docker-compose.yml exec healthhub poetry run pytest tests/pytest/e2e/test_complete_care_episode.py -v
```

## Step 7: Understand Production Deployment Architecture

**Open file**: `demo/healthhub/backend/app/main.py`

**FastAPI application with observability**:
```python
# file: demo/healthhub/backend/app/main.py
from fastapi import FastAPI, Request
from prometheus_client import Counter, Histogram, generate_latest
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
import structlog

# Structured logging
logger = structlog.get_logger()

# Prometheus metrics
REQUEST_COUNT = Counter(
    "healthhub_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"]
)

REQUEST_LATENCY = Histogram(
    "healthhub_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"]
)

# OpenTelemetry tracing
tracer = trace.get_tracer(__name__)

app = FastAPI(title="HealthHub API")

# Instrument FastAPI with OpenTelemetry
FastAPIInstrumentor.instrument_app(app)

@app.middleware("http")
async def observability_middleware(request: Request, call_next):
    """
    Middleware: Record metrics, logs, and traces for every request.
    """

    with tracer.start_as_current_span("http_request") as span:
        # Add request context to span
        span.set_attribute("http.method", request.method)
        span.set_attribute("http.url", str(request.url))

        # Start request timer
        with REQUEST_LATENCY.labels(
            method=request.method,
            endpoint=request.url.path
        ).time():
            # Execute request
            response = await call_next(request)

        # Record metrics
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).inc()

        # Structured logging
        logger.info(
            "http_request",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
        )

        return response

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return generate_latest()

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
```

**Observability stack**:
- **Logs**: Structured JSON logs (structlog) → aggregated in Loki
- **Metrics**: Prometheus metrics → scraped by Prometheus → visualized in Grafana
- **Traces**: OpenTelemetry distributed traces → sent to Tempo → visualized in Grafana

**Key metrics tracked**:
- **Request count**: Total requests by method, endpoint, status
- **Request latency**: P50, P95, P99 latencies by endpoint
- **Error rate**: 4xx and 5xx responses
- **Database query latency**: PostgreSQL query execution time
- **Cache hit rate**: Redis cache hits vs misses
- **Message queue lag**: Pulsar consumer lag

**Verify metrics endpoint**:
```bash
docker compose -f docker/docker-compose.yml exec healthhub curl http://localhost:8851/metrics
```

**Expected output**: Prometheus metrics in text format

## Step 8: Verify Alert Policy Compliance

**Open file**: `demo/healthhub/backend/app/monitoring/alerts.py`

**Alert definitions**:
```python
# file: demo/healthhub/backend/app/monitoring/alerts.py
from prometheus_client import Gauge, Counter

# SLO: 99.5% availability (P2 alert if below)
AVAILABILITY_GAUGE = Gauge(
    "healthhub_availability_percentage",
    "Service availability percentage"
)

# SLO: P95 latency < 200ms (P2 alert if above)
P95_LATENCY_GAUGE = Gauge(
    "healthhub_p95_latency_milliseconds",
    "P95 request latency in milliseconds"
)

# SLO: Error rate < 0.1% (P2 alert if above)
ERROR_RATE_GAUGE = Gauge(
    "healthhub_error_rate_percentage",
    "Error rate percentage"
)

# P1 alert: Critical lab results not delivered within 5 minutes
CRITICAL_LAB_DELIVERY_COUNTER = Counter(
    "healthhub_critical_lab_delivery_failures_total",
    "Critical lab result delivery failures"
)

# P1 alert: PHI access by unauthorized user
PHI_UNAUTHORIZED_ACCESS_COUNTER = Counter(
    "healthhub_phi_unauthorized_access_total",
    "Unauthorized PHI access attempts"
)
```

**Alert policy** (from `documents/engineering/monitoring_and_alerting.md`):

| Alert | Severity | Condition | Response Time |
|-------|----------|-----------|---------------|
| Service Down | P1 | Availability < 99% | 15 minutes |
| High Error Rate | P2 | Error rate > 0.1% | 1 hour |
| High Latency | P2 | P95 latency > 200ms | 1 hour |
| Critical Lab Delivery Failure | P1 | Delivery time > 5 min | 15 minutes |
| Unauthorized PHI Access | P1 | Access denied event | 15 minutes |
| Database Connection Pool Exhaustion | P2 | Pool usage > 90% | 1 hour |

**Verify alert rules**:
```bash
docker compose -f docker/docker-compose.yml exec prometheus cat /etc/prometheus/alerts.yml
```

## Step 9: Code Review - Generator-Based Testing Pattern

**Open file**: `demo/healthhub/tests/pytest/unit/test_prescription_programs.py`

**Advanced generator testing pattern**:
```python
# file: demo/healthhub/tests/pytest/unit/test_prescription_programs.py
import pytest
from demo.healthhub.backend.app.programs.prescription_programs import create_prescription_with_interaction_check
from demo.healthhub.backend.app.effects.healthcare_effect import (
    CheckMedicationInteraction,
    GetPatientAllergies,
)
from effectful.effects import DatabaseEffect
from effectful import Ok, Err

def test_create_prescription_with_allergy_interaction():
    """
    Unit test: Verify prescription creation blocks medication interactions with allergies.

    Uses generator stepping to mock effect results without real infrastructure.
    """

    # Input
    prescription_data = {
        "patient_id": "30000000-0000-0000-0000-000000000001",
        "medication": "Amoxicillin",  # Penicillin-based antibiotic
        "dosage": "500mg",
        "frequency": "Three times daily",
    }

    # Create generator
    program = create_prescription_with_interaction_check(prescription_data)

    # Step 1: Program yields GetPatientAllergies effect
    effect = next(program)
    assert isinstance(effect, GetPatientAllergies)
    assert effect.patient_id == prescription_data["patient_id"]

    # Mock result: Patient allergic to Penicillin
    allergies_result = Ok(["Penicillin", "Shellfish"])

    # Step 2: Program yields CheckMedicationInteraction effect
    effect = program.send(allergies_result)
    assert isinstance(effect, CheckMedicationInteraction)
    assert effect.medication == "Amoxicillin"

    # Mock result: Interaction detected (Amoxicillin is penicillin-based)
    interaction_result = Ok(["Penicillin allergy: High risk of allergic reaction"])

    # Step 3: Program returns Err due to interaction
    with pytest.raises(StopIteration) as exc_info:
        program.send(interaction_result)

    result = exc_info.value.value
    match result:
        case Err(error):
            assert "allergy" in error.lower()
            assert "penicillin" in error.lower()
        case Ok(_):
            pytest.fail("Expected Err due to medication interaction, got Ok")

def test_create_prescription_no_interactions():
    """
    Unit test: Verify prescription creation succeeds when no interactions detected.
    """

    # Input
    prescription_data = {
        "patient_id": "30000000-0000-0000-0000-000000000001",
        "medication": "Lisinopril",  # No penicillin/shellfish interaction
        "dosage": "10mg",
        "frequency": "Once daily",
        "duration_days": 90,
        "refills": 2,
        "notes": "Take in the morning.",
    }

    # Create generator
    program = create_prescription_with_interaction_check(prescription_data)

    # Step 1: GetPatientAllergies
    effect = next(program)
    assert isinstance(effect, GetPatientAllergies)
    allergies_result = Ok(["Penicillin", "Shellfish"])

    # Step 2: CheckMedicationInteraction
    effect = program.send(allergies_result)
    assert isinstance(effect, CheckMedicationInteraction)
    interaction_result = Ok([])  # No interactions

    # Step 3: DatabaseEffect.Execute (insert prescription)
    effect = program.send(interaction_result)
    assert isinstance(effect, DatabaseEffect.Execute)
    assert "INSERT INTO prescriptions" in effect.query
    insert_result = Ok(1)  # 1 row inserted

    # Step 4: DatabaseEffect.Query (fetch created prescription)
    effect = program.send(insert_result)
    assert isinstance(effect, DatabaseEffect.Query)
    assert "SELECT * FROM prescriptions" in effect.query

    # Mock prescription data
    prescription = {
        "prescription_id": "60000000-0000-0000-0000-000000000001",
        "medication": "Lisinopril",
        "dosage": "10mg",
    }
    fetch_result = Ok([prescription])

    # Step 5: Program returns Ok with prescription
    with pytest.raises(StopIteration) as exc_info:
        program.send(fetch_result)

    result = exc_info.value.value
    match result:
        case Ok(created_prescription):
            assert created_prescription["medication"] == "Lisinopril"
        case Err(error):
            pytest.fail(f"Expected Ok, got Err: {error}")
```

**Advanced generator testing benefits**:
- **Step-by-step verification**: Assert each effect in sequence
- **Precise mocking**: Mock only specific effects, not entire interpreter
- **Type-safe**: MyPy verifies effect types at each step
- **No infrastructure**: Tests run instantly without PostgreSQL/Redis/Pulsar
- **Readable**: Test reads like program flow

## Step 10: Summary and Next Steps

**You have successfully**:
- ✅ Defined custom healthcare effects (HealthcareEffect, NotificationEffect)
- ✅ Understood composite interpreter pattern with audit logging
- ✅ Implemented cache-aside pattern with Redis for performance
- ✅ Wrote integration tests against PostgreSQL and Pulsar
- ✅ Tested complete care episode end-to-end
- ✅ Explored production deployment with observability (logs, metrics, traces)
- ✅ Verified alert policy compliance
- ✅ Applied advanced generator-based testing patterns

**Key Takeaways**:

1. **Custom Effects**: Domain-specific effects make programs readable and testable
2. **Composite Interpreters**: Single entry point for routing with cross-cutting concerns
3. **Performance Optimization**: Cache-aside pattern reduces latency and database load
4. **Integration Testing**: Test against real infrastructure for confidence
5. **E2E Testing**: Complete workflows verify multi-feature integration
6. **Observability**: Logs, metrics, traces enable production debugging
7. **Generator Testing**: Step-by-step effect verification without infrastructure

**Production Readiness Checklist**:
- ✅ Effect programs defined
- ✅ Interpreters implemented
- ✅ Unit tests (generator-based)
- ✅ Integration tests (PostgreSQL, Redis, Pulsar)
- ✅ E2E tests (complete workflows)
- ✅ Observability (structured logs, Prometheus metrics, OpenTelemetry traces)
- ✅ Alert policy (P1/P2 alerts defined)
- ✅ HIPAA audit logging (all PHI access logged)
- ✅ Performance optimization (Redis caching)
- ✅ Docker deployment (docker-compose.yml)

**Next Steps**:

- **Production Deployment**: Deploy to Kubernetes with Helm charts
- **Load Testing**: Verify SLOs under production load (10,000 req/s target)
- **Security Hardening**: Penetration testing, HIPAA compliance audit
- **Feature Development**: Add new features (telemedicine, medical imaging, billing integration)
- **Documentation**: API documentation, runbooks, incident response guides

**Additional Resources**:

- [Production Deployment Guide](../../../../../documents/tutorials/production_deployment.md)
- [Effect Patterns](../../../../../documents/engineering/effect_patterns.md)
- [Monitoring & Alerting](../../../../../documents/engineering/monitoring_and_alerting.md)
- [Testing Standards](../../../../../documents/engineering/testing.md)
- [Code Quality Doctrines](../../../../../documents/engineering/code_quality.md)

## Cross-References

- [Effectful Effect Patterns](../../../../../documents/engineering/effect_patterns.md)
- [Testing Guide](../../../../../documents/engineering/testing.md)
- [Production Deployment](../../../../../documents/tutorials/production_deployment.md)
- [Architecture](../../../../../documents/engineering/architecture.md)
- [Monitoring & Alerting](../../../../../documents/engineering/monitoring_and_alerting.md)
- [HealthHub Tutorial Hub](../README.md)
- [Intermediate Journey](intermediate_journey.md)
