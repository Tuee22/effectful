"""
Type-safe converters for database rows to dataclasses.
Handles the explicit type conversion needed for mypy strict compliance.
Following ShipNorth patterns for object -> typed value conversion.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID


def safe_uuid(value: object) -> UUID:
    """Safely convert database value to UUID."""
    if isinstance(value, UUID):
        return value
    if isinstance(value, str):
        return UUID(value)
    raise TypeError(f"Cannot convert {type(value)} to UUID")


def safe_optional_uuid(value: object) -> UUID | None:
    """Safely convert database value to optional UUID."""
    if value is None:
        return None
    return safe_uuid(value)


def safe_str(value: object) -> str:
    """Safely convert database value to string."""
    if isinstance(value, str):
        return value
    if value is None:
        return ""
    return str(value)


def safe_optional_str(value: object) -> str | None:
    """Safely convert database value to optional string."""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return str(value)


def safe_int(value: object) -> int:
    """Safely convert database value to int."""
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(value)
    raise TypeError(f"Cannot convert {type(value)} to int")


def safe_optional_int(value: object) -> int | None:
    """Safely convert database value to optional int."""
    if value is None:
        return None
    return safe_int(value)


def safe_datetime(value: object) -> datetime:
    """Safely convert database value to datetime."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    raise TypeError(f"Cannot convert {type(value)} to datetime")


def safe_optional_datetime(value: object) -> datetime | None:
    """Safely convert database value to optional datetime."""
    if value is None:
        return None
    return safe_datetime(value)


def safe_date(value: object) -> date:
    """Safely convert database value to date."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    raise TypeError(f"Cannot convert {type(value)} to date")


def safe_optional_date(value: object) -> date | None:
    """Safely convert database value to optional date."""
    if value is None:
        return None
    return safe_date(value)


def safe_decimal(value: object) -> Decimal:
    """Safely convert database value to Decimal."""
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float, str)):
        return Decimal(str(value))
    raise TypeError(f"Cannot convert {type(value)} to Decimal")


def safe_optional_decimal(value: object) -> Decimal | None:
    """Safely convert database value to optional Decimal."""
    if value is None:
        return None
    return safe_decimal(value)


def safe_bool(value: object) -> bool:
    """Safely convert database value to bool."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("true", "1", "yes", "on")
    if isinstance(value, int):
        return bool(value)
    return bool(value)


def safe_invoice_status(
    value: object,
) -> Literal["draft", "sent", "paid", "overdue"]:
    """Safely convert database value to invoice status literal."""
    if isinstance(value, str) and value in ("draft", "sent", "paid", "overdue"):
        # mypy needs cast for literal narrowing from str
        if value == "draft":
            return "draft"
        if value == "sent":
            return "sent"
        if value == "paid":
            return "paid"
        return "overdue"
    raise TypeError(f"Invalid invoice status: {value}")


def safe_list_str(value: object) -> list[str]:
    """Safely convert database value to list of strings."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    raise TypeError(f"Cannot convert {type(value)} to list[str]")


def safe_dict_str_object(value: object) -> dict[str, object]:
    """Safely convert database value to dict[str, object]."""
    if value is None:
        return {}
    if isinstance(value, dict):
        return dict(value)
    raise TypeError(f"Cannot convert {type(value)} to dict[str, object]")
