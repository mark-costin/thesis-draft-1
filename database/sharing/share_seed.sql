-- =====================================================================
-- share_seed.sql
-- FAKE sample data for testing on a fresh CDSS database (schema v2).
-- Every name, number and record here is made up.
--
-- Loaded by:  setup.sh <file> --sample-data
-- Or by hand: psql -h localhost -U postgres -d cdss -v ON_ERROR_STOP=1 -1 -f share_seed.sql
--
-- Notes:
--  * The sample users CANNOT log in: their password_hash is a placeholder,
--    not a real hash. Register your own login through the app.
--  * role, relationship_tier and onset_classification values below are
--    guesses. If the app shows them oddly, change them to the exact
--    values your backend uses.
-- =====================================================================

SET search_path = public;

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM users) THEN
    RAISE EXCEPTION 'users already has rows; sample data is only for an empty database.';
  END IF;
END $$;

-- Users (placeholder hashes: these accounts cannot log in)
INSERT INTO users (username, password_hash, role) VALUES
  ('sample.doctor',  'SAMPLE-NOT-A-REAL-HASH', 'doctor'),
  ('sample.patient1','SAMPLE-NOT-A-REAL-HASH', 'patient'),
  ('sample.patient2','SAMPLE-NOT-A-REAL-HASH', 'patient'),
  ('sample.patient3','SAMPLE-NOT-A-REAL-HASH', 'patient');

INSERT INTO doctors (user_id, first_name, last_name, address, specialization,
                     hospital_affiliation, license_number, contact_number, email,
                     emergency_contact_name, emergency_contact_number, emergency_relation,
                     is_verified, date_of_birth)
SELECT user_id, 'Sample', 'Doctor', '123 Sample St, Sample City', 'Internal Medicine',
       'Sample General Hospital', 'SAMPLE-LIC-0001', '09000000000', 'sample.doctor@example.com',
       'Sample Contact', '09000000001', 'Sibling', true, DATE '1985-01-15'
FROM users WHERE username = 'sample.doctor';

-- Patients. The consent column is named hipaa_consent, or privacy_consent
-- once 02_optional_changes.sql has been applied; this handles both.
DO $$
DECLARE
  consent_col text;
BEGIN
  SELECT column_name INTO consent_col
  FROM information_schema.columns
  WHERE table_schema = 'public' AND table_name = 'patients'
    AND column_name IN ('privacy_consent', 'hipaa_consent');

  EXECUTE format($sql$
    INSERT INTO patients (user_id, first_name, last_name, date_of_birth, gender, address,
                          contact_number, email, emergency_contact_name,
                          emergency_contact_number, emergency_relation, %I, is_active)
    SELECT u.user_id, p.first_name, p.last_name, p.dob, p.gender, 'Sample Address',
           '09000000100', u.username || '@example.com', 'Sample Relative',
           '09000000101', 'Spouse', true, true
    FROM (VALUES
      ('sample.patient1', 'Ana',   'Sample',  DATE '1972-03-10', 'Female'),
      ('sample.patient2', 'Ben',   'Example', DATE '1965-07-22', 'Male'),
      ('sample.patient3', 'Carla', 'Test',    DATE '1990-11-05', 'Female')
    ) AS p(username, first_name, last_name, dob, gender)
    JOIN users u ON u.username = p.username
  $sql$, consent_col);
END $$;

-- Family history (fake)
INSERT INTO patient_family_history (patient_id, disease_domain, specific_diagnosis,
                                    relationship_tier, relationship_weight,
                                    onset_classification, onset_weight,
                                    age_at_diagnosis, shared_environment)
SELECT p.patient_id, f.domain, f.diagnosis, f.tier, f.tier_w, f.onset, f.onset_w, f.age, f.shared
FROM (VALUES
  ('sample.patient1', 'T2D',   'Type 2 diabetes mellitus', 'First-degree',  1.0, 'Late',  1.0, 55, true),
  ('sample.patient1', 'CVD',   'Hypertension',             'Second-degree', 0.5, 'Late',  1.0, 60, false),
  ('sample.patient2', 'CVD',   'Myocardial infarction',    'First-degree',  1.0, 'Early', 1.5, 48, true),
  ('sample.patient3', 'CRD',   'Asthma',                   'First-degree',  1.0, 'Early', 1.5, 12, true),
  ('sample.patient3', 'NEURO', 'Major depressive disorder','Second-degree', 0.5, 'Late',  1.0, 40, false)
) AS f(username, domain, diagnosis, tier, tier_w, onset, onset_w, age, shared)
JOIN users u ON u.username = f.username
JOIN patients p ON p.user_id = u.user_id;

-- Clinical metrics (fake; deliberately incomplete to exercise optional inputs)
INSERT INTO patient_t2d_metrics (patient_id, fpg, hba1c, bmi, waist_circumference,
                                 sbp, dbp, family_history_diabetes)
SELECT p.patient_id, 118, 6.1, 29.4, 94, 132, 84, 1
FROM patients p JOIN users u ON u.user_id = p.user_id
WHERE u.username = 'sample.patient1';

INSERT INTO patient_cvd_metrics (patient_id, age, biological_sex, sbp, dbp, bmi,
                                 total_cholesterol, hdl, ldl, smoking_history,
                                 family_history_premature_cvd)
SELECT p.patient_id, 61, 'Male', 145, 92, 27.8, 235, 38, 160, 30, 1
FROM patients p JOIN users u ON u.user_id = p.user_id
WHERE u.username = 'sample.patient2';

INSERT INTO patient_respiratory_metrics (patient_id, fev1, fvc, fev1_fvc_ratio, spo2,
                                         allergic_rhinitis, childhood_asthma, bmi)
SELECT p.patient_id, 2.6, 3.4, 76.5, 97.0, 1, 1, 22.1
FROM patients p JOIN users u ON u.user_id = p.user_id
WHERE u.username = 'sample.patient3';