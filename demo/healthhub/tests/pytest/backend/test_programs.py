"""Unit tests for effect programs.

Tests program logic using manual generator stepping.
No effects are executed - all results are manually sent into the generator.
"""

from datetime import date, datetime, timezone
from uuid import UUID, uuid4

import pytest

from app.domain.appointment import (
    Appointment,
    Cancelled,
    Completed,
    Confirmed,
    InProgress,
    Requested,
    TransitionInvalid,
    TransitionSuccess,
)
from app.domain.doctor import Doctor
from app.domain.patient import Patient
from app.domain.prescription import MedicationInteractionWarning, NoInteractions, Prescription
from app.effects.healthcare import (
    CheckMedicationInteractions,
    CreateAppointment,
    CreatePrescription,
    GetAppointmentById,
    GetDoctorById,
    GetPatientById,
    TransitionAppointmentStatus,
)
from app.effects.notification import LogAuditEvent, PublishWebSocketNotification
from app.programs.appointment_programs import (
    AppointmentDoctorMissing,
    AppointmentPatientMissing,
    AppointmentScheduled,
    schedule_appointment_program,
    transition_appointment_program,
)
from app.programs.prescription_programs import (
    PrescriptionBlocked,
    PrescriptionCreated,
    PrescriptionDoctorMissing,
    PrescriptionDoctorUnauthorized,
    PrescriptionPatientMissing,
    create_prescription_program,
)


