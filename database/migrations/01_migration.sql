-- =====================================================================
-- 01_migration.sql
-- CDSS database: schema fixes, version 1 -> version 2
--
-- What it does (each section is numbered below):
--   1. Allows repeat screenings (drops one-row-per-patient limits)
--   2. Makes non-core clinical inputs optional ("fewer inputs")
--   3. Replaces ON DELETE CASCADE with RESTRICT (protects clinical
--      records and the hash-chained audit trail)
--   4. Adds model_versions, risk_results, shap_explanations
--   5. Adds documents (OCR uploads and verification)
--   6. Links metric rows and FHRS rows to the encounter that used them
--   7. Standardizes timestamps to timestamptz
--   8. Gives flags and counters proper defaults
--   9. Adds missing indexes on foreign keys
--  10. Records the schema version
--
-- What it does NOT do: it never deletes a row or a column. Changes that
-- need backend code edits are in 02_optional_changes.sql.
--
-- Run (whole file is one transaction; any error rolls everything back):
--   psql -U <user> -d <database> -v ON_ERROR_STOP=1 -f 01_migration.sql
-- =====================================================================

BEGIN;

SET search_path = public;
SET LOCAL lock_timeout = '10s';

-- Refuse to run twice.
DO $$
DECLARE
  already_applied boolean := false;
BEGIN
  IF to_regclass('public.schema_version') IS NOT NULL THEN
    EXECUTE 'SELECT EXISTS (SELECT 1 FROM public.schema_version WHERE version = 2)'
      INTO already_applied;
  END IF;
  IF already_applied THEN
    RAISE EXCEPTION 'Migration v2 has already been applied.';
  END IF;
END $$;


-- ---------------------------------------------------------------------
-- 1. Allow repeat screenings
--    These UNIQUE(patient_id) constraints meant a patient could only
--    ever have one T2D, neuro or respiratory record.
-- ---------------------------------------------------------------------
ALTER TABLE patient_t2d_metrics
  DROP CONSTRAINT IF EXISTS patient_t2d_metrics_patient_id_key;
ALTER TABLE patient_neuro_mental_metrics
  DROP CONSTRAINT IF EXISTS patient_neuro_mental_metrics_patient_id_key;
ALTER TABLE patient_respiratory_metrics
  DROP CONSTRAINT IF EXISTS patient_respiratory_metrics_patient_id_key;


-- ---------------------------------------------------------------------
-- 2. Make clinical inputs optional
--    XGBoost handles missing values natively, so a patient no longer
--    needs every test before screening. The CHECK range constraints
--    stay in place and still apply whenever a value is entered.
-- ---------------------------------------------------------------------
ALTER TABLE patient_t2d_metrics
  ALTER COLUMN fpg                     DROP NOT NULL,
  ALTER COLUMN postprandial_glucose_2h DROP NOT NULL,
  ALTER COLUMN hba1c                   DROP NOT NULL,
  ALTER COLUMN fasting_insulin         DROP NOT NULL,
  ALTER COLUMN c_peptide               DROP NOT NULL,
  ALTER COLUMN homa_ir                 DROP NOT NULL,
  ALTER COLUMN bmi                     DROP NOT NULL,
  ALTER COLUMN waist_circumference     DROP NOT NULL,
  ALTER COLUMN whr                     DROP NOT NULL,
  ALTER COLUMN sbp                     DROP NOT NULL,
  ALTER COLUMN dbp                     DROP NOT NULL,
  ALTER COLUMN triglycerides           DROP NOT NULL,
  ALTER COLUMN hdl                     DROP NOT NULL,
  ALTER COLUMN uacr                    DROP NOT NULL,
  ALTER COLUMN serum_uric_acid         DROP NOT NULL,
  ALTER COLUMN gestational_diabetes    DROP NOT NULL,
  ALTER COLUMN family_history_diabetes DROP NOT NULL,
  ALTER COLUMN acanthosis_nigricans    DROP NOT NULL,
  ALTER COLUMN daily_carbs             DROP NOT NULL,
  ALTER COLUMN sedentary_duration      DROP NOT NULL;

