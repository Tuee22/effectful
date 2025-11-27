"""Doctor repository for database operations."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import asyncpg

from app.database import safe_bool, safe_datetime, safe_optional_str, safe_str, safe_uuid
from app.domain.doctor import Doctor


class DoctorRepository:
    """Repository for Doctor entity CRUD operations."""

    def __init__(self, pool: asyncpg.Pool[asyncpg.Record]) -> None:
        """Initialize repository with database pool.

        Args:
            pool: asyncpg connection pool
        """
        self.pool = pool

    async def get_by_id(self, doctor_id: UUID) -> Doctor | None:
        """Get doctor by ID.

        Args:
            doctor_id: Doctor UUID

        Returns:
            Doctor if found, None otherwise
        """
        row = await self.pool.fetchrow(
            """
            SELECT id, user_id, first_name, last_name, specialization,
                   license_number, can_prescribe, phone, created_at, updated_at
            FROM doctors
            WHERE id = $1
            """,
            doctor_id,
        )

        if row is None:
            return None

        return self._row_to_doctor(row)

    async def get_by_user_id(self, user_id: UUID) -> Doctor | None:
        """Get doctor by user ID.

        Args:
            user_id: User UUID

        Returns:
            Doctor if found, None otherwise
        """
        row = await self.pool.fetchrow(
            """
            SELECT id, user_id, first_name, last_name, specialization,
                   license_number, can_prescribe, phone, created_at, updated_at
            FROM doctors
            WHERE user_id = $1
            """,
            user_id,
        )

        if row is None:
            return None

        return self._row_to_doctor(row)

    async def create(
        self,
        user_id: UUID,
        first_name: str,
        last_name: str,
        specialization: str,
        license_number: str,
        can_prescribe: bool,
        phone: str | None,
    ) -> Doctor:
        """Create a new doctor.

        Args:
            user_id: User UUID (must exist)
            first_name: First name
            last_name: Last name
            specialization: Medical specialization
            license_number: Medical license number (must be unique)
            can_prescribe: Whether doctor can prescribe medications
            phone: Phone number (optional)

        Returns:
            Created doctor
        """
        now = datetime.now(timezone.utc)

        row = await self.pool.fetchrow(
            """
            INSERT INTO doctors (
                user_id, first_name, last_name, specialization,
                license_number, can_prescribe, phone, created_at, updated_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING id, user_id, first_name, last_name, specialization,
                      license_number, can_prescribe, phone, created_at, updated_at
            """,
            user_id,
            first_name,
            last_name,
            specialization,
            license_number,
            can_prescribe,
            phone,
            now,
            now,
        )

        if row is None:
            raise RuntimeError("Failed to create doctor")

        return self._row_to_doctor(row)

    def _row_to_doctor(self, row: asyncpg.Record) -> Doctor:
        """Convert database row to Doctor domain model.

        Args:
            row: Database row

        Returns:
            Doctor domain model
        """
        return Doctor(
            id=safe_uuid(row["id"]),
            user_id=safe_uuid(row["user_id"]),
            first_name=safe_str(row["first_name"]),
            last_name=safe_str(row["last_name"]),
            specialization=safe_str(row["specialization"]),
            license_number=safe_str(row["license_number"]),
            can_prescribe=safe_bool(row["can_prescribe"]),
            phone=safe_optional_str(row["phone"]),
            created_at=safe_datetime(row["created_at"]),
            updated_at=safe_datetime(row["updated_at"]),
        )
