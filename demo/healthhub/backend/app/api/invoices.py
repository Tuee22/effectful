"""Invoices API endpoints.

Provides CRUD operations for healthcare invoices and billing.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.database import (
    safe_datetime,
    safe_decimal,
    safe_int,
    safe_invoice_status,
    safe_optional_date,
    safe_optional_datetime,
    safe_optional_uuid,
    safe_str,
    safe_uuid,
)
from app.domain.invoice import Invoice, LineItem, InvoiceWithLineItems
from app.infrastructure import get_database_manager
from app.api.dependencies import (
    AdminAuthorized,
    DoctorAuthorized,
    PatientAuthorized,
    require_authenticated,
    require_doctor_or_admin,
)

router = APIRouter()


class LineItemResponse(BaseModel):
    """Line item response model."""

    id: str
    invoice_id: str
    description: str
    quantity: int
    unit_price: float
    total: float
    created_at: datetime


class InvoiceResponse(BaseModel):
    """Invoice response model."""

    id: str
    patient_id: str
    appointment_id: str | None
    status: Literal["draft", "sent", "paid", "overdue"]
    subtotal: float
    tax_amount: float
    total_amount: float
    due_date: date | None
    paid_at: datetime | None
    created_at: datetime
    updated_at: datetime


class InvoiceWithLineItemsResponse(BaseModel):
    """Invoice with line items response model."""

    invoice: InvoiceResponse
    line_items: list[LineItemResponse]


class CreateInvoiceRequest(BaseModel):
    """Create invoice request."""

    patient_id: str
    appointment_id: str | None = None
    due_date: date | None = None


class CreateLineItemRequest(BaseModel):
    """Create line item request."""

    description: str
    quantity: int = 1
    unit_price: float


class UpdateInvoiceStatusRequest(BaseModel):
    """Update invoice status request."""

    status: Literal["draft", "sent", "paid", "overdue"]


def _row_to_invoice(row: dict[str, object]) -> Invoice:
    """Convert database row to Invoice domain model."""
    return Invoice(
        id=safe_uuid(row["id"]),
        patient_id=safe_uuid(row["patient_id"]),
        appointment_id=safe_optional_uuid(row.get("appointment_id")),
        status=safe_invoice_status(row["status"]),
        subtotal=safe_decimal(row["subtotal"]),
        tax_amount=safe_decimal(row["tax_amount"]),
        total_amount=safe_decimal(row["total_amount"]),
        due_date=safe_optional_date(row.get("due_date")),
        paid_at=safe_optional_datetime(row.get("paid_at")),
        created_at=safe_datetime(row["created_at"]),
        updated_at=safe_datetime(row["updated_at"]),
    )


def _row_to_line_item(row: dict[str, object]) -> LineItem:
    """Convert database row to LineItem domain model."""
    return LineItem(
        id=safe_uuid(row["id"]),
        invoice_id=safe_uuid(row["invoice_id"]),
        description=safe_str(row["description"]),
        quantity=safe_int(row["quantity"]),
        unit_price=safe_decimal(row["unit_price"]),
        total=safe_decimal(row["total"]),
        created_at=safe_datetime(row["created_at"]),
    )


def invoice_to_response(invoice: Invoice) -> InvoiceResponse:
    """Convert Invoice domain model to API response."""
    return InvoiceResponse(
        id=str(invoice.id),
        patient_id=str(invoice.patient_id),
        appointment_id=str(invoice.appointment_id) if invoice.appointment_id else None,
        status=invoice.status,
        subtotal=float(invoice.subtotal),
        tax_amount=float(invoice.tax_amount),
        total_amount=float(invoice.total_amount),
        due_date=invoice.due_date,
        paid_at=invoice.paid_at,
        created_at=invoice.created_at,
        updated_at=invoice.updated_at,
    )


def line_item_to_response(line_item: LineItem) -> LineItemResponse:
    """Convert LineItem domain model to API response."""
    return LineItemResponse(
        id=str(line_item.id),
        invoice_id=str(line_item.invoice_id),
        description=line_item.description,
        quantity=line_item.quantity,
        unit_price=float(line_item.unit_price),
        total=float(line_item.total),
        created_at=line_item.created_at,
    )


@router.get("/", response_model=list[InvoiceResponse])
async def list_invoices(
    auth: Annotated[
        PatientAuthorized | DoctorAuthorized | AdminAuthorized,
        Depends(require_authenticated),
    ],
) -> list[InvoiceResponse]:
    """List invoices with role-based filtering.

    - Patient: sees only their own invoices
    - Doctor/Admin: sees all invoices
    """
    db_manager = get_database_manager()
    pool = db_manager.get_pool()

    # Build query based on role
    match auth:
        case PatientAuthorized(patient_id=patient_id):
            query = """
                SELECT id, patient_id, appointment_id, status, subtotal,
                       tax_amount, total_amount, due_date, paid_at,
                       created_at, updated_at
                FROM invoices
                WHERE patient_id = $1
                ORDER BY created_at DESC
            """
            rows = await pool.fetch(query, patient_id)

        case DoctorAuthorized() | AdminAuthorized():
            query = """
                SELECT id, patient_id, appointment_id, status, subtotal,
                       tax_amount, total_amount, due_date, paid_at,
                       created_at, updated_at
                FROM invoices
                ORDER BY created_at DESC
            """
            rows = await pool.fetch(query)

    invoices = [_row_to_invoice(dict(row)) for row in rows]
    return [invoice_to_response(inv) for inv in invoices]


@router.post("/", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    request: CreateInvoiceRequest,
    auth: Annotated[
        DoctorAuthorized | AdminAuthorized,
        Depends(require_doctor_or_admin),
    ],
) -> InvoiceResponse:
    """Create a new invoice.

    Requires: Doctor or Admin role.
    """
    db_manager = get_database_manager()
    pool = db_manager.get_pool()

    row = await pool.fetchrow(
        """
        INSERT INTO invoices (patient_id, appointment_id, due_date)
        VALUES ($1, $2, $3)
        RETURNING id, patient_id, appointment_id, status, subtotal,
                  tax_amount, total_amount, due_date, paid_at,
                  created_at, updated_at
        """,
        UUID(request.patient_id),
        UUID(request.appointment_id) if request.appointment_id else None,
        request.due_date,
    )

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create invoice",
        )

    invoice = _row_to_invoice(dict(row))
    return invoice_to_response(invoice)


@router.get("/{invoice_id}", response_model=InvoiceWithLineItemsResponse)
async def get_invoice(
    invoice_id: str,
    auth: Annotated[
        PatientAuthorized | DoctorAuthorized | AdminAuthorized,
        Depends(require_authenticated),
    ],
) -> InvoiceWithLineItemsResponse:
    """Get invoice by ID with line items.

    Requires appropriate authorization.
    """
    db_manager = get_database_manager()
    pool = db_manager.get_pool()

    # Get invoice
    invoice_row = await pool.fetchrow(
        """
        SELECT id, patient_id, appointment_id, status, subtotal,
               tax_amount, total_amount, due_date, paid_at,
               created_at, updated_at
        FROM invoices
        WHERE id = $1
        """,
        UUID(invoice_id),
    )

    if invoice_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice {invoice_id} not found",
        )

    invoice = _row_to_invoice(dict(invoice_row))

    # Authorization check - patient can only see their own invoices
    match auth:
        case PatientAuthorized(patient_id=patient_id):
            if invoice.patient_id != patient_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to view this invoice",
                )
        case _:
            pass  # Doctors and admins can view any invoice

    # Get line items
    line_item_rows = await pool.fetch(
        """
        SELECT id, invoice_id, description, quantity, unit_price, total, created_at
        FROM invoice_line_items
        WHERE invoice_id = $1
        ORDER BY created_at
        """,
        UUID(invoice_id),
    )

    line_items = [_row_to_line_item(dict(row)) for row in line_item_rows]

    return InvoiceWithLineItemsResponse(
        invoice=invoice_to_response(invoice),
        line_items=[line_item_to_response(li) for li in line_items],
    )


@router.post(
    "/{invoice_id}/line-items", response_model=LineItemResponse, status_code=status.HTTP_201_CREATED
)
async def add_line_item(
    invoice_id: str,
    request: CreateLineItemRequest,
    auth: Annotated[
        DoctorAuthorized | AdminAuthorized,
        Depends(require_doctor_or_admin),
    ],
) -> LineItemResponse:
    """Add a line item to an invoice.

    Requires: Doctor or Admin role.
    Also updates the invoice totals.
    """
    db_manager = get_database_manager()
    pool = db_manager.get_pool()

    # Calculate total for the line item
    total = request.quantity * request.unit_price

    # Insert line item
    line_item_row = await pool.fetchrow(
        """
        INSERT INTO invoice_line_items (invoice_id, description, quantity, unit_price, total)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id, invoice_id, description, quantity, unit_price, total, created_at
        """,
        UUID(invoice_id),
        request.description,
        request.quantity,
        Decimal(str(request.unit_price)),
        Decimal(str(total)),
    )

    if line_item_row is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add line item",
        )

    # Update invoice totals
    await pool.execute(
        """
        UPDATE invoices
        SET subtotal = (SELECT COALESCE(SUM(total), 0) FROM invoice_line_items WHERE invoice_id = $1),
            tax_amount = (SELECT COALESCE(SUM(total), 0) FROM invoice_line_items WHERE invoice_id = $1) * 0.1,
            total_amount = (SELECT COALESCE(SUM(total), 0) FROM invoice_line_items WHERE invoice_id = $1) * 1.1
        WHERE id = $1
        """,
        UUID(invoice_id),
    )

    line_item = _row_to_line_item(dict(line_item_row))
    return line_item_to_response(line_item)


@router.patch("/{invoice_id}/status", response_model=InvoiceResponse)
async def update_invoice_status(
    invoice_id: str,
    request: UpdateInvoiceStatusRequest,
    auth: Annotated[
        DoctorAuthorized | AdminAuthorized,
        Depends(require_doctor_or_admin),
    ],
) -> InvoiceResponse:
    """Update invoice status.

    Requires: Doctor or Admin role.
    """
    db_manager = get_database_manager()
    pool = db_manager.get_pool()

    # Build update query
    if request.status == "paid":
        row = await pool.fetchrow(
            """
            UPDATE invoices
            SET status = $2, paid_at = NOW()
            WHERE id = $1
            RETURNING id, patient_id, appointment_id, status, subtotal,
                      tax_amount, total_amount, due_date, paid_at,
                      created_at, updated_at
            """,
            UUID(invoice_id),
            request.status,
        )
    else:
        row = await pool.fetchrow(
            """
            UPDATE invoices
            SET status = $2
            WHERE id = $1
            RETURNING id, patient_id, appointment_id, status, subtotal,
                      tax_amount, total_amount, due_date, paid_at,
                      created_at, updated_at
            """,
            UUID(invoice_id),
            request.status,
        )

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice {invoice_id} not found",
        )

    invoice = _row_to_invoice(dict(row))
    return invoice_to_response(invoice)


@router.get("/patient/{patient_id}", response_model=list[InvoiceResponse])
async def get_patient_invoices(
    patient_id: str,
    auth: Annotated[
        PatientAuthorized | DoctorAuthorized | AdminAuthorized,
        Depends(require_authenticated),
    ],
) -> list[InvoiceResponse]:
    """Get all invoices for a patient.

    Requires appropriate authorization.
    """
    # Authorization check
    match auth:
        case PatientAuthorized(patient_id=auth_patient_id):
            if str(auth_patient_id) != patient_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to view these invoices",
                )
        case _:
            pass  # Doctors and admins can view any patient's invoices

    db_manager = get_database_manager()
    pool = db_manager.get_pool()

    rows = await pool.fetch(
        """
        SELECT id, patient_id, appointment_id, status, subtotal,
               tax_amount, total_amount, due_date, paid_at,
               created_at, updated_at
        FROM invoices
        WHERE patient_id = $1
        ORDER BY created_at DESC
        """,
        UUID(patient_id),
    )

    invoices = [_row_to_invoice(dict(row)) for row in rows]
    return [invoice_to_response(inv) for inv in invoices]
