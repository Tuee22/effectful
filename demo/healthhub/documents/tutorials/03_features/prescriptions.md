# Prescriptions Feature

**Status**: Authoritative source
**Supersedes**: none
**Referenced by**: demo/healthhub/documents/tutorials/README.md

> **Purpose**: Complete reference for HealthHub prescription system: prescription domain model, medication interaction checking, doctor-only creation with can_prescribe flag, and RBAC enforcement.

> **Core Doctrines**: For comprehensive patterns, see:
> - [ADTs and Result Types](../../../../../documents/tutorials/adts_and_results.md)
> - [Code Quality](../../../../../documents/engineering/code_quality.md)
> - [Effect Patterns](../../../../../documents/engineering/effect_patterns.md)

## Prerequisites

- Docker workflow running; commands executed via `docker compose -f docker/docker-compose.yml`.
- Completed [Intermediate Journey](../01_journeys/intermediate_journey.md).
- Familiarity with healthcare prescriptions, ADTs, Python type hints, pattern matching.

## Learning Objectives

- Define Prescription domain model (medication, dosage, frequency, duration, refills)
- Implement doctor-only creation with `can_prescribe` flag RBAC enforcement
- Execute medication interaction checking against patient allergies and current prescriptions
- Apply patient viewing restrictions (own prescriptions only)
- Apply doctor viewing (all prescriptions with filtering)
- Handle prescription expiration and refill tracking
- Write e2e tests for creation, viewing, and RBAC enforcement

## Overview

**Prescription System Architecture**:
- **Creation**: Doctors only (with `can_prescribe=true` flag)
- **Interaction Checking**: Automated validation against allergies and existing prescriptions
- **Expiration**: Prescriptions expire after specified duration
- **Refills**: Track remaining refills, prevent over-refill
- **Viewing**: Patients see own prescriptions, doctors see all prescriptions

**Safety Features**:
- **Allergy checking**: Block prescriptions that interact with patient allergies
- **Drug interaction checking**: Warn about interactions with current prescriptions
- **Controlled substance tracking**: Flag controlled substances for DEA compliance
- **Refill limits**: Prevent excessive refills without doctor review

## Domain Models

### Prescription Model

**File**: `demo/healthhub/backend/app/domain/prescriptions.py`

```python
# file: demo/healthhub/backend/app/domain/prescriptions.py
from dataclasses import dataclass
from uuid import UUID
from datetime import datetime

@dataclass(frozen=True)
class Prescription:
    """
    Prescription created by doctor for patient.

    Fields:
    - prescription_id: Unique identifier
    - patient_id: Links to patients table
    - doctor_id: Links to doctors table (prescribing doctor)
    - medication: Medication name (e.g., "Lisinopril", "Metformin")
    - dosage: Dosage amount (e.g., "10mg", "500mg")
    - frequency: How often to take (e.g., "Once daily", "Twice daily")
    - duration_days: Prescription duration in days (e.g., 30, 90)
    - refills: Number of refills remaining
    - notes: Doctor's instructions (e.g., "Take with food", "Monitor blood pressure")
    - created_at: When prescription was created
    - expires_at: When prescription expires (created_at + duration_days)
    """
    prescription_id: UUID
    patient_id: UUID
    doctor_id: UUID
    medication: str
    dosage: str
    frequency: str
    duration_days: int
    refills: int
    notes: str
    created_at: datetime
    expires_at: datetime
```

### Interaction Result

**File**: `demo/healthhub/backend/app/domain/prescriptions.py`

```python
# file: demo/healthhub/backend/app/domain/prescriptions.py
from dataclasses import dataclass

@dataclass(frozen=True)
class InteractionWarning:
    """
    Medication interaction warning.

    Fields:
    - severity: "low" | "medium" | "high" | "critical"
    - description: Human-readable warning description
    - recommendation: Action to take (e.g., "Monitor closely", "Consider alternative")
    """
    severity: str  # "low" | "medium" | "high" | "critical"
    description: str
    recommendation: str

@dataclass(frozen=True)
class InteractionCheckResult:
    """
    Result of medication interaction check.

    Fields:
    - is_safe: True if no critical interactions, False if blocked
    - warnings: List of interaction warnings (may be empty)
    """
    is_safe: bool
    warnings: list[InteractionWarning]
```

