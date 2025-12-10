# Invoices Feature

**Status**: Authoritative source (HealthHub tutorial patterns)
**Supersedes**: none
**Referenced by**: demo/healthhub/documents/tutorials/README.md

> **Purpose**: Complete reference for HealthHub invoice system: invoice domain model, generation from completed appointments, line item management, payment status tracking, and admin-only creation.

> **Core Doctrines**: For comprehensive patterns, see:
> - [ADTs and Result Types](../../../../../documents/tutorials/adts_and_results.md)
> - [Code Quality](../../../../../documents/engineering/code_quality.md)
> - [Effect Patterns](../../../../../documents/engineering/effect_patterns.md)

## Prerequisites

- Docker workflow running; commands executed via `docker compose -f docker/docker-compose.yml`.
- Completed [Intermediate Journey](../01_journeys/intermediate_journey.md).
- Familiarity with billing systems, ADTs, Python type hints, pattern matching.

## Learning Objectives

- Define Invoice and InvoiceLineItem domain models
- Generate invoices from completed appointments
- Manage line items (description, quantity, unit_price)
- Track payment status (Sent, Paid, Overdue)
- Apply patient viewing restrictions (own invoices only)
- Apply admin-only creation RBAC enforcement
- Write e2e tests for creation, viewing, and status transitions

## Overview

**Invoice System Architecture**:
- **Generation**: Invoices generated from completed appointments (admin-triggered)
- **Line Items**: Flexible line item structure (appointment charges, procedures, supplies)
- **Payment Tracking**: Status transitions (Sent → Paid | Overdue)
- **Due Dates**: Configurable due date (default: 30 days from issue)
- **Patient Access**: Patients view own invoices with payment history

**Invoice Lifecycle**:
1. **Appointment Completed**: Doctor completes appointment with notes
2. **Admin Generates Invoice**: Admin creates invoice from appointment
3. **Invoice Sent**: Status set to "Sent", patient notified
4. **Payment**: Patient pays invoice, status updated to "Paid"
5. **Overdue**: If unpaid past due date, status updated to "Overdue"

## Domain Models

### Invoice Model

**File**: `demo/healthhub/backend/app/domain/invoices.py`

```python
# file: demo/healthhub/backend/app/domain/invoices.py
from dataclasses import dataclass
from uuid import UUID
from datetime import datetime
from decimal import Decimal

@dataclass(frozen=True)
class Invoice:
    """
    Invoice for healthcare services.

    Fields:
    - invoice_id: Unique identifier
    - patient_id: Links to patients table
    - appointment_id: Optional link to appointment (if generated from appointment)
    - status: Payment status ("Sent" | "Paid" | "Overdue")
    - subtotal: Sum of line item amounts (before tax)
    - tax: Tax amount (calculated from subtotal)
    - total: Total amount due (subtotal + tax)
    - due_date: Payment due date
    - issued_date: When invoice was issued
    - paid_date: When invoice was paid (null if unpaid)
    - created_at: When invoice was created
    - updated_at: Last status change timestamp
    """
    invoice_id: UUID
    patient_id: UUID
    appointment_id: UUID | None
    status: str  # "Sent" | "Paid" | "Overdue"
    subtotal: Decimal
    tax: Decimal
    total: Decimal
    due_date: datetime
    issued_date: datetime
    paid_date: datetime | None
    created_at: datetime
    updated_at: datetime
```

### InvoiceLineItem Model

**File**: `demo/healthhub/backend/app/domain/invoices.py`

```python
# file: demo/healthhub/backend/app/domain/invoices.py
from dataclasses import dataclass
from uuid import UUID
from decimal import Decimal

@dataclass(frozen=True)
class InvoiceLineItem:
    """
    Individual line item on invoice.

    Fields:
    - line_item_id: Unique identifier
    - invoice_id: Links to invoices table
    - description: Service description (e.g., "Office Visit - Cardiology", "Lab Test - Lipid Panel")
    - quantity: Number of units (e.g., 1 for single office visit)
    - unit_price: Price per unit
    - amount: Total amount (quantity * unit_price)
    """
    line_item_id: UUID
    invoice_id: UUID
    description: str
    quantity: int
    unit_price: Decimal
    amount: Decimal
```

