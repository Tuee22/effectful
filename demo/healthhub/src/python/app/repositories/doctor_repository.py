"""Doctor repository for database operations."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import asyncpg

from app.protocols.database import DatabasePool
from app.database import safe_bool, safe_datetime, safe_optional_str, safe_str, safe_uuid
from effectful.domain.optional_value import Absent, OptionalValue, Provided
from app.domain.doctor import Doctor
from effectful.domain.optional_value import to_optional_value


class DoctorRepository:
    """Repository for Doctor entity CRUD operations."""

    def __init__(self, pool: DatabasePool) -> None:
        """Initialize repository with database pool.

        Args:
            pool: Database pool protocol (production or test mock)
        """
        self.pool = pool

    async def get_by_id(self, doctor_id: UUID) -> OptionalValue[Doctor]:
        """Get doctor by ID.

        Args:
            doctor_id: Doctor UUID

        Returns:
            Provided[Doctor] if found, Absent otherwise with explicit reason
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
            return Absent(reason="doctor_not_found")

        return Provided(self._row_to_doctor(row))

    async def get_by_user_id(self, user_id: UUID) -> OptionalValue[Doctor]:
        """Get doctor by user ID.

        Args:
            user_id: User UUID

        Returns:
            Provided[Doctor] if found, Absent otherwise with explicit reason
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
            return Absent(reason="doctor_not_found")

        return Provided(self._row_to_doctor(row))

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

        assert row is not None, "Database insert returned no doctor row"

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
            phone=to_optional_value(safe_optional_str(row["phone"]), reason="not_recorded"),
            created_at=safe_datetime(row["created_at"]),
            updated_at=safe_datetime(row["updated_at"]),
        )
