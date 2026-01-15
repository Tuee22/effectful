-- HealthHub Seed Data
-- Description: Demo users and sample data for development and testing
-- Password for all users: "password123" (hashed with bcrypt, cost=12)

-- Note: In production, generate these passwords with Python bcrypt (inside the container)
-- docker compose -f demo/healthhub/docker/docker-compose.yml exec healthhub poetry run python -c "import bcrypt; print(bcrypt.hashpw(b'password123', bcrypt.gensalt(12)).decode())"

-- Clear existing data (for development resets)
TRUNCATE TABLE
    audit_log,
    invoice_line_items,
    invoices,
    lab_results,
    prescriptions,
    appointments,
    doctors,
    patients,
    users
CASCADE;

-- 01: Admin Users
INSERT INTO users (id, email, password_hash, role, status) VALUES
('00000000-0000-0000-0000-000000000001', 'admin@healthhub.com', '$2b$12$iVwfUaEApSiRZ8OWCIJpVuiQ73N58zl9rb0mAWvroHdVItFGLuoe.', 'admin', 'active'),
('00000000-0000-0000-0000-000000000002', 'superadmin@healthhub.com', '$2b$12$iVwfUaEApSiRZ8OWCIJpVuiQ73N58zl9rb0mAWvroHdVItFGLuoe.', 'admin', 'active');

-- 02: Doctor Users
INSERT INTO users (id, email, password_hash, role, status) VALUES
('10000000-0000-0000-0000-000000000001', 'dr.smith@healthhub.com', '$2b$12$iVwfUaEApSiRZ8OWCIJpVuiQ73N58zl9rb0mAWvroHdVItFGLuoe.', 'doctor', 'active'),
('10000000-0000-0000-0000-000000000002', 'dr.johnson@healthhub.com', '$2b$12$iVwfUaEApSiRZ8OWCIJpVuiQ73N58zl9rb0mAWvroHdVItFGLuoe.', 'doctor', 'active'),
('10000000-0000-0000-0000-000000000003', 'dr.williams@healthhub.com', '$2b$12$iVwfUaEApSiRZ8OWCIJpVuiQ73N58zl9rb0mAWvroHdVItFGLuoe.', 'doctor', 'active'),
('10000000-0000-0000-0000-000000000004', 'dr.brown@healthhub.com', '$2b$12$iVwfUaEApSiRZ8OWCIJpVuiQ73N58zl9rb0mAWvroHdVItFGLuoe.', 'doctor', 'active');

-- 03: Patient Users
INSERT INTO users (id, email, password_hash, role, status) VALUES
('20000000-0000-0000-0000-000000000001', 'alice.patient@example.com', '$2b$12$iVwfUaEApSiRZ8OWCIJpVuiQ73N58zl9rb0mAWvroHdVItFGLuoe.', 'patient', 'active'),
('20000000-0000-0000-0000-000000000002', 'bob.patient@example.com', '$2b$12$iVwfUaEApSiRZ8OWCIJpVuiQ73N58zl9rb0mAWvroHdVItFGLuoe.', 'patient', 'active'),
('20000000-0000-0000-0000-000000000003', 'carol.patient@example.com', '$2b$12$iVwfUaEApSiRZ8OWCIJpVuiQ73N58zl9rb0mAWvroHdVItFGLuoe.', 'patient', 'active'),
('20000000-0000-0000-0000-000000000004', 'david.patient@example.com', '$2b$12$iVwfUaEApSiRZ8OWCIJpVuiQ73N58zl9rb0mAWvroHdVItFGLuoe.', 'patient', 'active'),
('20000000-0000-0000-0000-000000000005', 'emily.patient@example.com', '$2b$12$iVwfUaEApSiRZ8OWCIJpVuiQ73N58zl9rb0mAWvroHdVItFGLuoe.', 'patient', 'active');