ALTER TABLE patient_neuro_mental_metrics
  ALTER COLUMN phq9                       DROP NOT NULL,
  ALTER COLUMN gad7                       DROP NOT NULL,
  ALTER COLUMN mmse                       DROP NOT NULL,
  ALTER COLUMN moca                       DROP NOT NULL,
  ALTER COLUMN ham_d                      DROP NOT NULL,
  ALTER COLUMN updrs_part3                DROP NOT NULL,
  ALTER COLUMN daily_sleep                DROP NOT NULL,
  ALTER COLUMN psqi                       DROP NOT NULL,
  ALTER COLUMN seizure_frequency          DROP NOT NULL,
  ALTER COLUMN hrv_sdnn                   DROP NOT NULL,
  ALTER COLUMN serum_cortisol             DROP NOT NULL,
  ALTER COLUMN vitamin_b12                DROP NOT NULL,
  ALTER COLUMN serum_folate               DROP NOT NULL,
  ALTER COLUMN tsh                        DROP NOT NULL,
  ALTER COLUMN faq_score                  DROP NOT NULL,
  ALTER COLUMN tremor_rating              DROP NOT NULL,
  ALTER COLUMN tbi_history                DROP NOT NULL,
  ALTER COLUMN substance_abuse            DROP NOT NULL,
  ALTER COLUMN family_history_neuro_psych DROP NOT NULL,
  ALTER COLUMN age                        DROP NOT NULL;

ALTER TABLE patient_respiratory_metrics
  ALTER COLUMN fev1                 DROP NOT NULL,
  ALTER COLUMN fvc                  DROP NOT NULL,
  ALTER COLUMN fev1_fvc_ratio       DROP NOT NULL,
  ALTER COLUMN post_bd_fev1_pred    DROP NOT NULL,
  ALTER COLUMN pef                  DROP NOT NULL,
  ALTER COLUMN eosinophil_count     DROP NOT NULL,
  ALTER COLUMN feno                 DROP NOT NULL,
  ALTER COLUMN spo2                 DROP NOT NULL,
  ALTER COLUMN pao2                 DROP NOT NULL,
  ALTER COLUMN paco2                DROP NOT NULL,
  ALTER COLUMN mmrc_score           DROP NOT NULL,
  ALTER COLUMN act_score            DROP NOT NULL,
  ALTER COLUMN cat_score            DROP NOT NULL,
  ALTER COLUMN serum_ige            DROP NOT NULL,
  ALTER COLUMN annual_exacerbations DROP NOT NULL,
  ALTER COLUMN tobacco_exposure     DROP NOT NULL,
  ALTER COLUMN occupational_dust    DROP NOT NULL,
  ALTER COLUMN allergic_rhinitis    DROP NOT NULL,
  ALTER COLUMN childhood_asthma     DROP NOT NULL,
  ALTER COLUMN bmi                  DROP NOT NULL;


-- ---------------------------------------------------------------------
-- 3. Replace ON DELETE CASCADE with ON DELETE RESTRICT
--    Deleting a user or patient used to silently wipe encounters,
--    family history and metrics, which defeats the hash chain.
--    Deactivate patients with patients.is_active = false instead.
--
--    This finds EVERY cascading foreign key that points at patients or
--    users, including tables added after schema.sql was exported
--    (e.g. consultations, queue_tickets, patient_environmental_hazards).
--    Each original definition is saved in migration_v2_fk_changes so
--    99_rollback_migration.sql can restore it exactly.
-- ---------------------------------------------------------------------
CREATE TABLE migration_v2_fk_changes (
    table_name      regclass NOT NULL,
    constraint_name name     NOT NULL,
    original_def    text     NOT NULL,
    PRIMARY KEY (table_name, constraint_name)
);

