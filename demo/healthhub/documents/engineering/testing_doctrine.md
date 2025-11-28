# Testing Doctrine

**Single Source of Truth for HealthHub test infrastructure**

## Philosophy

Tests exist to find problems, not provide false confidence. Every test must validate actual functionality, not hardcoded expectations.

## Test Categories (MECE)

### Backend Unit Tests
**Purpose**: Test effect programs and interpreters in isolation

**Characteristics**:
- No I/O (pure logic testing)
- Use pytest-mock with AsyncMock
- Test programs via generator stepping
- Test interpreters with mocked infrastructure
- Fast execution (~0.5s for 100+ tests)

**Location**: `tests/pytest/backend/`

**Pattern**:
```python
def test_program() -> None:
    """Test effect program by stepping through generator."""
    gen = schedule_appointment_program(...)

    # Step 1: Yield first effect
    effect1 = next(gen)
    assert isinstance(effect1, GetPatientById)

    # Step 2: Send mock result, get next effect
    effect2 = gen.send(mock_patient)
    assert isinstance(effect2, GetDoctorById)

    # Continue until StopIteration
```

### Integration Tests
**Purpose**: Test multi-effect workflows with real infrastructure

**Characteristics**:
- Real PostgreSQL, Redis, Apache Pulsar
- No HTTP layer (direct program execution)
- Database isolation via TRUNCATE + seeding fixtures
- Test complete workflows end-to-end
- Medium execution (~1.5s for 24+ tests)

**Location**: `tests/pytest/integration/`

**Pattern**:
```python
@pytest.mark.asyncio
async def test_workflow(
    db_pool: asyncpg.Pool[asyncpg.Record],
    redis_client: redis.Redis[bytes],
) -> None:
    """Test complete appointment scheduling workflow."""
    interpreter = CompositeInterpreter(pool=db_pool, redis_client=redis_client)

    # Execute program with real infrastructure
    appointment = await run_program(
        schedule_appointment_program(...),
        interpreter,
    )

    # Level 1: Verify program result
    assert appointment is not None
    assert isinstance(appointment.status, Requested)

    # Level 2: Verify database persistence
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM appointments WHERE id = $1",
            appointment.id,
        )
        assert row is not None
        assert row["reason"] == "Annual checkup"

    # Level 3: Verify audit log created (HIPAA compliance)
    async with db_pool.acquire() as conn:
        audit_rows = await conn.fetch(
            """SELECT * FROM audit_log
               WHERE resource_type = 'appointment' AND resource_id = $1""",
            appointment.id,
        )
        assert len(audit_rows) > 0
        assert audit_rows[0]["action"] == "create_appointment"
```

### E2E Tests
**Purpose**: Test complete user flows via browser automation

**Characteristics**:
- Playwright browser automation (chromium/firefox/webkit)
- Real authentication (no mocking)
- ADT-based synchronization (no timing hacks)
- Full frontend + backend integration
- Test actual user workflows
- Variable execution time

**Location**: `tests/pytest/e2e/`

**Pattern**:
```python
from tests.pytest.e2e.helpers.adt_state_helpers import wait_for_remote_data_state
from playwright.async_api import Page, expect

@pytest.mark.asyncio
async def test_appointment_flow(authenticated_patient_page: Page) -> None:
    """Test complete appointment creation flow via UI."""
    page = authenticated_patient_page

    # Navigate to appointments page
    await page.goto("http://localhost:8850/appointments")
    await wait_for_remote_data_state(page, "Success")  # ADT-based sync

    # Click create button
    await page.click('button[data-testid="create-appointment"]')

    # Fill form
    await page.fill('select[name="doctor_id"]', str(doctor_id))
    await page.fill('input[name="reason"]', "Annual checkup")

    # Submit
    await page.click('button[type="submit"]')

    # Verify success (ADT state, not timing hack)
    await expect(page.locator('.success-message')).to_be_visible()
```

## Test Infrastructure

### Root Conftest (`tests/conftest.py`)

**Event Loop Management**:
```python
@pytest.fixture(scope="session")
def event_loop() -> Iterator[asyncio.AbstractEventLoop]:
    """Session-scoped event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
```

**Database Connection Pool** (asyncpg with JSON codec):
```python
@pytest.fixture
async def db_pool() -> AsyncIterator[asyncpg.Pool[asyncpg.Record]]:
    """Database pool with JSON/JSONB codec registration."""
    async def _init_connection(conn: asyncpg.Connection[asyncpg.Record]) -> None:
        await conn.set_type_codec(
            "json",
            encoder=json.dumps,
            decoder=json.loads,
            schema="pg_catalog",
        )
        await conn.set_type_codec(
            "jsonb",
            encoder=json.dumps,
            decoder=json.loads,
            schema="pg_catalog",
        )

    pool = await asyncpg.create_pool(
        host="postgres",
        port=5432,
        database="healthhub",
        user="healthhub",
        password="healthhub_pass",
        init=_init_connection,
    )
    yield pool
    await pool.close()
```

