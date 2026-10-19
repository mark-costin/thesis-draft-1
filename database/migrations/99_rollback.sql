-- =====================================================================
-- 99_rollback_migration.sql
-- Undo 01_migration.sql (v2 -> v1). Run 02 rollback by hand first if
-- you applied 02_optional_changes.sql.
--
-- WARNING: this DELETES everything stored in the new tables
-- (model_versions, risk_results, shap_explanations, documents) and the
-- new encounter_id links. Restoring from your pg_dump backup is usually
-- the better way back. Restoring NOT NULL and UNIQUE will FAIL if rows
-- saved after the migration contain NULLs or repeat screenings; that is
-- expected, and the whole rollback is cancelled if it happens.
--
--   psql -U <user> -d <database> -v ON_ERROR_STOP=1 -f 99_rollback_migration.sql
-- =====================================================================

BEGIN;
SET search_path = public;

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM schema_version WHERE version = 3) THEN
    RAISE EXCEPTION 'Version 3 (02_optional_changes.sql) is applied; undo it first.';
  END IF;
END $$;

-- 10
DROP TABLE schema_version;

-- 9
DROP INDEX IF EXISTS ix_cvd_metrics_patient_recorded, ix_t2d_metrics_patient_recorded,
  ix_neuro_metrics_patient_recorded, ix_resp_metrics_patient_recorded,
  ix_family_history_patient_id, ix_fhrs_patient_evaluated, ix_encounters_doctor_id;

-- 8 (keeps the filled-in values; only removes NOT NULL, defaults and the CHECK)
ALTER TABLE users
  DROP CONSTRAINT users_failed_attempts_check,
  ALTER COLUMN is_locked       DROP NOT NULL, ALTER COLUMN is_locked       DROP DEFAULT,
  ALTER COLUMN failed_attempts DROP NOT NULL, ALTER COLUMN failed_attempts DROP DEFAULT,
  ALTER COLUMN token_version   DROP NOT NULL, ALTER COLUMN token_version   DROP DEFAULT;
ALTER TABLE doctors  ALTER COLUMN is_verified DROP NOT NULL, ALTER COLUMN is_verified DROP DEFAULT;
ALTER TABLE admins   ALTER COLUMN is_verified DROP NOT NULL, ALTER COLUMN is_verified DROP DEFAULT;
ALTER TABLE patients ALTER COLUMN is_active   DROP NOT NULL, ALTER COLUMN is_active   DROP DEFAULT;

-- 7
ALTER TABLE doctors
  ALTER COLUMN created_at DROP DEFAULT, ALTER COLUMN updated_at DROP DEFAULT,
  ALTER COLUMN created_at TYPE timestamp USING created_at AT TIME ZONE 'UTC',
  ALTER COLUMN updated_at TYPE timestamp USING updated_at AT TIME ZONE 'UTC';
ALTER TABLE admins
  ALTER COLUMN created_at DROP DEFAULT, ALTER COLUMN updated_at DROP DEFAULT,
  ALTER COLUMN created_at TYPE timestamp USING created_at AT TIME ZONE 'UTC',
  ALTER COLUMN updated_at TYPE timestamp USING updated_at AT TIME ZONE 'UTC';
ALTER TABLE patient_clinical_vectors
  ALTER COLUMN updated_at DROP DEFAULT,
  ALTER COLUMN updated_at TYPE timestamp USING updated_at AT TIME ZONE 'UTC';

-- 6
ALTER TABLE patient_cvd_metrics          DROP COLUMN encounter_id;
ALTER TABLE patient_t2d_metrics          DROP COLUMN encounter_id;
ALTER TABLE patient_neuro_mental_metrics DROP COLUMN encounter_id;
ALTER TABLE patient_respiratory_metrics  DROP COLUMN encounter_id;
ALTER TABLE patient_fhrs_stratification  DROP COLUMN encounter_id;

-- 5 and 4
DROP TABLE documents;
DROP TABLE shap_explanations;
DROP TABLE risk_results;
DROP TABLE model_versions;

-- 3 (restore every foreign key exactly as it was before the migration)
DO $$
DECLARE
  fk record;
BEGIN
  FOR fk IN SELECT table_name, constraint_name, original_def FROM migration_v2_fk_changes LOOP
    EXECUTE format('ALTER TABLE %s DROP CONSTRAINT %I, ADD CONSTRAINT %I %s',
                   fk.table_name, fk.constraint_name, fk.constraint_name, fk.original_def);
  END LOOP;