DO $$
DECLARE
  fk record;
  new_def text;
BEGIN
  FOR fk IN
    SELECT c.conrelid::regclass AS tbl, c.conname, pg_get_constraintdef(c.oid) AS def
    FROM pg_constraint c
    WHERE c.contype = 'f'
      AND c.confdeltype = 'c'
      AND c.confrelid IN ('public.patients'::regclass, 'public.users'::regclass)
  LOOP
    new_def := replace(fk.def, 'ON DELETE CASCADE', 'ON DELETE RESTRICT');
    INSERT INTO migration_v2_fk_changes VALUES (fk.tbl, fk.conname, fk.def);
    EXECUTE format('ALTER TABLE %s DROP CONSTRAINT %I, ADD CONSTRAINT %I %s',
                   fk.tbl, fk.conname, fk.conname, new_def);
    RAISE NOTICE 'RESTRICT: %.%', fk.tbl, fk.conname;
  END LOOP;
END $$;


-- ---------------------------------------------------------------------
-- 4. Model outputs as real tables
--    risk_results:      one row per disease per encounter (4 per screening)
--    shap_explanations: the feature contributions behind each result
--    model_versions:    which trained model produced the result
--    encounters.cdss_payload is kept, so existing code keeps working.
-- ---------------------------------------------------------------------
CREATE TABLE model_versions (
    model_version_id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    disease_domain   varchar(10)  NOT NULL
                     CHECK (disease_domain IN ('CVD', 'T2D', 'CRD', 'NEURO')),
    version          varchar(30)  NOT NULL,
    algorithm        varchar(50)  NOT NULL DEFAULT 'XGBoost',
    artifact_path    text         NOT NULL,
    artifact_sha256  char(64),
    feature_list     jsonb,
    metrics          jsonb,       -- e.g. {"auc": 0.87, "f1": 0.79}
    trained_at       timestamptz,
    is_active        boolean      NOT NULL DEFAULT false,
    created_at       timestamptz  NOT NULL DEFAULT now(),
    UNIQUE (disease_domain, version)
);
-- Only one active model per disease at a time.
CREATE UNIQUE INDEX ux_model_versions_one_active
    ON model_versions (disease_domain) WHERE is_active;

CREATE TABLE risk_results (
    result_id        integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    encounter_id     integer      NOT NULL
                     REFERENCES encounters(id) ON DELETE RESTRICT,
    model_version_id integer      NOT NULL
                     REFERENCES model_versions(model_version_id) ON DELETE RESTRICT,
    disease_domain   varchar(10)  NOT NULL
                     CHECK (disease_domain IN ('CVD', 'T2D', 'CRD', 'NEURO')),
    risk_probability numeric(5,4) NOT NULL
                     CHECK (risk_probability >= 0 AND risk_probability <= 1),
    risk_level       varchar(20)  NOT NULL
                     CHECK (risk_level IN ('Low', 'Moderate', 'High')),
    shap_base_value  numeric,
    created_at       timestamptz  NOT NULL DEFAULT now(),
    UNIQUE (encounter_id, disease_domain)
);

CREATE TABLE shap_explanations (
    explanation_id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    result_id      integer      NOT NULL
                   REFERENCES risk_results(result_id) ON DELETE CASCADE,
    feature_name   varchar(100) NOT NULL,
    feature_value  numeric,               -- NULL when the input was missing
    shap_value     numeric      NOT NULL,
    rank           smallint     NOT NULL CHECK (rank >= 1),
    UNIQUE (result_id, feature_name),
    UNIQUE (result_id, rank)
);

CREATE INDEX ix_risk_results_model_version  ON risk_results (model_version_id);
CREATE INDEX ix_risk_results_disease_level  ON risk_results (disease_domain, risk_level);

COMMENT ON TABLE model_versions    IS 'Trained XGBoost models; each risk result points to the model that produced it.';
COMMENT ON TABLE risk_results      IS 'Predicted risk per disease per encounter (four rows per screening).';
COMMENT ON TABLE shap_explanations IS 'SHAP feature contributions explaining each risk result, ranked by absolute impact.';


