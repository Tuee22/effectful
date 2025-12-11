# Lab Results Feature

**Status**: Authoritative source (HealthHub tutorial patterns)
**Supersedes**: none
**Referenced by**: demo/healthhub/documents/tutorials/README.md

> **Purpose**: Complete reference for HealthHub lab results system: lab result domain model, critical value alerts, doctor review workflow, and patient notifications.

> **Core Doctrines**: For comprehensive patterns, see:
> - [ADTs and Result Types](../../../../../documents/tutorials/adts_and_results.md)
> - [Code Quality](../../../../../documents/engineering/code_quality.md)
> - [Effect Patterns](../../../../../documents/engineering/effect_patterns.md)

## Prerequisites

- Docker workflow running; commands executed via `docker compose -f docker/docker-compose.yml`.
- Completed [Intermediate Journey](../01_journeys/intermediate_journey.md).
- Familiarity with healthcare lab results, ADTs, Python type hints, pattern matching.

## Learning Objectives

- Define LabResult domain model (test_type, result_data, critical flag)
- Implement critical value alert system (automatic doctor notification)
- Execute doctor review workflow (reviewed_by_doctor flag + notes)
- Handle patient notifications (critical results notification cascade)
- Apply patient viewing restrictions (own results with doctor annotations)
- Write e2e tests for critical alerts, doctor review, and patient viewing

## Overview

**Lab Results System Architecture**:
- **Submission**: Lab submits results via API (external system integration)
- **Critical Detection**: Automatic flagging based on reference ranges
- **Doctor Alerts**: Critical results trigger immediate doctor notification
- **Doctor Review**: Doctor reviews results and adds clinical notes
- **Patient Notification**: Doctor review triggers patient notification
- **Patient Viewing**: Patients see results with doctor annotations

**Critical Alert Flow**:
1. Lab submits result with critical values
2. System automatically flags as critical
3. Immediate notification sent to doctor
4. Doctor reviews and adds notes
5. Patient notified that results are ready with doctor notes

## Domain Models

### LabResult Model

**File**: `demo/healthhub/backend/app/domain/lab_results.py`

```python
# file: demo/healthhub/backend/app/domain/lab_results.py
from dataclasses import dataclass
from uuid import UUID
from datetime import datetime

@dataclass(frozen=True)
class LabResult:
    """
    Lab test result for patient.

    Fields:
    - lab_result_id: Unique identifier
    - patient_id: Links to patients table
    - doctor_id: Ordering physician (links to doctors table)
    - test_type: Type of lab test (e.g., "Lipid Panel", "CBC", "Metabolic Panel")
    - result_data: JSON object with test values (e.g., {"cholesterol": 195, "ldl": 120})
    - reference_ranges: JSON object with normal ranges (e.g., {"cholesterol": {"min": 125, "max": 200}})
    - critical: Boolean flag (true if any value outside critical range)
    - reviewed_by_doctor: Boolean flag (true after doctor reviews)
    - doctor_notes: Doctor's clinical interpretation (null until reviewed)
    - created_at: When lab submitted result
    - reviewed_at: When doctor reviewed (null until reviewed)
    """
    lab_result_id: UUID
    patient_id: UUID
    doctor_id: UUID
    test_type: str
    result_data: dict
    reference_ranges: dict
    critical: bool
    reviewed_by_doctor: bool
    doctor_notes: str | None
    created_at: datetime
    reviewed_at: datetime | None
```

### Critical Value Detection

**File**: `demo/healthhub/backend/app/domain/lab_results.py`

```python
# file: demo/healthhub/backend/app/domain/lab_results.py
def detect_critical_values(
    result_data: dict,
    reference_ranges: dict
) -> tuple[bool, list[str]]:
    """
    Detect critical values in lab result.

    Returns:
    - is_critical: True if any value is critical
    - critical_values: List of critical value descriptions
    """

    critical_values: list[str] = []

    for test_name, value in result_data.items():
        if test_name not in reference_ranges:
            continue  # No reference range defined

        ref_range = reference_ranges[test_name]

        # Check if value is critically low
        if "critical_low" in ref_range and value < ref_range["critical_low"]:
            critical_values.append(
                f"{test_name}: {value} (critically low, threshold: {ref_range['critical_low']})"
            )

        # Check if value is critically high
        if "critical_high" in ref_range and value > ref_range["critical_high"]:
            critical_values.append(
                f"{test_name}: {value} (critically high, threshold: {ref_range['critical_high']})"
            )

    is_critical = len(critical_values) > 0

    return is_critical, critical_values
```