**Why separate line items?**
- **Flexible billing**: Support multiple charges per invoice
- **Detailed breakdown**: Patients see itemized charges
- **Audit trail**: Track individual service charges
- **Tax calculation**: Calculate tax on subtotal of all line items

## Invoice Generation from Appointment

**Endpoint**: `POST /api/invoices/generate-from-appointment/{appointment_id}` (admin-only)

**Program**: `demo/healthhub/backend/app/programs/invoice_programs.py`

```python
# file: demo/healthhub/backend/app/programs/invoice_programs.py
from effectful import Effect, Result, Ok, Err
from effectful.effects import DatabaseEffect
from demo.healthhub.backend.app.effects.notification_effect import SendPatientNotification
from uuid import UUID, uuid4
from typing import Generator
from datetime import datetime, timezone, timedelta
from decimal import Decimal

def generate_invoice_from_appointment(
    appointment_id: UUID,
    tax_rate: Decimal = Decimal("0.07")  # 7% tax rate
) -> Generator[Effect, Result, Result[dict]]:
    """
    Generate invoice from completed appointment.

    Flow:
    1. Fetch appointment (verify completed status)
    2. Fetch doctor specialization for pricing
    3. Create line items (office visit charge + any procedures)
    4. Calculate subtotal, tax, total
    5. Create invoice record
    6. Create line item records
    7. Notify patient
    """

    # Step 1: Fetch appointment
    appointment_result = yield DatabaseEffect.Query(
        query="""
            SELECT
                a.appointment_id,
                a.patient_id,
                a.doctor_id,
                a.status,
                a.reason,
                d.specialization
            FROM appointments a
            JOIN doctors d ON a.doctor_id = d.doctor_id
            WHERE a.appointment_id = $1
        """,
        params=(appointment_id,)
    )

    match appointment_result:
        case Ok(rows) if len(rows) > 0:
            appointment = rows[0]
        case Ok([]):
            return Err("Appointment not found")
        case Err(error):
            return Err(f"Database error: {error}")

    # Verify appointment is completed
    status_data = json.loads(appointment["status"])
    if status_data["type"] != "Completed":
        return Err(f"Cannot generate invoice for appointment in {status_data['type']} state")

    # Step 2: Determine pricing based on specialization
    specialization_pricing = {
        "Cardiology": Decimal("250.00"),
        "Pediatrics": Decimal("150.00"),
        "General Practice": Decimal("120.00"),
        "Orthopedics": Decimal("300.00"),
    }

    base_charge = specialization_pricing.get(
        appointment["specialization"],
        Decimal("150.00")  # Default charge
    )

    # Step 3: Create line items
    line_items = [
        {
            "description": f"Office Visit - {appointment['specialization']}",
            "quantity": 1,
            "unit_price": base_charge,
            "amount": base_charge,
        }
    ]

    # Add reason-specific charges (simplified)
    if "physical" in appointment["reason"].lower():
        line_items.append({
            "description": "Annual Physical Examination",
            "quantity": 1,
            "unit_price": Decimal("50.00"),
            "amount": Decimal("50.00"),
        })

    # Step 4: Calculate totals
    subtotal = sum(item["amount"] for item in line_items)
    tax = subtotal * tax_rate
    total = subtotal + tax

    # Step 5: Create invoice
    invoice_id = uuid4()
    issued_date = datetime.now(timezone.utc)
    due_date = issued_date + timedelta(days=30)  # 30 day payment terms

    insert_invoice_result = yield DatabaseEffect.Execute(
        query="""
            INSERT INTO invoices (
                invoice_id, patient_id, appointment_id, status,
                subtotal, tax, total, due_date, issued_date, paid_date,
                created_at, updated_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
        """,
        params=(
            invoice_id, appointment["patient_id"], appointment_id, "Sent",
            subtotal, tax, total, due_date, issued_date, None,
            issued_date, issued_date
        )
    )

    match insert_invoice_result:
        case Ok(_):
            pass  # Invoice created
        case Err(error):
            return Err(f"Failed to create invoice: {error}")

    # Step 6: Create line items
    for item in line_items:
        line_item_id = uuid4()

        insert_item_result = yield DatabaseEffect.Execute(
            query="""
                INSERT INTO invoice_line_items (
                    line_item_id, invoice_id, description,
                    quantity, unit_price, amount
                )
                VALUES ($1, $2, $3, $4, $5, $6)
            """,
            params=(
                line_item_id, invoice_id, item["description"],
                item["quantity"], item["unit_price"], item["amount"]
            )
        )

        match insert_item_result:
            case Ok(_):
                pass  # Line item created
            case Err(error):
                return Err(f"Failed to create line item: {error}")

    # Step 7: Notify patient
    _ = yield SendPatientNotification(
        patient_id=appointment["patient_id"],
        notification_type="invoice_ready",
        message=f"Your invoice for appointment on {issued_date.strftime('%Y-%m-%d')} is ready. Amount due: ${total}. Due date: {due_date.strftime('%Y-%m-%d')}.",
        metadata={
            "invoice_id": str(invoice_id),
            "total": str(total),
            "due_date": due_date.isoformat(),
        }
    )

    return Ok({
        "invoice_id": invoice_id,
        "subtotal": subtotal,
        "tax": tax,
        "total": total,
        "due_date": due_date,
    })
```

