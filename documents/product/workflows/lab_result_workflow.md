# Lab Result Workflow

**Status**: Authoritative source
**Supersedes**: none
**Referenced by**: demo/healthhub/documents/tutorials/README.md

> **Purpose**: Single Source of Truth for the HealthHub lab result workflow from submission through doctor review and notifications.

## SSoT Link Map

| Need                 | Link                                                                        |
| -------------------- | --------------------------------------------------------------------------- |
| Lab results feature  | [Lab Results Feature](../../engineering/features/lab_results.md)            |
| Intermediate journey | [Intermediate Journey](../../tutorials/01_journeys/intermediate_journey.md) |
| Doctor guide         | [Doctor Guide](../roles/doctor_guide.md)                                    |
| Patient guide        | [Patient Guide](../roles/patient_guide.md)                                  |
| HIPAA compliance     | [HIPAA Compliance](../../domain/hipaa_compliance.md)                        |

## Prerequisites

- Docker workflow running; commands executed via `docker compose -f docker/docker-compose.yml`.
- Completed [Intermediate Journey](../../tutorials/01_journeys/intermediate_journey.md).
- Access to HealthHub at `http://localhost:8851`.

## Learning Objectives

- Execute complete lab result workflow from order to patient viewing
- Understand critical value detection and automatic alert system
- Observe doctor review process with clinical notes
- Experience notification cascade (doctor alerted → reviews → patient notified)
- Verify e2e test coverage for lab result workflows

## Overview

**Workflow**: Order Lab → Submit Results → Critical Alert → Doctor Review → Patient Notification → Patient Views

**Duration**: ~1 hour (following the complete workflow)

**Features Involved**:

1. **Lab Results**: Test ordering, result submission, critical value detection
1. **Notifications**: Critical value alerts, review notifications
1. **Doctor Review**: Clinical interpretation, patient communication

**Demo Users**:

- Patient: david.patient@example.com (password: password123)
- Doctor: dr.brown@healthhub.com (password: password123)

**Learning Outcome**: Complete understanding of lab result lifecycle, critical value handling, and doctor-patient communication.

## Workflow Diagram

```text
# lab result workflow steps
Step 1: Doctor Orders Lab Work
   ↓ (creates LabResult record with pending=true)
Step 2: Lab Submits Results
   ↓ (updates LabResult with test_data, critical flag detection)
Step 3: Critical Value Detection (Automatic)
   ↓ (system detects critical values, sets is_critical=true)
Step 4: Doctor Notification (If Critical)
   ↓ (immediate alert sent to ordering doctor)
Step 5: Doctor Reviews Results
   ↓ (adds clinical notes, marks as reviewed)
Step 6: Patient Notification
   ↓ (patient notified results available)
Step 7: Patient Views Results
   ↓ (patient sees test data and doctor notes)
```

## Step 1: Doctor Orders Lab Work

**Goal**: Order comprehensive metabolic panel during patient appointment.

**Actor**: Dr. Brown (logged in as doctor)

**Actions**:

1. **Navigate to Patients**: Click "Patients" in sidebar

1. **Select Patient**: Click "David Daniels"

1. **Click "Order Lab Work"**

1. **Fill out Lab Order Form**:

   - **Test Name**: Comprehensive Metabolic Panel
   - **Test Type**: Blood
   - **Ordered Date**: 2025-12-09
   - **Priority**: Routine
   - **Clinical Indication**: Annual physical exam

1. **Submit Order**: Click "Order Lab Work"