## Medication Interaction Checking

### Check Against Patient Allergies

**File**: `demo/healthhub/backend/app/programs/prescription_programs.py`

```python
# file: demo/healthhub/backend/app/programs/prescription_programs.py
from effectful import Effect, Result, Ok, Err
from effectful.effects import DatabaseEffect
from demo.healthhub.backend.app.effects.healthcare_effect import CheckMedicationInteraction
from uuid import UUID
from typing import Generator

def check_allergy_interactions(
    patient_id: UUID,
    medication: str
) -> Generator[Effect, Result, Result[list[InteractionWarning]]]:
    """
    Check medication against patient allergies.

    Returns list of interaction warnings (empty if no interactions).
    """

    # Fetch patient allergies
    allergies_result = yield DatabaseEffect.Query(
        query="SELECT allergies FROM patients WHERE patient_id = $1",
        params=(patient_id,)
    )

    match allergies_result:
        case Ok(rows) if len(rows) > 0:
            allergies = rows[0]["allergies"]  # List of allergy strings
        case Ok([]):
            return Err("Patient not found")
        case Err(error):
            return Err(f"Database error: {error}")

    # Check medication against allergies
    warnings: list[InteractionWarning] = []

    for allergy in allergies:
        # Simplified interaction checking (production would use drug database API)
        if _medication_contains_allergen(medication, allergy):
            warnings.append(
                InteractionWarning(
                    severity="critical",
                    description=f"{medication} may cause allergic reaction in patients with {allergy} allergy",
                    recommendation="Do not prescribe - consider alternative medication"
                )
            )

    return Ok(warnings)

def _medication_contains_allergen(medication: str, allergen: str) -> bool:
    """
    Check if medication contains allergen.

    Simplified implementation - production would use drug database.
    """
    # Penicillin family
    if allergen.lower() == "penicillin":
        penicillin_drugs = ["amoxicillin", "ampicillin", "penicillin", "augmentin"]
        return any(drug in medication.lower() for drug in penicillin_drugs)

    # Sulfa drugs
    if allergen.lower() == "sulfa":
        sulfa_drugs = ["sulfamethoxazole", "trimethoprim", "bactrim"]
        return any(drug in medication.lower() for drug in sulfa_drugs)

    # Direct match
    return allergen.lower() in medication.lower()
```

### Check Against Current Prescriptions

**File**: `demo/healthhub/backend/app/programs/prescription_programs.py`

```python
# file: demo/healthhub/backend/app/programs/prescription_programs.py
def check_drug_interactions(
    patient_id: UUID,
    new_medication: str
) -> Generator[Effect, Result, Result[list[InteractionWarning]]]:
    """
    Check new medication against patient's current prescriptions.

    Returns list of interaction warnings (empty if no interactions).
    """

    # Fetch active prescriptions (not expired)
    prescriptions_result = yield DatabaseEffect.Query(
        query="""
            SELECT medication, dosage
            FROM prescriptions
            WHERE patient_id = $1
              AND expires_at > NOW()
        """,
        params=(patient_id,)
    )

    match prescriptions_result:
        case Ok(rows):
            current_medications = [row["medication"] for row in rows]
        case Err(error):
            return Err(f"Database error: {error}")

    # Check interactions
    warnings: list[InteractionWarning] = []

    for current_med in current_medications:
        interaction = _check_drug_pair_interaction(current_med, new_medication)
        if interaction:
            warnings.append(interaction)

    return Ok(warnings)

def _check_drug_pair_interaction(med1: str, med2: str) -> InteractionWarning | None:
    """
    Check interaction between two medications.

    Simplified implementation - production would use drug interaction database.
    """
    # Example interactions (simplified)
    known_interactions = {
        ("warfarin", "aspirin"): InteractionWarning(
            severity="high",
            description="Increased bleeding risk when combining Warfarin and Aspirin",
            recommendation="Monitor INR closely, consider alternative antiplatelet"
        ),
        ("lisinopril", "spironolactone"): InteractionWarning(
            severity="medium",
            description="Both medications increase potassium levels",
            recommendation="Monitor potassium levels regularly"
        ),
        ("metformin", "contrast dye"): InteractionWarning(
            severity="high",
            description="Contrast dye may increase metformin toxicity risk",
            recommendation="Discontinue metformin 48 hours before contrast procedure"
        ),
    }

    # Check both directions
    pair1 = (med1.lower(), med2.lower())
    pair2 = (med2.lower(), med1.lower())

    return known_interactions.get(pair1) or known_interactions.get(pair2)
```

