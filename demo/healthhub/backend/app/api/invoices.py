"""Invoices API endpoints.

Provides CRUD operations for healthcare invoices and billing.
"""

from collections.abc import Generator
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
import redis.asyncio as redis

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
from app.effects.healthcare import (
    AddInvoiceLineItem,
    CreateInvoice,
    GetInvoiceById,
    ListInvoiceLineItems,
    ListInvoices,
    UpdateInvoiceStatus,
)
from app.domain.optional_value import from_optional_value, to_optional_value
from app.infrastructure import get_database_manager, rate_limit
from app.interpreters.auditing_interpreter import AuditContext, AuditedCompositeInterpreter
from app.interpreters.composite_interpreter import AllEffects, CompositeInterpreter
from app.programs.runner import run_program
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
        appointment_id=to_optional_value(
            safe_optional_uuid(row.get("appointment_id")), reason="no_associated_appointment"
        ),
        status=safe_invoice_status(row["status"]),
        subtotal=safe_decimal(row["subtotal"]),
        tax_amount=safe_decimal(row["tax_amount"]),
        total_amount=safe_decimal(row["total_amount"]),
        due_date=to_optional_value(safe_optional_date(row.get("due_date")), reason="not_set"),
        paid_at=to_optional_value(safe_optional_datetime(row.get("paid_at")), reason="not_paid"),
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
        appointment_id=(
            str(from_optional_value(invoice.appointment_id))
            if from_optional_value(invoice.appointment_id)
            else None
        ),
        status=invoice.status,
        subtotal=float(invoice.subtotal),
        tax_amount=float(invoice.tax_amount),
        total_amount=float(invoice.total_amount),
        due_date=from_optional_value(invoice.due_date),
        paid_at=from_optional_value(invoice.paid_at),
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
    request: Request,
    auth: Annotated[
        PatientAuthorized | DoctorAuthorized | AdminAuthorized,
        Depends(require_authenticated),
    ],
    _rate_limit: Annotated[None, Depends(rate_limit(100, 60))],
) -> list[InvoiceResponse]:
    """List invoices with role-based filtering.

    - Patient: sees only their own invoices
    - Doctor/Admin: sees all invoices

    Logs all PHI access for HIPAA compliance.
    Rate limit: 100 requests per 60 seconds per IP address.
    """
    db_manager = get_database_manager()
    pool = db_manager.get_pool()

    # Extract actor ID and determine filters based on role
    actor_id: UUID
    patient_id: UUID | None = None

    match auth:
        case PatientAuthorized(user_id=uid, patient_id=pid):
            actor_id = uid
            patient_id = pid
        case DoctorAuthorized(user_id=uid):
            actor_id = uid
        case AdminAuthorized(user_id=uid):
            actor_id = uid

    # Extract IP and user agent from request
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    # Create Redis client
    redis_client: redis.Redis[bytes] = redis.Redis(
        host="redis",
        port=6379,
        decode_responses=False,
    )

    try:
        # Create composite interpreter
        base_interpreter = CompositeInterpreter(pool, redis_client)
        interpreter: AuditedCompositeInterpreter = AuditedCompositeInterpreter(
            base_interpreter,
            AuditContext(user_id=actor_id, ip_address=ip_address, user_agent=user_agent),
        )

        def list_program() -> Generator[AllEffects, object, list[Invoice]]:
            invoices = yield ListInvoices(patient_id=patient_id)
            assert isinstance(invoices, list)

            return invoices

        # Run effect program
        invoices = await run_program(list_program(), interpreter)

        return [invoice_to_response(inv) for inv in invoices]

    finally:
        await redis_client.aclose()