**Database Cleanup** (Critical for test isolation):
```python
@pytest.fixture
async def clean_db(db_pool: asyncpg.Pool[asyncpg.Record]) -> None:
    """TRUNCATE all tables in dependency order."""
    async with db_pool.acquire() as conn:
        # Order matters - respect foreign key constraints
        await conn.execute("TRUNCATE audit_log CASCADE")
        await conn.execute("TRUNCATE invoice_line_items CASCADE")
        await conn.execute("TRUNCATE invoices CASCADE")
        await conn.execute("TRUNCATE lab_results CASCADE")
        await conn.execute("TRUNCATE prescriptions CASCADE")
        await conn.execute("TRUNCATE appointments CASCADE")
        await conn.execute("TRUNCATE doctors CASCADE")
        await conn.execute("TRUNCATE patients CASCADE")
        await conn.execute("TRUNCATE users CASCADE")
```

**Sample ID Fixtures** (Immutable test data):
```python
@pytest.fixture
def sample_user_id() -> UUID:
    """Immutable user ID for tests."""
    return UUID("10000000-0000-0000-0000-000000000001")

@pytest.fixture
def sample_patient_id() -> UUID:
    return UUID("30000000-0000-0000-0000-000000000001")

@pytest.fixture
def sample_doctor_id() -> UUID:
    return UUID("40000000-0000-0000-0000-000000000001")
```

**Seeding Fixtures** (Fixture dependency chain):
```python
@pytest.fixture
async def seed_test_user(
    db_pool: asyncpg.Pool[asyncpg.Record],
    sample_user_id: UUID,
    clean_db: None,
) -> UUID:
    """Create test user with bcrypt-hashed password."""
    async with db_pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO users (id, email, password_hash, role, created_at)
               VALUES ($1, $2, $3, $4, $5)""",
            sample_user_id,
            "alice.patient@example.com",
            bcrypt.hashpw("password123".encode(), bcrypt.gensalt()).decode(),
            "patient",
            datetime.now(timezone.utc),
        )
    return sample_user_id

@pytest.fixture
async def seed_test_patient(
    db_pool: asyncpg.Pool[asyncpg.Record],
    seed_test_user: UUID,  # Depends on seed_test_user
    sample_patient_id: UUID,
    sample_user_id: UUID,
) -> UUID:
    """Create test patient linked to user."""
    async with db_pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO patients (
                id, user_id, first_name, last_name,
                date_of_birth, medical_history, allergies, created_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)""",
            sample_patient_id,
            sample_user_id,
            "Alice",
            "Patient",
            date(1985, 5, 15),
            "No significant medical history",
            "Penicillin",
            datetime.now(timezone.utc),
        )
    return sample_patient_id
```

**Fixture Dependency Chain**:
```
clean_db (TRUNCATE all tables)
    ↓
seed_test_user (bcrypt password)
    ↓
seed_test_patient (linked to user)
```

### E2E Conftest (`tests/pytest/e2e/conftest.py`)

**Browser Fixture** (Parametrized, function-scoped):
```python
@pytest_asyncio.fixture(
    scope="function",
    params=["chromium", "firefox", "webkit"]
)
async def browser(request: FixtureRequest) -> AsyncGenerator[Browser, None]:
    """Fresh browser instance per test (prevents resource exhaustion)."""
    async with async_playwright() as p:
        browser_type = getattr(p, request.param)
        browser = await browser_type.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-dbus",  # Docker-specific
            ],
        )
        yield browser
        await browser.close()
```

**Context Fixture** (Clears localStorage):
```python
@pytest_asyncio.fixture
async def context(browser: Browser) -> AsyncGenerator[BrowserContext, None]:
    """CRITICAL: Clears localStorage and sessionStorage after test."""
    context = await browser.new_context()
    yield context
    # Clear auth tokens to prevent leakage between tests
    await context.clear_cookies()
    for page in context.pages:
        await page.evaluate("() => { localStorage.clear(); sessionStorage.clear(); }")
    await context.close()
```

**Authenticated Fixtures** (Role-based login):
```python
@pytest_asyncio.fixture
async def authenticated_patient_page(
    context: BrowserContext
) -> AsyncGenerator[Page, None]:
    """Logs in as alice.patient@example.com."""
    page = await context.new_page()

    # Login
    await page.goto("http://localhost:8850/login")
    await page.fill('input[name="email"]', "alice.patient@example.com")
    await page.fill('input[name="password"]', "password123")
    await page.click('button[type="submit"]')

    # Wait for redirect
    await page.wait_for_url("**/dashboard")

    # CRITICAL: Wait for Zustand auth store hydration
    await wait_for_auth_hydration(page)

    yield page
    await page.close()

@pytest_asyncio.fixture
async def authenticated_doctor_page(context: BrowserContext) -> AsyncGenerator[Page, None]:
    """Logs in as dr.smith@healthhub.com."""
    # Similar pattern...

@pytest_asyncio.fixture
async def authenticated_admin_page(context: BrowserContext) -> AsyncGenerator[Page, None]:
    """Logs in as admin@healthhub.com."""
    # Similar pattern...
```

## HealthHub-Specific Testing Patterns

### Effect Program Testing (Generator Stepping)

**Pattern**: Manually step through generator, yielding effects and sending results.

