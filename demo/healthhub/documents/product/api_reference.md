# API Reference

> Extends base [Documentation Standards](../../../../documents/documentation_standards.md); base rules apply. HealthHub-specific API reference only.

---

## Overview

HealthHub exposes a REST API via FastAPI running on port 8850.

**Base URL**: `http://localhost:8850/api/v1`

**Authentication**: JWT Bearer token in Authorization header

---

## Authentication Endpoints

### POST /auth/login

Authenticate user and receive tokens.

**Request**:
```json
{
    "email": "patient@example.com",
    "password": "secure_password"
}
```

**Response** (200 OK):
```json
{
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "token_type": "bearer"
}
```

**Errors**:
- 401: Invalid credentials

---

### POST /auth/refresh

Renew access token using refresh token cookie.

**Response** (200 OK):
```json
{
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "token_type": "bearer"
}
```

**Errors**:
- 401: Invalid or expired refresh token

---

### POST /auth/logout

Clear refresh token and log out.

**Response**: 204 No Content

---

## Patient Endpoints

### GET /patients/{patient_id}

Get patient details.

**Authorization**: Patient (own record), Doctor, Admin

**Response** (200 OK):
```json
{
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "user_id": "123e4567-e89b-12d3-a456-426614174001",
    "first_name": "John",
    "last_name": "Doe",
    "date_of_birth": "1985-06-15",
    "blood_type": "A+",
    "allergies": ["Penicillin", "Peanuts"],
    "insurance_id": "INS123456",
    "emergency_contact": "Jane Doe: 555-0123",
    "phone": "555-0100",
    "address": "123 Main St, City, ST 12345"
}
```

**Errors**:
- 403: Not authorized to view this patient
- 404: Patient not found

---

### GET /patients/{patient_id}/appointments

List patient's appointments.

**Authorization**: Patient (own), Doctor (assigned), Admin

**Query Parameters**:
- `status`: Filter by status (requested, confirmed, in_progress, completed, cancelled)
- `limit`: Max results (default 20)
- `offset`: Pagination offset

**Response** (200 OK):
```json
{
    "appointments": [
        {
            "id": "...",
            "doctor_id": "...",
            "status": "confirmed",
            "scheduled_time": "2025-01-15T10:00:00Z",
            "reason": "Annual checkup"
        }
    ],
    "total": 5,
    "limit": 20,
    "offset": 0
}
```

---

## Appointment Endpoints

### POST /appointments

Create new appointment request.

**Authorization**: Patient, Admin

**Request**:
```json
{
    "patient_id": "123e4567-e89b-12d3-a456-426614174000",
    "doctor_id": "223e4567-e89b-12d3-a456-426614174000",
    "requested_time": "2025-01-15T10:00:00Z",
    "reason": "Annual checkup"
}
```

**Response** (201 Created):
```json
{
    "id": "323e4567-e89b-12d3-a456-426614174000",
    "patient_id": "123e4567-e89b-12d3-a456-426614174000",
    "doctor_id": "223e4567-e89b-12d3-a456-426614174000",
    "status": {
        "type": "requested",
        "requested_at": "2025-01-10T14:30:00Z"
    },
    "reason": "Annual checkup"
}
```

---

### GET /appointments/{appointment_id}

Get appointment details.

**Authorization**: Patient (participant), Doctor (participant), Admin

**Response** (200 OK):
```json
{
    "id": "323e4567-e89b-12d3-a456-426614174000",
    "patient_id": "123e4567-e89b-12d3-a456-426614174000",
    "doctor_id": "223e4567-e89b-12d3-a456-426614174000",
    "status": {
        "type": "confirmed",
        "confirmed_at": "2025-01-10T15:00:00Z",
        "scheduled_time": "2025-01-15T10:00:00Z"
    },
    "reason": "Annual checkup"
}
```

---

### POST /appointments/{appointment_id}/transition

Transition appointment status.

**Authorization**: Doctor (confirm, start, complete), Patient (cancel), Admin

**Request**:
```json
{
    "new_status": "confirmed",
    "scheduled_time": "2025-01-15T10:00:00Z"
}
```

**Response** (200 OK):
```json
{
    "id": "323e4567-e89b-12d3-a456-426614174000",
    "status": {
        "type": "confirmed",
        "confirmed_at": "2025-01-10T15:00:00Z",
        "scheduled_time": "2025-01-15T10:00:00Z"
    },
    "transition_result": "success"
}
```

**Errors**:
- 400: Invalid transition (e.g., Requested -> Completed)
- 403: Not authorized to perform this transition

---

## Prescription Endpoints

### POST /prescriptions

Create new prescription.

**Authorization**: Doctor (with can_prescribe=true)

**Request**:
```json
{
    "patient_id": "123e4567-e89b-12d3-a456-426614174000",
    "medication": "Amoxicillin",
    "dosage": "500mg",
    "frequency": "Three times daily",
    "duration_days": 10,
    "refills_remaining": 2,
    "notes": "Take with food"
}
```

**Response** (201 Created):
```json
{
    "id": "423e4567-e89b-12d3-a456-426614174000",
    "patient_id": "123e4567-e89b-12d3-a456-426614174000",
    "doctor_id": "223e4567-e89b-12d3-a456-426614174000",
    "medication": "Amoxicillin",
    "dosage": "500mg",
    "frequency": "Three times daily",
    "duration_days": 10,
    "refills_remaining": 2,
    "notes": "Take with food",
    "created_at": "2025-01-10T14:30:00Z",
    "expires_at": "2025-01-20T14:30:00Z"
}
```

