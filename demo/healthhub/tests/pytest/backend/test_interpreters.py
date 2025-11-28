"""Unit tests for effect interpreters.

Tests interpreter logic using pytest-mock with spec= parameter for type safety.
No real I/O - all database and Redis operations are mocked.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from pytest_mock import MockerFixture

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
from app.domain.invoice import Invoice, LineItem
from app.domain.lab_result import LabResult
from app.domain.patient import Patient
from app.domain.prescription import (
    MedicationInteractionWarning,
    NoInteractions,
    Prescription,
)
from app.effects.healthcare import (
    AddInvoiceLineItem,
    CheckMedicationInteractions,
    CreateAppointment,
    CreateInvoice,
    CreateLabResult,
    CreatePrescription,
    GetAppointmentById,
    GetDoctorById,
    GetLabResultById,
    GetPatientById,
    TransitionAppointmentStatus,
    UpdateInvoiceStatus,
)
from app.effects.notification import (
    AuditEventLogged,
    LogAuditEvent,
    NotificationPublished,
    NotificationValue,
    PublishFailed,
    PublishWebSocketNotification,
)
from app.interpreters.healthcare_interpreter import HealthcareInterpreter
from app.interpreters.notification_interpreter import NotificationInterpreter


class TestHealthcareInterpreterPatientOperations:
    """Test patient-related operations."""

    @pytest.mark.asyncio
    async def test_get_patient_by_id_found(self, mocker: MockerFixture) -> None:
        """GetPatientById should return Patient when found."""
        patient_id = uuid4()
        expected_patient = Patient(
            id=patient_id,
            user_id=uuid4(),
            first_name="John",
            last_name="Doe",
            date_of_birth=date(1985, 5, 15),
            blood_type="O+",
            allergies=[],
            insurance_id="INS-12345",
            emergency_contact="Jane Doe: 555-0100",
            phone="555-0123",
            address="123 Main St",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        # Mock database pool
        mock_pool = mocker.AsyncMock()
        mock_repo = mocker.AsyncMock()
        mock_repo.get_by_id.return_value = expected_patient

        interpreter = HealthcareInterpreter(mock_pool)
        interpreter.patient_repo = mock_repo

        # Execute
        effect = GetPatientById(patient_id=patient_id)
        result = await interpreter.handle(effect)

        # Assert
        assert result == expected_patient
        mock_repo.get_by_id.assert_called_once_with(patient_id)

    @pytest.mark.asyncio
    async def test_get_patient_by_id_not_found(self, mocker: MockerFixture) -> None:
        """GetPatientById should return None when not found."""
        patient_id = uuid4()

        # Mock database pool
        mock_pool = mocker.AsyncMock()
        mock_repo = mocker.AsyncMock()
        mock_repo.get_by_id.return_value = None

        interpreter = HealthcareInterpreter(mock_pool)
        interpreter.patient_repo = mock_repo

        # Execute
        effect = GetPatientById(patient_id=patient_id)
        result = await interpreter.handle(effect)

        # Assert
        assert result is None
        mock_repo.get_by_id.assert_called_once_with(patient_id)


class TestHealthcareInterpreterDoctorOperations:
    """Test doctor-related operations."""

    @pytest.mark.asyncio
    async def test_get_doctor_by_id_found(self, mocker: MockerFixture) -> None:
        """GetDoctorById should return Doctor when found."""
        doctor_id = uuid4()
        expected_doctor = Doctor(
            id=doctor_id,
            user_id=uuid4(),
            first_name="Jane",
            last_name="Smith",
            specialization="Cardiology",
            license_number="MD-12345",
            can_prescribe=True,
            phone="555-1234",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        # Mock database pool
        mock_pool = mocker.AsyncMock()
        mock_repo = mocker.AsyncMock()
        mock_repo.get_by_id.return_value = expected_doctor

        interpreter = HealthcareInterpreter(mock_pool)
        interpreter.doctor_repo = mock_repo

        # Execute
        effect = GetDoctorById(doctor_id=doctor_id)
        result = await interpreter.handle(effect)

        # Assert
        assert result == expected_doctor
        mock_repo.get_by_id.assert_called_once_with(doctor_id)

    @pytest.mark.asyncio
    async def test_get_doctor_by_id_not_found(self, mocker: MockerFixture) -> None:
        """GetDoctorById should return None when not found."""
        doctor_id = uuid4()

        # Mock database pool
        mock_pool = mocker.AsyncMock()
        mock_repo = mocker.AsyncMock()
        mock_repo.get_by_id.return_value = None

        interpreter = HealthcareInterpreter(mock_pool)
        interpreter.doctor_repo = mock_repo

        # Execute
        effect = GetDoctorById(doctor_id=doctor_id)
        result = await interpreter.handle(effect)

        # Assert
        assert result is None
        mock_repo.get_by_id.assert_called_once_with(doctor_id)


class TestHealthcareInterpreterAppointmentOperations:
    """Test appointment-related operations."""

    @pytest.mark.asyncio
    async def test_create_appointment_success(self, mocker: MockerFixture) -> None:
        """CreateAppointment should create appointment in Requested status."""
        patient_id = uuid4()
        doctor_id = uuid4()
        requested_time = datetime.now(timezone.utc)
        reason = "Annual checkup"

        # Mock database pool with fetchrow
        mock_pool = mocker.AsyncMock()
        mock_row = {
            "id": uuid4(),
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "status": "requested",
            "requested_time": requested_time,
            "reason": reason,
            "notes": None,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        mock_pool.fetchrow.return_value = mock_row

        interpreter = HealthcareInterpreter(mock_pool)

        # Execute
        effect = CreateAppointment(
            patient_id=patient_id,
            doctor_id=doctor_id,
            requested_time=requested_time,
            reason=reason,
        )
        result = await interpreter.handle(effect)

        # Assert
        assert isinstance(result, Appointment)
        assert result.patient_id == patient_id
        assert result.doctor_id == doctor_id
        assert isinstance(result.status, Requested)
        assert result.reason == reason
        mock_pool.fetchrow.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_appointment_by_id_found(self, mocker: MockerFixture) -> None:
        """GetAppointmentById should return Appointment when found."""
        appointment_id = uuid4()
        patient_id = uuid4()
        doctor_id = uuid4()

        # Mock database pool
        mock_pool = mocker.AsyncMock()
        mock_row = {
            "id": appointment_id,
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "status": "confirmed",
            "requested_time": datetime.now(timezone.utc),
            "reason": "Follow-up",
            "notes": None,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        mock_pool.fetchrow.return_value = mock_row

        interpreter = HealthcareInterpreter(mock_pool)

        # Execute
        effect = GetAppointmentById(appointment_id=appointment_id)
        result = await interpreter.handle(effect)

        # Assert
        assert isinstance(result, Appointment)
        assert result.id == appointment_id
        assert isinstance(result.status, Confirmed)
        mock_pool.fetchrow.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_appointment_by_id_not_found(self, mocker: MockerFixture) -> None:
        """GetAppointmentById should return None when not found."""
        appointment_id = uuid4()

        # Mock database pool
        mock_pool = mocker.AsyncMock()
        mock_pool.fetchrow.return_value = None

        interpreter = HealthcareInterpreter(mock_pool)

        # Execute
        effect = GetAppointmentById(appointment_id=appointment_id)
        result = await interpreter.handle(effect)

        # Assert
        assert result is None
        mock_pool.fetchrow.assert_called_once()

    @pytest.mark.asyncio
    async def test_transition_appointment_status_valid(self, mocker: MockerFixture) -> None:
        """TransitionAppointmentStatus should succeed for valid transition."""
        appointment_id = uuid4()
        patient_id = uuid4()
        doctor_id = uuid4()
        actor_id = uuid4()

        # Mock existing appointment in Requested status
        mock_pool = mocker.AsyncMock()
        mock_row = {
            "id": appointment_id,
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "status": "requested",
            "requested_time": datetime.now(timezone.utc),
            "reason": "Checkup",
            "notes": None,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        mock_pool.fetchrow.return_value = mock_row
        mock_pool.execute.return_value = None

        interpreter = HealthcareInterpreter(mock_pool)

        # Execute valid transition: Requested → Confirmed
        new_status = Confirmed(
            confirmed_at=datetime.now(timezone.utc),
            scheduled_time=datetime.now(timezone.utc),
        )
        effect = TransitionAppointmentStatus(
            appointment_id=appointment_id, new_status=new_status, actor_id=actor_id
        )
        result = await interpreter.handle(effect)

        # Assert
        assert isinstance(result, TransitionSuccess)
        assert result.new_status == new_status
        mock_pool.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_transition_appointment_status_invalid(self, mocker: MockerFixture) -> None:
        """TransitionAppointmentStatus should fail for invalid transition."""
        appointment_id = uuid4()
        patient_id = uuid4()
        doctor_id = uuid4()
        actor_id = uuid4()

        # Mock existing appointment in Completed status (terminal)
        mock_pool = mocker.AsyncMock()
        mock_row = {
            "id": appointment_id,
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "status": "completed",
            "requested_time": datetime.now(timezone.utc),
            "reason": "Checkup",
            "notes": None,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        mock_pool.fetchrow.return_value = mock_row

        interpreter = HealthcareInterpreter(mock_pool)

        # Execute invalid transition: Completed → Requested
        new_status = Requested(requested_at=datetime.now(timezone.utc))
        effect = TransitionAppointmentStatus(
            appointment_id=appointment_id, new_status=new_status, actor_id=actor_id
        )
        result = await interpreter.handle(effect)

        # Assert
        assert isinstance(result, TransitionInvalid)
        assert "Cannot transition" in result.reason

    @pytest.mark.asyncio
    async def test_transition_appointment_status_not_found(self, mocker: MockerFixture) -> None:
        """TransitionAppointmentStatus should fail when appointment not found."""
        appointment_id = uuid4()
        actor_id = uuid4()

        # Mock appointment not found
        mock_pool = mocker.AsyncMock()
        mock_pool.fetchrow.return_value = None

        interpreter = HealthcareInterpreter(mock_pool)

        # Execute
        new_status = Confirmed(
            confirmed_at=datetime.now(timezone.utc),
            scheduled_time=datetime.now(timezone.utc),
        )
        effect = TransitionAppointmentStatus(
            appointment_id=appointment_id, new_status=new_status, actor_id=actor_id
        )
        result = await interpreter.handle(effect)

        # Assert
        assert isinstance(result, TransitionInvalid)
        assert "not found" in result.reason


class TestHealthcareInterpreterPrescriptionOperations:
    """Test prescription-related operations."""

    @pytest.mark.asyncio
    async def test_create_prescription_success(self, mocker: MockerFixture) -> None:
        """CreatePrescription should create prescription successfully."""
        patient_id = uuid4()
        doctor_id = uuid4()
        prescription_id = uuid4()

        # Mock database pool
        mock_pool = mocker.AsyncMock()
        mock_row = {
            "id": prescription_id,
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "medication": "Lisinopril",
            "dosage": "10mg",
            "frequency": "once daily",
            "duration_days": 30,
            "refills_remaining": 3,
            "notes": "Monitor blood pressure",
            "created_at": datetime.now(timezone.utc),
            "expires_at": datetime.now(timezone.utc),
        }
        mock_pool.fetchrow.return_value = mock_row

        interpreter = HealthcareInterpreter(mock_pool)

        # Execute
        effect = CreatePrescription(
            patient_id=patient_id,
            doctor_id=doctor_id,
            medication="Lisinopril",
            dosage="10mg",
            frequency="once daily",
            duration_days=30,
            refills_remaining=3,
            notes="Monitor blood pressure",
        )
        result = await interpreter.handle(effect)

        # Assert
        assert isinstance(result, Prescription)
        assert result.patient_id == patient_id
        assert result.medication == "Lisinopril"
        assert result.dosage == "10mg"
        mock_pool.fetchrow.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_medication_interactions_no_interactions(
        self, mocker: MockerFixture
    ) -> None:
        """CheckMedicationInteractions should return NoInteractions when safe."""
        # Mock database pool (not used for this operation)
        mock_pool = mocker.AsyncMock()

        interpreter = HealthcareInterpreter(mock_pool)

        # Execute with safe medications
        effect = CheckMedicationInteractions(medications=["Lisinopril", "Metformin"])
        result = await interpreter.handle(effect)

        # Assert
        assert isinstance(result, NoInteractions)
        assert "Lisinopril" in result.medications_checked
        assert "Metformin" in result.medications_checked

    @pytest.mark.asyncio
    async def test_check_medication_interactions_warning_found(self, mocker: MockerFixture) -> None:
        """CheckMedicationInteractions should return warning for dangerous combinations."""
        # Mock database pool (not used for this operation)
        mock_pool = mocker.AsyncMock()

        interpreter = HealthcareInterpreter(mock_pool)

        # Execute with dangerous combination
        effect = CheckMedicationInteractions(medications=["Warfarin", "Aspirin"])
        result = await interpreter.handle(effect)

        # Assert
        assert isinstance(result, MedicationInteractionWarning)
        assert result.severity == "severe"
        assert "bleeding" in result.description.lower()


class TestHealthcareInterpreterLabResultOperations:
    """Test lab result-related operations."""

    @pytest.mark.asyncio
    async def test_create_lab_result_success(self, mocker: MockerFixture) -> None:
        """CreateLabResult should create lab result successfully."""
        result_id = uuid4()
        patient_id = uuid4()
        doctor_id = uuid4()

        # Mock database pool
        mock_pool = mocker.AsyncMock()
        mock_row = {
            "id": result_id,
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "test_type": "CBC",
            "result_data": {"wbc": "7.5", "rbc": "4.8"},
            "critical": False,
            "reviewed_by_doctor": False,
            "doctor_notes": None,
            "created_at": datetime.now(timezone.utc),
        }
        mock_pool.fetchrow.return_value = mock_row

        interpreter = HealthcareInterpreter(mock_pool)

        # Execute
        effect = CreateLabResult(
            result_id=result_id,
            patient_id=patient_id,
            doctor_id=doctor_id,
            test_type="CBC",
            result_data={"wbc": "7.5", "rbc": "4.8"},
            critical=False,
            doctor_notes=None,
        )
        result = await interpreter.handle(effect)

        # Assert
        assert isinstance(result, LabResult)
        assert result.id == result_id
        assert result.test_type == "CBC"
        assert result.critical is False
        mock_pool.fetchrow.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_lab_result_by_id_found(self, mocker: MockerFixture) -> None:
        """GetLabResultById should return LabResult when found."""
        result_id = uuid4()
        patient_id = uuid4()
        doctor_id = uuid4()

        # Mock database pool
        mock_pool = mocker.AsyncMock()
        mock_row = {
            "id": result_id,
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "test_type": "Lipid Panel",
            "result_data": {"cholesterol": "180", "triglycerides": "150"},
            "critical": False,
            "reviewed_by_doctor": True,
            "doctor_notes": "Results normal",
            "created_at": datetime.now(timezone.utc),
        }
        mock_pool.fetchrow.return_value = mock_row

        interpreter = HealthcareInterpreter(mock_pool)

        # Execute
        effect = GetLabResultById(result_id=result_id)
        result = await interpreter.handle(effect)

        # Assert
        assert isinstance(result, LabResult)
        assert result.id == result_id
        assert result.reviewed_by_doctor is True
        mock_pool.fetchrow.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_lab_result_by_id_not_found(self, mocker: MockerFixture) -> None:
        """GetLabResultById should return None when not found."""
        result_id = uuid4()

        # Mock database pool
        mock_pool = mocker.AsyncMock()
        mock_pool.fetchrow.return_value = None

        interpreter = HealthcareInterpreter(mock_pool)

        # Execute
        effect = GetLabResultById(result_id=result_id)
        result = await interpreter.handle(effect)

        # Assert
        assert result is None
        mock_pool.fetchrow.assert_called_once()


class TestHealthcareInterpreterInvoiceOperations:
    """Test invoice-related operations."""

    @pytest.mark.asyncio
    async def test_create_invoice_success(self, mocker: MockerFixture) -> None:
        """CreateInvoice should create invoice with line items."""
        patient_id = uuid4()
        appointment_id = uuid4()
        invoice_id = uuid4()

        line_item = LineItem(
            id=uuid4(),
            invoice_id=invoice_id,
            description="Office visit",
            quantity=1,
            unit_price=Decimal("150.00"),
            total=Decimal("150.00"),
            created_at=datetime.now(timezone.utc),
        )

        # Mock database pool
        mock_pool = mocker.AsyncMock()
        mock_row = {
            "id": invoice_id,
            "patient_id": patient_id,
            "appointment_id": appointment_id,
            "status": "draft",
            "subtotal": "150.00",
            "tax_amount": "0.00",
            "total_amount": "150.00",
            "due_date": None,
            "paid_at": None,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        mock_pool.fetchrow.return_value = mock_row
        mock_pool.execute.return_value = None

        interpreter = HealthcareInterpreter(mock_pool)

        # Execute
        effect = CreateInvoice(
            patient_id=patient_id,
            appointment_id=appointment_id,
            line_items=[line_item],
            due_date=None,
        )
        result = await interpreter.handle(effect)

        # Assert
        assert isinstance(result, Invoice)
        assert result.patient_id == patient_id
        assert result.status == "draft"
        assert result.total_amount == Decimal("150.00")
        mock_pool.fetchrow.assert_called_once()
        # Line item insert
        mock_pool.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_invoice_line_item_success(self, mocker: MockerFixture) -> None:
        """AddInvoiceLineItem should add line item and return LineItem."""
        invoice_id = uuid4()
        line_item_id = uuid4()
        description = "Lab work - CBC"
        quantity = 1
        unit_price = Decimal("75.00")

        # Mock database pool
        mock_pool = mocker.AsyncMock()
        mock_row = {
            "id": line_item_id,
            "invoice_id": invoice_id,
            "description": description,
            "quantity": quantity,
            "unit_price": "75.00",
            "total": "75.00",
            "created_at": datetime.now(timezone.utc),
        }
        mock_pool.fetchrow.return_value = mock_row

        interpreter = HealthcareInterpreter(mock_pool)

        # Execute
        effect = AddInvoiceLineItem(
            invoice_id=invoice_id,
            description=description,
            quantity=quantity,
            unit_price=unit_price,
        )
        result = await interpreter.handle(effect)

        # Assert
        assert isinstance(result, LineItem)
        assert result.invoice_id == invoice_id
        assert result.description == description
        assert result.quantity == quantity
        assert result.unit_price == unit_price
        mock_pool.fetchrow.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_invoice_status_success(self, mocker: MockerFixture) -> None:
        """UpdateInvoiceStatus should update status and return Invoice."""
        invoice_id = uuid4()
        patient_id = uuid4()
        new_status = "paid"

        # Mock database pool
        mock_pool = mocker.AsyncMock()
        mock_row = {
            "id": invoice_id,
            "patient_id": patient_id,
            "appointment_id": None,
            "status": new_status,
            "subtotal": "150.00",
            "tax_amount": "0.00",
            "total_amount": "150.00",
            "due_date": None,
            "paid_at": datetime.now(timezone.utc),
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        mock_pool.fetchrow.return_value = mock_row

        interpreter = HealthcareInterpreter(mock_pool)

        # Execute
        effect = UpdateInvoiceStatus(
            invoice_id=invoice_id,
            status=new_status,
        )
        result = await interpreter.handle(effect)

        # Assert
        assert isinstance(result, Invoice)
        assert result.id == invoice_id
        assert result.status == new_status
        mock_pool.fetchrow.assert_called_once()


class TestNotificationInterpreterWebSocketNotifications:
    """Test WebSocket notification publishing."""

    @pytest.mark.asyncio
    async def test_publish_websocket_notification_success(self, mocker: MockerFixture) -> None:
        """PublishWebSocketNotification should publish to Redis successfully."""
        channel = "patient:123:notifications"
        message: dict[str, NotificationValue] = {
            "type": "appointment_confirmed",
            "appointment_id": "abc-123",
        }
        recipient_id = uuid4()

        # Mock Redis client
        mock_pool = mocker.AsyncMock()
        mock_redis = mocker.AsyncMock()
        mock_redis.publish.return_value = 1  # 1 recipient

        interpreter = NotificationInterpreter(mock_pool, mock_redis)

        # Execute
        effect = PublishWebSocketNotification(
            channel=channel, message=message, recipient_id=recipient_id
        )
        result = await interpreter.handle(effect)

        # Assert
        assert isinstance(result, NotificationPublished)
        assert result.channel == channel
        assert result.recipients_count == 1
        mock_redis.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_websocket_notification_failure(self, mocker: MockerFixture) -> None:
        """PublishWebSocketNotification should handle Redis errors gracefully."""
        channel = "patient:123:notifications"
        message: dict[str, NotificationValue] = {"type": "test"}
        recipient_id = uuid4()

        # Mock Redis client that raises exception
        mock_pool = mocker.AsyncMock()
        mock_redis = mocker.AsyncMock()
        mock_redis.publish.side_effect = Exception("Redis connection failed")

        interpreter = NotificationInterpreter(mock_pool, mock_redis)

        # Execute
        effect = PublishWebSocketNotification(
            channel=channel, message=message, recipient_id=recipient_id
        )
        result = await interpreter.handle(effect)

        # Assert
        assert isinstance(result, PublishFailed)
        assert result.channel == channel
        assert "Redis connection failed" in result.reason


class TestNotificationInterpreterAuditLogging:
    """Test audit logging operations."""

    @pytest.mark.asyncio
    async def test_log_audit_event_success(self, mocker: MockerFixture) -> None:
        """LogAuditEvent should log to database successfully."""
        user_id = uuid4()
        resource_id = uuid4()

        # Mock database pool
        mock_pool = mocker.AsyncMock()
        mock_pool.execute.return_value = None
        mock_redis = mocker.AsyncMock()

        interpreter = NotificationInterpreter(mock_pool, mock_redis)

        # Execute
        effect = LogAuditEvent(
            user_id=user_id,
            action="view_patient",
            resource_type="patient",
            resource_id=resource_id,
            ip_address="192.168.1.1",
            user_agent="Test Browser",
            metadata={"key": "value"},
        )
        result = await interpreter.handle(effect)

        # Assert
        assert isinstance(result, AuditEventLogged)
        assert isinstance(result.event_id, UUID)
        assert isinstance(result.logged_at, datetime)
        mock_pool.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_audit_event_with_optional_fields_none(self, mocker: MockerFixture) -> None:
        """LogAuditEvent should handle None optional fields."""
        user_id = uuid4()
        resource_id = uuid4()

        # Mock database pool
        mock_pool = mocker.AsyncMock()
        mock_pool.execute.return_value = None
        mock_redis = mocker.AsyncMock()

        interpreter = NotificationInterpreter(mock_pool, mock_redis)

        # Execute with None optional fields
        effect = LogAuditEvent(
            user_id=user_id,
            action="delete_appointment",
            resource_type="appointment",
            resource_id=resource_id,
            ip_address=None,
            user_agent=None,
            metadata=None,
        )
        result = await interpreter.handle(effect)

        # Assert
        assert isinstance(result, AuditEventLogged)
        mock_pool.execute.assert_called_once()