```python
class TestScheduleAppointmentProgram:
    def test_success_path(self) -> None:
        """Test complete appointment scheduling workflow."""
        patient_id = uuid4()
        doctor_id = uuid4()
        actor_id = uuid4()
        requested_time = datetime.now(timezone.utc) + timedelta(days=7)

        # Create mock domain objects
        mock_patient = Patient(
            id=patient_id,
            user_id=uuid4(),
            first_name="Alice",
            last_name="Patient",
            date_of_birth=date(1985, 5, 15),
            medical_history="None",
            allergies="Penicillin",
            created_at=datetime.now(timezone.utc),
        )

        mock_doctor = Doctor(
            id=doctor_id,
            user_id=uuid4(),
            first_name="John",
            last_name="Smith",
            specialization="Family Medicine",
            can_prescribe=True,
            created_at=datetime.now(timezone.utc),
        )

        mock_appointment = Appointment(
            id=uuid4(),
            patient_id=patient_id,
            doctor_id=doctor_id,
            status=Requested(requested_at=datetime.now(timezone.utc)),
            reason="Annual checkup",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        # Initialize generator
        program = schedule_appointment_program(
            patient_id=patient_id,
            doctor_id=doctor_id,
            requested_time=requested_time,
            reason="Annual checkup",
            actor_id=actor_id,
        )

        # Step 1: Expect GetPatientById effect
        effect1 = next(program)
        assert isinstance(effect1, GetPatientById)
        assert effect1.patient_id == patient_id

        # Step 2: Send patient result, expect GetDoctorById
        effect2 = program.send(mock_patient)
        assert isinstance(effect2, GetDoctorById)
        assert effect2.doctor_id == doctor_id

        # Step 3: Send doctor result, expect CreateAppointment
        effect3 = program.send(mock_doctor)
        assert isinstance(effect3, CreateAppointment)
        assert effect3.patient_id == patient_id
        assert effect3.doctor_id == doctor_id
        assert effect3.reason == "Annual checkup"

        # Step 4: Send appointment result, expect PublishWebSocketNotification
        effect4 = program.send(mock_appointment)
        assert isinstance(effect4, PublishWebSocketNotification)
        assert effect4.channel == f"doctor:{doctor_id}:notifications"

        # Step 5: Send notification result, expect LogAuditEvent
        effect5 = program.send(None)
        assert isinstance(effect5, LogAuditEvent)
        assert effect5.action == "create_appointment"
        assert effect5.user_id == actor_id

        # Step 6: Send audit result - program terminates
        with pytest.raises(StopIteration) as exc_info:
            program.send(None)

        # Extract return value from StopIteration
        result = exc_info.value.value
        assert result == mock_appointment
```

### Effect Interpreter Testing (pytest-mock)

**Pattern**: Mock all I/O using pytest-mock with AsyncMock.

```python
class TestHealthcareInterpreterPatientOperations:
    @pytest.mark.asyncio
    async def test_get_patient_by_id_found(self, mocker: MockerFixture) -> None:
        """GetPatientById interpreter with mocked database."""
        patient_id = uuid4()
        expected_patient = Patient(
            id=patient_id,
            user_id=uuid4(),
            first_name="Alice",
            last_name="Patient",
            date_of_birth=date(1985, 5, 15),
            medical_history="None",
            allergies="Penicillin",
            created_at=datetime.now(timezone.utc),
        )

        # Mock the database pool
        mock_pool = mocker.AsyncMock()
        mock_pool.fetchrow.return_value = {
            "id": expected_patient.id,
            "user_id": expected_patient.user_id,
            "first_name": expected_patient.first_name,
            "last_name": expected_patient.last_name,
            "date_of_birth": expected_patient.date_of_birth,
            "medical_history": expected_patient.medical_history,
            "allergies": expected_patient.allergies,
            "created_at": expected_patient.created_at,
        }

        interpreter = HealthcareInterpreter(mock_pool)

        # Execute effect
        effect = GetPatientById(patient_id=patient_id)
        result = await interpreter.handle(effect)

        # Verify result
        assert result == expected_patient

        # Verify mock called correctly
        mock_pool.fetchrow.assert_called_once()
        call_args = mock_pool.fetchrow.call_args
        assert "SELECT * FROM patients WHERE id = $1" in call_args[0][0]
        assert call_args[0][1] == patient_id

    @pytest.mark.asyncio
    async def test_get_patient_by_id_not_found(self, mocker: MockerFixture) -> None:
        """GetPatientById returns None when patient not found."""
        patient_id = uuid4()

        # Mock database returning None
        mock_pool = mocker.AsyncMock()
        mock_pool.fetchrow.return_value = None

        interpreter = HealthcareInterpreter(mock_pool)

        effect = GetPatientById(patient_id=patient_id)
        result = await interpreter.handle(effect)

        assert result is None
```

### Integration Testing (Multi-level Assertions)

**Pattern**: Verify program result, database persistence, and audit logs.

