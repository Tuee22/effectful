# Tutorial 05: Billing and Invoices

> Creating and managing healthcare invoices.

---

## Overview

Invoice workflow:
1. Admin creates invoice with line items
2. Invoice sent to patient
3. Patient views and pays
4. Status tracked (draft → sent → paid/overdue)

---

## Step 1: Create Invoice (as Admin)

```bash
# Login as admin
TOKEN=$(curl -s -X POST http://localhost:8850/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@healthhub.com", "password": "admin123"}' | jq -r '.access_token')

# Create invoice
curl -X POST http://localhost:8850/api/v1/invoices \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": "<patient_id>",
    "appointment_id": "<appointment_id>",
    "line_items": [
        {
            "description": "Office Visit - New Patient",
            "quantity": 1,
            "unit_price": "200.00"
        },
        {
            "description": "Complete Blood Count (CBC)",
            "quantity": 1,
            "unit_price": "75.00"
        },
        {
            "description": "Basic Metabolic Panel (BMP)",
            "quantity": 1,
            "unit_price": "85.00"
        }
    ],
    "due_date": "2025-02-15"
  }'
```

**Response**:
```json
{
    "id": "...",
    "patient_id": "...",
    "appointment_id": "...",
    "status": "draft",
    "subtotal": "360.00",
    "tax_amount": "0.00",
    "total_amount": "360.00",
    "due_date": "2025-02-15",
    "line_items": [...]
}
```

---

## Step 2: Send Invoice

```bash
curl -X POST http://localhost:8850/api/v1/invoices/<invoice_id>/send \
  -H "Authorization: Bearer $TOKEN"
```

Status changes from `draft` to `sent`.

---

## Step 3: Patient Views Invoice

```bash
# Login as patient
TOKEN=$(curl -s -X POST http://localhost:8850/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "alice@example.com", "password": "patient123"}' | jq -r '.access_token')

# View all invoices
curl http://localhost:8850/api/v1/patients/me/invoices \
  -H "Authorization: Bearer $TOKEN"

# View specific invoice
curl http://localhost:8850/api/v1/invoices/<invoice_id> \
  -H "Authorization: Bearer $TOKEN"
```

---

## Step 4: Mark as Paid

```bash
# Admin marks invoice as paid
curl -X POST http://localhost:8850/api/v1/invoices/<invoice_id>/mark-paid \
  -H "Authorization: Bearer $TOKEN"
```

---

## Invoice Status Flow

```
draft → sent → paid
          ↓
       overdue
```

---

## Invoice Domain Model

```python
@dataclass(frozen=True)
class Invoice:
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

@dataclass(frozen=True)
class LineItem:
    id: UUID
    invoice_id: UUID
    description: str
    quantity: int
    unit_price: Decimal
    total: Decimal
    created_at: datetime
```

---

## Common Line Items

| Description | Typical Price |
|-------------|---------------|
| Office Visit - New Patient | $200 |
| Office Visit - Established | $150 |
| Complete Blood Count (CBC) | $75 |
| Basic Metabolic Panel (BMP) | $85 |
| Lipid Panel | $95 |
| Hemoglobin A1C | $50 |
| Urinalysis | $30 |
| X-Ray | $150-400 |
| EKG | $100 |

---

## Next Steps

- [Tutorial 06: Authorization](06_authorization.md)
- [Domain Models](../product/domain_models.md)
- [API Reference](../product/api_reference.md)

---

**Last Updated**: 2025-11-25
