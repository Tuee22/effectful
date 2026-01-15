"""Invoices API endpoints.

Boundary: OUTSIDE_PROOF
Target-Language: N/A (assumed correct)

Provides CRUD operations for healthcare invoices and billing.
HTTP layer - converts requests to effect programs and runs them.

Assumptions:
- [Framework] FastAPI correctly routes requests and validates payloads
"""

from collections.abc import Generator
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

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
from app.domain.lookup_result import (
    InvoiceFound,
    InvoiceMissing,
    is_invoice_lookup_result,
)
from effectful.domain.optional_value import (
    Absent,
    OptionalValue,
    Provided,
    from_optional_value,
    to_optional_value,
)
from app.effects.healthcare import (
    AddInvoiceLineItem,
    CreateInvoice,
    GetInvoiceById,
    ListInvoiceLineItems,
    ListInvoices,
    UpdateInvoiceStatus,
)
from app.infrastructure.rate_limiter import rate_limit
from app.interpreters.auditing_interpreter import AuditedCompositeInterpreter
from app.interpreters.composite_interpreter import AllEffects
from app.programs.runner import run_program, unwrap_program_result
from app.api.dependencies import (
    AdminAuthorized,
    DoctorAuthorized,
    PatientAuthorized,
    get_audited_composite_interpreter,
    require_authenticated,
    require_doctor_or_admin,
)

router = APIRouter()


def _normalize_optional_uuid(value: object, *, reason: str) -> OptionalValue[UUID]:
    """Normalize incoming UUID values to OptionalValue."""
    if isinstance(value, (Provided, Absent)):
        return value
    if value is None:
        return Absent(reason=reason)
    if isinstance(value, UUID):
        return Provided(value=value)
    if isinstance(value, str):
        return Provided(value=UUID(value))
    raise TypeError(f"Expected UUID, str, OptionalValue, or None but received {type(value)}")


def _normalize_optional_date(value: object, *, reason: str) -> OptionalValue[date]:
    """Normalize incoming date values to OptionalValue."""
    if isinstance(value, (Provided, Absent)):
        return value
    if value is None:
        return Absent(reason=reason)
    if isinstance(value, date):
        return Provided(value=value)
    if isinstance(value, str):
        return Provided(value=date.fromisoformat(value))
    raise TypeError(f"Expected date, str, OptionalValue, or None but received {type(value)}")


def _normalize_optional_datetime(value: object, *, reason: str) -> OptionalValue[datetime]:
    """Normalize incoming datetime values to OptionalValue."""
    if isinstance(value, (Provided, Absent)):
        return value
    if value is None:
        return Absent(reason=reason)
    if isinstance(value, datetime):
        return Provided(value=value)
    if isinstance(value, str):
        return Provided(value=datetime.fromisoformat(value))
    raise TypeError(f"Expected datetime, str, OptionalValue, or None but received {type(value)}")


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

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str
    patient_id: str
    appointment_id: OptionalValue[UUID] = Field(
        default_factory=lambda: Absent("no_associated_appointment")
    )
    status: Literal["draft", "sent", "paid", "overdue"]
    subtotal: float
    tax_amount: float
    total_amount: float
    due_date: OptionalValue[date] = Field(default_factory=lambda: Absent("not_set"))
    paid_at: OptionalValue[datetime] = Field(default_factory=lambda: Absent("not_paid"))
    created_at: datetime
    updated_at: datetime

    @field_serializer("appointment_id")
    def serialize_appointment_id(self, appointment_id: OptionalValue[UUID]) -> str | None:
        resolved = from_optional_value(appointment_id)
        return str(resolved) if resolved is not None else None

    @field_serializer("due_date")
    def serialize_due_date(self, due_date: OptionalValue[date]) -> date | None:
        return from_optional_value(due_date)

    @field_serializer("paid_at")
    def serialize_paid_at(self, paid_at: OptionalValue[datetime]) -> datetime | None:
        return from_optional_value(paid_at)


class InvoiceWithLineItemsResponse(BaseModel):
    """Invoice with line items response model."""

    invoice: InvoiceResponse
    line_items: list[LineItemResponse]