1. **Backend Processing**:

   ```python
   # Effect program: order_lab_work
   def order_lab_work(patient_id, doctor_id, test_name, test_type, clinical_indication):
       # Validate patient exists
       patient_result = yield DatabaseEffect.Query(
           query="SELECT * FROM patients WHERE patient_id = $1",
           params=(patient_id,)
       )

       # Create lab result record (pending)
       lab_result_id = uuid4()
       ordered_date = datetime.now(timezone.utc)

       insert_result = yield DatabaseEffect.Execute(
           query="INSERT INTO lab_results (lab_result_id, patient_id, doctor_id, test_name, test_type, ordered_date, is_critical, pending, created_at, updated_at) VALUES ($1, $2, $3, $4, $5, $6, false, true, $7, $8) RETURNING lab_result_id",
           params=(lab_result_id, patient_id, doctor_id, test_name, test_type, ordered_date, ordered_date, ordered_date)
       )

       # Log order (HIPAA audit)
       _ = yield AuditEffect.Log(
           action="order_lab_work",
           resource_type="lab_result",
           resource_id=lab_result_id,
           actor_id=doctor_id,
           details={"test_name": test_name, "clinical_indication": clinical_indication}
       )

       return Ok({"lab_result_id": lab_result_id, "status": "pending"})
   ```

1. **Expected Result**:

   - Lab result record created with pending=true
   - Order appears in doctor's "Pending Lab Orders"
   - Order sent to lab (external system integration)

**Data Created**:

- `lab_results` table: lab_result_id, patient_id, doctor_id, test_name (Comprehensive Metabolic Panel), test_type (Blood), ordered_date, pending=true, is_critical=false

**Test Coverage**: `test_lab_results.py::test_order_lab_work`

## Step 2: Lab Submits Results

**Goal**: External lab submits test results to HealthHub.

**Actor**: Lab System (automated submission via API)

**Actions**:

1. **Lab Processes Sample**: Lab performs comprehensive metabolic panel

1. **Lab Submits Results via API**: POST `/api/lab-results/{lab_result_id}/submit`

1. **Payload**:

   ```json
   // example payload body
   {
     "test_data": {
       "glucose": 250,        // mg/dL (HIGH - critical)
       "sodium": 142,         // mEq/L (normal: 136-145)
       "potassium": 4.1,      // mEq/L (normal: 3.5-5.0)
       "chloride": 101,       // mEq/L (normal: 98-107)
       "co2": 24,             // mEq/L (normal: 23-30)
       "bun": 18,             // mg/dL (normal: 7-20)
       "creatinine": 1.1,     // mg/dL (normal: 0.6-1.2)
       "calcium": 9.5,        // mg/dL (normal: 8.5-10.5)
       "total_protein": 7.2,  // g/dL (normal: 6.0-8.3)
       "albumin": 4.5,        // g/dL (normal: 3.5-5.5)
       "total_bilirubin": 0.8 // mg/dL (normal: 0.3-1.2)
     },
     "reference_ranges": {
       "glucose": {"low": 70, "high": 100, "critical_low": 40, "critical_high": 200},
       "sodium": {"low": 136, "high": 145, "critical_low": 120, "critical_high": 160},
       "potassium": {"low": 3.5, "high": 5.0, "critical_low": 2.5, "critical_high": 6.0}
       // ... other ranges
     },
     "completed_date": "2025-12-09T15:30:00Z"
   }
   ```

1. **Backend Processing**:

   ```python
   # Effect program: submit_lab_results
   def submit_lab_results(lab_result_id, test_data, reference_ranges, completed_date):
       # Fetch pending lab result
       lab_result = yield DatabaseEffect.Query(
           query="SELECT * FROM lab_results WHERE lab_result_id = $1 AND pending = true",
           params=(lab_result_id,)
       )

       # Detect critical values
       is_critical, critical_values = detect_critical_values(test_data, reference_ranges)

       # Update lab result with test data
       update_result = yield DatabaseEffect.Execute(
           query="UPDATE lab_results SET test_data = $1, is_critical = $2, pending = false, completed_date = $3, updated_at = $4 WHERE lab_result_id = $5",
           params=(json.dumps(test_data), is_critical, completed_date, datetime.now(timezone.utc), lab_result_id)
       )

       # If critical, alert doctor immediately
       if is_critical:
           alert_result = yield SendDoctorAlert(
               doctor_id=lab_result["doctor_id"],
               alert_type="critical_lab_result",
               message=f"CRITICAL LAB RESULT: {lab_result['test_name']} for patient {lab_result['patient_id']}. Critical values: {', '.join([f'{v['name']}: {v['value']}' for v in critical_values])}",
               urgency="critical"
           )

       return Ok({"lab_result_id": lab_result_id, "is_critical": is_critical, "critical_values": critical_values})

   def detect_critical_values(test_data, reference_ranges):
       """Detect critical values requiring immediate attention."""
       critical_values = []

       for test_name, value in test_data.items():
           if test_name not in reference_ranges:
               continue

           ref_range = reference_ranges[test_name]

           if value < ref_range["critical_low"]:
               critical_values.append({
                   "name": test_name,
                   "value": value,
                   "threshold": ref_range["critical_low"],
                   "direction": "low"
               })
           elif value > ref_range["critical_high"]:
               critical_values.append({
                   "name": test_name,
                   "value": value,
                   "threshold": ref_range["critical_high"],
                   "direction": "high"
               })

       is_critical = len(critical_values) > 0
       return is_critical, critical_values
   ```