-- 04: Doctor Profiles
INSERT INTO doctors (id, user_id, first_name, last_name, specialization, license_number, can_prescribe, phone) VALUES
('40000000-0000-0000-0000-000000000001', '10000000-0000-0000-0000-000000000001', 'Sarah', 'Smith', 'Cardiology', 'MD-CA-12345', TRUE, '+1-555-0101'),
('40000000-0000-0000-0000-000000000002', '10000000-0000-0000-0000-000000000002', 'Michael', 'Johnson', 'Orthopedics', 'MD-CA-23456', TRUE, '+1-555-0102'),
('40000000-0000-0000-0000-000000000003', '10000000-0000-0000-0000-000000000003', 'Jennifer', 'Williams', 'Dermatology', 'MD-CA-34567', TRUE, '+1-555-0103'),
('40000000-0000-0000-0000-000000000004', '10000000-0000-0000-0000-000000000004', 'Robert', 'Brown', 'Neurology', 'MD-CA-45678', TRUE, '+1-555-0104');

-- 05: Patient Profiles
INSERT INTO patients (id, user_id, first_name, last_name, date_of_birth, blood_type, allergies, insurance_id, emergency_contact, phone, address) VALUES
('30000000-0000-0000-0000-000000000001', '20000000-0000-0000-0000-000000000001', 'Alice', 'Anderson', '1985-03-15', 'O+', ARRAY['Penicillin', 'Shellfish'], 'INS-001-2024', 'John Anderson: +1-555-0201', '+1-555-1001', '123 Main St, San Francisco, CA 94102'),
('30000000-0000-0000-0000-000000000002', '20000000-0000-0000-0000-000000000002', 'Bob', 'Baker', '1978-07-22', 'A+', ARRAY['Latex'], 'INS-002-2024', 'Mary Baker: +1-555-0202', '+1-555-1002', '456 Oak Ave, San Francisco, CA 94103'),
('30000000-0000-0000-0000-000000000003', '20000000-0000-0000-0000-000000000003', 'Carol', 'Carter', '1992-11-08', 'B-', ARRAY[]::TEXT[], 'INS-003-2024', 'Tom Carter: +1-555-0203', '+1-555-1003', '789 Pine St, Oakland, CA 94601'),
('30000000-0000-0000-0000-000000000004', '20000000-0000-0000-0000-000000000004', 'David', 'Davis', '1965-01-30', 'AB+', ARRAY['Aspirin', 'Bee stings'], 'INS-004-2024', 'Lisa Davis: +1-555-0204', '+1-555-1004', '321 Elm St, Berkeley, CA 94704'),
('30000000-0000-0000-0000-000000000005', '20000000-0000-0000-0000-000000000005', 'Emily', 'Evans', '2000-05-12', 'O-', ARRAY['Peanuts'], 'INS-005-2024', 'Mark Evans: +1-555-0205', '+1-555-1005', '654 Maple Dr, Palo Alto, CA 94301');

-- 06: Sample Appointments
INSERT INTO appointments (id, patient_id, doctor_id, status, status_metadata, reason, requested_time) VALUES
-- Confirmed appointment
('50000000-0000-0000-0000-000000000001',
 '30000000-0000-0000-0000-000000000001',
 '40000000-0000-0000-0000-000000000001',
 'confirmed',
 '{"confirmed_at": "2025-11-20T10:00:00Z", "scheduled_time": "2025-12-01T14:00:00Z"}',
 'Annual cardiac checkup',
 '2025-12-01T14:00:00Z'),

-- Requested appointment (awaiting confirmation)
('50000000-0000-0000-0000-000000000002',
 '30000000-0000-0000-0000-000000000002',
 '40000000-0000-0000-0000-000000000002',
 'requested',
 '{"requested_at": "2025-11-24T09:00:00Z"}',
 'Knee pain evaluation',
 NULL),

-- Completed appointment
('50000000-0000-0000-0000-000000000003',
 '30000000-0000-0000-0000-000000000003',
 '40000000-0000-0000-0000-000000000003',
 'completed',
 '{"completed_at": "2025-11-15T11:30:00Z", "notes": "Prescribed topical treatment"}',
 'Skin rash consultation',
 '2025-11-15T10:00:00Z');