**Example Reference Ranges**:
```python
# Lipid Panel reference ranges
lipid_panel_ranges = {
    "total_cholesterol": {
        "min": 125,
        "max": 200,
        "critical_low": 100,
        "critical_high": 300,
        "unit": "mg/dL"
    },
    "ldl": {
        "min": 50,
        "max": 130,
        "critical_low": 40,
        "critical_high": 190,
        "unit": "mg/dL"
    },
    "hdl": {
        "min": 40,
        "max": 100,
        "critical_low": 30,
        "critical_high": None,  # No critical high for HDL
        "unit": "mg/dL"
    },
    "triglycerides": {
        "min": 50,
        "max": 150,
        "critical_low": 30,
        "critical_high": 500,
        "unit": "mg/dL"
    }
}
```

## Lab Result Submission Workflow

**Endpoint**: `POST /api/lab-results` (external lab system)

**Request**:
```json
{
  "patient_id": "30000000-0000-0000-0000-000000000001",
  "doctor_id": "40000000-0000-0000-0000-000000000001",
  "test_type": "Lipid Panel",
  "result_data": {
    "total_cholesterol": 280,
    "ldl": 190,
    "hdl": 35,
    "triglycerides": 250
  }
}
```

**Program**: `demo/healthhub/backend/app/programs/lab_result_programs.py`

```python
# file: demo/healthhub/backend/app/programs/lab_result_programs.py
from effectful import Effect, Result, Ok, Err
from effectful.effects import DatabaseEffect
from demo.healthhub.backend.app.effects.notification_effect import SendDoctorAlert, SendPatientNotification
from uuid import UUID, uuid4
from typing import Generator
from datetime import datetime, timezone

def submit_lab_result(
    patient_id: UUID,
    doctor_id: UUID,
    test_type: str,
    result_data: dict
) -> Generator[Effect, Result, Result[dict]]:
    """
    Submit lab result with automatic critical value detection.

    Flow:
    1. Fetch reference ranges for test type
    2. Detect critical values
    3. Create lab result record
    4. Send doctor alert if critical
    5. Return lab result
    """

    # Step 1: Fetch reference ranges
    ranges_result = yield DatabaseEffect.Query(
        query="SELECT reference_ranges FROM lab_test_types WHERE test_type = $1",
        params=(test_type,)
    )

    match ranges_result:
        case Ok(rows) if len(rows) > 0:
            reference_ranges = rows[0]["reference_ranges"]
        case Ok([]):
            return Err(f"Unknown test type: {test_type}")
        case Err(error):
            return Err(f"Database error: {error}")

    # Step 2: Detect critical values
    is_critical, critical_values = detect_critical_values(result_data, reference_ranges)

    # Step 3: Create lab result
    lab_result_id = uuid4()
    created_at = datetime.now(timezone.utc)

    insert_result = yield DatabaseEffect.Execute(
        query="""
            INSERT INTO lab_results (
                lab_result_id, patient_id, doctor_id, test_type,
                result_data, reference_ranges, critical,
                reviewed_by_doctor, doctor_notes, created_at, reviewed_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        """,
        params=(
            lab_result_id, patient_id, doctor_id, test_type,
            json.dumps(result_data), json.dumps(reference_ranges), is_critical,
            False, None, created_at, None
        )
    )

    match insert_result:
        case Ok(_):
            pass  # Lab result created
        case Err(error):
            return Err(f"Failed to create lab result: {error}")

    # Step 4: Send doctor alert if critical
    if is_critical:
        alert_message = f"Critical lab result for patient: {test_type}\n" + "\n".join(critical_values)

        _ = yield SendDoctorAlert(
            doctor_id=doctor_id,
            alert_type="critical_lab_result",
            message=alert_message,
            urgency="high",
            metadata={
                "lab_result_id": str(lab_result_id),
                "patient_id": str(patient_id),
                "test_type": test_type,
                "critical_values": critical_values,
            }
        )

    # Step 5: Return lab result
    return Ok({
        "lab_result_id": lab_result_id,
        "critical": is_critical,
        "critical_values": critical_values if is_critical else [],
    })
```