1. **Expected Result**:

   - Lab result updated: pending=false, is_critical=true
   - Critical value detected: glucose=250 (critical_high threshold: 200)
   - Dr. Brown receives immediate critical alert

**Data Updated**:

- `lab_results` table: test_data (JSON), is_critical=true, pending=false, completed_date

**Test Coverage**: `test_lab_results.py::test_submit_lab_results_with_critical_values`

## Step 3: Critical Value Detection (Automatic)

**Goal**: System automatically identifies values requiring immediate attention.

**Actor**: System (automatic during Step 2)

**Critical Value Thresholds**:

| Test       | Normal Range   | Critical Low | Critical High |
| ---------- | -------------- | ------------ | ------------- |
| Glucose    | 70-100 mg/dL   | \<40 mg/dL   | >200 mg/dL    |
| Sodium     | 136-145 mEq/L  | \<120 mEq/L  | >160 mEq/L    |
| Potassium  | 3.5-5.0 mEq/L  | \<2.5 mEq/L  | >6.0 mEq/L    |
| Creatinine | 0.6-1.2 mg/dL  | N/A          | >3.0 mg/dL    |
| Hemoglobin | 13.5-17.5 g/dL | \<7.0 g/dL   | >20.0 g/dL    |

**Detection Logic**:

```python
# Critical if value exceeds critical thresholds
glucose = 250 mg/dL
critical_high_threshold = 200 mg/dL

if glucose > critical_high_threshold:
    is_critical = True
    critical_values.append({"name": "glucose", "value": 250, "threshold": 200, "direction": "high"})
```

**Result for David's Test**:

- **Glucose**: 250 mg/dL > 200 mg/dL (critical_high) → ✗ CRITICAL
- **All other values**: Within normal or non-critical ranges → ✓ Normal
- **Overall**: is_critical=true (one or more critical values)

**Test Coverage**: `test_lab_results.py::test_critical_value_detection`

## Step 4: Doctor Notification (If Critical)

**Goal**: Alert ordering doctor immediately for critical results.

**Actor**: System (automatic during Step 2)

**Notification Details**:

- **Type**: Critical Alert (highest priority)
- **Recipient**: Dr. Brown (ordering doctor)
- **Message**: "CRITICAL LAB RESULT: Comprehensive Metabolic Panel for patient David Daniels. Critical values: glucose: 250 mg/dL"
- **Urgency**: Critical (red badge, push notification, email)

**Backend Processing**:

```python
# Effect: SendDoctorAlert
_ = yield SendDoctorAlert(
    doctor_id=dr_brown_id,
    alert_type="critical_lab_result",
    message="CRITICAL LAB RESULT: Comprehensive Metabolic Panel for patient David Daniels. Critical values: glucose: 250 mg/dL",
    urgency="critical"
)
```

**Expected Result**:

- Dr. Brown sees red alert badge in navigation
- Alert appears at top of dashboard: "🚨 CRITICAL LAB RESULT"
- Click alert navigates directly to lab result review page

**Test Coverage**: `test_lab_results.py::test_critical_value_doctor_notification`

## Step 5: Doctor Reviews Results

**Goal**: Doctor interprets lab results and documents clinical assessment.

**Actor**: Dr. Brown (logged in as doctor)