class CreateInvoiceRequest(BaseModel):
    """Create invoice request."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    patient_id: str
    appointment_id: OptionalValue[UUID] = Field(default_factory=lambda: Absent("not_linked"))
    due_date: OptionalValue[date] = Field(default_factory=lambda: Absent("not_provided"))

    @field_validator("appointment_id", mode="before")
    @classmethod
    def normalize_appointment_id(cls, value: object) -> OptionalValue[UUID]:
        return _normalize_optional_uuid(value, reason="not_linked")

    @field_validator("due_date", mode="before")
    @classmethod
    def normalize_due_date(cls, value: object) -> OptionalValue[date]:
        return _normalize_optional_date(value, reason="not_provided")


class CreateLineItemRequest(BaseModel):
    """Create line item request."""

    description: str
    quantity: int = 1
    unit_price: float


class UpdateInvoiceStatusRequest(BaseModel):
    """Update invoice status request."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    status: Literal["draft", "sent", "paid", "overdue"]
    paid_at: OptionalValue[datetime] = Field(default_factory=lambda: Absent("not_paid"))

    @field_validator("paid_at", mode="before")
    @classmethod
    def normalize_paid_at(cls, value: object) -> OptionalValue[datetime]:
        return _normalize_optional_datetime(value, reason="not_paid")


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
        appointment_id=invoice.appointment_id,
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
    interpreter: Annotated[
        AuditedCompositeInterpreter,
        Depends(get_audited_composite_interpreter),
    ],
    _rate_limit: Annotated[None, Depends(rate_limit(100, 60))],
) -> list[InvoiceResponse]:
    """List invoices with role-based filtering.

    - Patient: sees only their own invoices
    - Doctor/Admin: sees all invoices

    Logs all PHI access for HIPAA compliance.
    Rate limit: 100 requests per 60 seconds per IP address.
    """
    # Determine filters based on role
    patient_id: UUID | None = None

    match auth:
        case PatientAuthorized(patient_id=pid):
            patient_id = pid
        case DoctorAuthorized():
            pass  # No filtering
        case AdminAuthorized():
            pass  # No filtering

    def list_program() -> Generator[AllEffects, object, list[Invoice]]:
        invoices = yield ListInvoices(patient_id=to_optional_value(patient_id, reason="role_scope"))
        assert isinstance(invoices, list)
        return invoices

    # Run effect program
    invoices = unwrap_program_result(await run_program(list_program(), interpreter))

    return [invoice_to_response(inv) for inv in invoices]


@router.post("/", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    request_data: CreateInvoiceRequest,
    auth: Annotated[
        DoctorAuthorized | AdminAuthorized,
        Depends(require_doctor_or_admin),
    ],
    interpreter: Annotated[
        AuditedCompositeInterpreter,
        Depends(get_audited_composite_interpreter),
    ],
    _rate_limit: Annotated[None, Depends(rate_limit(100, 60))],
) -> InvoiceResponse:
    """Create a new invoice.

    Requires: Doctor or Admin role.
    Rate limit: 100 requests per 60 seconds per IP address.
    """

    def create_program() -> Generator[AllEffects, object, Invoice]:
        invoice = yield CreateInvoice(
            patient_id=UUID(request_data.patient_id),
            appointment_id=request_data.appointment_id,
            line_items=[],  # Empty invoice, line items added later
            due_date=request_data.due_date,
        )

        assert isinstance(invoice, Invoice)
        return invoice

    # Run effect program
    invoice = unwrap_program_result(await run_program(create_program(), interpreter))

    return invoice_to_response(invoice)