**Critical Alert Characteristics**:
- **Immediate**: Sent synchronously during lab result submission
- **High urgency**: Marked as "high" urgency for doctor's attention
- **Contextual**: Includes which values are critical and thresholds
- **Actionable**: Doctor can immediately review and respond

## Doctor Review Workflow

**Endpoint**: `POST /api/lab-results/{lab_result_id}/review`

**Request**:
```json
{
  "doctor_notes": "Total cholesterol and LDL are critically elevated. HDL is critically low. Patient at high cardiovascular risk. Recommend immediate statin therapy (Atorvastatin 40mg daily) and lifestyle modifications. Follow-up lipid panel in 3 months."
}
```

**Program**: `demo/healthhub/backend/app/programs/lab_result_programs.py`

```python
# file: demo/healthhub/backend/app/programs/lab_result_programs.py
def review_lab_result(
    lab_result_id: UUID,
    doctor_id: UUID,
    doctor_notes: str
) -> Generator[Effect, Result, Result[dict]]:
    """
    Doctor reviews lab result and adds clinical notes.

    Flow:
    1. Fetch lab result
    2. Verify doctor is authorized (ordering physician or assigned to patient)
    3. Update reviewed flag and notes
    4. Notify patient that results are ready
    """

    # Step 1: Fetch lab result
    lab_result_result = yield DatabaseEffect.Query(
        query="SELECT * FROM lab_results WHERE lab_result_id = $1",
        params=(lab_result_id,)
    )

    match lab_result_result:
        case Ok(rows) if len(rows) > 0:
            lab_result = rows[0]
        case Ok([]):
            return Err("Lab result not found")
        case Err(error):
            return Err(f"Database error: {error}")

    # Step 2: Verify doctor authorization
    if lab_result["doctor_id"] != doctor_id:
        # TODO: Check if doctor is assigned to patient
        return Err("Doctor not authorized to review this lab result")

    # Step 3: Update reviewed flag and notes
    reviewed_at = datetime.now(timezone.utc)

    update_result = yield DatabaseEffect.Execute(
        query="""
            UPDATE lab_results
            SET reviewed_by_doctor = true,
                doctor_notes = $1,
                reviewed_at = $2
            WHERE lab_result_id = $3
        """,
        params=(doctor_notes, reviewed_at, lab_result_id)
    )

    match update_result:
        case Ok(_):
            pass  # Review saved
        case Err(error):
            return Err(f"Failed to save review: {error}")

    # Step 4: Notify patient
    notification_message = (
        f"Your {lab_result['test_type']} results are ready and have been reviewed by your doctor. "
        f"Please log in to view the results and doctor's notes."
    )

    _ = yield SendPatientNotification(
        patient_id=lab_result["patient_id"],
        notification_type="lab_result_ready",
        message=notification_message,
        metadata={
            "lab_result_id": str(lab_result_id),
            "test_type": lab_result["test_type"],
            "critical": lab_result["critical"],
        }
    )

    return Ok({
        "lab_result_id": lab_result_id,
        "reviewed_at": reviewed_at,
    })
```

**Doctor Review Requirements**:
- **Authorization**: Only ordering physician or assigned doctors can review
- **Clinical interpretation**: Doctor provides actionable clinical notes
- **Patient notification**: Automatic notification after review
- **Timestamp**: `reviewed_at` recorded for audit trail

## Patient Viewing

**Endpoint**: `GET /api/lab-results` (as patient)

**Program**: `demo/healthhub/backend/app/programs/lab_result_programs.py`