**Actions**:

1. **Click Critical Alert**: Navigate to lab result from alert

1. **Review Test Data**:

   ```
   Comprehensive Metabolic Panel - David Daniels
   Completed: 2025-12-09 15:30:00
   Status: ⚠️ CRITICAL VALUES DETECTED

   Test Results:
   ✗ Glucose: 250 mg/dL (Critical High: >200)
   ✓ Sodium: 142 mEq/L (Normal: 136-145)
   ✓ Potassium: 4.1 mEq/L (Normal: 3.5-5.0)
   ✓ Chloride: 101 mEq/L (Normal: 98-107)
   ✓ CO2: 24 mEq/L (Normal: 23-30)
   ✓ BUN: 18 mg/dL (Normal: 7-20)
   ✓ Creatinine: 1.1 mg/dL (Normal: 0.6-1.2)
   ✓ Calcium: 9.5 mg/dL (Normal: 8.5-10.5)
   ✓ Total Protein: 7.2 g/dL (Normal: 6.0-8.3)
   ✓ Albumin: 4.5 g/dL (Normal: 3.5-5.5)
   ✓ Total Bilirubin: 0.8 mg/dL (Normal: 0.3-1.2)
   ```

1. **Click "Add Clinical Notes"**

1. **Enter Clinical Assessment**:

   ```
   CRITICAL LAB RESULT REVIEW

   Findings:
   - Fasting glucose: 250 mg/dL (significantly elevated, >2.5x upper limit of normal)
   - All other metabolic panel values within normal limits
   - No evidence of renal dysfunction (creatinine, BUN normal)
   - No electrolyte abnormalities

   Clinical Interpretation:
   Patient presents with hyperglycemia consistent with uncontrolled diabetes mellitus.
   Given fasting glucose >200 mg/dL, this meets diagnostic criteria for diabetes.

   Recommended Actions:
   1. Immediate appointment scheduled for diabetes counseling
   2. HbA1c ordered to assess long-term glucose control
   3. Started on Metformin 500mg twice daily
   4. Dietary consultation recommended
   5. Home glucose monitoring kit prescribed
   6. Follow-up in 2 weeks to reassess glucose control

   Patient Notification: Results discussed with patient via phone call. Patient
   aware of diagnosis and treatment plan. Expressed understanding and commitment
   to lifestyle modifications. No acute symptoms requiring emergency intervention.

   Dr. Emily Brown, MD
   2025-12-09 16:00:00
   ```

1. **Click "Mark as Reviewed"**

1. **Backend Processing**:

   ```python
   # Effect program: review_lab_result
   def review_lab_result(lab_result_id, doctor_id, clinical_notes):
       # Fetch lab result
       lab_result = yield DatabaseEffect.Query(
           query="SELECT * FROM lab_results WHERE lab_result_id = $1",
           params=(lab_result_id,)
       )

       # Verify doctor is authorized (ordering doctor or same specialty)
       if lab_result["doctor_id"] != doctor_id:
           return Err("Only ordering doctor can review lab results")

       # Update with clinical notes and mark as reviewed
       update_result = yield DatabaseEffect.Execute(
           query="UPDATE lab_results SET clinical_notes = $1, reviewed = true, reviewed_at = $2, reviewed_by_doctor_id = $3, updated_at = $4 WHERE lab_result_id = $5",
           params=(clinical_notes, datetime.now(timezone.utc), doctor_id, datetime.now(timezone.utc), lab_result_id)
       )

       # Log review (HIPAA audit)
       _ = yield AuditEffect.Log(
           action="review_lab_result",
           resource_type="lab_result",
           resource_id=lab_result_id,
           actor_id=doctor_id,
           details={"is_critical": lab_result["is_critical"]}
       )

       # Notify patient that results are available
       _ = yield SendPatientNotification(
           patient_id=lab_result["patient_id"],
           notification_type="lab_result_reviewed",
           message=f"Your {lab_result['test_name']} results have been reviewed by Dr. Brown and are now available in your portal.",
       )

       return Ok({"lab_result_id": lab_result_id, "reviewed": True})
   ```