END $$;
DROP TABLE migration_v2_fk_changes;

-- 2
ALTER TABLE patient_t2d_metrics
  ALTER COLUMN fpg SET NOT NULL, ALTER COLUMN postprandial_glucose_2h SET NOT NULL,
  ALTER COLUMN hba1c SET NOT NULL, ALTER COLUMN fasting_insulin SET NOT NULL,
  ALTER COLUMN c_peptide SET NOT NULL, ALTER COLUMN homa_ir SET NOT NULL,
  ALTER COLUMN bmi SET NOT NULL, ALTER COLUMN waist_circumference SET NOT NULL,
  ALTER COLUMN whr SET NOT NULL, ALTER COLUMN sbp SET NOT NULL, ALTER COLUMN dbp SET NOT NULL,
  ALTER COLUMN triglycerides SET NOT NULL, ALTER COLUMN hdl SET NOT NULL,
  ALTER COLUMN uacr SET NOT NULL, ALTER COLUMN serum_uric_acid SET NOT NULL,
  ALTER COLUMN gestational_diabetes SET NOT NULL, ALTER COLUMN family_history_diabetes SET NOT NULL,
  ALTER COLUMN acanthosis_nigricans SET NOT NULL, ALTER COLUMN daily_carbs SET NOT NULL,
  ALTER COLUMN sedentary_duration SET NOT NULL;
ALTER TABLE patient_neuro_mental_metrics
  ALTER COLUMN phq9 SET NOT NULL, ALTER COLUMN gad7 SET NOT NULL, ALTER COLUMN mmse SET NOT NULL,
  ALTER COLUMN moca SET NOT NULL, ALTER COLUMN ham_d SET NOT NULL, ALTER COLUMN updrs_part3 SET NOT NULL,
  ALTER COLUMN daily_sleep SET NOT NULL, ALTER COLUMN psqi SET NOT NULL,
  ALTER COLUMN seizure_frequency SET NOT NULL, ALTER COLUMN hrv_sdnn SET NOT NULL,
  ALTER COLUMN serum_cortisol SET NOT NULL, ALTER COLUMN vitamin_b12 SET NOT NULL,
  ALTER COLUMN serum_folate SET NOT NULL, ALTER COLUMN tsh SET NOT NULL,
  ALTER COLUMN faq_score SET NOT NULL, ALTER COLUMN tremor_rating SET NOT NULL,
  ALTER COLUMN tbi_history SET NOT NULL, ALTER COLUMN substance_abuse SET NOT NULL,
  ALTER COLUMN family_history_neuro_psych SET NOT NULL, ALTER COLUMN age SET NOT NULL;
ALTER TABLE patient_respiratory_metrics
  ALTER COLUMN fev1 SET NOT NULL, ALTER COLUMN fvc SET NOT NULL, ALTER COLUMN fev1_fvc_ratio SET NOT NULL,
  ALTER COLUMN post_bd_fev1_pred SET NOT NULL, ALTER COLUMN pef SET NOT NULL,
  ALTER COLUMN eosinophil_count SET NOT NULL, ALTER COLUMN feno SET NOT NULL,
  ALTER COLUMN spo2 SET NOT NULL, ALTER COLUMN pao2 SET NOT NULL, ALTER COLUMN paco2 SET NOT NULL,
  ALTER COLUMN mmrc_score SET NOT NULL, ALTER COLUMN act_score SET NOT NULL,
  ALTER COLUMN cat_score SET NOT NULL, ALTER COLUMN serum_ige SET NOT NULL,
  ALTER COLUMN annual_exacerbations SET NOT NULL, ALTER COLUMN tobacco_exposure SET NOT NULL,
  ALTER COLUMN occupational_dust SET NOT NULL, ALTER COLUMN allergic_rhinitis SET NOT NULL,
  ALTER COLUMN childhood_asthma SET NOT NULL, ALTER COLUMN bmi SET NOT NULL;

-- 1
ALTER TABLE patient_t2d_metrics
  ADD CONSTRAINT patient_t2d_metrics_patient_id_key UNIQUE (patient_id);
ALTER TABLE patient_neuro_mental_metrics
  ADD CONSTRAINT patient_neuro_mental_metrics_patient_id_key UNIQUE (patient_id);
ALTER TABLE patient_respiratory_metrics
  ADD CONSTRAINT patient_respiratory_metrics_patient_id_key UNIQUE (patient_id);

COMMIT;

-- Rolled back to schema v1.