```python
class TestAppointmentScheduling:
    @pytest.mark.asyncio
    async def test_schedule_creates_db_record(
        self,
        db_pool: asyncpg.Pool[asyncpg.Record],
        redis_client: redis.Redis[bytes],
        seed_test_patient: UUID,
        seed_test_doctor: UUID,
        sample_user_id: UUID,
    ) -> None:
        """Test complete appointment scheduling workflow."""
        # Setup composite interpreter
        interpreter = CompositeInterpreter(
            pool=db_pool,
            redis_client=redis_client,
        )

        # Execute program with real infrastructure
        appointment = await run_program(
            schedule_appointment_program(
                patient_id=seed_test_patient,
                doctor_id=seed_test_doctor,
                requested_time=datetime(2024, 12, 15, 14, 0, 0, tzinfo=timezone.utc),
                reason="Annual checkup",
                actor_id=sample_user_id,
            ),
            interpreter,
        )

        # Level 1: Verify program result
        assert appointment is not None
        assert isinstance(appointment, Appointment)
        assert appointment.patient_id == seed_test_patient
        assert appointment.doctor_id == seed_test_doctor
        assert appointment.reason == "Annual checkup"
        assert isinstance(appointment.status, Requested)

        # Level 2: CRITICAL - Verify database persistence
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM appointments WHERE id = $1",
                appointment.id,
            )
            assert row is not None, "Appointment not persisted to database"
            assert row["patient_id"] == seed_test_patient
            assert row["doctor_id"] == seed_test_doctor
            assert row["reason"] == "Annual checkup"
            assert row["status"] == "requested"

        # Level 3: CRITICAL - Verify audit log created (HIPAA compliance)
        async with db_pool.acquire() as conn:
            audit_rows = await conn.fetch(
                """SELECT * FROM audit_log
                   WHERE resource_type = 'appointment' AND resource_id = $1""",
                appointment.id,
            )
            assert len(audit_rows) > 0, "No audit log entry created"
            audit_row = audit_rows[0]
            assert audit_row["action"] == "create_appointment"
            assert audit_row["user_id"] == sample_user_id
```

### E2E Testing (ADT-Based Synchronization)

**Pattern**: Wait for semantic state changes via ADT attributes, not timing hacks.

```python
from tests.pytest.e2e.helpers.adt_state_helpers import (
    wait_for_remote_data_state,
    wait_for_loading_complete,
)

@pytest.mark.asyncio
async def test_appointments_page_loads(authenticated_patient_page: Page) -> None:
    """Test appointments page loads with RemoteData state tracking."""
    page = authenticated_patient_page

    # Navigate to appointments page
    await page.goto("http://localhost:8850/appointments")

    # BEFORE (antipattern): await page.wait_for_timeout(5000)
    # AFTER (correct): Wait for RemoteData state to reach Success
    await wait_for_remote_data_state(page, "Success")

    # Now safe to interact with data-dependent elements
    appointments = page.locator('[data-testid="appointment-item"]')
    count = await appointments.count()
    assert count >= 0
```

**E2E Helper Functions** (`tests/pytest/e2e/helpers/adt_state_helpers.py`):

```python
async def wait_for_remote_data_state(
    page: Page,
    state: Literal["NotAsked", "Loading", "Failure", "Success"],
    timeout: int = 5000,
) -> Locator:
    """Wait for RemoteData ADT to reach specified state.

    Looks for: elements with data-state="{state}" attribute
    Example: <div data-state="Success">...</div>
    """
    return await page.wait_for_selector(
        f'[data-state="{state}"]',
        state="attached",
        timeout=timeout,
    )

async def wait_for_loading_complete(page: Page, timeout: int = 5000) -> None:
    """Wait for Loading state to disappear OR Success/Failure to appear."""
    try:
        # Wait for Loading to disappear
        await page.wait_for_selector(
            '[data-state="Loading"]',
            state="hidden",
            timeout=timeout,
        )
    except:
        # Or wait for Success/Failure to appear
        await page.wait_for_selector(
            '[data-state="Success"], [data-state="Failure"]',
            state="attached",
            timeout=timeout,
        )
```

**E2E Auth Helpers** (`tests/pytest/e2e/helpers/auth_helpers.py`):

```python
async def wait_for_auth_hydration(page: Page, timeout_ms: int = 10000) -> None:
    """Wait for Zustand auth store to hydrate from localStorage.

    Monitors: localStorage.getItem('healthhub-auth')['state']['authState']['type']
    Waits for: not 'Hydrating' state (e.g., 'Authenticated', 'Unauthenticated')

    Critical for WebKit which has slower localStorage access.
    """
    await page.wait_for_function(
        """() => {
            const authStore = localStorage.getItem('healthhub-auth');
            if (!authStore) return false;
            const state = JSON.parse(authStore);
            return state.state.authState.type !== 'Hydrating';
        }""",
        timeout=timeout_ms,
    )
```

## Healthcare Domain Anti-Patterns

### Anti-Pattern 1: Tests Pass When Features Broken
❌ **Wrong**: Expecting valid data to fail
```python
async def test_create_appointment(async_client: httpx.AsyncClient) -> None:
    response = await async_client.post("/api/appointments", json=valid_data)
    assert response.status_code == 422  # Valid data should succeed!
```

✅ **Correct**: Test valid inputs return expected results
```python
async def test_create_appointment(async_client: httpx.AsyncClient) -> None:
    response = await async_client.post("/api/appointments", json=valid_data)
    assert response.status_code == 201
    assert response.json()["id"] is not None
    assert response.json()["status"] == "requested"
```

### Anti-Pattern 2: Accepting "Not Implemented" (501)
❌ **Wrong**: `assert status_code in [200, 501]`

✅ **Correct**: Only accept 200/201 (feature must be implemented)

### Anti-Pattern 3: Silent Effect Failures
❌ **Wrong**: Not verifying side effects
```python
async def test_create_appointment(db_pool) -> None:
    appointment = await run_program(schedule_appointment_program(...), interpreter)
    assert appointment is not None  # But is it in the database?
```

