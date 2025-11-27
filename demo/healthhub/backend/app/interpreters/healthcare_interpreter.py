"""Healthcare effect interpreter.

Handles all healthcare-related effects by delegating to appropriate repositories.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from uuid import UUID, uuid4

import asyncpg

from app.database.converters import (
    safe_bool,
    safe_datetime,
    safe_decimal,
    safe_dict_str_object,
    safe_int,
    safe_invoice_status,
    safe_optional_date,
    safe_optional_datetime,
    safe_optional_str,
    safe_optional_uuid,
    safe_str,
    safe_uuid,
)
from app.domain.appointment import (
    Appointment,
    AppointmentStatus,
    Cancelled,
    Completed,
    Confirmed,
    InProgress,
    Requested,
    TransitionInvalid,
    TransitionResult,
    TransitionSuccess,
    validate_transition,
)
from app.domain.doctor import Doctor
from app.domain.invoice import Invoice, LineItem
from app.domain.lab_result import LabResult
from app.domain.patient import Patient
from app.domain.prescription import (
    MedicationCheckResult,
    MedicationInteractionWarning,
    NoInteractions,
    Prescription,
)
from app.effects.healthcare import (
    CheckMedicationInteractions,
    CreateAppointment,
    CreateInvoice,
    CreateLabResult,
    CreatePrescription,
    GetAppointmentById,
    GetDoctorById,
    GetLabResultById,
    GetPatientById,
    HealthcareEffect,
    TransitionAppointmentStatus,
)
from app.repositories.doctor_repository import DoctorRepository
from app.repositories.patient_repository import PatientRepository


class HealthcareInterpreter:
    """Interpreter for healthcare effects.

    Delegates to repositories and domain services to execute healthcare operations.
    """

    def __init__(self, pool: asyncpg.Pool[asyncpg.Record]) -> None:
        """Initialize interpreter with database pool.

        Args:
            pool: asyncpg connection pool
        """
        self.pool = pool
        self.patient_repo = PatientRepository(pool)
        self.doctor_repo = DoctorRepository(pool)

    async def handle(
        self, effect: HealthcareEffect
    ) -> (
        Patient
        | None
        | Doctor
        | Appointment
        | TransitionResult
        | Prescription
        | MedicationCheckResult
        | LabResult
        | Invoice
    ):
        """Handle a healthcare effect.

        Args:
            effect: Healthcare effect to execute

        Returns:
            Result of executing the effect
        """
        match effect:
            case GetPatientById(patient_id=patient_id):
                return await self._get_patient_by_id(patient_id)

            case GetDoctorById(doctor_id=doctor_id):
                return await self._get_doctor_by_id(doctor_id)

            case CreateAppointment(
                patient_id=patient_id,
                doctor_id=doctor_id,
                requested_time=requested_time,
                reason=reason,
            ):
                return await self._create_appointment(patient_id, doctor_id, requested_time, reason)

            case GetAppointmentById(appointment_id=appointment_id):
                return await self._get_appointment_by_id(appointment_id)

            case TransitionAppointmentStatus(
                appointment_id=appointment_id, new_status=new_status, actor_id=actor_id
            ):
                return await self._transition_appointment_status(
                    appointment_id, new_status, actor_id
                )

            case CreatePrescription(
                patient_id=patient_id,
                doctor_id=doctor_id,
                medication=medication,
                dosage=dosage,
                frequency=frequency,
                duration_days=duration_days,
                refills_remaining=refills_remaining,
                notes=notes,
            ):
                return await self._create_prescription(
                    patient_id,
                    doctor_id,
                    medication,
                    dosage,
                    frequency,
                    duration_days,
                    refills_remaining,
                    notes,
                )

            case CheckMedicationInteractions(medications=medications):
                return await self._check_medication_interactions(medications)

            case CreateLabResult(
                result_id=result_id,
                patient_id=patient_id,
                doctor_id=doctor_id,
                test_type=test_type,
                result_data=result_data,
                critical=critical,
            ):
                return await self._create_lab_result(
                    result_id, patient_id, doctor_id, test_type, result_data, critical
                )

            case GetLabResultById(result_id=result_id):
                return await self._get_lab_result_by_id(result_id)

            case CreateInvoice(
                patient_id=patient_id,
                appointment_id=appointment_id,
                line_items=line_items,
                due_date=due_date,
            ):
                return await self._create_invoice(patient_id, appointment_id, line_items, due_date)

    # Patient operations
    async def _get_patient_by_id(self, patient_id: UUID) -> Patient | None:
        """Get patient by ID."""
        return await self.patient_repo.get_by_id(patient_id)

    # Doctor operations
    async def _get_doctor_by_id(self, doctor_id: UUID) -> Doctor | None:
        """Get doctor by ID."""
        return await self.doctor_repo.get_by_id(doctor_id)

    # Appointment operations
    async def _create_appointment(
        self,
        patient_id: UUID,
        doctor_id: UUID,
        requested_time: datetime | None,
        reason: str,
    ) -> Appointment:
        """Create new appointment in Requested status."""
        now = datetime.now(timezone.utc)
        appointment_id = uuid4()

        status = Requested(requested_at=now)

        row = await self.pool.fetchrow(
            """
            INSERT INTO appointments (
                id, patient_id, doctor_id, status, requested_time,
                reason, notes, created_at, updated_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING id, patient_id, doctor_id, status, requested_time,
                      reason, notes, created_at, updated_at
            """,
            appointment_id,
            patient_id,
            doctor_id,
            "requested",
            requested_time,
            reason,
            None,
            now,
            now,
        )

        if row is None:
            raise RuntimeError("Failed to create appointment")

        return self._row_to_appointment(row)

    async def _get_appointment_by_id(self, appointment_id: UUID) -> Appointment | None:
        """Get appointment by ID."""
        row = await self.pool.fetchrow(
            """
            SELECT id, patient_id, doctor_id, status, requested_time,
                   reason, notes, created_at, updated_at
            FROM appointments
            WHERE id = $1
            """,
            appointment_id,
        )

        if row is None:
            return None

        return self._row_to_appointment(row)

    async def _transition_appointment_status(
        self, appointment_id: UUID, new_status: AppointmentStatus, actor_id: UUID
    ) -> TransitionResult:
        """Transition appointment status."""
        # Get current appointment
        appointment = await self._get_appointment_by_id(appointment_id)
        if appointment is None:
            return TransitionInvalid(
                current_status="none",
                attempted_status=type(new_status).__name__,
                reason=f"Appointment {appointment_id} not found",
            )

        # Validate transition
        result = validate_transition(appointment.status, new_status)

        if isinstance(result, TransitionInvalid):
            return result

        # Perform transition
        status_str = self._status_to_string(new_status)
        now = datetime.now(timezone.utc)

        # Build status_metadata based on the new status
        status_metadata: dict[str, str] = {}
        if isinstance(new_status, Confirmed):
            status_metadata["confirmed_at"] = new_status.confirmed_at.isoformat()
            status_metadata["confirmed_by"] = str(actor_id)
            # Include the scheduled time from the confirmation
            status_metadata["scheduled_time"] = new_status.scheduled_time.isoformat()
        elif isinstance(new_status, InProgress):
            status_metadata["started_at"] = new_status.started_at.isoformat()
        elif isinstance(new_status, Completed):
            status_metadata["completed_at"] = new_status.completed_at.isoformat()
            if new_status.notes:
                status_metadata["notes"] = new_status.notes
        elif isinstance(new_status, Cancelled):
            status_metadata["cancelled_at"] = new_status.cancelled_at.isoformat()
            status_metadata["cancelled_by"] = new_status.cancelled_by
            status_metadata["reason"] = new_status.reason

        status_metadata_json = json.dumps(status_metadata) if status_metadata else None

        await self.pool.execute(
            """
            UPDATE appointments
            SET status = $1, status_metadata = $2::jsonb, updated_at = $3
            WHERE id = $4
            """,
            status_str,
            status_metadata_json,
            now,
            appointment_id,
        )

        return TransitionSuccess(new_status=new_status)

    # Prescription operations
    async def _create_prescription(
        self,
        patient_id: UUID,
        doctor_id: UUID,
        medication: str,
        dosage: str,
        frequency: str,
        duration_days: int,
        refills_remaining: int,
        notes: str | None,
    ) -> Prescription:
        """Create new prescription."""
        now = datetime.now(timezone.utc)
        prescription_id = uuid4()
        expires_at = now + timedelta(days=duration_days)

        row = await self.pool.fetchrow(
            """
            INSERT INTO prescriptions (
                id, patient_id, doctor_id, medication, dosage,
                frequency, duration_days, refills_remaining, notes,
                created_at, expires_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            RETURNING id, patient_id, doctor_id, medication, dosage,
                      frequency, duration_days, refills_remaining, notes,
                      created_at, expires_at
            """,
            prescription_id,
            patient_id,
            doctor_id,
            medication,
            dosage,
            frequency,
            duration_days,
            refills_remaining,
            notes,
            now,
            expires_at,
        )

        if row is None:
            raise RuntimeError("Failed to create prescription")

        return self._row_to_prescription(row)

    async def _check_medication_interactions(self, medications: list[str]) -> MedicationCheckResult:
        """Check for medication interactions.

        Stub implementation - would integrate with drug interaction API.
        """
        from typing import Literal

        # Type alias for severity levels
        type SeverityLevel = Literal["minor", "moderate", "severe"]

        # Known dangerous interactions (simplified)
        # Each tuple: (drug_pair, severity, base_description)
        dangerous_pairs: list[tuple[set[str], SeverityLevel, str]] = [
            (
                {"warfarin", "aspirin"},
                "severe",
                "Warfarin and Aspirin interaction: Increased bleeding risk",
            ),
            (
                {"lisinopril", "ibuprofen"},
                "moderate",
                "Lisinopril and Ibuprofen interaction: May reduce ACE inhibitor effectiveness",
            ),
            (
                {"levothyroxine", "calcium carbonate"},
                "minor",
                "Levothyroxine and Calcium Carbonate interaction: May reduce absorption",
            ),
        ]

        med_set = {med.lower() for med in medications}

        for pair, severity, description in dangerous_pairs:
            if pair.issubset(med_set):
                return MedicationInteractionWarning(
                    medications=list(pair),
                    severity=severity,
                    description=description,
                )

        return NoInteractions(medications_checked=medications)

    # Lab result operations
    async def _create_lab_result(
        self,
        result_id: UUID,
        patient_id: UUID,
        doctor_id: UUID,
        test_type: str,
        result_data: dict[str, str],
        critical: bool,
    ) -> LabResult:
        """Create new lab result."""
        now = datetime.now(timezone.utc)

        # Convert result_data dict to JSON string for JSONB column
        result_data_json = json.dumps(result_data)

        row = await self.pool.fetchrow(
            """
            INSERT INTO lab_results (
                id, patient_id, doctor_id, test_type, result_data,
                critical, reviewed_by_doctor, doctor_notes, created_at
            )
            VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7, $8, $9)
            RETURNING id, patient_id, doctor_id, test_type, result_data,
                      critical, reviewed_by_doctor, doctor_notes, created_at
            """,
            result_id,
            patient_id,
            doctor_id,
            test_type,
            result_data_json,
            critical,
            False,
            None,
            now,
        )

        if row is None:
            raise RuntimeError("Failed to create lab result")

        return self._row_to_lab_result(row)

    async def _get_lab_result_by_id(self, result_id: UUID) -> LabResult | None:
        """Get lab result by ID."""
        row = await self.pool.fetchrow(
            """
            SELECT id, patient_id, doctor_id, test_type, result_data,
                   critical, reviewed_by_doctor, doctor_notes, created_at
            FROM lab_results
            WHERE id = $1
            """,
            result_id,
        )

        if row is None:
            return None

        return self._row_to_lab_result(row)

    # Invoice operations
    async def _create_invoice(
        self,
        patient_id: UUID,
        appointment_id: UUID | None,
        line_items: list[LineItem],
        due_date: date | None,
    ) -> Invoice:
        """Create new invoice with line items."""
        now = datetime.now(timezone.utc)
        invoice_id = uuid4()

        # Calculate totals
        subtotal = sum((item.total for item in line_items), start=0)
        tax_amount = subtotal * 0  # No tax for now
        total_amount = subtotal + tax_amount

        # Insert invoice
        invoice_row = await self.pool.fetchrow(
            """
            INSERT INTO invoices (
                id, patient_id, appointment_id, status, subtotal,
                tax_amount, total_amount, due_date, paid_at,
                created_at, updated_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            RETURNING id, patient_id, appointment_id, status, subtotal,
                      tax_amount, total_amount, due_date, paid_at,
                      created_at, updated_at
            """,
            invoice_id,
            patient_id,
            appointment_id,
            "draft",
            str(subtotal),
            str(tax_amount),
            str(total_amount),
            due_date,
            None,
            now,
            now,
        )

        if invoice_row is None:
            raise RuntimeError("Failed to create invoice")

        # Insert line items
        for item in line_items:
            await self.pool.execute(
                """
                INSERT INTO invoice_line_items (
                    id, invoice_id, description, quantity, unit_price,
                    total, created_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                item.id,
                invoice_id,
                item.description,
                item.quantity,
                str(item.unit_price),
                str(item.total),
                now,
            )

        return self._row_to_invoice(invoice_row)

    # Helper methods for row-to-domain conversion
    def _row_to_appointment(self, row: asyncpg.Record) -> Appointment:
        """Convert database row to Appointment domain model."""
        status_str = safe_str(row["status"])
        status = self._string_to_status(status_str, row)

        return Appointment(
            id=safe_uuid(row["id"]),
            patient_id=safe_uuid(row["patient_id"]),
            doctor_id=safe_uuid(row["doctor_id"]),
            status=status,
            reason=safe_str(row["reason"]),
            created_at=safe_datetime(row["created_at"]),
            updated_at=safe_datetime(row["updated_at"]),
        )

    def _string_to_status(self, status_str: str, row: asyncpg.Record) -> AppointmentStatus:
        """Convert string status to AppointmentStatus ADT."""
        match status_str:
            case "requested":
                return Requested(requested_at=safe_datetime(row["created_at"]))
            case "confirmed":
                requested_time = safe_optional_datetime(row["requested_time"])
                updated_at = safe_datetime(row["updated_at"])
                return Confirmed(
                    confirmed_at=updated_at,
                    scheduled_time=requested_time if requested_time is not None else updated_at,
                )
            case "in_progress":
                return InProgress(started_at=safe_datetime(row["updated_at"]))
            case "completed":
                notes = safe_optional_str(row.get("notes"))
                return Completed(
                    completed_at=safe_datetime(row["updated_at"]),
                    notes=notes if notes is not None else "No notes",
                )
            case "cancelled":
                notes = safe_optional_str(row.get("notes"))
                return Cancelled(
                    cancelled_at=safe_datetime(row["updated_at"]),
                    cancelled_by="system",
                    reason=notes if notes is not None else "No reason provided",
                )
            case _:
                raise ValueError(f"Unknown appointment status: {status_str}")

    def _status_to_string(self, status: AppointmentStatus) -> str:
        """Convert AppointmentStatus ADT to string."""
        match status:
            case Requested():
                return "requested"
            case Confirmed():
                return "confirmed"
            case InProgress():
                return "in_progress"
            case Completed():
                return "completed"
            case Cancelled():
                return "cancelled"

    def _row_to_prescription(self, row: asyncpg.Record) -> Prescription:
        """Convert database row to Prescription domain model."""
        return Prescription(
            id=safe_uuid(row["id"]),
            patient_id=safe_uuid(row["patient_id"]),
            doctor_id=safe_uuid(row["doctor_id"]),
            medication=safe_str(row["medication"]),
            dosage=safe_str(row["dosage"]),
            frequency=safe_str(row["frequency"]),
            duration_days=safe_int(row["duration_days"]),
            refills_remaining=safe_int(row["refills_remaining"]),
            notes=safe_optional_str(row["notes"]),
            created_at=safe_datetime(row["created_at"]),
            expires_at=safe_datetime(row["expires_at"]),
        )

    def _row_to_lab_result(self, row: asyncpg.Record) -> LabResult:
        """Convert database row to LabResult domain model."""
        result_data_obj = safe_dict_str_object(row["result_data"])
        result_data = {str(k): str(v) for k, v in result_data_obj.items()}
        return LabResult(
            id=safe_uuid(row["id"]),
            patient_id=safe_uuid(row["patient_id"]),
            doctor_id=safe_uuid(row["doctor_id"]),
            test_type=safe_str(row["test_type"]),
            result_data=result_data,
            critical=safe_bool(row["critical"]),
            reviewed_by_doctor=safe_bool(row["reviewed_by_doctor"]),
            doctor_notes=safe_optional_str(row["doctor_notes"]),
            created_at=safe_datetime(row["created_at"]),
        )

    def _row_to_invoice(self, row: asyncpg.Record) -> Invoice:
        """Convert database row to Invoice domain model."""
        return Invoice(
            id=safe_uuid(row["id"]),
            patient_id=safe_uuid(row["patient_id"]),
            appointment_id=safe_optional_uuid(row["appointment_id"]),
            status=safe_invoice_status(row["status"]),
            subtotal=safe_decimal(row["subtotal"]),
            tax_amount=safe_decimal(row["tax_amount"]),
            total_amount=safe_decimal(row["total_amount"]),
            due_date=safe_optional_date(row["due_date"]),
            paid_at=safe_optional_datetime(row["paid_at"]),
            created_at=safe_datetime(row["created_at"]),
            updated_at=safe_datetime(row["updated_at"]),
        )