@router.post("/", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    request_data: CreateInvoiceRequest,
    http_request: Request,
    auth: Annotated[
        DoctorAuthorized | AdminAuthorized,
        Depends(require_doctor_or_admin),
    ],
    _rate_limit: Annotated[None, Depends(rate_limit(100, 60))],
) -> InvoiceResponse:
    """Create a new invoice.

    Requires: Doctor or Admin role.
    Rate limit: 100 requests per 60 seconds per IP address.
    """
    db_manager = get_database_manager()
    pool = db_manager.get_pool()

    # Extract actor ID from auth state
    actor_id: UUID
    match auth:
        case DoctorAuthorized(user_id=uid):
            actor_id = uid
        case AdminAuthorized(user_id=uid):
            actor_id = uid

    # Extract IP and user agent from request
    ip_address = http_request.client.host if http_request.client else None
    user_agent = http_request.headers.get("user-agent")

    # Create Redis client with resource management
    redis_client: redis.Redis[bytes] = redis.Redis(
        host="redis",
        port=6379,
        decode_responses=False,
    )

    try:
        # Create composite interpreter
        base_interpreter = CompositeInterpreter(pool, redis_client)
        interpreter: AuditedCompositeInterpreter = AuditedCompositeInterpreter(
            base_interpreter,
            AuditContext(user_id=actor_id, ip_address=ip_address, user_agent=user_agent),
        )

        def create_program() -> Generator[AllEffects, object, Invoice]:
            invoice = yield CreateInvoice(
                patient_id=UUID(request_data.patient_id),
                appointment_id=(
                    UUID(request_data.appointment_id) if request_data.appointment_id else None
                ),
                line_items=[],  # Empty invoice, line items added later
                due_date=request_data.due_date,
            )

            assert isinstance(invoice, Invoice)
            return invoice

        # Run effect program
        invoice = await run_program(create_program(), interpreter)

        return invoice_to_response(invoice)

    finally:
        await redis_client.aclose()


@router.get("/{invoice_id}", response_model=InvoiceWithLineItemsResponse)
async def get_invoice(
    invoice_id: str,
    request: Request,
    auth: Annotated[
        PatientAuthorized | DoctorAuthorized | AdminAuthorized,
        Depends(require_authenticated),
    ],
    _rate_limit: Annotated[None, Depends(rate_limit(100, 60))],
) -> InvoiceWithLineItemsResponse:
    """Get invoice by ID with line items.

    Requires appropriate authorization.
    Logs all PHI access for HIPAA compliance.
    Rate limit: 100 requests per 60 seconds per IP address.
    """
    db_manager = get_database_manager()
    pool = db_manager.get_pool()

    # Create Redis client
    redis_client: redis.Redis[bytes] = redis.Redis(
        host="redis",
        port=6379,
        decode_responses=False,
    )

    try:
        # Extract actor ID from auth state
        actor_id: UUID
        match auth:
            case PatientAuthorized(user_id=uid):
                actor_id = uid
            case DoctorAuthorized(user_id=uid):
                actor_id = uid
            case AdminAuthorized(user_id=uid):
                actor_id = uid

        # Extract IP and user agent from request
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

        # Create composite interpreter
        base_interpreter = CompositeInterpreter(pool, redis_client)
        interpreter = AuditedCompositeInterpreter(
            base_interpreter,
            AuditContext(user_id=actor_id, ip_address=ip_address, user_agent=user_agent),
        )

        def get_program() -> Generator[AllEffects, object, tuple[Invoice, list[LineItem]]]:
            invoice = yield GetInvoiceById(invoice_id=UUID(invoice_id))
            if invoice is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Invoice {invoice_id} not found",
                )
            assert isinstance(invoice, Invoice)
            line_items = yield ListInvoiceLineItems(invoice_id=UUID(invoice_id))
            assert isinstance(line_items, list)
            return invoice, line_items

        # Run effect program
        invoice, line_items = await run_program(get_program(), interpreter)

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

        return InvoiceWithLineItemsResponse(
            invoice=invoice_to_response(invoice),
            line_items=[line_item_to_response(li) for li in line_items],
        )

    finally:
        await redis_client.aclose()