**API Endpoint with RBAC**:
```python
# file: demo/healthhub/backend/app/api/invoices.py
from fastapi import APIRouter, Depends, HTTPException
from demo.healthhub.backend.app.api.dependencies import get_auth_state
from demo.healthhub.backend.app.domain.auth import AuthorizationState, AdminAuthorized, PatientAuthorized, DoctorAuthorized, Unauthorized

router = APIRouter(prefix="/api/invoices")

@router.post("/generate-from-appointment/{appointment_id}")
async def generate_invoice_from_appointment_endpoint(
    appointment_id: str,
    auth_state: AuthorizationState = Depends(get_auth_state)
):
    """
    Generate invoice from completed appointment (admin-only).
    """

    match auth_state:
        case AdminAuthorized():
            # Admin authorized to generate invoices
            program = generate_invoice_from_appointment(UUID(appointment_id))
            result = await interpreter.run(program)

            match result:
                case Ok(invoice):
                    return {
                        "invoice_id": str(invoice["invoice_id"]),
                        "subtotal": str(invoice["subtotal"]),
                        "tax": str(invoice["tax"]),
                        "total": str(invoice["total"]),
                        "due_date": invoice["due_date"].isoformat(),
                    }
                case Err(error):
                    raise HTTPException(400, str(error))

        case PatientAuthorized() | DoctorAuthorized():
            raise HTTPException(403, "Only admins can generate invoices")

        case Unauthorized(reason=reason):
            raise HTTPException(401, f"Unauthorized: {reason}")
```

**RBAC Enforcement**: Only `AdminAuthorized` variant can generate invoices (enforced by pattern matching).

## Payment Status Management

### Mark Invoice as Paid

**Endpoint**: `POST /api/invoices/{invoice_id}/mark-paid` (admin-only)

**Request**:
```json
{
  "payment_method": "credit_card",
  "payment_reference": "CH_abc123xyz"
}
```

**Program**: `demo/healthhub/backend/app/programs/invoice_programs.py`

