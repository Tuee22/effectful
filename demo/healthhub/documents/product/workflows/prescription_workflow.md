# Prescription Workflow

**Status**: Authoritative source
**Supersedes**: none **📖 Base Standard**: [prescription_workflow.md](../../../../../documents/product/workflows/prescription_workflow.md)
**Referenced by**: demo/healthhub/documents/tutorials/README.md

> **Purpose**: HealthHub overlay deltas for Prescription Workflow. **📖 Base Standard**: [prescription_workflow.md](../../../../../documents/product/workflows/prescription_workflow.md)

## Prerequisites

- Docker workflow running; commands executed via `docker compose -f docker/docker-compose.yml`.
- Completed [Intermediate Journey](../../tutorials/01_journeys/intermediate_journey.md).
- Access to HealthHub at `http://localhost:8851`.
- Understanding of medication safety and interaction checking.

## Learning Objectives

- Execute complete prescription creation workflow with interaction checking
- Understand medication allergy checking against patient allergies
- Understand drug interaction checking against current prescriptions
- Observe doctor-patient data flow (doctor creates, patient views)
- Experience notification system integration
- Verify prescription safety features (warnings, blocking)

## Overview

**Workflow**: Diagnosis → Patient Lookup → Medication Interaction Check → Create Prescription → Patient Views

**Duration**: ~1 hour

**Features Involved**:

1. **Appointments**: Context for prescription (doctor appointment with patient)
1. **Patient Management**: Doctor searches/views patient history
1. **Prescriptions**: Creation with interaction checking
1. **Notifications**: Prescription ready notification

**Demo Users**:

- Patient: alice.patient@example.com (allergies: Penicillin, Shellfish)
- Doctor: dr.smith@healthhub.com (can_prescribe=true)

**Learning Outcome**: Deep understanding of prescription safety features and doctor-patient workflow.

## Workflow Diagram

```text
Step 1: Doctor Completes Appointment (Context)
   ↓ (Diagnosis: Hypertension)
Step 2: Doctor Looks Up Patient
   ↓ (View allergies, current medications)
Step 3: Doctor Initiates Prescription
   ↓ (Select medication, dosage, frequency)
Step 4: System Checks Allergy Interactions
   ↓ (Check against Penicillin, Shellfish)
Step 5: System Checks Drug Interactions
   ↓ (Check against current prescriptions)
Step 6: Doctor Reviews Warnings
   ↓ (Critical → Blocked, High → Warning, Medium/Low → Proceed)
Step 7: Prescription Created
   ↓ (Patient notified)
Step 8: Patient Views Prescription
   ↓ (Medication, dosage, doctor instructions)
```

## Medication Interaction Checking

**Two-Phase Checking**:

1. **Allergy Checking**:

   - Check medication against patient's known allergies
   - Block if critical allergy interaction detected
   - Example: Amoxicillin vs Penicillin allergy → BLOCKED

1. **Drug Interaction Checking**:

   - Check medication against patient's current active prescriptions
   - Warn if drug interaction detected
   - Example: Warfarin + Aspirin → HIGH WARNING (bleeding risk)

**Interaction Severity Levels**:

- **Critical**: Prescription blocked, must select alternative
- **High**: Serious warning, proceed with caution
- **Medium**: Moderate warning, monitor patient
- **Low**: Minor warning, informational only

## Step 1: Doctor Completes Appointment (Context)

**Goal**: Establish clinical context for prescription.

**Actor**: Dr. Sarah Smith (Cardiology)

**Login**:

- Email: `dr.smith@healthhub.com`
- Password: `password123`

**Scenario**: Alice's annual cardiac checkup completed, diagnosis of mild hypertension.

**Appointment Notes** (already completed in previous step):

```text
Diagnosis: Mild hypertension (blood pressure 135/85)

Treatment Plan:
- Prescribe Lisinopril 10mg once daily
- Dietary modifications (low sodium)
- Regular exercise
- Follow-up in 3 months
```