-- 07: Sample Prescriptions
INSERT INTO prescriptions (id, patient_id, doctor_id, medication, dosage, frequency, duration_days, refills_remaining, notes, created_at, expires_at) VALUES
('60000000-0000-0000-0000-000000000001',
 '30000000-0000-0000-0000-000000000001',
 '40000000-0000-0000-0000-000000000001',
 'Lisinopril',
 '10mg',
 'Once daily',
 90,
 2,
 'Take in the morning with water. Monitor blood pressure.',
 '2025-11-01T00:00:00Z',
 '2026-11-01T00:00:00Z'),

('60000000-0000-0000-0000-000000000002',
 '30000000-0000-0000-0000-000000000003',
 '40000000-0000-0000-0000-000000000003',
 'Hydrocortisone Cream',
 '1%',
 'Apply twice daily',
 14,
 0,
 'Apply to affected area. Avoid eyes.',
 '2025-11-15T00:00:00Z',
 '2026-02-15T00:00:00Z');

-- 08: Sample Lab Results
INSERT INTO lab_results (id, patient_id, doctor_id, test_type, result_data, critical, reviewed_by_doctor, doctor_notes) VALUES
('70000000-0000-0000-0000-000000000001',
 '30000000-0000-0000-0000-000000000001',
 '40000000-0000-0000-0000-000000000001',
 'Lipid Panel',
 '{"total_cholesterol": "195", "ldl": "120", "hdl": "55", "triglycerides": "100"}',
 FALSE,
 TRUE,
 'Results within normal range. Continue current medication.'),

('70000000-0000-0000-0000-000000000002',
 '30000000-0000-0000-0000-000000000004',
 '40000000-0000-0000-0000-000000000004',
 'Blood Glucose',
 '{"fasting_glucose": "105", "hba1c": "6.2"}',
 TRUE,
 TRUE,
 'Prediabetic range. Recommend lifestyle modifications and follow-up in 3 months.');

-- 09: Sample Invoices
INSERT INTO invoices (id, patient_id, appointment_id, status, subtotal, tax_amount, total_amount, due_date) VALUES
('80000000-0000-0000-0000-000000000001',
 '30000000-0000-0000-0000-000000000003',
 '50000000-0000-0000-0000-000000000003',
 'sent',
 250.00,
 22.50,
 272.50,
 '2025-12-15');

-- 10: Sample Invoice Line Items
INSERT INTO invoice_line_items (invoice_id, description, quantity, unit_price, total) VALUES
('80000000-0000-0000-0000-000000000001', 'Office Visit - Dermatology Consultation', 1, 200.00, 200.00),
('80000000-0000-0000-0000-000000000001', 'Prescription - Hydrocortisone Cream', 1, 50.00, 50.00);

-- 11: Sample Audit Log Entries
INSERT INTO audit_log (user_id, action, resource_type, resource_id, ip_address, user_agent, metadata) VALUES
('20000000-0000-0000-0000-000000000001', 'appointment_created', 'appointment', '50000000-0000-0000-0000-000000000001', '192.168.1.100', 'Mozilla/5.0', '{"status": "confirmed"}'),
('10000000-0000-0000-0000-000000000001', 'prescription_created', 'prescription', '60000000-0000-0000-0000-000000000001', '192.168.1.101', 'Mozilla/5.0', '{"medication": "Lisinopril", "dosage": "10mg"}'),
('20000000-0000-0000-0000-000000000001', 'lab_result_viewed', 'lab_result', '70000000-0000-0000-0000-000000000001', '192.168.1.102', 'Mozilla/5.0', '{"test_type": "Lipid Panel"}');

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'HealthHub seed data loaded successfully!';
    RAISE NOTICE 'Login credentials: All users have password "password123"';
    RAISE NOTICE 'Admin: admin@healthhub.com';
    RAISE NOTICE 'Doctor: dr.smith@healthhub.com';
    RAISE NOTICE 'Patient: alice.patient@example.com';
END
$$;