**Errors**:
- 400: Severe drug interaction detected
- 403: Doctor lacks prescribing authority

---

### GET /prescriptions/{prescription_id}

Get prescription details.

**Authorization**: Patient (own), Doctor, Admin

**Response** (200 OK): Same as create response

---

### POST /prescriptions/check-interactions

Check medication interactions without creating prescription.

**Authorization**: Doctor, Admin

**Request**:
```json
{
    "medications": ["Warfarin", "Aspirin"]
}
```

**Response** (200 OK):
```json
{
    "status": "interaction_detected",
    "interaction": {
        "medications": ["Warfarin", "Aspirin"],
        "severity": "severe",
        "description": "Increased bleeding risk"
    }
}
```

---

## Lab Result Endpoints

### POST /lab-results

Create new lab result.

**Authorization**: Doctor, Admin

**Request**:
```json
{
    "patient_id": "123e4567-e89b-12d3-a456-426614174000",
    "test_type": "CBC",
    "result_data": {
        "WBC": "7.5",
        "RBC": "4.8",
        "Hemoglobin": "14.2",
        "Hematocrit": "42%",
        "Platelets": "250"
    },
    "critical": false
}
```

**Response** (201 Created):
```json
{
    "id": "523e4567-e89b-12d3-a456-426614174000",
    "patient_id": "123e4567-e89b-12d3-a456-426614174000",
    "doctor_id": "223e4567-e89b-12d3-a456-426614174000",
    "test_type": "CBC",
    "result_data": {...},
    "critical": false,
    "reviewed_by_doctor": false,
    "doctor_notes": null,
    "created_at": "2025-01-10T14:30:00Z"
}
```

---

### GET /lab-results/{result_id}

Get lab result details.

**Authorization**: Patient (own), Doctor, Admin

**Response** (200 OK): Same as create response

---

### POST /lab-results/{result_id}/review

Doctor reviews lab result.

**Authorization**: Doctor

**Request**:
```json
{
    "notes": "Results within normal range. No follow-up needed."
}
```

**Response** (200 OK):
```json
{
    "id": "523e4567-e89b-12d3-a456-426614174000",
    "reviewed_by_doctor": true,
    "doctor_notes": "Results within normal range. No follow-up needed."
}
```

---

## Invoice Endpoints

### POST /invoices

Create new invoice.

**Authorization**: Admin

**Request**:
```json
{
    "patient_id": "123e4567-e89b-12d3-a456-426614174000",
    "appointment_id": "323e4567-e89b-12d3-a456-426614174000",
    "line_items": [
        {
            "description": "Office Visit",
            "quantity": 1,
            "unit_price": "150.00"
        },
        {
            "description": "Lab Work - CBC",
            "quantity": 1,
            "unit_price": "75.00"
        }
    ],
    "due_date": "2025-02-10"
}
```

**Response** (201 Created):
```json
{
    "id": "623e4567-e89b-12d3-a456-426614174000",
    "patient_id": "123e4567-e89b-12d3-a456-426614174000",
    "appointment_id": "323e4567-e89b-12d3-a456-426614174000",
    "status": "draft",
    "subtotal": "225.00",
    "tax_amount": "0.00",
    "total_amount": "225.00",
    "due_date": "2025-02-10",
    "created_at": "2025-01-10T14:30:00Z"
}
```

---

### GET /invoices/{invoice_id}

Get invoice details with line items.

**Authorization**: Patient (own), Admin

---

## Health Check

### GET /health

Check API health status.

**Authorization**: None (public)

**Response** (200 OK):
```json
{
    "status": "healthy",
    "database": "connected",
    "redis": "connected",
    "version": "1.0.0"
}
```

---

## Error Response Format

All errors return consistent format:

```json
{
    "detail": "Error message describing what went wrong",
    "error_code": "SPECIFIC_ERROR_CODE"
}
```

**Common Error Codes**:
- `INVALID_CREDENTIALS`: Authentication failed
- `TOKEN_EXPIRED`: JWT token has expired
- `UNAUTHORIZED`: Insufficient permissions
- `NOT_FOUND`: Resource does not exist
- `INVALID_TRANSITION`: Invalid state machine transition
- `SEVERE_INTERACTION`: Drug interaction blocked prescription

---

## Related Documentation

### Domain Knowledge
- [Appointment Workflows](../domain/appointment_workflows.md) - Appointment lifecycle and medical context
- [HIPAA Compliance](../domain/hipaa_compliance.md) - PHI access logging requirements

### Best Practices
- [Authorization Patterns](../engineering/authorization_patterns.md) - Route-level authorization checks
- [Testing](../engineering/testing.md) - API endpoint testing strategies

### Product Documentation
- [Authentication](authentication.md) - JWT token details and login/logout endpoints
- [Authorization System](authorization_system.md) - Permission model and role-based access
- [Domain Models](domain_models.md) - Entity schemas returned by endpoints
- [Effects Reference](effects_reference.md) - Backend operations triggered by API calls
- [Appointment State Machine](appointment_state_machine.md) - State transitions via API

---

**Last Updated**: 2025-11-26  
**Supersedes**: none  
**Referenced by**: ../README.md, ../engineering/fastapi_integration_patterns.md
**Maintainer**: HealthHub Team