```python
# file: demo/healthhub/backend/app/programs/invoice_programs.py
def mark_invoice_paid(
    invoice_id: UUID,
    payment_method: str,
    payment_reference: str
) -> Generator[Effect, Result, Result[dict]]:
    """
    Mark invoice as paid (transition Sent|Overdue → Paid).
    """

    # Fetch invoice
    invoice_result = yield DatabaseEffect.Query(
        query="SELECT * FROM invoices WHERE invoice_id = $1",
        params=(invoice_id,)
    )

    match invoice_result:
        case Ok(rows) if len(rows) > 0:
            invoice = rows[0]
        case Ok([]):
            return Err("Invoice not found")
        case Err(error):
            return Err(f"Database error: {error}")

    # Validate status (can only pay Sent or Overdue invoices)
    if invoice["status"] not in ("Sent", "Overdue"):
        return Err(f"Cannot mark invoice in {invoice['status']} status as paid")

    # Update status to Paid
    paid_date = datetime.now(timezone.utc)

    update_result = yield DatabaseEffect.Execute(
        query="""
            UPDATE invoices
            SET status = 'Paid',
                paid_date = $1,
                updated_at = $2
            WHERE invoice_id = $3
        """,
        params=(paid_date, paid_date, invoice_id)
    )

    match update_result:
        case Ok(_):
            # Log payment (for audit trail)
            _ = yield DatabaseEffect.Execute(
                query="""
                    INSERT INTO payment_log (invoice_id, payment_method, payment_reference, paid_at)
                    VALUES ($1, $2, $3, $4)
                """,
                params=(invoice_id, payment_method, payment_reference, paid_date)
            )

            return Ok({
                "invoice_id": invoice_id,
                "status": "Paid",
                "paid_date": paid_date,
            })
        case Err(error):
            return Err(f"Failed to update invoice: {error}")
```

### Mark Overdue Invoices (Scheduled Job)

**Program**: `demo/healthhub/backend/app/programs/invoice_programs.py`

```python
# file: demo/healthhub/backend/app/programs/invoice_programs.py
def mark_overdue_invoices() -> Generator[Effect, Result, Result[dict]]:
    """
    Mark all unpaid invoices past due date as Overdue.

    Scheduled job (runs daily).
    """

    # Find Sent invoices past due date
    overdue_result = yield DatabaseEffect.Query(
        query="""
            SELECT invoice_id, patient_id, total, due_date
            FROM invoices
            WHERE status = 'Sent'
              AND due_date < NOW()
        """,
        params=()
    )

    match overdue_result:
        case Ok(rows):
            overdue_invoices = rows
        case Err(error):
            return Err(f"Failed to fetch overdue invoices: {error}")

    # Update status to Overdue
    updated_count = 0

    for invoice in overdue_invoices:
        update_result = yield DatabaseEffect.Execute(
            query="""
                UPDATE invoices
                SET status = 'Overdue',
                    updated_at = NOW()
                WHERE invoice_id = $1
            """,
            params=(invoice["invoice_id"],)
        )

        match update_result:
            case Ok(_):
                updated_count += 1

                # Notify patient
                _ = yield SendPatientNotification(
                    patient_id=invoice["patient_id"],
                    notification_type="invoice_overdue",
                    message=f"Your invoice for ${invoice['total']} is overdue. Payment was due on {invoice['due_date'].strftime('%Y-%m-%d')}. Please submit payment to avoid late fees.",
                    metadata={
                        "invoice_id": str(invoice["invoice_id"]),
                        "total": str(invoice["total"]),
                    }
                )
            case Err(error):
                # Log error but continue processing other invoices
                pass

    return Ok({"updated_count": updated_count})
```

## Patient Viewing

**Endpoint**: `GET /api/invoices` (as patient)

**Program**: `demo/healthhub/backend/app/programs/invoice_programs.py`