-- ---------------------------------------------------------------------
-- 5. OCR documents
--    OCR text is only used once a doctor has verified it.
-- ---------------------------------------------------------------------
CREATE TABLE documents (
    document_id    integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    patient_id     integer      NOT NULL
                   REFERENCES patients(patient_id) ON DELETE RESTRICT,
    encounter_id   integer
                   REFERENCES encounters(id) ON DELETE RESTRICT,
    uploaded_by    integer      NOT NULL
                   REFERENCES users(user_id) ON DELETE RESTRICT,
    document_type  varchar(50)  NOT NULL DEFAULT 'medical_record',
    file_path      text         NOT NULL,
    mime_type      varchar(100),
    file_sha256    char(64),
    ocr_engine     varchar(50),
    ocr_text       text,
    ocr_confidence numeric(5,2)
                   CHECK (ocr_confidence >= 0 AND ocr_confidence <= 100),
    status         varchar(20)  NOT NULL DEFAULT 'pending'
                   CHECK (status IN ('pending', 'verified', 'rejected')),
    verified_by    integer
                   REFERENCES users(user_id) ON DELETE RESTRICT,
    verified_at    timestamptz,
    uploaded_at    timestamptz  NOT NULL DEFAULT now(),
    -- A verified document must say who verified it and when.
    CHECK (status <> 'verified' OR (verified_by IS NOT NULL AND verified_at IS NOT NULL))
);

CREATE INDEX ix_documents_patient_id   ON documents (patient_id);
CREATE INDEX ix_documents_encounter_id ON documents (encounter_id);
CREATE INDEX ix_documents_status       ON documents (status);

COMMENT ON TABLE documents IS 'Uploaded medical records, their OCR output, and physician verification status.';


-- ---------------------------------------------------------------------
-- 6. Link inputs to the encounter that used them
--    Nullable, because existing rows cannot be matched reliably.
--    New screenings should always fill it.
-- ---------------------------------------------------------------------
ALTER TABLE patient_cvd_metrics
  ADD COLUMN encounter_id integer REFERENCES encounters(id) ON DELETE RESTRICT;
ALTER TABLE patient_t2d_metrics
  ADD COLUMN encounter_id integer REFERENCES encounters(id) ON DELETE RESTRICT;
ALTER TABLE patient_neuro_mental_metrics
  ADD COLUMN encounter_id integer REFERENCES encounters(id) ON DELETE RESTRICT;
ALTER TABLE patient_respiratory_metrics
  ADD COLUMN encounter_id integer REFERENCES encounters(id) ON DELETE RESTRICT;
ALTER TABLE patient_fhrs_stratification
  ADD COLUMN encounter_id integer REFERENCES encounters(id) ON DELETE RESTRICT;

CREATE INDEX ix_cvd_metrics_encounter_id   ON patient_cvd_metrics (encounter_id);
CREATE INDEX ix_t2d_metrics_encounter_id   ON patient_t2d_metrics (encounter_id);
CREATE INDEX ix_neuro_metrics_encounter_id ON patient_neuro_mental_metrics (encounter_id);
CREATE INDEX ix_resp_metrics_encounter_id  ON patient_respiratory_metrics (encounter_id);
CREATE INDEX ix_fhrs_encounter_id          ON patient_fhrs_stratification (encounter_id);


-- ---------------------------------------------------------------------
-- 7. Standardize timestamps to timestamptz
--    Existing naive values are treated as UTC. If preflight check 6
--    shows they were saved in Manila time, replace 'UTC' with
--    'Asia/Manila' in the four USING clauses below.
-- ---------------------------------------------------------------------
ALTER TABLE doctors
  ALTER COLUMN created_at TYPE timestamptz USING created_at AT TIME ZONE 'UTC',
  ALTER COLUMN updated_at TYPE timestamptz USING updated_at AT TIME ZONE 'UTC',
  ALTER COLUMN created_at SET DEFAULT now(),
  ALTER COLUMN updated_at SET DEFAULT now();