**Expected Result**:

- Appointment status: Completed
- Clinical indication for prescription documented
- Doctor ready to prescribe medication

## Step 2: Doctor Looks Up Patient

**Goal**: Review patient allergies and current medications before prescribing.

**Actor**: Dr. Sarah Smith

**Actions**:

1. **Navigate to Patients**: Click "Patients" in sidebar

1. **Search for Alice**: Enter "Alice" or "alice.patient@example.com"

1. **Click Alice Anderson**: View patient profile

1. **Review Patient Information**:

   - **Demographics**: Alice Anderson, DOB: 1985-03-15 (39 years old)
   - **Blood Type**: O+
   - **Allergies**: **Penicillin, Shellfish** ← CRITICAL for prescribing
   - **Emergency Contact**: John Anderson, (555) 234-5678

1. **View Medical History**:

   - **Active Prescriptions**: Currently none (new prescription will be first)
   - **Past Appointments**: Previous cardiac checkups
   - **Lab Results**: Lipid panel results normal

1. **Expected Result**:

   - Doctor aware of Alice's allergies (Penicillin, Shellfish)
   - Doctor aware Alice has no current prescriptions (no drug interactions possible)
   - Doctor ready to prescribe with allergy context

**Key Insight**: Reviewing patient allergies BEFORE prescribing is critical for medication safety.

## Step 3: Doctor Initiates Prescription

**Goal**: Start prescription creation process.

**Actor**: Dr. Sarah Smith

**Actions**:

1. **Click "Prescribe Medication"** (from patient profile page)

1. **Fill out Prescription Form**:

   - **Medication**: Lisinopril ← ACE inhibitor for hypertension
   - **Dosage**: 10mg
   - **Frequency**: Once daily
   - **Duration**: 90 days (3 months)
   - **Refills**: 2
   - **Instructions**: "Take in the morning with water. Monitor blood pressure daily."

1. **Click "Check Interactions"** (automatic or manual trigger)

1. **Expected Result**:

   - Form filled out completely
   - System ready to check interactions
   - Doctor waiting for interaction check results

## Step 4: System Checks Allergy Interactions

**Goal**: Automatically check medication against patient allergies.

**Backend Processing**:

```python
# snippet
def check_allergy_interactions(patient_id, medication):
    # Fetch patient allergies
    allergies_result = yield DatabaseEffect.Query(
        query="SELECT allergies FROM patients WHERE patient_id = $1",
        params=(patient_id,)
    )

    match allergies_result:
        case Ok(rows) if len(rows) > 0:
            allergies = rows[0]["allergies"]  # ["Penicillin", "Shellfish"]
        case _:
            return Err("Patient not found")

    # Check medication against allergies
    warnings = []

    for allergy in allergies:
        if _medication_contains_allergen(medication, allergy):
            warnings.append(
                InteractionWarning(
                    severity="critical",
                    description=f"{medication} may cause allergic reaction in patients with {allergy} allergy",
                    recommendation="Do not prescribe - consider alternative medication"
                )
            )

    return Ok(warnings)

def _medication_contains_allergen(medication, allergen):
    # Simplified interaction checking
    if allergen.lower() == "penicillin":
        penicillin_drugs = ["amoxicillin", "ampicillin", "penicillin", "augmentin"]
        return any(drug in medication.lower() for drug in penicillin_drugs)

    # Direct match
    return allergen.lower() in medication.lower()
```

**Scenario 1: Safe Medication (Lisinopril)**

**Check**: Lisinopril vs Penicillin allergy
**Result**: No interaction (Lisinopril is not penicillin-based)

**Check**: Lisinopril vs Shellfish allergy
**Result**: No interaction (Lisinopril is not derived from shellfish)

**Outcome**: No allergy warnings, proceed to drug interaction check

______________________________________________________________________

**Scenario 2: Unsafe Medication (Amoxicillin)**