```python
# file: demo/healthhub/backend/app/programs/invoice_programs.py
def get_patient_invoices(patient_id: UUID) -> Generator[Effect, Result, Result[list[dict]]]:
    """
    Get all invoices for patient with line items.
    """

    # Fetch invoices
    invoices_result = yield DatabaseEffect.Query(
        query="""
            SELECT
                i.invoice_id,
                i.appointment_id,
                i.status,
                i.subtotal,
                i.tax,
                i.total,
                i.due_date,
                i.issued_date,
                i.paid_date
            FROM invoices i
            WHERE i.patient_id = $1
            ORDER BY i.issued_date DESC
        """,
        params=(patient_id,)
    )

    match invoices_result:
        case Ok(invoice_rows):
            invoices = invoice_rows
        case Err(error):
            return Err(f"Failed to fetch invoices: {error}")

    # Fetch line items for each invoice
    result_invoices = []

    for invoice in invoices:
        line_items_result = yield DatabaseEffect.Query(
            query="""
                SELECT
                    line_item_id,
                    description,
                    quantity,
                    unit_price,
                    amount
                FROM invoice_line_items
                WHERE invoice_id = $1
                ORDER BY line_item_id
            """,
            params=(invoice["invoice_id"],)
        )

        match line_items_result:
            case Ok(line_items):
                invoice["line_items"] = line_items
                result_invoices.append(invoice)
            case Err(error):
                return Err(f"Failed to fetch line items: {error}")

    return Ok(result_invoices)
```

**API Endpoint with RBAC**:
```python
# file: demo/healthhub/backend/app/api/invoices.py
@router.get("/")
async def get_invoices(
    auth_state: AuthorizationState = Depends(get_auth_state)
):
    """
    Get invoices (role-based filtering).

    - Patient: Own invoices only
    - Admin: All invoices (with optional patient_id filter)
    """

    match auth_state:
        case PatientAuthorized(patient_id=pid):
            # Patient can only view own invoices
            program = get_patient_invoices(pid)
            result = await interpreter.run(program)

            match result:
                case Ok(invoices):
                    return {"invoices": invoices}
                case Err(error):
                    raise HTTPException(500, str(error))

        case AdminAuthorized():
            # Admin can view all invoices
            # ... (fetch all with optional patient_id filter) ...
            pass

        case DoctorAuthorized():
            raise HTTPException(403, "Doctors cannot view invoices (admin-only)")

        case Unauthorized(reason=reason):
            raise HTTPException(401, f"Unauthorized: {reason}")
```

## E2E Tests

**File**: `demo/healthhub/tests/pytest/e2e/test_invoices.py`