ALTER TABLE admins
  ALTER COLUMN created_at TYPE timestamptz USING created_at AT TIME ZONE 'UTC',
  ALTER COLUMN updated_at TYPE timestamptz USING updated_at AT TIME ZONE 'UTC',
  ALTER COLUMN created_at SET DEFAULT now(),
  ALTER COLUMN updated_at SET DEFAULT now();

ALTER TABLE patient_clinical_vectors
  ALTER COLUMN updated_at TYPE timestamptz USING updated_at AT TIME ZONE 'UTC',
  ALTER COLUMN updated_at SET DEFAULT now();


-- ---------------------------------------------------------------------
-- 8. Defaults for flags and counters
--    NULL here meant "unknown", which is not a valid security state.
-- ---------------------------------------------------------------------
UPDATE users SET is_locked       = false WHERE is_locked       IS NULL;
UPDATE users SET failed_attempts = 0     WHERE failed_attempts IS NULL;
UPDATE users SET token_version   = 0     WHERE token_version   IS NULL;

ALTER TABLE users
  ALTER COLUMN is_locked       SET DEFAULT false,
  ALTER COLUMN is_locked       SET NOT NULL,
  ALTER COLUMN failed_attempts SET DEFAULT 0,
  ALTER COLUMN failed_attempts SET NOT NULL,
  ALTER COLUMN token_version   SET DEFAULT 0,
  ALTER COLUMN token_version   SET NOT NULL,
  ADD CONSTRAINT users_failed_attempts_check CHECK (failed_attempts >= 0);

UPDATE doctors  SET is_verified = false WHERE is_verified IS NULL;
UPDATE admins   SET is_verified = false WHERE is_verified IS NULL;
UPDATE patients SET is_active   = true  WHERE is_active   IS NULL;

ALTER TABLE doctors  ALTER COLUMN is_verified SET DEFAULT false,
                     ALTER COLUMN is_verified SET NOT NULL;
ALTER TABLE admins   ALTER COLUMN is_verified SET DEFAULT false,
                     ALTER COLUMN is_verified SET NOT NULL;
ALTER TABLE patients ALTER COLUMN is_active   SET DEFAULT true,
                     ALTER COLUMN is_active   SET NOT NULL;


-- ---------------------------------------------------------------------
-- 9. Indexes on foreign keys
--    PostgreSQL does not create these automatically.
-- ---------------------------------------------------------------------
CREATE INDEX ix_cvd_metrics_patient_recorded   ON patient_cvd_metrics          (patient_id, recorded_at DESC);
CREATE INDEX ix_t2d_metrics_patient_recorded   ON patient_t2d_metrics          (patient_id, recorded_at DESC);
CREATE INDEX ix_neuro_metrics_patient_recorded ON patient_neuro_mental_metrics (patient_id, recorded_at DESC);
CREATE INDEX ix_resp_metrics_patient_recorded  ON patient_respiratory_metrics  (patient_id, recorded_at DESC);
CREATE INDEX ix_family_history_patient_id      ON patient_family_history       (patient_id);
CREATE INDEX ix_fhrs_patient_evaluated         ON patient_fhrs_stratification  (patient_id, evaluated_at DESC);
CREATE INDEX ix_encounters_doctor_id           ON encounters                   (doctor_id);


-- ---------------------------------------------------------------------
-- 10. Record the schema version
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS schema_version (
    version     integer     PRIMARY KEY,
    description text        NOT NULL,
    applied_at  timestamptz NOT NULL DEFAULT now()
);
INSERT INTO schema_version (version, description)
VALUES (2, 'Repeat screenings, optional inputs, RESTRICT deletes, risk/SHAP/model tables, OCR documents');

COMMIT;

-- Migration v2 applied successfully.