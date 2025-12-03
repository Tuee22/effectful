# Tutorial 03: Creating Prescriptions

> Extends base [Tutorial 03: ADTs and Results](../../../../documents/tutorials/03_adts_and_results.md); base steps apply. This tutorial documents HealthHub-specific deltas only.

---

## Overview

Prescription creation involves:
1. Authorization check (doctor must have `can_prescribe=true`)
2. Medication interaction check
3. Prescription creation
4. Patient notification

---

## Step 1: Check Doctor's Prescribing Authority

Not all doctors can prescribe. Check the `can_prescribe` field:

```bash
# Login as doctor
TOKEN=$(curl -s -X POST http://localhost:8851/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "dr.smith@example.com", "password": "doctor123"}' | jq -r '.access_token')

# Check your profile
curl http://localhost:8851/api/v1/doctors/me \
  -H "Authorization: Bearer $TOKEN"
```

Look for: `"can_prescribe": true`

---

## Step 2: Check for Drug Interactions

Before prescribing, check for interactions with the patient's current medications:

```bash
curl -X POST http://localhost:8851/api/v1/prescriptions/check-interactions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"medications": ["Aspirin", "Warfarin"]}'
```

**Severe interaction detected**:
```json
{
    "status": "interaction_detected",
    "interaction": {
        "medications": ["Aspirin", "Warfarin"],
        "severity": "severe",
        "description": "Increased bleeding risk"
    }
}
```

---

## Step 3: Create Prescription (No Interactions)

```bash
curl -X POST http://localhost:8851/api/v1/prescriptions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": "<patient_id>",
    "medication": "Amoxicillin",
    "dosage": "500mg",
    "frequency": "Three times daily",
    "duration_days": 10,
    "refills_remaining": 2,
    "notes": "Take with food"
  }'
```

**Success response**:
```json
{
    "id": "...",
    "patient_id": "...",
    "doctor_id": "...",
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

---

## Step 4: Handle Moderate Interactions

Moderate interactions require acknowledgment but can proceed:

```bash
# First check shows moderate interaction
curl -X POST http://localhost:8851/api/v1/prescriptions/check-interactions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"medications": ["Metformin", "Lisinopril"]}'

# Response:
# {
#     "status": "warning",
#     "interaction": {
#         "medications": ["Metformin", "Lisinopril"],
#         "severity": "moderate",
#         "description": "Monitor kidney function"
#     },
#     "override_available": true
# }

# Proceed with override
curl -X POST http://localhost:8851/api/v1/prescriptions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": "<patient_id>",
    "medication": "Lisinopril",
    "dosage": "10mg",
    "frequency": "Once daily",
    "duration_days": 30,
    "refills_remaining": 5,
    "notes": "Monitor kidney function",
    "override_interaction_warning": true
  }'
```

---

## Understanding the Effect Program

```python
def prescribe_medication_program(
    patient_id: UUID,
    doctor_auth: DoctorAuthorized,
    medication: str,
    dosage: str,
    frequency: str,
    duration_days: int,
) -> Generator[AllEffects, object, Prescription | None]:
    # Check prescribing authority
    if not doctor_auth.can_prescribe:
        return None

    # Get patient's current medications
    current_meds = yield GetActivePatientMedications(patient_id=patient_id)

    # Check for interactions
    check_result = yield CheckMedicationInteractions(
        medications=[*current_meds, medication]
    )

    match check_result:
        case MedicationInteractionWarning(severity="severe"):
            return None  # Block prescription

        case _:
            pass  # Safe to proceed

    # Create prescription
    prescription = yield CreatePrescription(
        patient_id=patient_id,
        doctor_id=doctor_auth.doctor_id,
        medication=medication,
        dosage=dosage,
        frequency=frequency,
        duration_days=duration_days,
        ...
    )

    # Notify patient
    yield PublishWebSocketNotification(
        channel=f"patient:{patient_id}:notifications",
        message={
            "type": "new_prescription",
            "medication": medication,
        },
        recipient_id=patient_id,
    )

    return prescription
```

---

## Common Interaction Severities

| Severity | Action | Example |
|----------|--------|---------|
| None | Proceed normally | Acetaminophen + Ibuprofen |
| Minor | Log warning, proceed | Simvastatin + Grapefruit |
| Moderate | Require acknowledgment | Metformin + Lisinopril |
| Severe | Block prescription | Warfarin + Aspirin |

---

## Viewing Prescriptions (as Patient)

```bash
# Login as patient
TOKEN=$(curl -s -X POST http://localhost:8851/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "alice@example.com", "password": "patient123"}' | jq -r '.access_token')

# View prescriptions
curl http://localhost:8851/api/v1/patients/me/prescriptions \
  -H "Authorization: Bearer $TOKEN"
```

---

## Next Steps

- [Tutorial 04: Lab Results](04_lab_results.md)
- [Medication Interactions](../product/medication_interactions.md)
- [Authorization System](../product/authorization_system.md)

---

**Last Updated**: 2025-11-25  
**Supersedes**: none  
**Referenced by**: ../README.md