**Check**: Amoxicillin vs Penicillin allergy
**Result**: CRITICAL INTERACTION (Amoxicillin is penicillin-based)

**Warning**:

```text
Critical Allergy Interaction:

Amoxicillin may cause allergic reaction in patients with Penicillin allergy.

Recommendation: Do not prescribe - consider alternative medication (e.g., Azithromycin, Doxycycline)
```

**Outcome**: Prescription blocked, doctor must select alternative

## Step 5: System Checks Drug Interactions

**Goal**: Check medication against patient's current active prescriptions.

**Backend Processing**:

```python
# snippet
def check_drug_interactions(patient_id, new_medication):
    # Fetch active prescriptions
    prescriptions_result = yield DatabaseEffect.Query(
        query="""
            SELECT medication, dosage
            FROM prescriptions
            WHERE patient_id = $1 AND expires_at > NOW()
        """,
        params=(patient_id,)
    )

    match prescriptions_result:
        case Ok(rows):
            current_medications = [row["medication"] for row in rows]
        case Err(error):
            return Err(f"Database error: {error}")

    # Check interactions
    warnings = []

    for current_med in current_medications:
        interaction = _check_drug_pair_interaction(current_med, new_medication)
        if interaction:
            warnings.append(interaction)

    return Ok(warnings)

def _check_drug_pair_interaction(med1, med2):
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
    }

    pair1 = (med1.lower(), med2.lower())
    pair2 = (med2.lower(), med1.lower())

    return known_interactions.get(pair1) or known_interactions.get(pair2)
```

**Scenario: Alice's First Prescription**

**Check**: Lisinopril vs (no current prescriptions)
**Result**: No drug interactions (Alice has no current prescriptions)

**Outcome**: No drug interaction warnings, safe to proceed

## Step 6: Doctor Reviews Warnings

**Goal**: Doctor reviews interaction warnings and decides whether to proceed.

**Scenario 1: No Warnings (Lisinopril for Alice)**

**Interaction Check Results**:

```text
✓ Allergy Check: No interactions detected
✓ Drug Interaction Check: No interactions detected

Safe to prescribe.
```

**Doctor Action**: Click "Create Prescription"

**Outcome**: Prescription created successfully

______________________________________________________________________

**Scenario 2: Critical Warning (Amoxicillin for Alice)**

**Interaction Check Results**:

```text
✗ Critical Allergy Interaction:

Amoxicillin may cause allergic reaction in patients with Penicillin allergy.

Recommendation: Do not prescribe - consider alternative medication.

[Select Alternative] [Cancel]
```

**Doctor Action**: Click "Select Alternative", choose Azithromycin instead

**Outcome**: Prescription blocked for Amoxicillin, doctor selects alternative medication

______________________________________________________________________

**Scenario 3: High Warning (Aspirin for patient on Warfarin)**

**Interaction Check Results**:

```text
⚠ High Drug Interaction Warning:

Increased bleeding risk when combining Warfarin and Aspirin.

Recommendation: Monitor INR closely, consider alternative antiplatelet.

[Proceed Anyway] [Select Alternative] [Cancel]
```

**Doctor Action**: Reviews warning, decides clinical benefit outweighs risk, clicks "Proceed Anyway"

**Outcome**: Prescription created with warning documented

## Step 7: Prescription Created

**Goal**: Prescription successfully created and stored in database.

**Backend Processing**:

