"""Patient repository for database operations."""

from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import UUID

import asyncpg

from app.protocols.database import DatabasePool
from app.database import (
    safe_date,
    safe_datetime,
    safe_list_str,
    safe_optional_str,
    safe_str,
    safe_uuid,
)
from app.domain.patient import Patient
from effectful.domain.optional_value import to_optional_value


class PatientRepository:
    """Repository for Patient entity CRUD operations."""

    def __init__(self, pool: DatabasePool) -> None:
        """Initialize repository with database pool.

        Args:
            pool: Database pool protocol (production or test mock)
        """
        self.pool = pool

    async def get_by_id(self, patient_id: UUID) -> Patient | None:
        """Get patient by ID.

        Args:
            patient_id: Patient UUID

        Returns:
            Patient if found, None otherwise
        """
        row = await self.pool.fetchrow(
            """
            SELECT id, user_id, first_name, last_name, date_of_birth,
                   blood_type, allergies, insurance_id, emergency_contact,
                   phone, address, created_at, updated_at
            FROM patients
            WHERE id = $1
            """,
            patient_id,
        )

        if row is None:
            return None

        return self._row_to_patient(row)

    async def get_by_user_id(self, user_id: UUID) -> Patient | None:
        """Get patient by user ID.

        Args:
            user_id: User UUID

        Returns:
            Patient if found, None otherwise
        """
        row = await self.pool.fetchrow(
            """
            SELECT id, user_id, first_name, last_name, date_of_birth,
                   blood_type, allergies, insurance_id, emergency_contact,
                   phone, address, created_at, updated_at
            FROM patients
            WHERE user_id = $1
            """,
            user_id,
        )

        if row is None:
            return None

        return self._row_to_patient(row)

    async def create(
        self,
        user_id: UUID,
        first_name: str,
        last_name: str,
        date_of_birth: date,
        blood_type: str | None,
        allergies: list[str],
        insurance_id: str | None,
        emergency_contact: str,
        phone: str | None,
        address: str | None,
    ) -> Patient:
        """Create a new patient.

        Args:
            user_id: User UUID (must exist)
            first_name: First name
            last_name: Last name
            date_of_birth: Date of birth
            blood_type: Blood type (optional)
            allergies: List of allergies
            insurance_id: Insurance ID (optional)
            emergency_contact: Emergency contact info
            phone: Phone number (optional)
            address: Address (optional)

        Returns:
            Created patient
        """
        now = datetime.now(timezone.utc)

        row = await self.pool.fetchrow(
            """
            INSERT INTO patients (
                user_id, first_name, last_name, date_of_birth,
                blood_type, allergies, insurance_id, emergency_contact,
                phone, address, created_at, updated_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            RETURNING id, user_id, first_name, last_name, date_of_birth,
                      blood_type, allergies, insurance_id, emergency_contact,
                      phone, address, created_at, updated_at
            """,
            user_id,
            first_name,
            last_name,
            date_of_birth,
            blood_type,
            allergies,
            insurance_id,
            emergency_contact,
            phone,
            address,
            now,
            now,
        )

        assert row is not None, "Database insert returned no patient row"

        return self._row_to_patient(row)

    def _row_to_patient(self, row: asyncpg.Record) -> Patient:
        """Convert database row to Patient domain model.

        Args:
            row: Database row

        Returns:
            Patient domain model
        """
        return Patient(
            id=safe_uuid(row["id"]),
            user_id=safe_uuid(row["user_id"]),
            first_name=safe_str(row["first_name"]),
            last_name=safe_str(row["last_name"]),
            date_of_birth=safe_date(row["date_of_birth"]),
            blood_type=to_optional_value(
                safe_optional_str(row["blood_type"]), reason="not_recorded"
            ),
            allergies=tuple(safe_list_str(row["allergies"])),
            insurance_id=to_optional_value(
                safe_optional_str(row["insurance_id"]), reason="not_recorded"
            ),
            emergency_contact=safe_str(row["emergency_contact"]),
            phone=to_optional_value(safe_optional_str(row["phone"]), reason="not_recorded"),
            address=to_optional_value(safe_optional_str(row["address"]), reason="not_recorded"),
            created_at=safe_datetime(row["created_at"]),
            updated_at=safe_datetime(row["updated_at"]),
        )
