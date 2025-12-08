"""User repository for database operations."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import asyncpg

from app.protocols.database import DatabasePool
from app.database import safe_datetime, safe_optional_datetime, safe_str, safe_uuid
from effectful.domain.optional_value import to_optional_value
from app.domain.user import User, UserRole, UserStatus


class UserRepository:
    """Repository for User entity CRUD operations."""

    def __init__(self, pool: DatabasePool) -> None:
        """Initialize repository with database pool.

        Args:
            pool: Database pool protocol (production or test mock)
        """
        self.pool = pool

    async def create(
        self,
        email: str,
        password_hash: str,
        role: UserRole,
    ) -> User:
        """Create a new user.

        Args:
            email: User email (must be unique)
            password_hash: Bcrypt password hash
            role: User role (patient, doctor, admin)

        Returns:
            Created user

        Raises:
            asyncpg.UniqueViolationError: If email already exists
        """
        now = datetime.now(timezone.utc)

        row = await self.pool.fetchrow(
            """
            INSERT INTO users (email, password_hash, role, status, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id, email, password_hash, role, status, last_login, created_at, updated_at
            """,
            email,
            password_hash,
            role.value,
            UserStatus.ACTIVE.value,
            now,
            now,
        )

        assert row is not None, "Database insert returned no user row"

        return self._row_to_user(row)

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Get user by ID.

        Args:
            user_id: User UUID

        Returns:
            User if found, None otherwise
        """
        row = await self.pool.fetchrow(
            """
            SELECT id, email, password_hash, role, status, last_login, created_at, updated_at
            FROM users
            WHERE id = $1
            """,
            user_id,
        )

        if row is None:
            return None

        return self._row_to_user(row)

    async def get_by_email(self, email: str) -> User | None:
        """Get user by email.

        Args:
            email: User email

        Returns:
            User if found, None otherwise
        """
        row = await self.pool.fetchrow(
            """
            SELECT id, email, password_hash, role, status, last_login, created_at, updated_at
            FROM users
            WHERE email = $1
            """,
            email,
        )

        if row is None:
            return None

        return self._row_to_user(row)

    async def update_last_login(self, user_id: UUID) -> None:
        """Update user's last login timestamp.

        Args:
            user_id: User UUID
        """
        now = datetime.now(timezone.utc)

        await self.pool.execute(
            """
            UPDATE users
            SET last_login = $1, updated_at = $2
            WHERE id = $3
            """,
            now,
            now,
            user_id,
        )

    def _row_to_user(self, row: asyncpg.Record) -> User:
        """Convert database row to User domain model.

        Args:
            row: Database row

        Returns:
            User domain model
        """
        return User(
            id=safe_uuid(row["id"]),
            email=safe_str(row["email"]),
            password_hash=safe_str(row["password_hash"]),
            role=UserRole(safe_str(row["role"])),
            status=UserStatus(safe_str(row["status"])),
            last_login=to_optional_value(
                safe_optional_datetime(row["last_login"]), reason="never_logged_in"
            ),
            created_at=safe_datetime(row["created_at"]),
            updated_at=safe_datetime(row["updated_at"]),
        )