```python
# snippet
def create_prescription_with_interaction_check(patient_id, doctor_id, medication, dosage, frequency, duration_days, refills, notes):
    # Check allergies
    allergy_warnings = yield from check_allergy_interactions(patient_id, medication)
    if any(w.severity == "critical" for w in allergy_warnings):
        return Err(f"Critical allergy interaction: {allergy_warnings[0].description}")

    # Check drug interactions
    drug_warnings = yield from check_drug_interactions(patient_id, medication)
    if any(w.severity == "critical" for w in drug_warnings):
        return Err(f"Critical drug interaction: {drug_warnings[0].description}")

    # Create prescription
    prescription_id = uuid4()
    created_at = datetime.now(timezone.utc)
    expires_at = created_at + timedelta(days=duration_days)

    insert_result = yield DatabaseEffect.Execute(
        query="INSERT INTO prescriptions (...) VALUES (...)",
        params=(prescription_id, patient_id, doctor_id, medication, dosage, frequency, duration_days, refills, notes, created_at, expires_at)
    )

    # Notify patient
    _ = yield SendPatientNotification(
        patient_id=patient_id,
        notification_type="prescription_ready",
        message=f"New prescription for {medication} is ready. Pick up at your pharmacy.",
        metadata={"prescription_id": str(prescription_id), "medication": medication}
    )

    return Ok({"prescription_id": prescription_id, "warnings": allergy_warnings + drug_warnings})
```

**Expected Result**:

- **Prescription Created**: prescription_id generated
- **Database Record**: Stored in `prescriptions` table
- **Notification Sent**: Alice receives "prescription_ready" notification
- **Warnings Logged**: All warnings (if any) logged for audit trail

**Prescription Details**:

```text
Prescription ID: 60000000-0000-0000-0000-000000000001
Patient: Alice Anderson
Doctor: Dr. Sarah Smith (Cardiology)
Medication: Lisinopril
Dosage: 10mg
Frequency: Once daily
Duration: 90 days
Refills: 2
Instructions: "Take in the morning with water. Monitor blood pressure daily."
Created: 2025-12-10 15:00:00
Expires: 2026-03-10 15:00:00
```

**Notification Sent**:

- **Recipient**: Alice Anderson
- **Type**: "prescription_ready"
- **Message**: "New prescription for Lisinopril is ready. Pick up at your pharmacy."

## Step 8: Patient Views Prescription

**Goal**: Alice views her new prescription.

**Actor**: Alice Anderson (patient)

**Login**:

- Email: `alice.patient@example.com`
- Password: `password123`

**Actions**:

1. **Navigate to Prescriptions**: Click "Prescriptions" in sidebar

1. **View Prescription List**: See newly created prescription

1. **Click Prescription**: View details

   ```
   Medication: Lisinopril
   Dosage: 10mg
   Frequency: Once daily
   Duration: 90 days
   Refills Remaining: 2

   Doctor Instructions:
   "Take in the morning with water. Monitor blood pressure daily."

   Prescribing Doctor: Dr. Sarah Smith (Cardiology)
   Created: 2025-12-10
   Expires: 2026-03-10

   [Request Refill] (available when refills remain and not expired)
   ```

1. **Expected Result**:

   - Alice sees complete prescription details
   - Doctor's instructions clearly visible
   - Refill count and expiration date displayed
   - Option to request refill (when applicable)

## Interaction Checking Examples

### Example 1: Safe Prescription (No Interactions)

**Patient**: Bob Baker (allergies: Latex)
**Current Prescriptions**: None
**New Medication**: Metformin 500mg (for diabetes)

**Allergy Check**: Metformin vs Latex → No interaction
**Drug Interaction Check**: Metformin vs (none) → No interaction

**Result**: ✓ Safe to prescribe

______________________________________________________________________

### Example 2: Critical Allergy Interaction (Blocked)

**Patient**: Alice Anderson (allergies: Penicillin, Shellfish)
**Current Prescriptions**: None
**New Medication**: Amoxicillin 500mg

**Allergy Check**: Amoxicillin vs Penicillin → ✗ CRITICAL INTERACTION
**Result**: Prescription blocked

**Alternative**: Azithromycin 250mg (not penicillin-based)

______________________________________________________________________

### Example 3: High Drug Interaction (Warning)

**Patient**: Carol Carter (allergies: None)
**Current Prescriptions**: Warfarin 5mg (anticoagulant)
**New Medication**: Aspirin 81mg (antiplatelet)

**Allergy Check**: Aspirin vs (none) → No interaction
**Drug Interaction Check**: Aspirin vs Warfarin → ⚠ HIGH WARNING (bleeding risk)

