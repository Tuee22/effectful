"""Invoice and billing domain models."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID


@dataclass(frozen=True)
class LineItem:
    """Invoice line item.

    Immutable domain model following Effectful patterns.
    """

    id: UUID
    invoice_id: UUID
    description: str
    quantity: int
    unit_price: Decimal
    total: Decimal
    created_at: datetime


@dataclass(frozen=True)
class Invoice:
    """Healthcare invoice entity.

    Immutable domain model following Effectful patterns.
    """

    id: UUID
    patient_id: UUID
    appointment_id: UUID | None
    status: Literal["draft", "sent", "paid", "overdue"]
    subtotal: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    due_date: date | None
    paid_at: datetime | None
    created_at: datetime
    updated_at: datetime


# Invoice with line items (aggregate)
@dataclass(frozen=True)
class InvoiceWithLineItems:
    """Invoice aggregate with its line items."""

    invoice: Invoice
    line_items: list[LineItem]
