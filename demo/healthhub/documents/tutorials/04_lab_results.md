# Tutorial 04: Lab Results

> Extends base [Tutorial 04: Testing Guide](../../../../documents/tutorials/04_testing_guide.md); base steps apply. This tutorial documents HealthHub-specific lab workflows only.

---

## Overview

Lab results workflow:
1. Doctor orders lab test
2. Results are recorded (may be critical)
3. Critical results trigger immediate notification
4. Doctor reviews and adds notes
5. Patient can view results

---

## Step 1: Create Lab Result (as Doctor)

```bash
# Login as doctor
TOKEN=$(curl -s -X POST http://localhost:8850/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "dr.smith@example.com", "password": "doctor123"}' | jq -r '.access_token')

# Create lab result
curl -X POST http://localhost:8850/api/v1/lab-results \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": "<patient_id>",
    "test_type": "CBC",
    "result_data": {
        "WBC": "7.5",
        "RBC": "4.8",
        "Hemoglobin": "14.2",
        "Hematocrit": "42%",
        "Platelets": "250"
    },
    "critical": false
  }'
```

---

## Step 2: Create Critical Lab Result

Critical results require immediate attention:

```bash
curl -X POST http://localhost:8850/api/v1/lab-results \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": "<patient_id>",
    "test_type": "BMP",
    "result_data": {
        "Sodium": "125",
        "Potassium": "6.5",
        "Glucose": "45"
    },
    "critical": true
  }'
```

**Critical values trigger**:
- Immediate WebSocket notification to doctor
- Alert flag in patient records
- Audit log entry

---

## Step 3: Doctor Reviews Result

```bash
curl -X POST http://localhost:8850/api/v1/lab-results/<result_id>/review \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "notes": "Elevated potassium - recommend dietary changes and recheck in 1 week."
  }'
```

---

## Step 4: Patient Views Results

```bash
# Login as patient
TOKEN=$(curl -s -X POST http://localhost:8850/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "alice@example.com", "password": "patient123"}' | jq -r '.access_token')

# View all lab results
curl http://localhost:8850/api/v1/patients/me/lab-results \
  -H "Authorization: Bearer $TOKEN"

# View specific result
curl http://localhost:8850/api/v1/lab-results/<result_id> \
  -H "Authorization: Bearer $TOKEN"
```

---

## Common Test Types

| Test Type | Description | Example Values |
|-----------|-------------|----------------|
| CBC | Complete Blood Count | WBC, RBC, Hemoglobin, Platelets |
| BMP | Basic Metabolic Panel | Sodium, Potassium, Glucose, Creatinine |
| Lipid | Lipid Panel | Total Cholesterol, LDL, HDL, Triglycerides |
| A1C | Hemoglobin A1C | Percentage (diabetes indicator) |
| TSH | Thyroid Stimulating Hormone | mIU/L |
| UA | Urinalysis | pH, Protein, Glucose, Blood |

---

## Critical Value Notifications

When a critical result is created, notifications are sent:

```python
def create_lab_result_program(
    patient_id: UUID,
    doctor_id: UUID,
    test_type: str,
    result_data: dict[str, str],
    critical: bool,
) -> Generator[AllEffects, object, LabResult]:
    # Create the lab result
    result = yield CreateLabResult(
        result_id=uuid4(),
        patient_id=patient_id,
        doctor_id=doctor_id,
        test_type=test_type,
        result_data=result_data,
        critical=critical,
    )

    # If critical, notify doctor immediately
    if critical:
        patient = yield GetPatientById(patient_id=patient_id)
        yield PublishWebSocketNotification(
            channel=f"doctor:{doctor_id}:notifications",
            message={
                "type": "critical_lab_result",
                "urgent": True,
                "result_id": str(result.id),
                "patient_name": f"{patient.first_name} {patient.last_name}",
                "test_type": test_type,
            },
            recipient_id=doctor_id,
        )

    # Log audit event
    yield LogAuditEvent(
        user_id=doctor_id,
        action="create_lab_result",
        resource_type="lab_result",
        resource_id=result.id,
        metadata={"critical": str(critical), "test_type": test_type},
        ...
    )

    return result
```

---

## Next Steps

- [Tutorial 05: Billing and Invoices](05_billing_invoices.md)
- [Notification System](../product/notification_system.md)
- [Audit Logging](../product/audit_logging.md)

---

**Last Updated**: 2025-11-25  
**Supersedes**: none  
**Referenced by**: ../README.md