**Result**: Warning displayed, doctor decides to proceed with careful monitoring

______________________________________________________________________

### Example 4: Medium Drug Interaction (Monitor)

**Patient**: David Davis (allergies: Aspirin, Bee stings)
**Current Prescriptions**: Lisinopril 10mg (ACE inhibitor)
**New Medication**: Spironolactone 25mg (diuretic)

**Allergy Check**: Spironolactone vs Aspirin → No interaction
**Drug Interaction Check**: Spironolactone vs Lisinopril → ⚠ MEDIUM WARNING (potassium levels)

**Result**: Warning displayed, prescription created with monitoring recommendation

## RBAC Enforcement

**Doctor with can_prescribe=true**:

```python
# snippet
@router.post("/api/prescriptions")
async def create_prescription(
    prescription_data: dict,
    auth_state: AuthorizationState = Depends(get_auth_state)
):
    match auth_state:
        case DoctorAuthorized(can_prescribe=True):
            # Authorized - proceed with prescription creation
            program = create_prescription_with_interaction_check(...)
            result = await interpreter.run(program)
            # ...
        case DoctorAuthorized(can_prescribe=False):
            raise HTTPException(403, "Doctor not authorized to prescribe medications")
        case PatientAuthorized() | AdminAuthorized():
            raise HTTPException(403, "Only doctors can create prescriptions")
```

**Enforcement**:

- Only doctors with `can_prescribe=true` can create prescriptions
- Flag checked during API endpoint authorization
- Flag stored in JWT token for efficiency

## E2E Test Coverage

**File**: `demo/healthhub/tests/pytest/e2e/test_prescriptions.py`

**Test Functions**:

1. `test_create_prescription_no_interactions` - Safe prescription (Lisinopril for Bob)
1. `test_create_prescription_blocked_by_allergy` - Blocked prescription (Amoxicillin for Alice)
1. `test_create_prescription_drug_interaction_warning` - Warning prescription (Aspirin for patient on Warfarin)
1. `test_patient_view_prescription` - Patient viewing own prescription
1. `test_doctor_without_can_prescribe_blocked` - RBAC enforcement

**Run Tests**:

```bash
# snippet
docker compose -f docker/docker-compose.yml exec healthhub poetry run pytest tests/pytest/e2e/test_prescriptions.py -v
```

## Summary

**You have successfully**:

- ✅ Reviewed patient allergies before prescribing
- ✅ Initiated prescription creation
- ✅ Executed allergy interaction checking (blocked critical interactions)
- ✅ Executed drug interaction checking (warned about high-risk interactions)
- ✅ Created prescription with safety checks
- ✅ Notified patient of prescription ready
- ✅ Viewed prescription as patient with complete instructions
- ✅ Understood RBAC enforcement (can_prescribe flag)

**Key Takeaways**:

1. **Two-Phase Checking**: Allergy check → Drug interaction check
1. **Severity Levels**: Critical (blocked) → High (warning) → Medium (monitor) → Low (informational)
1. **Patient Safety First**: Critical interactions blocked automatically
1. **Doctor Discretion**: High/medium warnings allow doctor to proceed with caution
1. **Full Transparency**: Patient sees complete prescription details and instructions
1. **RBAC Enforcement**: Only doctors with can_prescribe=true can prescribe
1. **Notification System**: Patient notified immediately when prescription ready

**Workflow Duration**: ~1 hour from patient lookup to prescription viewing

## Cross-References

- [Intermediate Journey - Prescription Creation](../../tutorials/01_journeys/intermediate_journey.md#step-3-create-prescription-with-interaction-checking)
- [Prescriptions Feature](../../engineering/features/prescriptions.md)
- [Patient Guide](../../product/roles/patient_guide.md)
- [Doctor Guide](../../product/roles/doctor_guide.md)
- [Code Quality](../../../../../documents/engineering/code_quality.md)