✅ **Correct**: Verify all side effects (DB, Redis, audit logs)
```python
async def test_create_appointment(db_pool, redis_client) -> None:
    appointment = await run_program(schedule_appointment_program(...), interpreter)

    # Verify program result
    assert appointment is not None

    # Verify database persistence
    row = await db_pool.fetchrow("SELECT * FROM appointments WHERE id = $1", appointment.id)
    assert row is not None

    # Verify audit log created
    audit = await db_pool.fetch("SELECT * FROM audit_log WHERE resource_id = $1", appointment.id)
    assert len(audit) > 0
```

### Anti-Pattern 4: Testing Actions Without Validating Results
❌ **Wrong**: Submit form without checking success
```python
async def test_create_appointment_e2e(page: Page) -> None:
    await page.click("button[type='submit']")
    # Test ends - did it work?
```

✅ **Correct**: Verify success message + data
```python
async def test_create_appointment_e2e(page: Page) -> None:
    await page.click("button[type='submit']")
    await expect(page.locator(".success-message")).to_be_visible()

    # Verify appointment appears in list
    await wait_for_remote_data_state(page, "Success")
    appointment = page.locator('[data-testid="appointment-item"]').first
    await expect(appointment).to_contain_text("Annual checkup")
```

### Anti-Pattern 5: Using pytest.skip()
❌ **Wrong**: `@pytest.mark.skip(reason="TODO")`

✅ **Correct**: Let test FAIL or delete it

**Rule**: Zero skipped tests. 100% pass rate or fix the test.

### Anti-Pattern 6: Hardcoded Success
❌ **Wrong**: `assert True`

✅ **Correct**: Validate actual functionality

### Anti-Pattern 7: Overly Permissive Status Codes
❌ **Wrong**: `assert status_code in [200, 404, 500, 501]`

✅ **Correct**: Only accept success codes or specific error codes you're testing

### Anti-Pattern 8: Test Timeouts
❌ **Wrong**: Using `timeout` command with tests

✅ **Correct**: Let tests complete naturally (integration: ~1.5s is expected)

### Anti-Pattern 9: Missing Database Persistence Verification
❌ **Wrong**: Only verifying program return value
```python
async def test_create_appointment(db_pool) -> None:
    appointment = await run_program(...)
    assert appointment is not None  # Not enough!
```

✅ **Correct**: Verify database persistence
```python
async def test_create_appointment(db_pool) -> None:
    appointment = await run_program(...)
    assert appointment is not None

    # CRITICAL: Verify persisted to database
    row = await db_pool.fetchrow("SELECT * FROM appointments WHERE id = $1", appointment.id)
    assert row is not None
```

### Anti-Pattern 10: Incomplete Test Data
❌ **Wrong**: Missing required fields
```python
appointment_data = {
    "reason": "Checkup",
    # Missing: patient_id, doctor_id, requested_time
}
```

✅ **Correct**: Complete test data
```python
appointment_data = {
    "patient_id": str(patient_id),
    "doctor_id": str(doctor_id),
    "requested_time": datetime.now(timezone.utc).isoformat(),
    "reason": "Annual checkup",
}
```

### Anti-Pattern 11: String-Based Authorization
❌ **Wrong**: String comparisons for authorization
```python
if user.role == "doctor":
    # Can prescribe
```

✅ **Correct**: ADT pattern matching
```python
match auth_state:
    case DoctorAuthorized(can_prescribe=True):
        # Can prescribe
    case DoctorAuthorized(can_prescribe=False):
        # Cannot prescribe
    case _:
        # Unauthorized
```

### Anti-Pattern 12: String-Based Status
❌ **Wrong**: String status fields
```python
appointment.status = "confirmed"  # Mutable, error-prone
```

✅ **Correct**: ADT variants with context
```python
appointment.status = Confirmed(
    confirmed_at=datetime.now(timezone.utc),
    scheduled_time=datetime(2024, 12, 15, 14, 0, tzinfo=timezone.utc),
)
```

### Anti-Pattern 13: Missing Type Narrowing
❌ **Wrong**: Using effect result without isinstance check
```python
patient = yield GetPatientById(patient_id=patient_id)
greeting = f"Hello {patient.first_name}"  # Type error if patient is None
```

✅ **Correct**: Always narrow union types
```python
patient = yield GetPatientById(patient_id=patient_id)
if not isinstance(patient, Patient):
    return None
greeting = f"Hello {patient.first_name}"  # Type-safe
```

### Anti-Pattern 14: Direct Infrastructure Calls
❌ **Wrong**: Calling infrastructure directly in programs
```python
async def schedule_appointment(...):
    row = await db_pool.fetchrow("SELECT * FROM patients WHERE id = $1", patient_id)
    # Breaks separation of concerns
```

✅ **Correct**: Yield effects
```python
def schedule_appointment_program(...) -> Generator[AllEffects, EffectResult, ...]:
    patient = yield GetPatientById(patient_id=patient_id)
    # Effect interpreter handles database access
```

### Anti-Pattern 15: Unlogged PHI Access
❌ **Wrong**: Accessing patient data without audit trail
```python
def view_patient_program(patient_id: UUID) -> Generator[...]:
    patient = yield GetPatientById(patient_id=patient_id)
    return patient  # No audit log!
```

