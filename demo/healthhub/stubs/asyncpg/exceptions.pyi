"""
Custom asyncpg exceptions type stubs.
"""

class PostgresError(Exception):
    """Base asyncpg error."""
    pass

class IntegrityConstraintViolationError(PostgresError):
    """Integrity constraint violation error."""
    pass

class UniqueViolationError(IntegrityConstraintViolationError):
    """Unique constraint violation error."""
    pass

class ForeignKeyViolationError(IntegrityConstraintViolationError):
    """Foreign key constraint violation error."""
    pass