```python
# file: demo/healthhub/backend/app/programs/lab_result_programs.py
def get_patient_lab_results(patient_id: UUID) -> Generator[Effect, Result, Result[list[dict]]]:
    """
    Get all lab results for patient.

    Returns:
    - Lab results with doctor notes (if reviewed)
    - Critical flag for UI highlighting
    - Ordering physician information
    """

    lab_results_result = yield DatabaseEffect.Query(
        query="""
            SELECT
                lr.lab_result_id,
                lr.test_type,
                lr.result_data,
                lr.reference_ranges,
                lr.critical,
                lr.reviewed_by_doctor,
                lr.doctor_notes,
                lr.created_at,
                lr.reviewed_at,
                d.first_name || ' ' || d.last_name AS doctor_name,
                d.specialization
            FROM lab_results lr
            JOIN doctors d ON lr.doctor_id = d.doctor_id
            WHERE lr.patient_id = $1
            ORDER BY lr.created_at DESC
        """,
        params=(patient_id,)
    )

    match lab_results_result:
        case Ok(rows):
            return Ok(rows)
        case Err(error):
            return Err(f"Failed to fetch lab results: {error}")
```

**API Endpoint with RBAC**:
```python
# file: demo/healthhub/backend/app/api/lab_results.py
from fastapi import APIRouter, Depends, HTTPException
from demo.healthhub.backend.app.api.dependencies import get_auth_state
from demo.healthhub.backend.app.domain.auth import AuthorizationState, PatientAuthorized, DoctorAuthorized, AdminAuthorized, Unauthorized

router = APIRouter(prefix="/api/lab-results")

@router.get("/")
async def get_lab_results(
    auth_state: AuthorizationState = Depends(get_auth_state)
):
    """
    Get lab results (role-based filtering).

    - Patient: Own lab results only (with doctor notes)
    - Doctor/Admin: All lab results (with optional patient_id filter)
    """

    match auth_state:
        case PatientAuthorized(patient_id=pid):
            # Patient can only view own lab results
            program = get_patient_lab_results(pid)
            result = await interpreter.run(program)

            match result:
                case Ok(lab_results):
                    return {"lab_results": lab_results}
                case Err(error):
                    raise HTTPException(500, str(error))

        case DoctorAuthorized():
            # Doctor can view all lab results (with optional patient filter)
            # ... (fetch all with optional patient_id query param) ...
            pass

        case AdminAuthorized():
            # Admin can view all lab results
            # ... (fetch all) ...
            pass

        case Unauthorized(reason=reason):
            raise HTTPException(401, f"Unauthorized: {reason}")
```

**Patient View Features**:
- **Critical highlighting**: Critical results shown with visual indicator
- **Doctor notes**: Clinical interpretation visible to patient
- **Test values**: All test values with reference ranges
- **Historical trends**: View previous results for same test type

## Notification Cascade

**Critical Lab Result Notification Flow**:

```
1. Lab submits critical result
   ↓
2. System detects critical values (detect_critical_values)
   ↓
3. Doctor alert sent (SendDoctorAlert - urgency: high)
   ↓
4. Doctor reviews result (review_lab_result)
   ↓
5. Doctor adds clinical notes
   ↓
6. Patient notification sent (SendPatientNotification)
   ↓
7. Patient views result with doctor notes
```

**Notification Timing**:
- **Doctor alert**: Immediate (sent during lab result submission)
- **Patient notification**: After doctor review (ensures clinical context provided)

**Rationale**: Patients receive notification only after doctor has reviewed and provided clinical interpretation, preventing panic from raw critical values without context.

## E2E Tests

**File**: `demo/healthhub/tests/pytest/e2e/test_lab_results.py`