@router.get("/{invoice_id}", response_model=InvoiceWithLineItemsResponse)
async def get_invoice(
    invoice_id: str,
    auth: Annotated[
        PatientAuthorized | DoctorAuthorized | AdminAuthorized,
        Depends(require_authenticated),
    ],
    interpreter: Annotated[
        AuditedCompositeInterpreter,
        Depends(get_audited_composite_interpreter),
    ],
    _rate_limit: Annotated[None, Depends(rate_limit(100, 60))],
) -> InvoiceWithLineItemsResponse:
    """Get invoice by ID with line items.

    Requires appropriate authorization.
    Logs all PHI access for HIPAA compliance.
    Rate limit: 100 requests per 60 seconds per IP address.
    """

    def get_program() -> (
        Generator[AllEffects, object, InvoiceMissing | tuple[Invoice, list[LineItem]]]
    ):
        invoice_result = yield GetInvoiceById(invoice_id=UUID(invoice_id))
        assert is_invoice_lookup_result(invoice_result)
        match invoice_result:
            case InvoiceMissing() as missing:
                return missing
            case InvoiceFound(invoice=invoice):
                line_items = yield ListInvoiceLineItems(invoice_id=UUID(invoice_id))
                assert isinstance(line_items, list)
                return invoice, line_items
            # MyPy enforces exhaustiveness - no fallback needed

    # Run effect program
    result = unwrap_program_result(await run_program(get_program(), interpreter))

    match result:
        case InvoiceMissing():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Invoice {invoice_id} not found",
            )
        case tuple() as invoice_tuple:
            invoice, line_items = invoice_tuple
        # MyPy enforces exhaustiveness - no fallback needed

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


@router.post(
    "/{invoice_id}/line-items", response_model=LineItemResponse, status_code=status.HTTP_201_CREATED
)
async def add_line_item(
    invoice_id: str,
    request_data: CreateLineItemRequest,
    auth: Annotated[
        DoctorAuthorized | AdminAuthorized,
        Depends(require_doctor_or_admin),
    ],
    interpreter: Annotated[
        AuditedCompositeInterpreter,
        Depends(get_audited_composite_interpreter),
    ],
    _rate_limit: Annotated[None, Depends(rate_limit(100, 60))],
) -> LineItemResponse:
    """Add a line item to an invoice.

    Requires: Doctor or Admin role.
    Also updates the invoice totals.
    Rate limit: 100 requests per 60 seconds per IP address.
    """

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
    line_item = unwrap_program_result(await run_program(add_line_item_program(), interpreter))

    return line_item_to_response(line_item)


@router.patch("/{invoice_id}/status", response_model=InvoiceResponse)
async def update_invoice_status(
    invoice_id: str,
    request_data: UpdateInvoiceStatusRequest,
    auth: Annotated[
        DoctorAuthorized | AdminAuthorized,
        Depends(require_doctor_or_admin),
    ],
    interpreter: Annotated[
        AuditedCompositeInterpreter,
        Depends(get_audited_composite_interpreter),
    ],
    _rate_limit: Annotated[None, Depends(rate_limit(100, 60))],
) -> InvoiceResponse:
    """Update invoice status.

    Requires: Doctor or Admin role.
    Rate limit: 100 requests per 60 seconds per IP address.
    """

    def update_status_program() -> Generator[AllEffects, object, InvoiceFound | InvoiceMissing]:
        result = yield UpdateInvoiceStatus(
            invoice_id=UUID(invoice_id),
            status=request_data.status,
            paid_at=request_data.paid_at,
        )
        assert is_invoice_lookup_result(result)
        return result

    # Run effect program
    invoice_result = unwrap_program_result(await run_program(update_status_program(), interpreter))

    match invoice_result:
        case InvoiceFound(invoice=invoice):
            return invoice_to_response(invoice)
        case InvoiceMissing():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Invoice {invoice_id} not found",
            )
        # MyPy enforces exhaustiveness - no fallback needed


@router.get("/patient/{patient_id}", response_model=list[InvoiceResponse])
async def get_patient_invoices(
    patient_id: str,
    auth: Annotated[
        PatientAuthorized | DoctorAuthorized | AdminAuthorized,
        Depends(require_authenticated),
    ],
    interpreter: Annotated[
        AuditedCompositeInterpreter,
        Depends(get_audited_composite_interpreter),
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

    def list_program() -> Generator[AllEffects, object, list[Invoice]]:
        invoices = yield ListInvoices(
            patient_id=to_optional_value(UUID(patient_id), reason="explicit_filter")
        )
        assert isinstance(invoices, list)
        return invoices

    # Run effect program
    invoices = unwrap_program_result(await run_program(list_program(), interpreter))

    return [invoice_to_response(inv) for inv in invoices]