class TestScheduleAppointmentProgram:
    """Test schedule_appointment_program with manual generator stepping."""

    def test_schedule_appointment_success_path(self) -> None:
        """Should yield correct effects in order for successful scheduling."""
        patient_id = uuid4()
        doctor_id = uuid4()
        actor_id = uuid4()
        requested_time = datetime.now(timezone.utc)
        reason = "Annual checkup"

        # Create mock responses
        mock_patient = Patient(
            id=patient_id,
            user_id=uuid4(),
            first_name="John",
            last_name="Doe",
            date_of_birth=date(1985, 5, 15),
            blood_type="O+",
            allergies=[],
            insurance_id="INS-123",
            emergency_contact="Jane: 555-0100",
            phone="555-0123",
            address="123 Main St",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        mock_doctor = Doctor(
            id=doctor_id,
            user_id=uuid4(),
            first_name="Jane",
            last_name="Smith",
            specialization="Cardiology",
            license_number="MD-123",
            can_prescribe=True,
            phone="555-1234",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        mock_appointment = Appointment(
            id=uuid4(),
            patient_id=patient_id,
            doctor_id=doctor_id,
            status=Requested(requested_at=datetime.now(timezone.utc)),
            reason=reason,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        # Initialize generator
        program = schedule_appointment_program(
            patient_id=patient_id,
            doctor_id=doctor_id,
            requested_time=requested_time,
            reason=reason,
            actor_id=actor_id,
        )

        # Step 1: Should yield GetPatientById
        effect1 = next(program)
        assert isinstance(effect1, GetPatientById)
        assert effect1.patient_id == patient_id

        # Step 2: Send patient, should yield GetDoctorById
        effect2 = program.send(mock_patient)
        assert isinstance(effect2, GetDoctorById)
        assert effect2.doctor_id == doctor_id

        # Step 3: Send doctor, should yield CreateAppointment
        effect3 = program.send(mock_doctor)
        assert isinstance(effect3, CreateAppointment)
        assert effect3.patient_id == patient_id
        assert effect3.doctor_id == doctor_id
        assert effect3.reason == reason

        # Step 4: Send appointment, should yield PublishWebSocketNotification
        effect4 = program.send(mock_appointment)
        assert isinstance(effect4, PublishWebSocketNotification)
        assert effect4.channel == f"doctor:{doctor_id}:notifications"
        assert effect4.message["type"] == "appointment_requested"
        assert effect4.recipient_id == doctor_id

        # Step 5: Send notification result, should yield LogAuditEvent
        effect5 = program.send(None)
        assert isinstance(effect5, LogAuditEvent)
        assert effect5.action == "create_appointment"
        assert effect5.resource_type == "appointment"

        # Step 6: Send audit result, should return appointment
        with pytest.raises(StopIteration) as exc_info:
            program.send(None)

        result = exc_info.value.value
        assert isinstance(result, AppointmentScheduled)
        assert result.appointment == mock_appointment

    def test_schedule_appointment_patient_not_found(self) -> None:
        """Should return None when patient not found."""
        patient_id = uuid4()
        doctor_id = uuid4()
        actor_id = uuid4()

        # Initialize generator
        program = schedule_appointment_program(
            patient_id=patient_id,
            doctor_id=doctor_id,
            requested_time=None,
            reason="Checkup",
            actor_id=actor_id,
        )

        # Step 1: Yield GetPatientById
        effect1 = next(program)
        assert isinstance(effect1, GetPatientById)

        # Step 2: Send None (patient not found), should return patient-missing ADT
        with pytest.raises(StopIteration) as exc_info:
            program.send(None)

        result = exc_info.value.value
        assert isinstance(result, AppointmentPatientMissing)
        assert result.patient_id == patient_id

    def test_schedule_appointment_doctor_not_found(self) -> None:
        """Should return None when doctor not found."""
        patient_id = uuid4()
        doctor_id = uuid4()
        actor_id = uuid4()

        mock_patient = Patient(
            id=patient_id,
            user_id=uuid4(),
            first_name="John",
            last_name="Doe",
            date_of_birth=date(1985, 5, 15),
            blood_type="O+",
            allergies=[],
            insurance_id="INS-123",
            emergency_contact="Jane: 555-0100",
            phone="555-0123",
            address="123 Main St",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        # Initialize generator
        program = schedule_appointment_program(
            patient_id=patient_id,
            doctor_id=doctor_id,
            requested_time=None,
            reason="Checkup",
            actor_id=actor_id,
        )

        # Step 1: Yield GetPatientById
        effect1 = next(program)
        assert isinstance(effect1, GetPatientById)

        # Step 2: Send patient, should yield GetDoctorById
        effect2 = program.send(mock_patient)
        assert isinstance(effect2, GetDoctorById)

        # Step 3: Send None (doctor not found), should return doctor-missing ADT
        with pytest.raises(StopIteration) as exc_info:
            program.send(None)

        result = exc_info.value.value
        assert isinstance(result, AppointmentDoctorMissing)
        assert result.doctor_id == doctor_id


class TestTransitionAppointmentProgram:
    """Test transition_appointment_program with manual generator stepping."""

    def test_transition_appointment_success_path(self) -> None:
        """Should yield correct effects for successful transition."""
        appointment_id = uuid4()
        patient_id = uuid4()
        doctor_id = uuid4()
        actor_id = uuid4()

        mock_appointment = Appointment(
            id=appointment_id,
            patient_id=patient_id,
            doctor_id=doctor_id,
            status=Requested(requested_at=datetime.now(timezone.utc)),
            reason="Checkup",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        new_status = Confirmed(
            confirmed_at=datetime.now(timezone.utc),
            scheduled_time=datetime.now(timezone.utc),
        )

        mock_transition_result = TransitionSuccess(new_status=new_status)

        # Initialize generator
        program = transition_appointment_program(
            appointment_id=appointment_id,
            new_status=new_status,
            actor_id=actor_id,
        )

        # Step 1: Should yield GetAppointmentById
        effect1 = next(program)
        assert isinstance(effect1, GetAppointmentById)
        assert effect1.appointment_id == appointment_id

        # Step 2: Send appointment, should yield TransitionAppointmentStatus
        effect2 = program.send(mock_appointment)
        assert isinstance(effect2, TransitionAppointmentStatus)
        assert effect2.appointment_id == appointment_id
        assert effect2.new_status == new_status

        # Step 3: Send success result, should yield patient notification
        effect3 = program.send(mock_transition_result)
        assert isinstance(effect3, PublishWebSocketNotification)
        assert effect3.channel == f"patient:{patient_id}:notifications"
        assert effect3.message["type"] == "appointment_status_changed"

        # Step 4: Send notification result, should yield doctor notification
        effect4 = program.send(None)
        assert isinstance(effect4, PublishWebSocketNotification)
        assert effect4.channel == f"doctor:{doctor_id}:notifications"

        # Step 5: Send notification result, should yield LogAuditEvent
        effect5 = program.send(None)
        assert isinstance(effect5, LogAuditEvent)
        assert effect5.action == "transition_appointment_status"

        # Step 6: Send audit result, should return TransitionSuccess
        with pytest.raises(StopIteration) as exc_info:
            program.send(None)

        result = exc_info.value.value
        assert isinstance(result, TransitionSuccess)
        assert result.new_status == new_status

    def test_transition_appointment_not_found(self) -> None:
        """Should return TransitionInvalid when appointment not found."""
        appointment_id = uuid4()
        actor_id = uuid4()
        new_status = Confirmed(
            confirmed_at=datetime.now(timezone.utc),
            scheduled_time=datetime.now(timezone.utc),
        )

        # Initialize generator
        program = transition_appointment_program(
            appointment_id=appointment_id,
            new_status=new_status,
            actor_id=actor_id,
        )

        # Step 1: Yield GetAppointmentById
        effect1 = next(program)
        assert isinstance(effect1, GetAppointmentById)

        # Step 2: Send None (not found), should return TransitionInvalid
        with pytest.raises(StopIteration) as exc_info:
            program.send(None)

        result = exc_info.value.value
        assert isinstance(result, TransitionInvalid)
        assert "not found" in result.reason

    def test_transition_appointment_invalid_transition(self) -> None:
        """Should not send notifications for invalid transition."""
        appointment_id = uuid4()
        patient_id = uuid4()
        doctor_id = uuid4()
        actor_id = uuid4()

        # Appointment in terminal Completed status
        mock_appointment = Appointment(
            id=appointment_id,
            patient_id=patient_id,
            doctor_id=doctor_id,
            status=Completed(
                completed_at=datetime.now(timezone.utc), notes="Appointment completed"
            ),
            reason="Checkup",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        # Try to transition back to Requested (invalid)
        new_status = Requested(requested_at=datetime.now(timezone.utc))
        mock_transition_result = TransitionInvalid(
            current_status=str(mock_appointment.status),
            attempted_status=str(new_status),
            reason="Invalid transition from Completed to Requested",
        )

        # Initialize generator
        program = transition_appointment_program(
            appointment_id=appointment_id,
            new_status=new_status,
            actor_id=actor_id,
        )

        # Step 1: Yield GetAppointmentById
        effect1 = next(program)
        assert isinstance(effect1, GetAppointmentById)

        # Step 2: Send appointment, should yield TransitionAppointmentStatus
        effect2 = program.send(mock_appointment)
        assert isinstance(effect2, TransitionAppointmentStatus)

        # Step 3: Send failure result, should return immediately (no notifications)
        with pytest.raises(StopIteration) as exc_info:
            program.send(mock_transition_result)

        result = exc_info.value.value
        assert isinstance(result, TransitionInvalid)


class TestCreatePrescriptionProgram:
    """Test create_prescription_program with manual generator stepping."""

    def test_create_prescription_success_no_interactions(self) -> None:
        """Should create prescription when no interactions found."""
        patient_id = uuid4()
        doctor_id = uuid4()
        actor_id = uuid4()

        mock_patient = Patient(
            id=patient_id,
            user_id=uuid4(),
            first_name="John",
            last_name="Doe",
            date_of_birth=date(1985, 5, 15),
            blood_type="O+",
            allergies=[],
            insurance_id="INS-123",
            emergency_contact="Jane: 555-0100",
            phone="555-0123",
            address="123 Main St",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        mock_doctor = Doctor(
            id=doctor_id,
            user_id=uuid4(),
            first_name="Jane",
            last_name="Smith",
            specialization="Cardiology",
            license_number="MD-123",
            can_prescribe=True,
            phone="555-1234",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        mock_interaction_result = NoInteractions(medications_checked=["Metformin", "Lisinopril"])

        mock_prescription = Prescription(
            id=uuid4(),
            patient_id=patient_id,
            doctor_id=doctor_id,
            medication="Lisinopril",
            dosage="10mg",
            frequency="once daily",
            duration_days=30,
            refills_remaining=3,
            notes="Monitor BP",
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc),
        )

        # Initialize generator
        program = create_prescription_program(
            patient_id=patient_id,
            doctor_id=doctor_id,
            medication="Lisinopril",
            dosage="10mg",
            frequency="once daily",
            duration_days=30,
            refills_remaining=3,
            notes="Monitor BP",
            actor_id=actor_id,
            existing_medications=["Metformin"],
        )

        # Step 1: Yield GetPatientById
        effect1 = next(program)
        assert isinstance(effect1, GetPatientById)

        # Step 2: Send patient, should yield GetDoctorById
        effect2 = program.send(mock_patient)
        assert isinstance(effect2, GetDoctorById)

        # Step 3: Send doctor, should yield CheckMedicationInteractions
        effect3 = program.send(mock_doctor)
        assert isinstance(effect3, CheckMedicationInteractions)
        assert "Metformin" in effect3.medications
        assert "Lisinopril" in effect3.medications

        # Step 4: Send no interactions, should yield CreatePrescription
        effect4 = program.send(mock_interaction_result)
        assert isinstance(effect4, CreatePrescription)
        assert effect4.medication == "Lisinopril"

        # Step 5: Send prescription, should yield PublishWebSocketNotification
        effect5 = program.send(mock_prescription)
        assert isinstance(effect5, PublishWebSocketNotification)
        assert effect5.channel == f"patient:{patient_id}:notifications"
        assert effect5.message["type"] == "prescription_created"

        # Step 6: Send notification result, should yield LogAuditEvent
        effect6 = program.send(None)
        assert isinstance(effect6, LogAuditEvent)
        assert effect6.action == "create_prescription"

        # Step 7: Send audit result, should return prescription
        with pytest.raises(StopIteration) as exc_info:
            program.send(None)

        result = exc_info.value.value
        assert isinstance(result, PrescriptionCreated)
        assert result.prescription == mock_prescription

    def test_create_prescription_patient_not_found(self) -> None:
        """Should return error string when patient not found."""
        patient_id = uuid4()
        doctor_id = uuid4()
        actor_id = uuid4()

        # Initialize generator
        program = create_prescription_program(
            patient_id=patient_id,
            doctor_id=doctor_id,
            medication="Lisinopril",
            dosage="10mg",
            frequency="once daily",
            duration_days=30,
            refills_remaining=3,
            notes=None,
            actor_id=actor_id,
            existing_medications=[],
        )

        # Step 1: Yield GetPatientById
        effect1 = next(program)
        assert isinstance(effect1, GetPatientById)

        # Step 2: Send None (not found), should return patient-missing ADT
        with pytest.raises(StopIteration) as exc_info:
            program.send(None)

        result = exc_info.value.value
        assert isinstance(result, PrescriptionPatientMissing)
        assert result.patient_id == patient_id

    def test_create_prescription_doctor_not_found(self) -> None:
        """Should return error string when doctor not found."""
        patient_id = uuid4()
        doctor_id = uuid4()
        actor_id = uuid4()

        mock_patient = Patient(
            id=patient_id,
            user_id=uuid4(),
            first_name="John",
            last_name="Doe",
            date_of_birth=date(1985, 5, 15),
            blood_type="O+",
            allergies=[],
            insurance_id="INS-123",
            emergency_contact="Jane: 555-0100",
            phone="555-0123",
            address="123 Main St",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        # Initialize generator
        program = create_prescription_program(
            patient_id=patient_id,
            doctor_id=doctor_id,
            medication="Lisinopril",
            dosage="10mg",
            frequency="once daily",
            duration_days=30,
            refills_remaining=3,
            notes=None,
            actor_id=actor_id,
            existing_medications=[],
        )

        # Step 1: Yield GetPatientById
        effect1 = next(program)
        assert isinstance(effect1, GetPatientById)

        # Step 2: Send patient, should yield GetDoctorById
        effect2 = program.send(mock_patient)
        assert isinstance(effect2, GetDoctorById)

        # Step 3: Send None (doctor not found), should return doctor-missing ADT
        with pytest.raises(StopIteration) as exc_info:
            program.send(None)

        result = exc_info.value.value
        assert isinstance(result, PrescriptionDoctorMissing)
        assert result.doctor_id == doctor_id

    def test_create_prescription_doctor_cannot_prescribe(self) -> None:
        """Should return error string when doctor cannot prescribe."""
        patient_id = uuid4()
        doctor_id = uuid4()
        actor_id = uuid4()

        mock_patient = Patient(
            id=patient_id,
            user_id=uuid4(),
            first_name="John",
            last_name="Doe",
            date_of_birth=date(1985, 5, 15),
            blood_type="O+",
            allergies=[],
            insurance_id="INS-123",
            emergency_contact="Jane: 555-0100",
            phone="555-0123",
            address="123 Main St",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        # Doctor without prescription authority
        mock_doctor = Doctor(
            id=doctor_id,
            user_id=uuid4(),
            first_name="Jane",
            last_name="Smith",
            specialization="Physical Therapy",
            license_number="PT-123",
            can_prescribe=False,
            phone="555-5678",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        # Initialize generator
        program = create_prescription_program(
            patient_id=patient_id,
            doctor_id=doctor_id,
            medication="Lisinopril",
            dosage="10mg",
            frequency="once daily",
            duration_days=30,
            refills_remaining=3,
            notes=None,
            actor_id=actor_id,
            existing_medications=[],
        )

        # Step 1: Yield GetPatientById
        effect1 = next(program)
        assert isinstance(effect1, GetPatientById)

        # Step 2: Send patient, should yield GetDoctorById
        effect2 = program.send(mock_patient)
        assert isinstance(effect2, GetDoctorById)

        # Step 3: Send doctor without authority, should return unauthorized ADT
        with pytest.raises(StopIteration) as exc_info:
            program.send(mock_doctor)

        result = exc_info.value.value
        assert isinstance(result, PrescriptionDoctorUnauthorized)
        assert result.doctor_id == doctor_id

    def test_create_prescription_severe_interaction_blocks(self) -> None:
        """Should block prescription and return warning for severe interaction."""
        patient_id = uuid4()
        doctor_id = uuid4()
        actor_id = uuid4()

        mock_patient = Patient(
            id=patient_id,
            user_id=uuid4(),
            first_name="John",
            last_name="Doe",
            date_of_birth=date(1985, 5, 15),
            blood_type="O+",
            allergies=[],
            insurance_id="INS-123",
            emergency_contact="Jane: 555-0100",
            phone="555-0123",
            address="123 Main St",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        mock_doctor = Doctor(
            id=doctor_id,
            user_id=uuid4(),
            first_name="Jane",
            last_name="Smith",
            specialization="Cardiology",
            license_number="MD-123",
            can_prescribe=True,
            phone="555-1234",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        mock_interaction_warning = MedicationInteractionWarning(
            medications=["Warfarin", "Aspirin"],
            severity="severe",
            description="Increased bleeding risk",
        )

        # Initialize generator
        program = create_prescription_program(
            patient_id=patient_id,
            doctor_id=doctor_id,
            medication="Aspirin",
            dosage="81mg",
            frequency="once daily",
            duration_days=30,
            refills_remaining=0,
            notes=None,
            actor_id=actor_id,
            existing_medications=["Warfarin"],
        )

        # Step 1: Yield GetPatientById
        effect1 = next(program)
        assert isinstance(effect1, GetPatientById)

        # Step 2: Send patient, should yield GetDoctorById
        effect2 = program.send(mock_patient)
        assert isinstance(effect2, GetDoctorById)

        # Step 3: Send doctor, should yield CheckMedicationInteractions
        effect3 = program.send(mock_doctor)
        assert isinstance(effect3, CheckMedicationInteractions)

        # Step 4: Send severe warning, should yield LogAuditEvent (blocked)
        effect4 = program.send(mock_interaction_warning)
        assert isinstance(effect4, LogAuditEvent)
        assert effect4.action == "prescription_blocked_severe_interaction"

        # Step 5: Send audit result, should return blocked ADT carrying warning
        with pytest.raises(StopIteration) as exc_info:
            program.send(None)

        result = exc_info.value.value
        assert isinstance(result, PrescriptionBlocked)
        assert result.warning == mock_interaction_warning

    def test_create_prescription_moderate_interaction_allowed(self) -> None:
        """Should create prescription but include warning for moderate interaction."""
        patient_id = uuid4()
        doctor_id = uuid4()
        actor_id = uuid4()

        mock_patient = Patient(
            id=patient_id,
            user_id=uuid4(),
            first_name="John",
            last_name="Doe",
            date_of_birth=date(1985, 5, 15),
            blood_type="O+",
            allergies=[],
            insurance_id="INS-123",
            emergency_contact="Jane: 555-0100",
            phone="555-0123",
            address="123 Main St",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        mock_doctor = Doctor(
            id=doctor_id,
            user_id=uuid4(),
            first_name="Jane",
            last_name="Smith",
            specialization="Cardiology",
            license_number="MD-123",
            can_prescribe=True,
            phone="555-1234",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        mock_interaction_warning = MedicationInteractionWarning(
            medications=["Lisinopril", "Potassium"],
            severity="moderate",
            description="Hyperkalemia risk",
        )

        mock_prescription = Prescription(
            id=uuid4(),
            patient_id=patient_id,
            doctor_id=doctor_id,
            medication="Lisinopril",
            dosage="10mg",
            frequency="once daily",
            duration_days=30,
            refills_remaining=3,
            notes="Monitor potassium",
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc),
        )

        # Initialize generator
        program = create_prescription_program(
            patient_id=patient_id,
            doctor_id=doctor_id,
            medication="Lisinopril",
            dosage="10mg",
            frequency="once daily",
            duration_days=30,
            refills_remaining=3,
            notes="Monitor potassium",
            actor_id=actor_id,
            existing_medications=["Potassium"],
        )

        # Step 1: Yield GetPatientById
        effect1 = next(program)
        assert isinstance(effect1, GetPatientById)

        # Step 2: Send patient, should yield GetDoctorById
        effect2 = program.send(mock_patient)
        assert isinstance(effect2, GetDoctorById)

        # Step 3: Send doctor, should yield CheckMedicationInteractions
        effect3 = program.send(mock_doctor)
        assert isinstance(effect3, CheckMedicationInteractions)

        # Step 4: Send moderate warning, should yield CreatePrescription (allowed)
        effect4 = program.send(mock_interaction_warning)
        assert isinstance(effect4, CreatePrescription)

        # Step 5: Send prescription, should yield PublishWebSocketNotification with warning
        effect5 = program.send(mock_prescription)
        assert isinstance(effect5, PublishWebSocketNotification)
        # Check new nested dict format for interaction_warning
        assert "interaction_warning" in effect5.message
        warning = effect5.message["interaction_warning"]
        assert isinstance(warning, dict)
        assert warning["severity"] == "moderate"
        assert "description" in warning

        # Step 6: Send notification result, should yield LogAuditEvent
        effect6 = program.send(None)
        assert isinstance(effect6, LogAuditEvent)

        # Step 7: Send audit result, should return prescription
        with pytest.raises(StopIteration) as exc_info:
            program.send(None)

        result = exc_info.value.value
        assert isinstance(result, PrescriptionCreated)
        assert result.prescription == mock_prescription