```python
# file: demo/healthhub/tests/pytest/e2e/test_lab_results.py
import pytest
from demo.healthhub.backend.app.programs.lab_result_programs import (
    submit_lab_result,
    review_lab_result,
    get_patient_lab_results,
)
from effectful import Ok, Err

@pytest.mark.asyncio
async def test_submit_critical_lab_result_triggers_alert(clean_healthhub_state, postgres_interpreter):
    """E2E: Critical lab result triggers immediate doctor alert."""

    program = submit_lab_result(
        patient_id=UUID("30000000-0000-0000-0000-000000000001"),
        doctor_id=UUID("40000000-0000-0000-0000-000000000001"),
        test_type="Lipid Panel",
        result_data={
            "total_cholesterol": 280,  # Critical high
            "ldl": 190,  # Critical high
            "hdl": 35,  # Critical low
            "triglycerides": 250  # High but not critical
        }
    )

    result = await postgres_interpreter.run(program)

    match result:
        case Ok(response):
            assert response["critical"] is True
            assert len(response["critical_values"]) == 3  # Cholesterol, LDL, HDL
            assert any("total_cholesterol" in v for v in response["critical_values"])
            assert any("ldl" in v for v in response["critical_values"])
            assert any("hdl" in v for v in response["critical_values"])
        case Err(error):
            pytest.fail(f"Expected Ok, got Err: {error}")

@pytest.mark.asyncio
async def test_doctor_review_notifies_patient(clean_healthhub_state, postgres_interpreter):
    """E2E: Doctor review triggers patient notification."""

    # Submit lab result
    submit_program = submit_lab_result(
        patient_id=UUID("30000000-0000-0000-0000-000000000001"),
        doctor_id=UUID("40000000-0000-0000-0000-000000000001"),
        test_type="CBC",
        result_data={"hemoglobin": 12.5, "wbc": 7000, "platelets": 250000}
    )

    submit_result = await postgres_interpreter.run(submit_program)

    match submit_result:
        case Ok(response):
            lab_result_id = response["lab_result_id"]
        case Err(error):
            pytest.fail(f"Failed to submit lab result: {error}")

    # Doctor reviews result
    review_program = review_lab_result(
        lab_result_id=lab_result_id,
        doctor_id=UUID("40000000-0000-0000-0000-000000000001"),
        doctor_notes="CBC results within normal range. No concerns."
    )

    review_result = await postgres_interpreter.run(review_program)

    match review_result:
        case Ok(response):
            assert "reviewed_at" in response
            # Notification should have been sent (verify via notification check)
        case Err(error):
            pytest.fail(f"Expected Ok, got Err: {error}")

@pytest.mark.asyncio
async def test_patient_can_view_lab_results_with_doctor_notes(clean_healthhub_state, postgres_interpreter):
    """E2E: Patient views lab results including doctor notes."""

    # Alice has lab results from seed data
    program = get_patient_lab_results(UUID("30000000-0000-0000-0000-000000000001"))
    result = await postgres_interpreter.run(program)

    match result:
        case Ok(lab_results):
            assert len(lab_results) > 0

            # Find reviewed result
            reviewed_result = next(
                (r for r in lab_results if r["reviewed_by_doctor"]),
                None
            )

            if reviewed_result:
                assert reviewed_result["doctor_notes"] is not None
                assert "normal range" in reviewed_result["doctor_notes"].lower()

        case Err(error):
            pytest.fail(f"Expected Ok, got Err: {error}")
```

## Summary

**You have learned**:
- ✅ LabResult domain model (test_type, result_data, critical flag)
- ✅ Critical value detection (automatic flagging based on reference ranges)
- ✅ Doctor alert system (immediate notification for critical results)
- ✅ Doctor review workflow (reviewed_by_doctor flag + clinical notes)
- ✅ Patient notification cascade (after doctor review)
- ✅ Patient viewing (own results with doctor annotations)
- ✅ E2E testing for critical alerts, review, and viewing

**Key Takeaways**:
1. **Automatic Critical Detection**: System flags critical values based on reference ranges
2. **Notification Cascade**: Doctor alerted immediately, patient notified after review
3. **Clinical Context**: Patients receive results only with doctor interpretation
4. **RBAC Enforcement**: Patients see own results, doctors see all results
5. **Audit Trail**: Timestamps track submission and review
6. **Safety First**: Critical alerts prioritize patient safety

## Cross-References

- [Intermediate Journey - Lab Results](../01_journeys/intermediate_journey.md#step-4-view-lab-results-with-critical-alerts)
- [Doctor Guide - Lab Result Review](../02_roles/doctor_guide.md)
- [Patient Guide - Viewing Lab Results](../02_roles/patient_guide.md)
- [Lab Result Workflow](../04_workflows/lab_result_workflow.md)
- [ADTs and Result Types](../../../../../documents/tutorials/adts_and_results.md)
- [Code Quality](../../../../../documents/engineering/code_quality.md)