## Prescription Creation Workflow

**Endpoint**: `POST /api/prescriptions`

**Request**:
```json
{
  "patient_id": "30000000-0000-0000-0000-000000000001",
  "medication": "Lisinopril",
  "dosage": "10mg",
  "frequency": "Once daily",
  "duration_days": 90,
  "refills": 2,
  "notes": "Take in the morning with water. Monitor blood pressure."
}
```

**Program**: `demo/healthhub/backend/app/programs/prescription_programs.py`

```python
# file: demo/healthhub/backend/app/programs/prescription_programs.py
def create_prescription_with_interaction_check(
    patient_id: UUID,
    doctor_id: UUID,
    medication: str,
    dosage: str,
    frequency: str,
    duration_days: int,
    refills: int,
    notes: str
) -> Generator[Effect, Result, Result[dict]]:
    """
    Create prescription with medication interaction checking.

    Flow:
    1. Check medication against patient allergies
    2. Check medication against current prescriptions
    3. Evaluate warnings (block if critical, warn if high/medium, allow if low)
    4. Create prescription if safe
    5. Notify patient
    """

    # Step 1: Check allergies
    allergy_check_program = check_allergy_interactions(patient_id, medication)
    allergy_result = yield from allergy_check_program

    match allergy_result:
        case Ok(allergy_warnings):
            # Check for critical allergy interactions
            critical_allergy = next(
                (w for w in allergy_warnings if w.severity == "critical"),
                None
            )
            if critical_allergy:
                return Err(f"Critical allergy interaction: {critical_allergy.description}")
        case Err(error):
            return Err(f"Allergy check failed: {error}")

    # Step 2: Check drug interactions
    drug_check_program = check_drug_interactions(patient_id, medication)
    drug_result = yield from drug_check_program

    match drug_result:
        case Ok(drug_warnings):
            # Accumulate all warnings
            all_warnings = allergy_warnings + drug_warnings

            # Block if any critical warnings
            critical_warning = next(
                (w for w in all_warnings if w.severity == "critical"),
                None
            )
            if critical_warning:
                return Err(f"Critical drug interaction: {critical_warning.description}")
        case Err(error):
            return Err(f"Drug interaction check failed: {error}")

    # Step 3: Create prescription (checks passed or only low/medium warnings)
    prescription_id = uuid4()
    created_at = datetime.now(timezone.utc)
    expires_at = created_at + timedelta(days=duration_days)

    insert_result = yield DatabaseEffect.Execute(
        query="""
            INSERT INTO prescriptions (
                prescription_id, patient_id, doctor_id, medication, dosage,
                frequency, duration_days, refills, notes, created_at, expires_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        """,
        params=(
            prescription_id, patient_id, doctor_id, medication, dosage,
            frequency, duration_days, refills, notes, created_at, expires_at
        )
    )

    match insert_result:
        case Ok(_):
            # Step 4: Notify patient
            _ = yield NotificationEffect.SendPatientNotification(
                patient_id=patient_id,
                notification_type="prescription_ready",
                message=f"New prescription for {medication} is ready",
            )

            return Ok({
                "prescription_id": prescription_id,
                "warnings": all_warnings,  # Return warnings for doctor review
            })
        case Err(error):
            return Err(f"Failed to create prescription: {error}")
```

