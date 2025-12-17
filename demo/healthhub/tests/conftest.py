"""Pytest configuration and shared fixtures."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterator
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Protocol, TypeGuard
from uuid import UUID

import asyncpg
import pytest
import redis.asyncio as redis
from fastapi import FastAPI
from prometheus_client import CollectorRegistry
from typing import NoReturn

from effectful.algebraic.result import Ok
from effectful.effects.runtime import ResourceHandle
from effectful.programs.runners import run_ws_program

from app.config import Settings
from app.programs.startup import StartupAssembly, StaticMountSpec, shutdown_program, startup_program
from app.interpreters.runtime_interpreter import build_runtime_interpreter


# Override pytest.skip to enforce "zero skipped tests" policy
def _forbid_skip(*args: object, **kwargs: object) -> NoReturn:
    pytest.fail("Test skipping is forbidden")


pytest.skip = _forbid_skip


def assert_frozen(obj: object, attr: str, value: object) -> None:
    """Assert that frozen dataclass raises AttributeError on assignment.

    Centralizes type:ignore for immutability testing to single location.
    Frozen dataclasses are read-only at the type level, so assignment
    requires suppressing type check even though it's correct to test.

    Args:
        obj: Frozen dataclass instance to test
        attr: Attribute name to attempt assignment
        value: Value to attempt to assign

    Raises:
        AssertionError: If attribute assignment succeeds (object is mutable)
    """
    with pytest.raises(AttributeError):
        setattr(obj, attr, value)


class SupportsAclose(Protocol):
    async def aclose(self) -> None:
        ...


def has_aclose(pubsub: object) -> TypeGuard[SupportsAclose]:
    return hasattr(pubsub, "aclose")


async def close_pubsub(pubsub: redis.client.PubSub | SupportsAclose) -> None:
    """Close a Redis PubSub object safely."""
    assert has_aclose(pubsub)
    await pubsub.aclose()


@pytest.fixture
async def runtime_startup(tmp_path: Path) -> AsyncIterator[StartupAssembly]:
    """Start the runtime via pure startup program to obtain handles."""
    frontend_dir = tmp_path / "frontend-build"
    static_dir = frontend_dir / "static"
    assets_dir = frontend_dir / "assets"
    static_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)

    settings = Settings(
        postgres_host="postgres",
        postgres_port=5432,
        postgres_db="healthhub_db",
        postgres_user="healthhub",
        postgres_password="healthhub_secure_pass",
        redis_host="redis",
        redis_port=6379,
        redis_db=0,
        pulsar_url="pulsar://pulsar:6650",
        pulsar_admin_url="http://pulsar:8080",
        minio_endpoint="minio:9000",
        minio_access_key="minioadmin",
        minio_secret_key="minioadmin",
        minio_bucket="healthhub",
        minio_secure=False,
        jwt_secret_key="dev-secret",
        jwt_algorithm="HS256",
        jwt_access_token_expire_minutes=15,
        jwt_refresh_token_expire_days=7,
        cors_origins=["http://localhost:8851"],
        cors_allow_credentials=True,
        cors_allow_methods=["*"],
        cors_allow_headers=["*"],
        app_env="integration",
        log_level="INFO",
        frontend_build_path=str(frontend_dir),
    )

    app = FastAPI()
    runtime_interpreter = build_runtime_interpreter()
    startup_result = await run_ws_program(
        startup_program(
            settings=settings,
            app_handle=ResourceHandle(kind="fastapi_app", resource=app),
            routers=(),
            static_mounts=(
                StaticMountSpec(path="/static", directory=str(static_dir), name="static"),
                StaticMountSpec(path="/assets", directory=str(assets_dir), name="assets"),
            ),
            frontend_build_path=frontend_dir,
            collector_registry=CollectorRegistry(),
        ),
        runtime_interpreter,
    )

    if not isinstance(startup_result, Ok):
        pytest.fail(f"Runtime startup failed: {startup_result}")

    assembly = startup_result.value
    try:
        yield assembly
    finally:
        shutdown_result = await run_ws_program(shutdown_program(assembly), runtime_interpreter)
        if not isinstance(shutdown_result, Ok):
            pytest.fail(f"Runtime shutdown failed: {shutdown_result}")


@pytest.fixture
async def db_pool(runtime_startup: StartupAssembly) -> AsyncIterator[asyncpg.Pool[asyncpg.Record]]:
    """Provide the asyncpg pool created by the runtime interpreter."""
    yield runtime_startup.database_pool.resource


@pytest.fixture
async def clean_db(db_pool: asyncpg.Pool[asyncpg.Record]) -> None:
    """Clean database before each integration test."""
    async with db_pool.acquire() as conn:
        # TRUNCATE all tables in correct order (respecting foreign keys)
        await conn.execute("TRUNCATE TABLE audit_log CASCADE")
        await conn.execute("TRUNCATE TABLE invoice_line_items CASCADE")
        await conn.execute("TRUNCATE TABLE invoices CASCADE")
        await conn.execute("TRUNCATE TABLE lab_results CASCADE")
        await conn.execute("TRUNCATE TABLE prescriptions CASCADE")
        await conn.execute("TRUNCATE TABLE appointments CASCADE")
        await conn.execute("TRUNCATE TABLE doctors CASCADE")
        await conn.execute("TRUNCATE TABLE patients CASCADE")
        await conn.execute("TRUNCATE TABLE users CASCADE")

        # Seed a default user to satisfy audit_log foreign key constraints in tests
        from app.auth.password import hash_password

        default_user_id = UUID("10000000-0000-0000-0000-000000000001")
        now = datetime.now(timezone.utc)
        await conn.execute(
            """
            INSERT INTO users (id, email, password_hash, role, status, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            default_user_id,
            "default_audit_user@example.com",
            hash_password("password123"),
            "patient",
            "active",
            now,
            now,
        )