1. **Expected Result**:

   - Lab result marked as reviewed=true
   - Clinical notes saved
   - Patient notified results are available
   - Critical alert cleared from Dr. Brown's dashboard

**Data Updated**:

- `lab_results` table: clinical_notes (text), reviewed=true, reviewed_at, reviewed_by_doctor_id

**Test Coverage**: `test_lab_results.py::test_doctor_review_lab_result`

## Step 6: Patient Notification

**Goal**: Notify patient that lab results are reviewed and available.

**Actor**: System (automatic during Step 5)

**Notification Details**:

- **Type**: Lab Result Available
- **Recipient**: David Daniels (patient)
- **Message**: "Your Comprehensive Metabolic Panel results have been reviewed by Dr. Brown and are now available in your portal."
- **Urgency**: Medium (blue badge, in-app notification)

**Backend Processing**:

```python
# Effect: SendPatientNotification
_ = yield SendPatientNotification(
    patient_id=david_patient_id,
    notification_type="lab_result_reviewed",
    message="Your Comprehensive Metabolic Panel results have been reviewed by Dr. Brown and are now available in your portal.",
)
```

**Expected Result**:

- David sees notification badge in navigation
- Notification appears in "Notifications" section
- Click notification navigates to lab results page

**Test Coverage**: `test_lab_results.py::test_patient_notification_on_review`

## Step 7: Patient Views Results

**Goal**: Patient reviews lab results and doctor's clinical assessment.

**Actor**: David Daniels (logged in as patient)

**Actions**:

1. **Click Notification**: Navigate to lab results from notification

1. **View Lab Result Details**:

   ```
   Comprehensive Metabolic Panel
   Ordered: 2025-12-09
   Completed: 2025-12-09 15:30:00
   Ordered by: Dr. Emily Brown
   Status: ✓ Reviewed

   Test Results:
   ⚠️ Glucose: 250 mg/dL (High - above normal range)
   ✓ Sodium: 142 mEq/L (Normal)
   ✓ Potassium: 4.1 mEq/L (Normal)
   ✓ Chloride: 101 mEq/L (Normal)
   ✓ CO2: 24 mEq/L (Normal)
   ✓ BUN: 18 mg/dL (Normal)
   ✓ Creatinine: 1.1 mg/dL (Normal)
   ✓ Calcium: 9.5 mg/dL (Normal)
   ✓ Total Protein: 7.2 g/dL (Normal)
   ✓ Albumin: 4.5 g/dL (Normal)
   ✓ Total Bilirubin: 0.8 mg/dL (Normal)

   Clinical Notes from Dr. Brown:
   [Clinical assessment displayed here - see Step 5]

   Next Steps:
   - Follow-up appointment scheduled: 2025-12-23
   - Prescriptions: Metformin 500mg (see Prescriptions section)
   - Dietary consultation scheduled
   ```

1. **Expected Result**:

   - David sees all test results with normal/abnormal indicators
   - Clinical notes explain significance of elevated glucose
   - Treatment plan clearly outlined
   - David understands diagnosis and next steps

**RBAC Enforcement**:

```python
# Patient can only view own lab results
def get_lab_result(auth_state: AuthorizationState, lab_result_id: UUID):
    match auth_state:
        case PatientAuthorized(patient_id=patient_id):
            # Verify lab result belongs to this patient
            lab_result = yield DatabaseEffect.Query(...)
            if lab_result["patient_id"] != patient_id:
                return Err("Access denied")
            return Ok(lab_result)
        case DoctorAuthorized(doctor_id=doctor_id):
            # Doctors can view all lab results
            return Ok(lab_result)
        case Unauthorized():
            return Err("Not authenticated")
```

**Test Coverage**: `test_lab_results.py::test_patient_view_lab_result`

## Integration Points

**Feature-to-Feature Data Flow**:

1. **Lab Results → Appointments**:

   - Lab work often ordered during appointment
   - Appointment notes reference pending lab orders
   - Follow-up appointments scheduled based on results

1. **Lab Results → Prescriptions**:

   - Critical lab results trigger medication orders (e.g., Metformin for elevated glucose)
   - Prescription creation references lab result findings
   - Medication adjustments based on lab monitoring

