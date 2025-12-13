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
from app.domain.lookup_result import (
    AppointmentFound,
    AppointmentMissing,
    DoctorFound,
    DoctorMissingById,
    PatientFound,
    PatientMissingById,
)
from app.domain.patient import Patient
from effectful.domain.optional_value import from_optional_value, to_optional_value
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
from app.effects.observability import IncrementCounter, MetricRecorded, ObserveHistogram
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
            blood_type=to_optional_value("O+"),
            allergies=(),
            insurance_id=to_optional_value("INS-123"),
            emergency_contact="Jane: 555-0100",
            phone=to_optional_value("555-0123"),
            address=to_optional_value("123 Main St"),
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
            phone=to_optional_value("555-1234"),
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
            requested_time=to_optional_value(requested_time),
            reason=reason,
            actor_id=actor_id,
        )

        # Step 1: Should yield GetPatientById
        effect1 = next(program)
        assert isinstance(effect1, GetPatientById)
        assert effect1.patient_id == patient_id

        # Step 2: Send patient, should yield GetDoctorById
        effect2 = program.send(PatientFound(patient=mock_patient))
        assert isinstance(effect2, GetDoctorById)
        assert effect2.doctor_id == doctor_id

        # Step 3: Send doctor, should yield CreateAppointment
        effect3 = program.send(DoctorFound(doctor=mock_doctor))
        assert isinstance(effect3, CreateAppointment)
        assert effect3.patient_id == patient_id
        assert effect3.doctor_id == doctor_id
        assert effect3.reason == reason

        # Step 4: Send appointment, should yield IncrementCounter
        effect4 = program.send(mock_appointment)
        assert isinstance(effect4, IncrementCounter)
        assert effect4.metric_name == "healthhub_appointments_created_total"
        assert effect4.labels["doctor_specialization"] == "Cardiology"

        # Step 5: Send counter result, should yield PublishWebSocketNotification
        effect5 = program.send(
            MetricRecorded(
                metric_name=effect4.metric_name,
                metric_type="counter",
                labels=effect4.labels,
                value=1.0,
            )
        )
        assert isinstance(effect5, PublishWebSocketNotification)
        assert effect5.channel == f"doctor:{doctor_id}:notifications"
        assert effect5.message["type"] == "appointment_requested"
        assert from_optional_value(effect5.recipient_id) == doctor_id

        # Step 6: Send notification result, should yield LogAuditEvent
        effect6 = program.send(None)
        assert isinstance(effect6, LogAuditEvent)
        assert effect6.action == "create_appointment"
        assert effect6.resource_type == "appointment"

        # Step 7: Send audit result, should return appointment
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
            requested_time=to_optional_value(None, reason="not_requested"),
            reason="Checkup",
            actor_id=actor_id,
        )

        # Step 1: Yield GetPatientById
        effect1 = next(program)
        assert isinstance(effect1, GetPatientById)

        # Step 2: Send missing patient ADT, should return patient-missing ADT
        with pytest.raises(StopIteration) as exc_info:
            program.send(PatientMissingById(patient_id=patient_id))

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
            blood_type=to_optional_value("O+"),
            allergies=(),
            insurance_id=to_optional_value("INS-123"),
            emergency_contact="Jane: 555-0100",
            phone=to_optional_value("555-0123"),
            address=to_optional_value("123 Main St"),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        # Initialize generator
        program = schedule_appointment_program(
            patient_id=patient_id,
            doctor_id=doctor_id,
            requested_time=to_optional_value(None, reason="not_requested"),
            reason="Checkup",
            actor_id=actor_id,
        )

        # Step 1: Yield GetPatientById
        effect1 = next(program)
        assert isinstance(effect1, GetPatientById)

        # Step 2: Send patient, should yield GetDoctorById
        effect2 = program.send(PatientFound(patient=mock_patient))
        assert isinstance(effect2, GetDoctorById)

        # Step 3: Send None (doctor not found), should return doctor-missing ADT
        with pytest.raises(StopIteration) as exc_info:
            program.send(DoctorMissingById(doctor_id=doctor_id))

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
        transition_time = datetime.now(timezone.utc)
        transition_latency_seconds = (transition_time - mock_appointment.created_at).total_seconds()

        mock_transition_result = TransitionSuccess(new_status=new_status)

        # Initialize generator
        program = transition_appointment_program(
            appointment_id=appointment_id,
            new_status=new_status,
            actor_id=actor_id,
            transition_time=transition_time,
        )

        # Step 1: Should yield GetAppointmentById
        effect1 = next(program)
        assert isinstance(effect1, GetAppointmentById)
        assert effect1.appointment_id == appointment_id

        # Step 2: Send appointment, should yield TransitionAppointmentStatus
        effect2 = program.send(AppointmentFound(appointment=mock_appointment))
        assert isinstance(effect2, TransitionAppointmentStatus)
        assert effect2.appointment_id == appointment_id
        assert effect2.new_status == new_status

        # Step 3: Send success result, should yield observability histogram
        effect3 = program.send(mock_transition_result)
        assert isinstance(effect3, ObserveHistogram)
        assert effect3.metric_name == "healthhub_appointment_transition_latency_seconds"

        # Step 4: Send histogram result, should yield patient notification
        effect4 = program.send(
            MetricRecorded(
                metric_name=effect3.metric_name,
                metric_type="histogram",
                labels=effect3.labels,
                value=transition_latency_seconds,
            )
        )
        assert isinstance(effect4, PublishWebSocketNotification)
        assert effect4.channel == f"patient:{patient_id}:notifications"
        assert effect4.message["type"] == "appointment_status_changed"

        # Step 5: Send notification result, should yield doctor notification
        effect5 = program.send(None)
        assert isinstance(effect5, PublishWebSocketNotification)
        assert effect5.channel == f"doctor:{doctor_id}:notifications"

        # Step 6: Send notification result, should yield LogAuditEvent
        effect6 = program.send(None)
        assert isinstance(effect6, LogAuditEvent)
        assert effect6.action == "transition_appointment_status"

        # Step 7: Send audit result, should return TransitionSuccess
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
        transition_time = datetime.now(timezone.utc)

        # Initialize generator
        program = transition_appointment_program(
            appointment_id=appointment_id,
            new_status=new_status,
            actor_id=actor_id,
            transition_time=transition_time,
        )

        # Step 1: Yield GetAppointmentById
        effect1 = next(program)
        assert isinstance(effect1, GetAppointmentById)

        # Step 2: Send missing appointment ADT, should return TransitionInvalid
        with pytest.raises(StopIteration) as exc_info:
            program.send(AppointmentMissing(appointment_id=appointment_id))

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
                completed_at=datetime.now(timezone.utc),
                notes="Appointment completed",
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
        transition_time = datetime.now(timezone.utc)

        # Initialize generator
        program = transition_appointment_program(
            appointment_id=appointment_id,
            new_status=new_status,
            actor_id=actor_id,
            transition_time=transition_time,
        )

        # Step 1: Yield GetAppointmentById
        effect1 = next(program)
        assert isinstance(effect1, GetAppointmentById)

        # Step 2: Send appointment, should yield TransitionAppointmentStatus
        effect2 = program.send(AppointmentFound(appointment=mock_appointment))
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
            blood_type=to_optional_value("O+"),
            allergies=(),
            insurance_id=to_optional_value("INS-123"),
            emergency_contact="Jane: 555-0100",
            phone=to_optional_value("555-0123"),
            address=to_optional_value("123 Main St"),
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
            phone=to_optional_value("555-1234"),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        mock_interaction_result = NoInteractions(medications_checked=("Metformin", "Lisinopril"))

        mock_prescription = Prescription(
            id=uuid4(),
            patient_id=patient_id,
            doctor_id=doctor_id,
            medication="Lisinopril",
            dosage="10mg",
            frequency="once daily",
            duration_days=30,
            refills_remaining=3,
            notes=to_optional_value("Monitor BP"),
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
            notes=to_optional_value("Monitor BP"),
            actor_id=actor_id,
            existing_medications=["Metformin"],
        )

        # Step 1: Yield GetPatientById
        effect1 = next(program)
        assert isinstance(effect1, GetPatientById)

        # Step 2: Send patient, should yield GetDoctorById
        effect2 = program.send(PatientFound(patient=mock_patient))
        assert isinstance(effect2, GetDoctorById)

        # Step 3: Send doctor, should yield CheckMedicationInteractions
        effect3 = program.send(DoctorFound(doctor=mock_doctor))
        assert isinstance(effect3, CheckMedicationInteractions)
        assert "Metformin" in effect3.medications
        assert "Lisinopril" in effect3.medications

        # Step 4: Send no interactions, should yield CreatePrescription
        effect4 = program.send(mock_interaction_result)
        assert isinstance(effect4, CreatePrescription)
        assert effect4.medication == "Lisinopril"

        # Step 5: Send prescription, should yield IncrementCounter
        effect5 = program.send(mock_prescription)
        assert isinstance(effect5, IncrementCounter)
        assert effect5.metric_name == "healthhub_prescriptions_created_total"
        assert effect5.labels["doctor_specialization"] == "Cardiology"
        assert effect5.labels["severity"] == "none"
        assert effect5.labels["doctor_specialization"] == "Cardiology"
        assert effect5.labels["severity"] == "none"

        # Step 6: Send counter result, should yield PublishWebSocketNotification
        effect6 = program.send(
            MetricRecorded(
                metric_name=effect5.metric_name,
                metric_type="counter",
                labels=effect5.labels,
                value=1.0,
            )
        )
        assert isinstance(effect6, PublishWebSocketNotification)
        assert effect6.channel == f"patient:{patient_id}:notifications"
        assert effect6.message["type"] == "prescription_created"

        # Step 7: Send notification result, should yield LogAuditEvent
        effect7 = program.send(None)
        assert isinstance(effect7, LogAuditEvent)
        assert effect7.action == "create_prescription"

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
            notes=to_optional_value(None, reason="not_provided"),
            actor_id=actor_id,
            existing_medications=[],
        )

        # Step 1: Yield GetPatientById
        effect1 = next(program)
        assert isinstance(effect1, GetPatientById)

        # Step 2: Send missing patient ADT, should return patient-missing ADT
        with pytest.raises(StopIteration) as exc_info:
            program.send(PatientMissingById(patient_id=patient_id))

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
            blood_type=to_optional_value("O+"),
            allergies=(),
            insurance_id=to_optional_value("INS-123"),
            emergency_contact="Jane: 555-0100",
            phone=to_optional_value("555-0123"),
            address=to_optional_value("123 Main St"),
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
            notes=to_optional_value(None, reason="not_provided"),
            actor_id=actor_id,
            existing_medications=[],
        )

        # Step 1: Yield GetPatientById
        effect1 = next(program)
        assert isinstance(effect1, GetPatientById)

        # Step 2: Send patient, should yield GetDoctorById
        effect2 = program.send(PatientFound(patient=mock_patient))
        assert isinstance(effect2, GetDoctorById)

        # Step 3: Send None (doctor not found), should return doctor-missing ADT
        with pytest.raises(StopIteration) as exc_info:
            program.send(DoctorMissingById(doctor_id=doctor_id))

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
            blood_type=to_optional_value("O+"),
            allergies=(),
            insurance_id=to_optional_value("INS-123"),
            emergency_contact="Jane: 555-0100",
            phone=to_optional_value("555-0123"),
            address=to_optional_value("123 Main St"),
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
            phone=to_optional_value("555-5678"),
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
            notes=to_optional_value(None, reason="not_provided"),
            actor_id=actor_id,
            existing_medications=[],
        )

        # Step 1: Yield GetPatientById
        effect1 = next(program)
        assert isinstance(effect1, GetPatientById)

        # Step 2: Send patient, should yield GetDoctorById
        effect2 = program.send(PatientFound(patient=mock_patient))
        assert isinstance(effect2, GetDoctorById)

        # Step 3: Send doctor without authority, should return unauthorized ADT
        with pytest.raises(StopIteration) as exc_info:
            program.send(DoctorFound(doctor=mock_doctor))

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
            blood_type=to_optional_value("O+"),
            allergies=(),
            insurance_id=to_optional_value("INS-123"),
            emergency_contact="Jane: 555-0100",
            phone=to_optional_value("555-0123"),
            address=to_optional_value("123 Main St"),
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
            phone=to_optional_value("555-1234"),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        mock_interaction_warning = MedicationInteractionWarning(
            medications=("Warfarin", "Aspirin"),
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
            notes=to_optional_value(None, reason="not_provided"),
            actor_id=actor_id,
            existing_medications=["Warfarin"],
        )

        # Step 1: Yield GetPatientById
        effect1 = next(program)
        assert isinstance(effect1, GetPatientById)

        # Step 2: Send patient, should yield GetDoctorById
        effect2 = program.send(PatientFound(patient=mock_patient))
        assert isinstance(effect2, GetDoctorById)

        # Step 3: Send doctor, should yield CheckMedicationInteractions
        effect3 = program.send(DoctorFound(doctor=mock_doctor))
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
            blood_type=to_optional_value("O+"),
            allergies=(),
            insurance_id=to_optional_value("INS-123"),
            emergency_contact="Jane: 555-0100",
            phone=to_optional_value("555-0123"),
            address=to_optional_value("123 Main St"),
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
            phone=to_optional_value("555-1234"),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        mock_interaction_warning = MedicationInteractionWarning(
            medications=("Lisinopril", "Potassium"),
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
            notes=to_optional_value("Monitor potassium"),
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
            notes=to_optional_value("Monitor potassium"),
            actor_id=actor_id,
            existing_medications=["Potassium"],
        )

        # Step 1: Yield GetPatientById
        effect1 = next(program)
        assert isinstance(effect1, GetPatientById)

        # Step 2: Send patient, should yield GetDoctorById
        effect2 = program.send(PatientFound(patient=mock_patient))
        assert isinstance(effect2, GetDoctorById)

        # Step 3: Send doctor, should yield CheckMedicationInteractions
        effect3 = program.send(DoctorFound(doctor=mock_doctor))
        assert isinstance(effect3, CheckMedicationInteractions)

        # Step 4: Send moderate warning, should yield CreatePrescription (allowed)
        effect4 = program.send(mock_interaction_warning)
        assert isinstance(effect4, CreatePrescription)

        # Step 5: Send prescription, should yield IncrementCounter
        effect5 = program.send(mock_prescription)
        assert isinstance(effect5, IncrementCounter)
        assert effect5.metric_name == "healthhub_prescriptions_created_total"

        # Step 6: Send counter result, should yield PublishWebSocketNotification with warning
        effect6 = program.send(None)
        assert isinstance(effect6, PublishWebSocketNotification)
        # Check new nested dict format for interaction_warning
        assert "interaction_warning" in effect6.message
        warning = effect6.message["interaction_warning"]
        assert isinstance(warning, dict)
        assert warning["severity"] == "moderate"
        assert "description" in warning

        # Step 7: Send notification result, should yield LogAuditEvent
        effect7 = program.send(None)
        assert isinstance(effect7, LogAuditEvent)

        # Step 8: Send audit result, should return prescription
        with pytest.raises(StopIteration) as exc_info:
            program.send(None)

        result = exc_info.value.value
        assert isinstance(result, PrescriptionCreated)
        assert result.prescription == mock_prescription