@pytest.fixture
async def redis_client(
    runtime_startup: StartupAssembly,
) -> AsyncIterator[redis.Redis[bytes]]:
    """Provide Redis client via runtime-managed factory."""
    factory = runtime_startup.redis_factory.resource
    async with factory.managed() as client:
        yield client


async def _clear_all_redis_keys(client: redis.Redis[bytes]) -> None:
    """Clear all Redis keys to ensure clean state."""
    cursor: int = 0
    while True:
        cursor, keys = await client.scan(cursor=cursor, match="*", count=1000)
        if keys:
            # Keys are bytes; decode to str for delete signature
            decoded_keys = [
                k.decode("utf-8") if isinstance(k, (bytes, bytearray)) else str(k) for k in keys
            ]
            await client.delete(*decoded_keys)
        if cursor == 0:
            break


@pytest.fixture
async def clean_healthhub_state(
    db_pool: asyncpg.Pool[asyncpg.Record],
    runtime_startup: StartupAssembly,
) -> AsyncIterator[None]:
    """Fixture-level isolation: Idempotent base state across all microservices.

    Ensures every test starts with the SAME deterministic state by:
    1. Truncating all PostgreSQL tables
    2. Loading seed_data.sql (2 admins, 4 doctors, 5 patients + sample data)
    3. Clearing all Redis keys (cache, rate limits, notifications)
    4. (MinIO/Pulsar cleanup would go here if actively used)

    This fixture enforces the DRY principle: isolation and reproducibility
    managed in ONE place rather than scattered across test files.

    Usage in e2e tests:
        @pytest.mark.asyncio
        async def test_something(clean_healthhub_state, page):
            # Test starts with known seed data state
            ...

    SSoT: Phase 6 of tutorial refactor plan (fixture-level isolation doctrine).
    """
    # 1. Clean PostgreSQL: Truncate all tables
    async with db_pool.acquire() as conn:
        await conn.execute("TRUNCATE TABLE audit_log CASCADE")
        await conn.execute("TRUNCATE TABLE invoice_line_items CASCADE")
        await conn.execute("TRUNCATE TABLE invoices CASCADE")
        await conn.execute("TRUNCATE TABLE lab_results CASCADE")
        await conn.execute("TRUNCATE TABLE prescriptions CASCADE")
        await conn.execute("TRUNCATE TABLE appointments CASCADE")
        await conn.execute("TRUNCATE TABLE doctors CASCADE")
        await conn.execute("TRUNCATE TABLE patients CASCADE")
        await conn.execute("TRUNCATE TABLE users CASCADE")

    # 2. Load deterministic seed data from seed_data.sql
    import subprocess
    from pathlib import Path

    seed_file = Path(__file__).parent.parent / "backend" / "scripts" / "seed_data.sql"
    result = subprocess.run(
        [
            "psql",
            "-h",
            "postgres",
            "-p",
            "5432",
            "-U",
            "healthhub",
            "-d",
            "healthhub_db",
            "-f",
            str(seed_file),
        ],
        env={**subprocess.os.environ, "PGPASSWORD": "healthhub_secure_pass"},
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        pytest.fail(f"Failed to load seed data: {result.stderr}")

    # 3. Clean Redis: Clear all keys
    redis_factory = runtime_startup.redis_factory.resource
    async with redis_factory.managed() as client:
        await _clear_all_redis_keys(client)

    # 4. (Future) MinIO cleanup would go here:
    # - Delete all buckets and objects
    # - Recreate default buckets if needed

    # 5. (Future) Pulsar cleanup would go here:
    # - Delete topics or clear messages
    # - Reset consumer positions

    yield

    # Post-test cleanup (optional, but ensures no leakage)
    async with redis_factory.managed() as client:
        await _clear_all_redis_keys(client)


@pytest.fixture
async def observability_interpreter(
    runtime_startup: StartupAssembly,
) -> AsyncIterator[object]:
    """Provide observability interpreter handle created by startup program."""
    yield runtime_startup.observability.resource


# Sample data fixtures for testing
@pytest.fixture
def sample_user_id() -> UUID:
    """Sample user ID for testing."""
    return UUID("10000000-0000-0000-0000-000000000001")


@pytest.fixture
def sample_patient_id() -> UUID:
    """Sample patient ID for testing."""
    return UUID("30000000-0000-0000-0000-000000000001")


@pytest.fixture
def sample_doctor_id() -> UUID:
    """Sample doctor ID for testing."""
    return UUID("40000000-0000-0000-0000-000000000001")


@pytest.fixture
def sample_appointment_id() -> UUID:
    """Sample appointment ID for testing."""
    return UUID("50000000-0000-0000-0000-000000000001")


@pytest.fixture
def sample_prescription_id() -> UUID:
    """Sample prescription ID for testing."""
    return UUID("60000000-0000-0000-0000-000000000001")


@pytest.fixture
def sample_lab_result_id() -> UUID:
    """Sample lab result ID for testing."""
    return UUID("70000000-0000-0000-0000-000000000001")


@pytest.fixture
def sample_date_of_birth() -> date:
    """Sample date of birth for testing."""
    return date(1985, 5, 15)


@pytest.fixture
def sample_datetime() -> datetime:
    """Sample datetime for testing."""
    return datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)