**API Endpoint with RBAC**:
```python
# file: demo/healthhub/backend/app/api/prescriptions.py
from fastapi import APIRouter, Depends, HTTPException
from demo.healthhub.backend.app.api.dependencies import get_auth_state
from demo.healthhub.backend.app.domain.auth import AuthorizationState, DoctorAuthorized, PatientAuthorized, AdminAuthorized, Unauthorized

router = APIRouter(prefix="/api/prescriptions")

@router.post("/")
async def create_prescription(
    prescription_data: dict,
    auth_state: AuthorizationState = Depends(get_auth_state)
):
    """
    Create prescription (doctors only, with can_prescribe flag).
    """

    match auth_state:
        case DoctorAuthorized(doctor_id=did, can_prescribe=True):
            # Authorized - doctor can prescribe
            program = create_prescription_with_interaction_check(
                patient_id=UUID(prescription_data["patient_id"]),
                doctor_id=did,
                medication=prescription_data["medication"],
                dosage=prescription_data["dosage"],
                frequency=prescription_data["frequency"],
                duration_days=prescription_data["duration_days"],
                refills=prescription_data["refills"],
                notes=prescription_data["notes"],
            )

            result = await interpreter.run(program)

            match result:
                case Ok(response):
                    return {
                        "prescription_id": str(response["prescription_id"]),
                        "warnings": [
                            {
                                "severity": w.severity,
                                "description": w.description,
                                "recommendation": w.recommendation,
                            }
                            for w in response["warnings"]
                        ]
                    }
                case Err(error):
                    raise HTTPException(400, str(error))

        case DoctorAuthorized(can_prescribe=False):
            raise HTTPException(403, "Doctor not authorized to prescribe medications")

        case PatientAuthorized() | AdminAuthorized():
            raise HTTPException(403, "Only doctors can create prescriptions")

        case Unauthorized(reason=reason):
            raise HTTPException(401, f"Unauthorized: {reason}")
```

**RBAC Enforcement**:
1. **Doctor-only**: Only `DoctorAuthorized` variant can create prescriptions
2. **can_prescribe flag**: Doctor must have `can_prescribe=true` in database
3. **Pattern matching**: MyPy enforces exhaustive case coverage

## Viewing Prescriptions

### Patient View (Own Prescriptions Only)

**Endpoint**: `GET /api/prescriptions` (as patient)

**Program**:
```python
# file: demo/healthhub/backend/app/programs/prescription_programs.py
def get_patient_prescriptions(patient_id: UUID) -> Generator[Effect, Result, Result[list[dict]]]:
    """
    Get all prescriptions for patient.

    Returns active and expired prescriptions.
    """

    prescriptions_result = yield DatabaseEffect.Query(
        query="""
            SELECT
                p.prescription_id,
                p.medication,
                p.dosage,
                p.frequency,
                p.duration_days,
                p.refills,
                p.notes,
                p.created_at,
                p.expires_at,
                d.first_name || ' ' || d.last_name AS doctor_name,
                d.specialization
            FROM prescriptions p
            JOIN doctors d ON p.doctor_id = d.doctor_id
            WHERE p.patient_id = $1
            ORDER BY p.created_at DESC
        """,
        params=(patient_id,)
    )

    match prescriptions_result:
        case Ok(rows):
            return Ok(rows)
        case Err(error):
            return Err(f"Failed to fetch prescriptions: {error}")
```

**API Endpoint**:
```python
# file: demo/healthhub/backend/app/api/prescriptions.py
@router.get("/")
async def get_prescriptions(
    auth_state: AuthorizationState = Depends(get_auth_state)
):
    """
    Get prescriptions (role-based filtering).

    - Patient: Own prescriptions only
    - Doctor/Admin: All prescriptions (with optional patient_id filter)
    """

    match auth_state:
        case PatientAuthorized(patient_id=pid):
            # Patient can only view own prescriptions
            program = get_patient_prescriptions(pid)
            result = await interpreter.run(program)

            match result:
                case Ok(prescriptions):
                    return {"prescriptions": prescriptions}
                case Err(error):
                    raise HTTPException(500, str(error))

        case DoctorAuthorized() | AdminAuthorized():
            # Doctor/Admin can view all prescriptions
            # ... (fetch all with optional patient_id filter) ...
            pass

        case Unauthorized(reason=reason):
            raise HTTPException(401, f"Unauthorized: {reason}")
```