✅ **Correct**: LogAuditEvent for all PHI access
```python
def view_patient_program(patient_id: UUID, actor_id: UUID) -> Generator[...]:
    patient = yield GetPatientById(patient_id=patient_id)
    if not isinstance(patient, Patient):
        return None

    # CRITICAL: Log PHI access
    yield LogAuditEvent(
        user_id=actor_id,
        action="view_patient",
        resource_type="patient",
        resource_id=patient_id,
        ip_address=None,
        user_agent=None,
        metadata=None,
    )

    return patient
```

### Anti-Pattern 16: Success-Only Logging
❌ **Wrong**: Only logging successful operations
```python
if prescription_created:
    yield LogAuditEvent(action="create_prescription", ...)
```

✅ **Correct**: Log all attempts (including blocked)
```python
# Always log, regardless of outcome
yield LogAuditEvent(
    action="prescription_blocked_severe_interaction" if blocked else "create_prescription",
    ...
)
```

### Anti-Pattern 17: Real Infrastructure in Unit Tests
❌ **Wrong**: Connecting to PostgreSQL in backend tests
```python
async def test_get_patient():
    pool = await asyncpg.create_pool(...)  # Real DB!
    patient = await get_patient(pool, patient_id)
```

✅ **Correct**: pytest-mock only
```python
def test_get_patient(mocker: MockerFixture) -> None:
    mock_pool = mocker.AsyncMock()
    mock_pool.fetchrow.return_value = {...}
    interpreter = HealthcareInterpreter(mock_pool)
    # No real I/O
```

### Anti-Pattern 18: Missing Error Path Tests
❌ **Wrong**: Only testing happy path
```python
def test_create_prescription():
    result = create_prescription(valid_data)
    assert result is not None
```

✅ **Correct**: Test all error paths
```python
def test_create_prescription_success():
    # Happy path

def test_create_prescription_patient_not_found():
    # Error path 1

def test_create_prescription_severe_interaction():
    # Error path 2 - medication interaction blocks creation

def test_create_prescription_unauthorized_doctor():
    # Error path 3 - doctor cannot prescribe
```

### Anti-Pattern 19: Incomplete State Machine Tests
❌ **Wrong**: Not testing all transitions
```python
def test_confirm_appointment():
    # Only tests Requested → Confirmed
```

✅ **Correct**: Test all valid/invalid transitions
```python
def test_requested_to_confirmed():  # Valid
def test_requested_to_cancelled():  # Valid
def test_confirmed_to_in_progress():  # Valid
def test_confirmed_to_cancelled():  # Valid
def test_in_progress_to_completed():  # Valid
def test_in_progress_to_cancelled():  # Valid
def test_completed_to_requested():  # Invalid (terminal state)
def test_cancelled_to_confirmed():  # Invalid (terminal state)
```

### Anti-Pattern 20: Timing Hacks in E2E
❌ **Wrong**: Arbitrary timeouts
```python
await page.goto("/appointments")
await page.wait_for_timeout(5000)  # Hope data loaded?
```

✅ **Correct**: Wait for ADT state attributes
```python
await page.goto("/appointments")
await wait_for_remote_data_state(page, "Success")  # Semantic state change
```

### Anti-Pattern 21: Mutable Domain Models
❌ **Wrong**: Dataclasses without frozen=True
```python
@dataclass
class Patient:
    id: UUID
    first_name: str
    # Mutable - can be changed accidentally
```

✅ **Correct**: All models immutable
```python
@dataclass(frozen=True)
class Patient:
    id: UUID
    first_name: str
    # Immutable - cannot be changed after creation
```

### Anti-Pattern 22: Silent Notification Failures
❌ **Wrong**: Ignoring Redis pub/sub errors
```python
async def test_appointment_created(db_pool) -> None:
    appointment = await run_program(...)
    assert appointment is not None
    # But was notification sent?
```

✅ **Correct**: Verify messages published
```python
async def test_appointment_notification(db_pool, redis_client) -> None:
    pubsub = redis_client.pubsub()
    channel = f"doctor:{doctor_id}:notifications"
    await pubsub.subscribe(channel)

    appointment = await run_program(...)

    # Verify notification published
    message = await pubsub.get_message(timeout=2.0)
    assert message is not None
    assert message["type"] == "message"
    data = json.loads(message["data"])
    assert data["type"] == "appointment_requested"
```

## Test Data Management

### Sample IDs (Immutable UUIDs)

```python
User:         UUID("10000000-0000-0000-0000-000000000001")
Patient:      UUID("30000000-0000-0000-0000-000000000001")
Doctor:       UUID("40000000-0000-0000-0000-000000000001")
Appointment:  UUID("50000000-0000-0000-0000-000000000001")
Prescription: UUID("60000000-0000-0000-0000-000000000001")
Lab Result:   UUID("70000000-0000-0000-0000-000000000001")
```

### Seeding Pattern (Fixture Dependency Chain)

```
clean_db (TRUNCATE all tables in dependency order)
    ↓
seed_test_user (creates user with bcrypt password)
    ↓
seed_test_patient (linked to user)
seed_test_doctor (separate from patient chain)
```

### Test User Credentials (from seed_data.sql)