@router.post(
    "/{invoice_id}/line-items", response_model=LineItemResponse, status_code=status.HTTP_201_CREATED
)
async def add_line_item(
    invoice_id: str,
    request_data: CreateLineItemRequest,
    http_request: Request,
    auth: Annotated[
        DoctorAuthorized | AdminAuthorized,
        Depends(require_doctor_or_admin),
    ],
    _rate_limit: Annotated[None, Depends(rate_limit(100, 60))],
) -> LineItemResponse:
    """Add a line item to an invoice.

    Requires: Doctor or Admin role.
    Also updates the invoice totals.
    Rate limit: 100 requests per 60 seconds per IP address.
    """
    db_manager = get_database_manager()
    pool = db_manager.get_pool()

    # Extract actor ID from auth state
    actor_id: UUID
    match auth:
        case DoctorAuthorized(user_id=uid):
            actor_id = uid
        case AdminAuthorized(user_id=uid):
            actor_id = uid

    # Extract IP and user agent from request
    ip_address = http_request.client.host if http_request.client else None
    user_agent = http_request.headers.get("user-agent")

    # Create Redis client with resource management
    redis_client: redis.Redis[bytes] = redis.Redis(
        host="redis",
        port=6379,
        decode_responses=False,
    )

    try:
        # Create composite interpreter
        base_interpreter = CompositeInterpreter(pool, redis_client)
        interpreter: AuditedCompositeInterpreter = AuditedCompositeInterpreter(
            base_interpreter,
            AuditContext(user_id=actor_id, ip_address=ip_address, user_agent=user_agent),
        )

        def add_line_item_program() -> Generator[AllEffects, object, LineItem]:
            line_item = yield AddInvoiceLineItem(
                invoice_id=UUID(invoice_id),
                description=request_data.description,
                quantity=request_data.quantity,
                unit_price=Decimal(str(request_data.unit_price)),
            )

            assert isinstance(line_item, LineItem)
            return line_item

        # Run effect program
        line_item = await run_program(add_line_item_program(), interpreter)

        return line_item_to_response(line_item)

    finally:
        await redis_client.aclose()


@router.patch("/{invoice_id}/status", response_model=InvoiceResponse)
async def update_invoice_status(
    invoice_id: str,
    request_data: UpdateInvoiceStatusRequest,
    http_request: Request,
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

    # Extract actor ID from auth state
    actor_id: UUID
    match auth:
        case DoctorAuthorized(user_id=uid):
            actor_id = uid
        case AdminAuthorized(user_id=uid):
            actor_id = uid

    # Extract IP and user agent from request
    ip_address = http_request.client.host if http_request.client else None
    user_agent = http_request.headers.get("user-agent")

    # Create Redis client with resource management
    redis_client: redis.Redis[bytes] = redis.Redis(
        host="redis",
        port=6379,
        decode_responses=False,
    )

    try:
        # Create composite interpreter
        base_interpreter = CompositeInterpreter(pool, redis_client)
        interpreter: AuditedCompositeInterpreter = AuditedCompositeInterpreter(
            base_interpreter,
            AuditContext(user_id=actor_id, ip_address=ip_address, user_agent=user_agent),
        )

        def update_status_program() -> Generator[AllEffects, object, Invoice]:
            invoice = yield UpdateInvoiceStatus(
                invoice_id=UUID(invoice_id),
                status=request_data.status,
            )

            if invoice is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Invoice {invoice_id} not found",
                )

            assert isinstance(invoice, Invoice)

            return invoice

        # Run effect program
        invoice = await run_program(update_status_program(), interpreter)

        return invoice_to_response(invoice)

    finally:
        await redis_client.aclose()


@router.get("/patient/{patient_id}", response_model=list[InvoiceResponse])
async def get_patient_invoices(
    patient_id: str,
    request: Request,
    auth: Annotated[
        PatientAuthorized | DoctorAuthorized | AdminAuthorized,
        Depends(require_authenticated),
    ],
    _rate_limit: Annotated[None, Depends(rate_limit(100, 60))],
) -> list[InvoiceResponse]:
    """Get all invoices for a patient.

    Requires appropriate authorization.
    Logs all PHI access for HIPAA compliance.
    Rate limit: 100 requests per 60 seconds per IP address.
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

    # Create Redis client
    redis_client: redis.Redis[bytes] = redis.Redis(
        host="redis",
        port=6379,
        decode_responses=False,
    )

    try:
        # Extract actor ID from auth state
        actor_id: UUID
        match auth:
            case PatientAuthorized(user_id=uid):
                actor_id = uid
            case DoctorAuthorized(user_id=uid):
                actor_id = uid
            case AdminAuthorized(user_id=uid):
                actor_id = uid

        # Extract IP and user agent from request
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

        # Create composite interpreter
        base_interpreter = CompositeInterpreter(pool, redis_client)
        interpreter = AuditedCompositeInterpreter(
            base_interpreter,
            AuditContext(user_id=actor_id, ip_address=ip_address, user_agent=user_agent),
        )

        def list_program() -> Generator[AllEffects, object, list[Invoice]]:
            invoices = yield ListInvoices(patient_id=UUID(patient_id))
            assert isinstance(invoices, list)

            return invoices

        # Run effect program
        invoices = await run_program(list_program(), interpreter)

        return [invoice_to_response(inv) for inv in invoices]

    finally:
        await redis_client.aclose()