```python
# file: demo/healthhub/tests/pytest/e2e/test_invoices.py
import pytest
from demo.healthhub.backend.app.programs.invoice_programs import (
    generate_invoice_from_appointment,
    mark_invoice_paid,
    get_patient_invoices,
)
from effectful import Ok, Err
from decimal import Decimal

@pytest.mark.asyncio
async def test_generate_invoice_from_completed_appointment(clean_healthhub_state, postgres_interpreter):
    """E2E: Generate invoice from completed appointment."""

    # Use completed appointment from seed data
    # (Alice's appointment with Dr. Williams - completed)
    appointment_id = UUID("50000000-0000-0000-0000-000000000002")

    program = generate_invoice_from_appointment(appointment_id)
    result = await postgres_interpreter.run(program)

    match result:
        case Ok(invoice):
            assert "invoice_id" in invoice
            assert invoice["subtotal"] > Decimal("0")
            assert invoice["tax"] > Decimal("0")
            assert invoice["total"] == invoice["subtotal"] + invoice["tax"]
            assert "due_date" in invoice
        case Err(error):
            pytest.fail(f"Expected Ok, got Err: {error}")

@pytest.mark.asyncio
async def test_cannot_generate_invoice_from_non_completed_appointment(clean_healthhub_state, postgres_interpreter):
    """E2E: Invoice generation fails for non-completed appointments."""

    # Use confirmed appointment (not completed)
    appointment_id = UUID("50000000-0000-0000-0000-000000000001")  # Alice's confirmed appointment

    program = generate_invoice_from_appointment(appointment_id)
    result = await postgres_interpreter.run(program)

    match result:
        case Err(error):
            assert "cannot generate invoice" in error.lower()
        case Ok(_):
            pytest.fail("Expected Err for non-completed appointment, got Ok")

@pytest.mark.asyncio
async def test_mark_invoice_paid(clean_healthhub_state, postgres_interpreter):
    """E2E: Mark invoice as paid updates status."""

    # Generate invoice first
    appointment_id = UUID("50000000-0000-0000-0000-000000000002")
    generate_program = generate_invoice_from_appointment(appointment_id)
    generate_result = await postgres_interpreter.run(generate_program)

    match generate_result:
        case Ok(invoice):
            invoice_id = invoice["invoice_id"]
        case Err(error):
            pytest.fail(f"Failed to generate invoice: {error}")

    # Mark as paid
    paid_program = mark_invoice_paid(invoice_id, "credit_card", "CH_test123")
    paid_result = await postgres_interpreter.run(paid_program)

    match paid_result:
        case Ok(response):
            assert response["status"] == "Paid"
            assert response["paid_date"] is not None
        case Err(error):
            pytest.fail(f"Expected Ok, got Err: {error}")

@pytest.mark.asyncio
async def test_patient_can_view_own_invoices_with_line_items(clean_healthhub_state, postgres_interpreter):
    """E2E: Patient views invoices including line items."""

    # Generate invoice for Alice
    appointment_id = UUID("50000000-0000-0000-0000-000000000002")
    generate_program = generate_invoice_from_appointment(appointment_id)
    _ = await postgres_interpreter.run(generate_program)

    # Fetch invoices for Alice
    alice_patient_id = UUID("30000000-0000-0000-0000-000000000001")
    fetch_program = get_patient_invoices(alice_patient_id)
    fetch_result = await postgres_interpreter.run(fetch_program)

    match fetch_result:
        case Ok(invoices):
            assert len(invoices) > 0

            # Verify line items included
            invoice = invoices[0]
            assert "line_items" in invoice
            assert len(invoice["line_items"]) > 0

            # Verify line item structure
            line_item = invoice["line_items"][0]
            assert "description" in line_item
            assert "quantity" in line_item
            assert "unit_price" in line_item
            assert "amount" in line_item

        case Err(error):
            pytest.fail(f"Expected Ok, got Err: {error}")
```

## Summary

**You have learned**:
- ✅ Invoice and InvoiceLineItem domain models
- ✅ Invoice generation from completed appointments
- ✅ Line item management (flexible billing structure)
- ✅ Payment status tracking (Sent → Paid | Overdue)
- ✅ Patient viewing restrictions (own invoices with line items)
- ✅ Admin-only creation RBAC enforcement
- ✅ E2E testing for creation, viewing, and status transitions

**Key Takeaways**:
1. **Admin-Only Creation**: Only `AdminAuthorized` can generate invoices (RBAC)
2. **Flexible Line Items**: Support itemized billing with multiple charges
3. **Status Transitions**: Sent → Paid | Overdue (scheduled job marks overdue)
4. **Patient Transparency**: Patients see detailed line items and payment history
5. **Audit Trail**: Payment log tracks all payment transactions
6. **Automatic Notifications**: Patient notified when invoice issued and when overdue

## Cross-References

- [Appointments - Invoice Generation](appointments.md#workflow-4-doctor-completes-appointment)
- [Admin Guide - Invoice Management](../02_roles/admin_guide.md)
- [Patient Guide - Viewing Invoices](../02_roles/patient_guide.md)
- [Patient Onboarding Workflow](../04_workflows/patient_onboarding.md)
- [ADTs and Result Types](../../../../../documents/tutorials/adts_and_results.md)
- [Code Quality](../../../../../documents/engineering/code_quality.md)