```python
TEST_PASSWORD = "password123"

TEST_USERS = {
    "admin": {"email": "admin@healthhub.com", "password": TEST_PASSWORD},
    "superadmin": {"email": "superadmin@healthhub.com", "password": TEST_PASSWORD},
    "doctor": {"email": "dr.smith@healthhub.com", "password": TEST_PASSWORD},
    "doctor2": {"email": "dr.johnson@healthhub.com", "password": TEST_PASSWORD},
    "patient": {"email": "alice.patient@example.com", "password": TEST_PASSWORD},
    "patient2": {"email": "bob.patient@example.com", "password": TEST_PASSWORD},
}
```

## Test Organization

### Directory Structure

```
tests/pytest/
├── backend/                  # Unit tests (pytest-mock)
│   ├── test_programs.py      # 799 lines, 80+ program tests
│   ├── test_interpreters.py  # 741 lines, 40+ interpreter tests
│   ├── test_effects.py       # Effect immutability tests
│   └── test_domain_models.py # ADT and state machine tests
├── integration/              # Real infrastructure tests
│   ├── test_appointment_workflows.py
│   ├── test_prescription_workflows.py
│   └── test_notification_infrastructure.py
├── e2e/                      # Playwright browser tests
│   ├── test_appointments.py
│   ├── test_prescriptions.py
│   ├── test_lab_results.py
│   ├── test_invoices.py
│   ├── test_login_flow.py
│   ├── test_rbac.py           # 21 tests (patient/doctor/admin access)
│   └── helpers/
│       ├── auth_helpers.py    # wait_for_auth_hydration, get_auth_state
│       └── adt_state_helpers.py  # wait_for_remote_data_state
└── conftest.py               # Root fixtures (252 lines)
```

### Naming Conventions

- Test files: `test_*.py`
- Test functions: `test_*`
- Test classes: `TestFeatureName`
- Helper functions: `_helper_name` (prefix with underscore)

## Success Criteria

All tests must meet Universal Success Criteria:
- ✅ Exit code 0
- ✅ Zero MyPy errors (mypy --strict)
- ✅ Zero stderr output
- ✅ Zero console warnings
- ✅ Zero skipped tests (pytest.skip() forbidden)
- ✅ 100% test pass rate
- ✅ Zero `Any`, `cast()`, or `# type: ignore`

## Test Output Management

**CRITICAL**: Bash tool truncates at 30,000 characters. Large test suites can exceed this.

**Required Pattern**:

```bash
# Step 1: Run tests with output redirection
docker compose -f docker/docker-compose.yml exec healthhub poetry run test-all > /tmp/test-output.txt 2>&1

# Step 2: Read complete output using Read tool
# (Read tool has no size limits)

# Step 3: Analyze ALL failures, not just visible ones
```

**Why This Matters**: Truncated output hides failures, making diagnosis impossible. File-based approach ensures complete output is always available.

**For all test categories**: Use pattern above with `test-backend`, `test-integration`, or specific test paths.

**Forbidden Practices**:
- ❌ Running tests via Bash tool and analyzing truncated stdout
- ❌ Drawing conclusions without seeing complete output
- ❌ Creating fix plans based on partial failure information

**Required Practices**:
- ✅ Always redirect to /tmp/, then read complete output
- ✅ Verify you have seen ALL test results before creating fix plans
- ✅ Let tests complete naturally (integration tests may take 1-2 seconds)

## Commands Reference

| Command | Purpose | Duration |
|---------|---------|----------|
| `poetry run test-all` | All tests | ~2s |
| `poetry run test-backend` | Backend unit tests only | ~0.5s |
| `poetry run test-integration` | Integration tests only | ~1.5s |
| `poetry run test-e2e` | E2E browser tests only | Variable |
| `poetry run check-code` | Black + MyPy | ~1s |

**Always prefix**: `docker compose -f docker/docker-compose.yml exec healthhub`

**With output capture**: Add `> /tmp/test-output.txt 2>&1` to any test command

## Healthcare Domain Testing Examples

### Authorization Testing

```python
# E2E: Patient cannot create prescriptions (RBAC)
@pytest.mark.asyncio
async def test_patient_cannot_create_prescriptions(
    authenticated_patient_page: Page
) -> None:
    """Test that patient does not see create prescription button."""
    page = authenticated_patient_page

    await page.goto("http://localhost:8850/prescriptions")
    await wait_for_remote_data_state(page, "Success")

    # Verify create button not visible
    create_button = page.locator('button[data-testid="create-prescription"]')
    is_visible = await create_button.is_visible()
    assert not is_visible, "Patient should not see create prescription button"
```

### State Machine Testing

```python
# Integration: Invalid transition blocked
@pytest.mark.asyncio
async def test_invalid_transition_blocked(
    db_pool: asyncpg.Pool[asyncpg.Record],
    redis_client: redis.Redis[bytes],
    seed_test_appointment: UUID,
) -> None:
    """Test that invalid state transition (Completed → Requested) is blocked."""
    interpreter = CompositeInterpreter(pool=db_pool, redis_client=redis_client)

    # First, transition to Completed state
    completed_appointment = await run_program(
        transition_appointment_program(
            appointment_id=seed_test_appointment,
            new_status=Completed(
                completed_at=datetime.now(timezone.utc),
                notes="Checkup completed successfully",
            ),
            actor_id=uuid4(),
        ),
        interpreter,
    )
    assert isinstance(completed_appointment.status, Completed)

    # Attempt invalid transition: Completed → Requested
    result = await run_program(
        transition_appointment_program(
            appointment_id=seed_test_appointment,
            new_status=Requested(requested_at=datetime.now(timezone.utc)),
            actor_id=uuid4(),
        ),
        interpreter,
    )

    # Transition should be rejected (returns None)
    assert result is None, "Invalid transition should be blocked"

    # Verify database unchanged
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT status FROM appointments WHERE id = $1",
            seed_test_appointment,
        )
        assert row["status"] == "completed", "Status should remain completed"
```

