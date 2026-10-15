-- AI <-> database part 2: what the FHRS formula and the feature pipeline need. 2026-10-15.
--
--   patient_family_history.is_verified   S_i in the FHRS formula (verified 1.0, unverified 0.5).
--                                          Existing rows start unverified, as the dictionary says
--                                          for family reports without records.
--   patients.biological_sex               used by all four models (Female 0, Male 1, CDSS dictionary).
--   patient_environmental_hazards         e_j hazards from the fixed list in cdss_spec.json.
--
-- Run this BEFORE starting the updated backend: the new code reads these columns, and
-- db.create_all() never adds columns to an existing table.
-- Safe to rerun (IF NOT EXISTS / DROP IF EXISTS), all in one transaction.
--
-- Run:  psql -h localhost -U postgres -d postgres -v ON_ERROR_STOP=1 -f database/migrations/2026-10-15_fhrs_part2.sql

BEGIN;

ALTER TABLE patient_family_history ADD COLUMN IF NOT EXISTS is_verified boolean NOT NULL DEFAULT false;

ALTER TABLE patients ADD COLUMN IF NOT EXISTS biological_sex varchar(10);
ALTER TABLE patients DROP CONSTRAINT IF EXISTS patients_biological_sex_check;
ALTER TABLE patients ADD CONSTRAINT patients_biological_sex_check CHECK (biological_sex IN ('Female', 'Male'));

CREATE TABLE IF NOT EXISTS patient_environmental_hazards (
    id serial PRIMARY KEY,
    patient_id integer NOT NULL REFERENCES patients (patient_id) ON DELETE CASCADE,
    disease_domain varchar(10) NOT NULL,
    hazard_code varchar(50) NOT NULL,
    recorded_at timestamp with time zone DEFAULT now(),
    CONSTRAINT patient_environmental_hazards_unique UNIQUE (patient_id, disease_domain, hazard_code)
);
CREATE INDEX IF NOT EXISTS ix_patient_environmental_hazards_patient_id ON patient_environmental_hazards (patient_id);

COMMIT;
