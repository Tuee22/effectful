"""Invoice and billing domain models.

Boundary: PURITY
Target-Language: Haskell

Pure immutable data models for invoices and line items.
Payment status uses typed ADT variants, not string literals.
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from effectful.domain.optional_value import OptionalValue


@dataclass(frozen=True)
class LineItem:
    """Invoice line item.

    Immutable domain model following Effectful patterns.

    Attributes:
        id: Unique line item identifier
        invoice_id: Parent invoice UUID reference
        description: Line item description
        quantity: Item quantity
        unit_price: Price per unit
        total: Total line item price (quantity * unit_price)
        created_at: Timestamp when line item was created
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

    Attributes:
        id: Unique invoice identifier
        patient_id: Patient UUID reference
        appointment_id: Optional associated appointment UUID
        status: Invoice payment status
        subtotal: Subtotal before tax
        tax_amount: Tax amount
        total_amount: Total amount including tax
        due_date: Optional payment due date
        paid_at: Optional payment completion timestamp
        created_at: Timestamp when invoice was created
        updated_at: Timestamp of last update
    """

    id: UUID
    patient_id: UUID
    appointment_id: OptionalValue[UUID]
    status: Literal["draft", "sent", "paid", "overdue"]
    subtotal: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    due_date: OptionalValue[date]
    paid_at: OptionalValue[datetime]
    created_at: datetime
    updated_at: datetime


# Invoice with line items (aggregate)
@dataclass(frozen=True)
class InvoiceWithLineItems:
    """Invoice aggregate with its line items.

    Attributes:
        invoice: The invoice entity
        line_items: Tuple of associated line items
    """

    invoice: Invoice
    line_items: tuple[LineItem, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "line_items", tuple(self.line_items))