### HIPAA Audit Logging

```python
# Integration: Verify audit log created for prescription
@pytest.mark.asyncio
async def test_prescription_creates_audit_log(
    db_pool: asyncpg.Pool[asyncpg.Record],
    redis_client: redis.Redis[bytes],
    seed_test_patient: UUID,
    seed_test_doctor: UUID,
    sample_user_id: UUID,
) -> None:
    """Test that prescription creation logs audit event for HIPAA compliance."""
    interpreter = CompositeInterpreter(pool=db_pool, redis_client=redis_client)

    prescription = await run_program(
        create_prescription_program(
            patient_id=seed_test_patient,
            doctor_id=seed_test_doctor,
            medications=["Lisinopril 10mg"],
            instructions="Take once daily",
            actor_id=sample_user_id,
        ),
        interpreter,
    )

    assert prescription is not None

    # CRITICAL: Verify audit log entry created
    async with db_pool.acquire() as conn:
        audit_rows = await conn.fetch(
            """SELECT * FROM audit_log
               WHERE resource_type = 'prescription' AND resource_id = $1""",
            prescription.id,
        )
        assert len(audit_rows) > 0, "No audit log entry created"
        audit_row = audit_rows[0]
        assert audit_row["action"] == "create_prescription"
        assert audit_row["user_id"] == sample_user_id

        # Verify metadata includes medication info
        metadata = json.loads(audit_row["metadata"]) if audit_row["metadata"] else {}
        assert "medications" in metadata or "has_interaction_warning" in metadata
```

### Medication Interaction Testing

```python
# Integration: Severe interaction blocks prescription
@pytest.mark.asyncio
async def test_severe_interaction_blocks_prescription(
    db_pool: asyncpg.Pool[asyncpg.Record],
    redis_client: redis.Redis[bytes],
    seed_test_patient: UUID,
    seed_test_doctor: UUID,
    sample_user_id: UUID,
) -> None:
    """Test that severe medication interaction blocks prescription creation."""
    interpreter = CompositeInterpreter(pool=db_pool, redis_client=redis_client)

    # Attempt to create prescription with dangerous drug pair
    result = await run_program(
        create_prescription_program(
            patient_id=seed_test_patient,
            doctor_id=seed_test_doctor,
            medications=["warfarin", "aspirin"],  # Dangerous combination
            instructions="Take as directed",
            actor_id=sample_user_id,
        ),
        interpreter,
    )

    # Prescription should NOT be created
    # Program returns MedicationInteractionWarning instead
    assert isinstance(result, MedicationInteractionWarning)
    assert result.severity == "severe"
    assert "warfarin" in result.medications
    assert "aspirin" in result.medications

    # Verify prescription NOT persisted to database
    async with db_pool.acquire() as conn:
        count = await conn.fetchval(
            """SELECT COUNT(*) FROM prescriptions
               WHERE patient_id = $1 AND doctor_id = $2""",
            seed_test_patient,
            seed_test_doctor,
        )
        assert count == 0, "Prescription should not be persisted"

    # Verify blocked attempt logged in audit log
    async with db_pool.acquire() as conn:
        audit_row = await conn.fetchrow(
            """SELECT * FROM audit_log
               WHERE action = 'prescription_blocked_severe_interaction'
               AND user_id = $1""",
            sample_user_id,
        )
        assert audit_row is not None, "Blocked attempt should be logged"
```

## Troubleshooting

### Test fails with "missing required fields"
**Cause**: Test data missing required fields

**Fix**: Use complete test data with all required fields

### Integration test fails with "relation does not exist"
**Cause**: Database schema not initialized

**Fix**: Run `docker compose -f docker/docker-compose.yml exec healthhub poetry run python backend/scripts/init_db.py`

### E2E test fails with "Element not found"
**Cause**: Test running before page loaded, or ADT state not tracked

**Fix**: Use `wait_for_remote_data_state(page, "Success")` instead of `wait_for_timeout()`

### Test passes locally but fails in CI
**Cause**: Test depends on timing or local state

**Fix**:
1. Ensure `clean_db` fixture is used
2. Use ADT-based synchronization, not timeouts
3. Verify no hardcoded UUIDs (use sample_* fixtures)

### Redis pub/sub test fails intermittently
**Cause**: Message published before subscription established

**Fix**: Subscribe before executing program
```python
pubsub = redis_client.pubsub()
await pubsub.subscribe(channel)  # Subscribe FIRST
appointment = await run_program(...)  # Then execute
message = await pubsub.get_message(timeout=2.0)
```

---

**Last Updated**: 2025-11-26 (Comprehensive HealthHub testing doctrine)
