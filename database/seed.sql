-- 1. Clear all data and reset identity sequences
TRUNCATE TABLE users RESTART IDENTITY CASCADE;

-- 2. Insert Base Authentication Users with explicit IDs
INSERT INTO users (user_id, username, password_hash, role) VALUES
(1, 'admin_user', 'admin123', 'ADMIN'),
(2, 'doc_smith', 'doc123', 'DOCTOR'),
(3, 'patient_jane', 'patient123', 'PATIENT');

-- Sync the PostgreSQL auto-increment sequence to start at 4 for future inserts
SELECT setval('users_user_id_seq', (SELECT MAX(user_id) FROM users));

-- 3. Insert Admin Profile (Linked to user_id = 1)
INSERT INTO admins (user_id, first_name, last_name, employee_id, email)
VALUES (1, 'System', 'Admin', 'EMP-001', 'admin@hospital.com');

-- 4. Insert Doctor Profile (Linked to user_id = 2)
INSERT INTO doctors (user_id, first_name, last_name, license_number, specialization, contact_number, email)
VALUES (2, 'John', 'Smith', 'PRC-123456', 'General Practice', '09171234567', 'doc.smith@hospital.com');

-- 5. Insert Patient Profile (Linked to user_id = 3)
INSERT INTO patients (
    user_id, first_name, last_name, date_of_birth, gender, 
    address, contact_number, email, emergency_contact_name, 
    emergency_contact_number, emergency_relation, hipaa_consent
) VALUES (
    3, 'Jane', 'Doe', '1995-05-15', 'Female', 
    '123 Main St', '09181234567', 'jane.doe@email.com', 'Mary Doe', 
    '09191234567', 'Mother', TRUE
);