### Doctor View (All Prescriptions with Filtering)

**Endpoint**: `GET /api/prescriptions?patient_id=<uuid>` (as doctor)

**Program**:
```python
# file: demo/healthhub/backend/app/programs/prescription_programs.py
def get_all_prescriptions(
    patient_id: UUID | None = None
) -> Generator[Effect, Result, Result[list[dict]]]:
    """
    Get all prescriptions (doctor/admin only).

    Optional patient_id filter.
    """

    if patient_id:
        query = """
            SELECT
                p.prescription_id,
                p.medication,
                p.dosage,
                p.frequency,
                p.refills,
                p.created_at,
                p.expires_at,
                pat.first_name || ' ' || pat.last_name AS patient_name
            FROM prescriptions p
            JOIN patients pat ON p.patient_id = pat.patient_id
            WHERE p.patient_id = $1
            ORDER BY p.created_at DESC
        """
        params = (patient_id,)
    else:
        query = """
            SELECT
                p.prescription_id,
                p.medication,
                p.dosage,
                p.frequency,
                p.refills,
                p.created_at,
                p.expires_at,
                pat.first_name || ' ' || pat.last_name AS patient_name
            FROM prescriptions p
            JOIN patients pat ON p.patient_id = pat.patient_id
            ORDER BY p.created_at DESC
            LIMIT 100
        """
        params = ()

    prescriptions_result = yield DatabaseEffect.Query(query=query, params=params)

    match prescriptions_result:
        case Ok(rows):
            return Ok(rows)
        case Err(error):
            return Err(f"Failed to fetch prescriptions: {error}")
```

## Refill Management

**Endpoint**: `POST /api/prescriptions/{prescription_id}/refill`

**Program**:
```python
# file: demo/healthhub/backend/app/programs/prescription_programs.py
def refill_prescription(prescription_id: UUID) -> Generator[Effect, Result, Result[dict]]:
    """
    Refill prescription (decrement refills count).

    Validation:
    - Prescription must not be expired
    - Refills remaining must be > 0
    """

    # Fetch prescription
    prescription_result = yield DatabaseEffect.Query(
        query="SELECT * FROM prescriptions WHERE prescription_id = $1",
        params=(prescription_id,)
    )

    match prescription_result:
        case Ok(rows) if len(rows) > 0:
            prescription = rows[0]
        case Ok([]):
            return Err("Prescription not found")
        case Err(error):
            return Err(f"Database error: {error}")

    # Validate not expired
    if prescription["expires_at"] < datetime.now(timezone.utc):
        return Err("Prescription expired - contact doctor for new prescription")

    # Validate refills remaining
    if prescription["refills"] <= 0:
        return Err("No refills remaining - contact doctor for refill authorization")

    # Decrement refills
    update_result = yield DatabaseEffect.Execute(
        query="""
            UPDATE prescriptions
            SET refills = refills - 1
            WHERE prescription_id = $1
        """,
        params=(prescription_id,)
    )

    match update_result:
        case Ok(_):
            return Ok({
                "prescription_id": prescription_id,
                "refills_remaining": prescription["refills"] - 1,
            })
        case Err(error):
            return Err(f"Failed to refill prescription: {error}")
```

## E2E Tests

**File**: `demo/healthhub/tests/pytest/e2e/test_prescriptions.py`