# Authorization fixtures
@pytest.fixture
async def unauthorized_doctor(
    db_pool: asyncpg.Pool[asyncpg.Record],
) -> tuple[UUID, UUID]:
    """Seed a doctor who cannot prescribe (returns doctor_id, user_id)."""
    unauthorized_doctor_id = UUID("99000000-0000-0000-0000-000000000001")
    unauthorized_user_id = UUID("99000000-0000-0000-0000-000000000000")

    from app.auth.password import hash_password

    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO users (id, email, password_hash, role, status, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (id) DO NOTHING
            """,
            unauthorized_user_id,
            "unauthorized@example.com",
            hash_password("password123"),
            "doctor",
            "active",
            datetime.now(timezone.utc),
            datetime.now(timezone.utc),
        )

        await conn.execute(
            """
            INSERT INTO doctors (
                id, user_id, first_name, last_name, specialization,
                license_number, can_prescribe, created_at, updated_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            ON CONFLICT (id) DO NOTHING
            """,
            unauthorized_doctor_id,
            unauthorized_user_id,
            "Bob",
            "Johnson",
            "Dentistry",
            "DDS-99999",
            False,
            datetime.now(timezone.utc),
            datetime.now(timezone.utc),
        )

    return unauthorized_doctor_id, unauthorized_user_id


# Integration test data setup fixtures
@pytest.fixture
async def seed_test_user(db_pool: asyncpg.Pool[asyncpg.Record], sample_user_id: UUID) -> UUID:
    """Seed a test user in the database."""
    from app.auth.password import hash_password

    async with db_pool.acquire() as conn:
        existing = await conn.fetchval(
            "SELECT 1 FROM users WHERE id = $1",
            sample_user_id,
        )
        if existing is None:
            await conn.execute(
                """
                INSERT INTO users (id, email, password_hash, role, status, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                sample_user_id,
                "test@example.com",
                hash_password("password123"),
                "patient",
                "active",
                datetime.now(timezone.utc),
                datetime.now(timezone.utc),
            )

    return sample_user_id


@pytest.fixture
async def seed_test_patient(
    db_pool: asyncpg.Pool[asyncpg.Record],
    seed_test_user: UUID,
    sample_patient_id: UUID,
    sample_date_of_birth: date,
) -> UUID:
    """Seed a test patient in the database."""
    async with db_pool.acquire() as conn:
        existing_patient = await conn.fetchval(
            "SELECT 1 FROM patients WHERE id = $1",
            sample_patient_id,
        )
        if existing_patient is None:
            await conn.execute(
                """
                INSERT INTO patients (
                    id, user_id, first_name, last_name, date_of_birth,
                    blood_type, allergies, insurance_id, emergency_contact,
                    phone, address, created_at, updated_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                """,
                sample_patient_id,
                seed_test_user,
                "John",
                "Doe",
                sample_date_of_birth,
                "O+",
                [],
                "INS-12345",
                "Jane Doe: 555-0100",
                "555-0123",
                "123 Main St",
                datetime.now(timezone.utc),
                datetime.now(timezone.utc),
            )

    return sample_patient_id


@pytest.fixture
async def seed_test_doctor(
    db_pool: asyncpg.Pool[asyncpg.Record],
    sample_doctor_id: UUID,
) -> UUID:
    """Seed a test doctor in the database."""
    # Create doctor user
    doctor_user_id = UUID("40000000-0000-0000-0000-000000000000")
    from app.auth.password import hash_password

    async with db_pool.acquire() as conn:
        existing_doctor = await conn.fetchval(
            "SELECT 1 FROM doctors WHERE id = $1",
            sample_doctor_id,
        )

        if existing_doctor is None:
            await conn.execute(
                """
                INSERT INTO users (id, email, password_hash, role, status, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (id) DO NOTHING
                """,
                doctor_user_id,
                "doctor@example.com",
                hash_password("password123"),
                "doctor",
                "active",
                datetime.now(timezone.utc),
                datetime.now(timezone.utc),
            )

            await conn.execute(
                """
                INSERT INTO doctors (
                    id, user_id, first_name, last_name, specialization,
                    license_number, can_prescribe, created_at, updated_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """,
                sample_doctor_id,
                doctor_user_id,
                "Jane",
                "Smith",
                "Cardiology",
                "MD-12345",
                True,
                datetime.now(timezone.utc),
                datetime.now(timezone.utc),
            )

    return sample_doctor_id