1. **Lab Results → Notifications**:

   - Critical values trigger immediate doctor alerts
   - Doctor review triggers patient notifications
   - Escalation cascade: Lab → Doctor → Patient

1. **Lab Results → Audit Logs**:

   - All PHI access logged (doctor ordering, doctor reviewing, patient viewing)
   - Critical value alerts logged for compliance
   - HIPAA-compliant audit trail

## E2E Test Coverage

**File**: `demo/healthhub/tests/pytest/e2e/test_lab_results.py`

**Test Functions**:

1. **test_complete_lab_result_workflow**: Tests entire workflow (order → submit → review → view)
1. **test_critical_value_detection**: Tests detection logic with various thresholds
1. **test_critical_value_doctor_notification**: Tests immediate alert on critical values
1. **test_doctor_review_lab_result**: Tests review process and notification cascade
1. **test_patient_view_lab_result**: Tests patient access and RBAC
1. **test_non_critical_lab_result_workflow**: Tests workflow without critical values

**Assertions**:

- Lab result created with pending=true
- Critical values correctly detected (glucose > 200)
- Doctor receives immediate critical alert
- Doctor can add clinical notes and mark as reviewed
- Patient notified after doctor review
- Patient can view results and clinical notes
- RBAC enforced (patients can only view own results)

**Run Tests**:

```bash
# snippet
docker compose -f docker/docker-compose.yml exec healthhub poetry run pytest tests/pytest/e2e/test_lab_results.py -v
```

## Critical Value Scenarios

### Scenario 1: Critical Glucose (This Tutorial)

```text
# critical glucose scenario
Test Data: glucose = 250 mg/dL
Threshold: critical_high = 200 mg/dL
Result: ✗ CRITICAL
Action: Immediate doctor alert, diabetes diagnosis, Metformin prescribed
```

### Scenario 2: Critical Potassium (Hyperkalemia)

```text
# critical potassium scenario
Test Data: potassium = 6.5 mEq/L
Threshold: critical_high = 6.0 mEq/L
Result: ✗ CRITICAL
Action: Immediate doctor alert, emergency treatment, cardiac monitoring
```

### Scenario 3: Critical Hemoglobin (Severe Anemia)

```text
# critical hemoglobin scenario
Test Data: hemoglobin = 6.0 g/dL
Threshold: critical_low = 7.0 g/dL
Result: ✗ CRITICAL
Action: Immediate doctor alert, transfusion consideration, urgent hematology consult
```

### Scenario 4: Normal Results

```text
# normal lab result scenario
Test Data: All values within normal ranges
Threshold: No critical values
Result: ✓ Normal
Action: Routine doctor review, patient notified when reviewed, no urgent intervention
```

## Summary

**You have successfully**:

- ✅ Ordered lab work during patient care
- ✅ Submitted lab results with critical value detection
- ✅ Triggered immediate doctor notification for critical glucose
- ✅ Reviewed results and documented clinical assessment
- ✅ Notified patient of available results
- ✅ Viewed results from patient perspective

**Key Takeaways**:

1. **Critical Value Detection**: Automatic detection triggers immediate alerts
1. **Notification Cascade**: Lab → Doctor (if critical) → Doctor Review → Patient
1. **Clinical Interpretation**: Doctor adds context and treatment plan to raw data
1. **RBAC Throughout**: Patients can only view own results, doctors can view all
1. **HIPAA Compliance**: All PHI access logged in audit trail
1. **Integration**: Lab results drive prescriptions, appointments, and follow-up care

**Workflow Duration**: ~1 hour from order to patient viewing

## Cross-References

- [Intermediate Journey](../../tutorials/01_journeys/intermediate_journey.md)
- [Lab Results Feature](../../engineering/features/lab_results.md)
- [Doctor Guide](../../product/roles/doctor_guide.md)
- [Patient Guide](../../product/roles/patient_guide.md)
- [Appointment Lifecycle](appointment_lifecycle.md)
- [Prescription Workflow](prescription_workflow.md)