```python
# file: demo/healthhub/tests/pytest/e2e/test_prescriptions.py
import pytest
from demo.healthhub.backend.app.programs.prescription_programs import (
    create_prescription_with_interaction_check,
    get_patient_prescriptions,
)
from effectful import Ok, Err

@pytest.mark.asyncio
async def test_create_prescription_success(clean_healthhub_state, postgres_interpreter):
    """E2E: Create prescription with no interactions."""

    program = create_prescription_with_interaction_check(
        patient_id=UUID("30000000-0000-0000-0000-000000000002"),  # Bob (no allergies conflicting with Metformin)
        doctor_id=UUID("40000000-0000-0000-0000-000000000001"),
        medication="Metformin",
        dosage="500mg",
        frequency="Twice daily",
        duration_days=90,
        refills=2,
        notes="Take with meals"
    )

    result = await postgres_interpreter.run(program)

    match result:
        case Ok(response):
            assert "prescription_id" in response
            assert len(response["warnings"]) == 0  # No interactions
        case Err(error):
            pytest.fail(f"Expected Ok, got Err: {error}")

@pytest.mark.asyncio
async def test_create_prescription_blocked_by_allergy(clean_healthhub_state, postgres_interpreter):
    """E2E: Prescription blocked due to patient allergy."""

    # Alice has Penicillin allergy
    program = create_prescription_with_interaction_check(
        patient_id=UUID("30000000-0000-0000-0000-000000000001"),  # Alice (Penicillin allergy)
        doctor_id=UUID("40000000-0000-0000-0000-000000000001"),
        medication="Amoxicillin",  # Penicillin-based antibiotic
        dosage="500mg",
        frequency="Three times daily",
        duration_days=10,
        refills=0,
        notes="Take with food"
    )

    result = await postgres_interpreter.run(program)

    match result:
        case Err(error):
            assert "allergy" in error.lower()
            assert "penicillin" in error.lower()
        case Ok(_):
            pytest.fail("Expected Err due to allergy interaction, got Ok")

@pytest.mark.asyncio
async def test_patient_can_only_view_own_prescriptions(clean_healthhub_state, postgres_interpreter):
    """E2E: Patient viewing prescriptions is filtered to own prescriptions only."""

    # Alice's prescriptions
    alice_program = get_patient_prescriptions(UUID("30000000-0000-0000-0000-000000000001"))
    alice_result = await postgres_interpreter.run(alice_program)

    match alice_result:
        case Ok(prescriptions):
            # Verify all prescriptions belong to Alice
            for prescription in prescriptions:
                assert prescription["patient_id"] == UUID("30000000-0000-0000-0000-000000000001")
        case Err(error):
            pytest.fail(f"Expected Ok, got Err: {error}")
```

## Summary

**You have learned**:
- ✅ Prescription domain model (medication, dosage, frequency, duration, refills)
- ✅ Doctor-only creation with `can_prescribe` flag RBAC enforcement
- ✅ Medication interaction checking (allergies and drug interactions)
- ✅ Patient viewing restrictions (own prescriptions only)
- ✅ Doctor viewing (all prescriptions with filtering)
- ✅ Prescription expiration and refill management
- ✅ E2E testing for creation, viewing, and RBAC

**Key Takeaways**:
1. **Medication Safety**: Automated interaction checking prevents dangerous prescriptions
2. **RBAC Enforcement**: `can_prescribe` flag controls prescription creation access
3. **Pattern Matching**: AuthorizationState ADT enforces role-based access
4. **Warnings vs Errors**: Low/medium warnings inform, critical warnings block
5. **Expiration Tracking**: Automatic expiration based on duration
6. **Refill Management**: Prevent over-refill, enforce doctor review

## Cross-References

- [Intermediate Journey - Prescription Creation](../01_journeys/intermediate_journey.md#step-3-create-prescription-with-interaction-checking)
- [Authentication - can_prescribe Flag](authentication.md#pattern-3-feature-flags-doctor-prescription-access)
- [ADTs and Result Types](../../../../../documents/tutorials/adts_and_results.md)
- [Code Quality](../../../../../documents/engineering/code_quality.md)
- [Doctor Guide](../02_roles/doctor_guide.md)
- [Prescription Workflow](../04_workflows/prescription_workflow.md)
