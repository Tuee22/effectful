"""Pytest configuration and shared fixtures."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Iterator
from datetime import date, datetime, timezone
from uuid import UUID, uuid4

import asyncpg
import pytest
import redis.asyncio as redis
from pytest_mock import MockerFixture
from typing import NoReturn


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


async def _init_connection(conn: asyncpg.Connection[asyncpg.Record]) -> None:
    """Initialize connection with JSON codec for JSONB columns."""
    await conn.set_type_codec(
        "jsonb",
        encoder=json.dumps,
        decoder=json.loads,
        schema="pg_catalog",
    )
    await conn.set_type_codec(
        "json",
        encoder=json.dumps,
        decoder=json.loads,
        schema="pg_catalog",
    )


@pytest.fixture(scope="session")
def event_loop() -> Iterator[asyncio.AbstractEventLoop]:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def db_pool() -> AsyncIterator[asyncpg.Pool[asyncpg.Record]]:
    """Create database connection pool for integration tests."""
    pool: asyncpg.Pool[asyncpg.Record] = await asyncpg.create_pool(
        host="postgres",
        port=5432,
        database="healthhub_db",
        user="healthhub",
        password="healthhub_secure_pass",
        min_size=1,
        max_size=5,
        init=_init_connection,
    )

    assert pool is not None

    yield pool

    await pool.close()


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
async def redis_client() -> AsyncIterator[redis.Redis[bytes]]:
    """Create Redis client for integration tests."""
    client: redis.Redis[bytes] = redis.Redis(
        host="redis",
        port=6379,
        decode_responses=False,
    )

    yield client

    await client.aclose()


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


# Integration test data setup fixtures
@pytest.fixture
async def seed_test_user(
    db_pool: asyncpg.Pool[asyncpg.Record], sample_user_id: UUID, clean_db: None
) -> UUID:
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
    clean_db: None,
) -> UUID:
    """Seed a test doctor in the database."""
    # Create doctor user
    doctor_user_id = UUID("40000000-0000-0000-0000-000000000000")
    from app.auth.password import hash_password

    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO users (id, email, password_hash, role, status, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
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
