-- Clinical range CHECKs for the four biomarker tables, from CDSS_Data_Dictionary.pdf
-- (Parameter Ingestion Tables) via backend/biomarker_ranges.py. 2026-10-15.
--
-- Why: the T2D, respiratory and neuro tables were created by an older SQL script with
-- these limits, except neuro age, which stopped at 90 (the dictionary says 100). The CVD
-- table had no limits at all. db.create_all() never changes an existing table, so this
-- file brings the live tables in line with the models.
--
-- Safe to rerun: every constraint is dropped (if present) and re-added inside one
-- transaction. If an existing row breaks a limit, PostgreSQL stops with
-- 'check constraint ... is violated by some row' and nothing is changed.
--
-- Run:  psql -h localhost -U postgres -d postgres -v ON_ERROR_STOP=1 -f database/migrations/2026-10-15_biomarker_ranges.sql

BEGIN;

-- patient_cvd_metrics
ALTER TABLE patient_cvd_metrics DROP CONSTRAINT IF EXISTS patient_cvd_metrics_age_check;
ALTER TABLE patient_cvd_metrics ADD CONSTRAINT patient_cvd_metrics_age_check CHECK (age >= 18 AND age <= 100);
ALTER TABLE patient_cvd_metrics DROP CONSTRAINT IF EXISTS patient_cvd_metrics_sbp_check;
ALTER TABLE patient_cvd_metrics ADD CONSTRAINT patient_cvd_metrics_sbp_check CHECK (sbp >= 70 AND sbp <= 220);
ALTER TABLE patient_cvd_metrics DROP CONSTRAINT IF EXISTS patient_cvd_metrics_dbp_check;
ALTER TABLE patient_cvd_metrics ADD CONSTRAINT patient_cvd_metrics_dbp_check CHECK (dbp >= 40 AND dbp <= 130);
ALTER TABLE patient_cvd_metrics DROP CONSTRAINT IF EXISTS patient_cvd_metrics_resting_hr_check;
ALTER TABLE patient_cvd_metrics ADD CONSTRAINT patient_cvd_metrics_resting_hr_check CHECK (resting_hr >= 40 AND resting_hr <= 180);
ALTER TABLE patient_cvd_metrics DROP CONSTRAINT IF EXISTS patient_cvd_metrics_bmi_check;
ALTER TABLE patient_cvd_metrics ADD CONSTRAINT patient_cvd_metrics_bmi_check CHECK (bmi >= 12.0 AND bmi <= 60.0);
ALTER TABLE patient_cvd_metrics DROP CONSTRAINT IF EXISTS patient_cvd_metrics_total_cholesterol_check;
ALTER TABLE patient_cvd_metrics ADD CONSTRAINT patient_cvd_metrics_total_cholesterol_check CHECK (total_cholesterol >= 100 AND total_cholesterol <= 400);
ALTER TABLE patient_cvd_metrics DROP CONSTRAINT IF EXISTS patient_cvd_metrics_hdl_check;
ALTER TABLE patient_cvd_metrics ADD CONSTRAINT patient_cvd_metrics_hdl_check CHECK (hdl >= 15 AND hdl <= 120);
ALTER TABLE patient_cvd_metrics DROP CONSTRAINT IF EXISTS patient_cvd_metrics_ldl_check;
ALTER TABLE patient_cvd_metrics ADD CONSTRAINT patient_cvd_metrics_ldl_check CHECK (ldl >= 30 AND ldl <= 300);
ALTER TABLE patient_cvd_metrics DROP CONSTRAINT IF EXISTS patient_cvd_metrics_triglycerides_check;
ALTER TABLE patient_cvd_metrics ADD CONSTRAINT patient_cvd_metrics_triglycerides_check CHECK (triglycerides >= 40 AND triglycerides <= 1000);
ALTER TABLE patient_cvd_metrics DROP CONSTRAINT IF EXISTS patient_cvd_metrics_hs_crp_check;
ALTER TABLE patient_cvd_metrics ADD CONSTRAINT patient_cvd_metrics_hs_crp_check CHECK (hs_crp >= 0.1 AND hs_crp <= 50.0);
ALTER TABLE patient_cvd_metrics DROP CONSTRAINT IF EXISTS patient_cvd_metrics_serum_creatinine_check;
ALTER TABLE patient_cvd_metrics ADD CONSTRAINT patient_cvd_metrics_serum_creatinine_check CHECK (serum_creatinine >= 0.4 AND serum_creatinine <= 10.0);
ALTER TABLE patient_cvd_metrics DROP CONSTRAINT IF EXISTS patient_cvd_metrics_egfr_check;
ALTER TABLE patient_cvd_metrics ADD CONSTRAINT patient_cvd_metrics_egfr_check CHECK (egfr >= 5 AND egfr <= 140);
ALTER TABLE patient_cvd_metrics DROP CONSTRAINT IF EXISTS patient_cvd_metrics_lvef_check;
ALTER TABLE patient_cvd_metrics ADD CONSTRAINT patient_cvd_metrics_lvef_check CHECK (lvef >= 15 AND lvef <= 75);
ALTER TABLE patient_cvd_metrics DROP CONSTRAINT IF EXISTS patient_cvd_metrics_ctni_check;
ALTER TABLE patient_cvd_metrics ADD CONSTRAINT patient_cvd_metrics_ctni_check CHECK (ctni >= 0.01 AND ctni <= 50.0);
ALTER TABLE patient_cvd_metrics DROP CONSTRAINT IF EXISTS patient_cvd_metrics_nt_probnp_check;
ALTER TABLE patient_cvd_metrics ADD CONSTRAINT patient_cvd_metrics_nt_probnp_check CHECK (nt_probnp >= 10 AND nt_probnp <= 35000);
ALTER TABLE patient_cvd_metrics DROP CONSTRAINT IF EXISTS patient_cvd_metrics_smoking_history_check;
ALTER TABLE patient_cvd_metrics ADD CONSTRAINT patient_cvd_metrics_smoking_history_check CHECK (smoking_history >= 0 AND smoking_history <= 120);
ALTER TABLE patient_cvd_metrics DROP CONSTRAINT IF EXISTS patient_cvd_metrics_daily_sodium_check;
ALTER TABLE patient_cvd_metrics ADD CONSTRAINT patient_cvd_metrics_daily_sodium_check CHECK (daily_sodium >= 500 AND daily_sodium <= 10000);
ALTER TABLE patient_cvd_metrics DROP CONSTRAINT IF EXISTS patient_cvd_metrics_family_history_premature_cvd_check;
ALTER TABLE patient_cvd_metrics ADD CONSTRAINT patient_cvd_metrics_family_history_premature_cvd_check CHECK (family_history_premature_cvd >= 0 AND family_history_premature_cvd <= 1);
ALTER TABLE patient_cvd_metrics DROP CONSTRAINT IF EXISTS patient_cvd_metrics_physical_activity_check;
ALTER TABLE patient_cvd_metrics ADD CONSTRAINT patient_cvd_metrics_physical_activity_check CHECK (physical_activity >= 0 AND physical_activity <= 1050);
ALTER TABLE patient_cvd_metrics DROP CONSTRAINT IF EXISTS patient_cvd_metrics_biological_sex_check;
ALTER TABLE patient_cvd_metrics ADD CONSTRAINT patient_cvd_metrics_biological_sex_check CHECK (biological_sex IN ('Female', 'Male'));

-- patient_t2d_metrics
ALTER TABLE patient_t2d_metrics DROP CONSTRAINT IF EXISTS patient_t2d_metrics_fpg_check;
ALTER TABLE patient_t2d_metrics ADD CONSTRAINT patient_t2d_metrics_fpg_check CHECK (fpg >= 50 AND fpg <= 450);
ALTER TABLE patient_t2d_metrics DROP CONSTRAINT IF EXISTS patient_t2d_metrics_postprandial_glucose_2h_check;
ALTER TABLE patient_t2d_metrics ADD CONSTRAINT patient_t2d_metrics_postprandial_glucose_2h_check CHECK (postprandial_glucose_2h >= 60 AND postprandial_glucose_2h <= 600);
ALTER TABLE patient_t2d_metrics DROP CONSTRAINT IF EXISTS patient_t2d_metrics_hba1c_check;
ALTER TABLE patient_t2d_metrics ADD CONSTRAINT patient_t2d_metrics_hba1c_check CHECK (hba1c >= 4.0 AND hba1c <= 15.0);
ALTER TABLE patient_t2d_metrics DROP CONSTRAINT IF EXISTS patient_t2d_metrics_fasting_insulin_check;
ALTER TABLE patient_t2d_metrics ADD CONSTRAINT patient_t2d_metrics_fasting_insulin_check CHECK (fasting_insulin >= 1.0 AND fasting_insulin <= 100.0);
ALTER TABLE patient_t2d_metrics DROP CONSTRAINT IF EXISTS patient_t2d_metrics_c_peptide_check;
ALTER TABLE patient_t2d_metrics ADD CONSTRAINT patient_t2d_metrics_c_peptide_check CHECK (c_peptide >= 0.1 AND c_peptide <= 12.0);
ALTER TABLE patient_t2d_metrics DROP CONSTRAINT IF EXISTS patient_t2d_metrics_homa_ir_check;
ALTER TABLE patient_t2d_metrics ADD CONSTRAINT patient_t2d_metrics_homa_ir_check CHECK (homa_ir >= 0.2 AND homa_ir <= 25.0);
ALTER TABLE patient_t2d_metrics DROP CONSTRAINT IF EXISTS patient_t2d_metrics_bmi_check;
ALTER TABLE patient_t2d_metrics ADD CONSTRAINT patient_t2d_metrics_bmi_check CHECK (bmi >= 12.0 AND bmi <= 60.0);
ALTER TABLE patient_t2d_metrics DROP CONSTRAINT IF EXISTS patient_t2d_metrics_waist_circumference_check;
ALTER TABLE patient_t2d_metrics ADD CONSTRAINT patient_t2d_metrics_waist_circumference_check CHECK (waist_circumference >= 50 AND waist_circumference <= 160);
ALTER TABLE patient_t2d_metrics DROP CONSTRAINT IF EXISTS patient_t2d_metrics_whr_check;
ALTER TABLE patient_t2d_metrics ADD CONSTRAINT patient_t2d_metrics_whr_check CHECK (whr >= 0.6 AND whr <= 1.4);
ALTER TABLE patient_t2d_metrics DROP CONSTRAINT IF EXISTS patient_t2d_metrics_sbp_check;
ALTER TABLE patient_t2d_metrics ADD CONSTRAINT patient_t2d_metrics_sbp_check CHECK (sbp >= 70 AND sbp <= 220);
ALTER TABLE patient_t2d_metrics DROP CONSTRAINT IF EXISTS patient_t2d_metrics_dbp_check;
ALTER TABLE patient_t2d_metrics ADD CONSTRAINT patient_t2d_metrics_dbp_check CHECK (dbp >= 40 AND dbp <= 130);
ALTER TABLE patient_t2d_metrics DROP CONSTRAINT IF EXISTS patient_t2d_metrics_triglycerides_check;
ALTER TABLE patient_t2d_metrics ADD CONSTRAINT patient_t2d_metrics_triglycerides_check CHECK (triglycerides >= 40 AND triglycerides <= 1000);
ALTER TABLE patient_t2d_metrics DROP CONSTRAINT IF EXISTS patient_t2d_metrics_hdl_check;
ALTER TABLE patient_t2d_metrics ADD CONSTRAINT patient_t2d_metrics_hdl_check CHECK (hdl >= 15 AND hdl <= 120);
ALTER TABLE patient_t2d_metrics DROP CONSTRAINT IF EXISTS patient_t2d_metrics_uacr_check;
ALTER TABLE patient_t2d_metrics ADD CONSTRAINT patient_t2d_metrics_uacr_check CHECK (uacr >= 1 AND uacr <= 3500);
ALTER TABLE patient_t2d_metrics DROP CONSTRAINT IF EXISTS patient_t2d_metrics_serum_uric_acid_check;
ALTER TABLE patient_t2d_metrics ADD CONSTRAINT patient_t2d_metrics_serum_uric_acid_check CHECK (serum_uric_acid >= 1.5 AND serum_uric_acid <= 14.0);
ALTER TABLE patient_t2d_metrics DROP CONSTRAINT IF EXISTS patient_t2d_metrics_gestational_diabetes_check;
ALTER TABLE patient_t2d_metrics ADD CONSTRAINT patient_t2d_metrics_gestational_diabetes_check CHECK (gestational_diabetes >= 0 AND gestational_diabetes <= 1);
ALTER TABLE patient_t2d_metrics DROP CONSTRAINT IF EXISTS patient_t2d_metrics_family_history_diabetes_check;
ALTER TABLE patient_t2d_metrics ADD CONSTRAINT patient_t2d_metrics_family_history_diabetes_check CHECK (family_history_diabetes >= 0 AND family_history_diabetes <= 1);
ALTER TABLE patient_t2d_metrics DROP CONSTRAINT IF EXISTS patient_t2d_metrics_acanthosis_nigricans_check;
ALTER TABLE patient_t2d_metrics ADD CONSTRAINT patient_t2d_metrics_acanthosis_nigricans_check CHECK (acanthosis_nigricans >= 0 AND acanthosis_nigricans <= 1);
ALTER TABLE patient_t2d_metrics DROP CONSTRAINT IF EXISTS patient_t2d_metrics_daily_carbs_check;
ALTER TABLE patient_t2d_metrics ADD CONSTRAINT patient_t2d_metrics_daily_carbs_check CHECK (daily_carbs >= 50 AND daily_carbs <= 600);
ALTER TABLE patient_t2d_metrics DROP CONSTRAINT IF EXISTS patient_t2d_metrics_sedentary_duration_check;
ALTER TABLE patient_t2d_metrics ADD CONSTRAINT patient_t2d_metrics_sedentary_duration_check CHECK (sedentary_duration >= 1.0 AND sedentary_duration <= 18.0);

-- patient_respiratory_metrics
ALTER TABLE patient_respiratory_metrics DROP CONSTRAINT IF EXISTS patient_respiratory_metrics_fev1_check;
ALTER TABLE patient_respiratory_metrics ADD CONSTRAINT patient_respiratory_metrics_fev1_check CHECK (fev1 >= 0.5 AND fev1 <= 5.5);
ALTER TABLE patient_respiratory_metrics DROP CONSTRAINT IF EXISTS patient_respiratory_metrics_fvc_check;
ALTER TABLE patient_respiratory_metrics ADD CONSTRAINT patient_respiratory_metrics_fvc_check CHECK (fvc >= 1.0 AND fvc <= 7.0);
ALTER TABLE patient_respiratory_metrics DROP CONSTRAINT IF EXISTS patient_respiratory_metrics_fev1_fvc_ratio_check;
ALTER TABLE patient_respiratory_metrics ADD CONSTRAINT patient_respiratory_metrics_fev1_fvc_ratio_check CHECK (fev1_fvc_ratio >= 25.0 AND fev1_fvc_ratio <= 95.0);
ALTER TABLE patient_respiratory_metrics DROP CONSTRAINT IF EXISTS patient_respiratory_metrics_post_bd_fev1_pred_check;
ALTER TABLE patient_respiratory_metrics ADD CONSTRAINT patient_respiratory_metrics_post_bd_fev1_pred_check CHECK (post_bd_fev1_pred >= 15.0 AND post_bd_fev1_pred <= 120.0);
ALTER TABLE patient_respiratory_metrics DROP CONSTRAINT IF EXISTS patient_respiratory_metrics_pef_check;
ALTER TABLE patient_respiratory_metrics ADD CONSTRAINT patient_respiratory_metrics_pef_check CHECK (pef >= 50 AND pef <= 800);
ALTER TABLE patient_respiratory_metrics DROP CONSTRAINT IF EXISTS patient_respiratory_metrics_eosinophil_count_check;
ALTER TABLE patient_respiratory_metrics ADD CONSTRAINT patient_respiratory_metrics_eosinophil_count_check CHECK (eosinophil_count >= 0 AND eosinophil_count <= 2500);
ALTER TABLE patient_respiratory_metrics DROP CONSTRAINT IF EXISTS patient_respiratory_metrics_feno_check;
ALTER TABLE patient_respiratory_metrics ADD CONSTRAINT patient_respiratory_metrics_feno_check CHECK (feno >= 5 AND feno <= 150);
ALTER TABLE patient_respiratory_metrics DROP CONSTRAINT IF EXISTS patient_respiratory_metrics_spo2_check;
ALTER TABLE patient_respiratory_metrics ADD CONSTRAINT patient_respiratory_metrics_spo2_check CHECK (spo2 >= 65.0 AND spo2 <= 100.0);
ALTER TABLE patient_respiratory_metrics DROP CONSTRAINT IF EXISTS patient_respiratory_metrics_pao2_check;
ALTER TABLE patient_respiratory_metrics ADD CONSTRAINT patient_respiratory_metrics_pao2_check CHECK (pao2 >= 40 AND pao2 <= 110);
ALTER TABLE patient_respiratory_metrics DROP CONSTRAINT IF EXISTS patient_respiratory_metrics_paco2_check;
ALTER TABLE patient_respiratory_metrics ADD CONSTRAINT patient_respiratory_metrics_paco2_check CHECK (paco2 >= 25 AND paco2 <= 90);
ALTER TABLE patient_respiratory_metrics DROP CONSTRAINT IF EXISTS patient_respiratory_metrics_mmrc_score_check;
ALTER TABLE patient_respiratory_metrics ADD CONSTRAINT patient_respiratory_metrics_mmrc_score_check CHECK (mmrc_score >= 0 AND mmrc_score <= 4);
ALTER TABLE patient_respiratory_metrics DROP CONSTRAINT IF EXISTS patient_respiratory_metrics_act_score_check;
ALTER TABLE patient_respiratory_metrics ADD CONSTRAINT patient_respiratory_metrics_act_score_check CHECK (act_score >= 5 AND act_score <= 25);
ALTER TABLE patient_respiratory_metrics DROP CONSTRAINT IF EXISTS patient_respiratory_metrics_cat_score_check;
ALTER TABLE patient_respiratory_metrics ADD CONSTRAINT patient_respiratory_metrics_cat_score_check CHECK (cat_score >= 0 AND cat_score <= 40);
ALTER TABLE patient_respiratory_metrics DROP CONSTRAINT IF EXISTS patient_respiratory_metrics_serum_ige_check;
ALTER TABLE patient_respiratory_metrics ADD CONSTRAINT patient_respiratory_metrics_serum_ige_check CHECK (serum_ige >= 2 AND serum_ige <= 3000);
ALTER TABLE patient_respiratory_metrics DROP CONSTRAINT IF EXISTS patient_respiratory_metrics_annual_exacerbations_check;
ALTER TABLE patient_respiratory_metrics ADD CONSTRAINT patient_respiratory_metrics_annual_exacerbations_check CHECK (annual_exacerbations >= 0 AND annual_exacerbations <= 15);
ALTER TABLE patient_respiratory_metrics DROP CONSTRAINT IF EXISTS patient_respiratory_metrics_tobacco_exposure_check;
ALTER TABLE patient_respiratory_metrics ADD CONSTRAINT patient_respiratory_metrics_tobacco_exposure_check CHECK (tobacco_exposure >= 0 AND tobacco_exposure <= 120);
ALTER TABLE patient_respiratory_metrics DROP CONSTRAINT IF EXISTS patient_respiratory_metrics_occupational_dust_check;
ALTER TABLE patient_respiratory_metrics ADD CONSTRAINT patient_respiratory_metrics_occupational_dust_check CHECK (occupational_dust >= 0 AND occupational_dust <= 1);
ALTER TABLE patient_respiratory_metrics DROP CONSTRAINT IF EXISTS patient_respiratory_metrics_allergic_rhinitis_check;
ALTER TABLE patient_respiratory_metrics ADD CONSTRAINT patient_respiratory_metrics_allergic_rhinitis_check CHECK (allergic_rhinitis >= 0 AND allergic_rhinitis <= 1);
ALTER TABLE patient_respiratory_metrics DROP CONSTRAINT IF EXISTS patient_respiratory_metrics_childhood_asthma_check;
ALTER TABLE patient_respiratory_metrics ADD CONSTRAINT patient_respiratory_metrics_childhood_asthma_check CHECK (childhood_asthma >= 0 AND childhood_asthma <= 1);
ALTER TABLE patient_respiratory_metrics DROP CONSTRAINT IF EXISTS patient_respiratory_metrics_bmi_check;
ALTER TABLE patient_respiratory_metrics ADD CONSTRAINT patient_respiratory_metrics_bmi_check CHECK (bmi >= 12.0 AND bmi <= 60.0);

-- patient_neuro_mental_metrics
ALTER TABLE patient_neuro_mental_metrics DROP CONSTRAINT IF EXISTS patient_neuro_mental_metrics_phq9_check;
ALTER TABLE patient_neuro_mental_metrics ADD CONSTRAINT patient_neuro_mental_metrics_phq9_check CHECK (phq9 >= 0 AND phq9 <= 27);
ALTER TABLE patient_neuro_mental_metrics DROP CONSTRAINT IF EXISTS patient_neuro_mental_metrics_gad7_check;
ALTER TABLE patient_neuro_mental_metrics ADD CONSTRAINT patient_neuro_mental_metrics_gad7_check CHECK (gad7 >= 0 AND gad7 <= 21);
ALTER TABLE patient_neuro_mental_metrics DROP CONSTRAINT IF EXISTS patient_neuro_mental_metrics_mmse_check;
ALTER TABLE patient_neuro_mental_metrics ADD CONSTRAINT patient_neuro_mental_metrics_mmse_check CHECK (mmse >= 0 AND mmse <= 30);
ALTER TABLE patient_neuro_mental_metrics DROP CONSTRAINT IF EXISTS patient_neuro_mental_metrics_moca_check;
ALTER TABLE patient_neuro_mental_metrics ADD CONSTRAINT patient_neuro_mental_metrics_moca_check CHECK (moca >= 0 AND moca <= 30);
ALTER TABLE patient_neuro_mental_metrics DROP CONSTRAINT IF EXISTS patient_neuro_mental_metrics_ham_d_check;
ALTER TABLE patient_neuro_mental_metrics ADD CONSTRAINT patient_neuro_mental_metrics_ham_d_check CHECK (ham_d >= 0 AND ham_d <= 52);
ALTER TABLE patient_neuro_mental_metrics DROP CONSTRAINT IF EXISTS patient_neuro_mental_metrics_updrs_part3_check;
ALTER TABLE patient_neuro_mental_metrics ADD CONSTRAINT patient_neuro_mental_metrics_updrs_part3_check CHECK (updrs_part3 >= 0 AND updrs_part3 <= 132);
ALTER TABLE patient_neuro_mental_metrics DROP CONSTRAINT IF EXISTS patient_neuro_mental_metrics_daily_sleep_check;
ALTER TABLE patient_neuro_mental_metrics ADD CONSTRAINT patient_neuro_mental_metrics_daily_sleep_check CHECK (daily_sleep >= 1.0 AND daily_sleep <= 16.0);
ALTER TABLE patient_neuro_mental_metrics DROP CONSTRAINT IF EXISTS patient_neuro_mental_metrics_psqi_check;
ALTER TABLE patient_neuro_mental_metrics ADD CONSTRAINT patient_neuro_mental_metrics_psqi_check CHECK (psqi >= 0 AND psqi <= 21);
ALTER TABLE patient_neuro_mental_metrics DROP CONSTRAINT IF EXISTS patient_neuro_mental_metrics_seizure_frequency_check;
ALTER TABLE patient_neuro_mental_metrics ADD CONSTRAINT patient_neuro_mental_metrics_seizure_frequency_check CHECK (seizure_frequency >= 0 AND seizure_frequency <= 100);
ALTER TABLE patient_neuro_mental_metrics DROP CONSTRAINT IF EXISTS patient_neuro_mental_metrics_hrv_sdnn_check;
ALTER TABLE patient_neuro_mental_metrics ADD CONSTRAINT patient_neuro_mental_metrics_hrv_sdnn_check CHECK (hrv_sdnn >= 5.0 AND hrv_sdnn <= 250.0);
ALTER TABLE patient_neuro_mental_metrics DROP CONSTRAINT IF EXISTS patient_neuro_mental_metrics_serum_cortisol_check;
ALTER TABLE patient_neuro_mental_metrics ADD CONSTRAINT patient_neuro_mental_metrics_serum_cortisol_check CHECK (serum_cortisol >= 1.0 AND serum_cortisol <= 45.0);
ALTER TABLE patient_neuro_mental_metrics DROP CONSTRAINT IF EXISTS patient_neuro_mental_metrics_vitamin_b12_check;
ALTER TABLE patient_neuro_mental_metrics ADD CONSTRAINT patient_neuro_mental_metrics_vitamin_b12_check CHECK (vitamin_b12 >= 50 AND vitamin_b12 <= 2000);
ALTER TABLE patient_neuro_mental_metrics DROP CONSTRAINT IF EXISTS patient_neuro_mental_metrics_serum_folate_check;
ALTER TABLE patient_neuro_mental_metrics ADD CONSTRAINT patient_neuro_mental_metrics_serum_folate_check CHECK (serum_folate >= 1.0 AND serum_folate <= 25.0);
ALTER TABLE patient_neuro_mental_metrics DROP CONSTRAINT IF EXISTS patient_neuro_mental_metrics_tsh_check;
ALTER TABLE patient_neuro_mental_metrics ADD CONSTRAINT patient_neuro_mental_metrics_tsh_check CHECK (tsh >= 0.01 AND tsh <= 100.0);
ALTER TABLE patient_neuro_mental_metrics DROP CONSTRAINT IF EXISTS patient_neuro_mental_metrics_faq_score_check;
ALTER TABLE patient_neuro_mental_metrics ADD CONSTRAINT patient_neuro_mental_metrics_faq_score_check CHECK (faq_score >= 0 AND faq_score <= 30);
ALTER TABLE patient_neuro_mental_metrics DROP CONSTRAINT IF EXISTS patient_neuro_mental_metrics_tremor_rating_check;
ALTER TABLE patient_neuro_mental_metrics ADD CONSTRAINT patient_neuro_mental_metrics_tremor_rating_check CHECK (tremor_rating >= 0 AND tremor_rating <= 4);
ALTER TABLE patient_neuro_mental_metrics DROP CONSTRAINT IF EXISTS patient_neuro_mental_metrics_tbi_history_check;
ALTER TABLE patient_neuro_mental_metrics ADD CONSTRAINT patient_neuro_mental_metrics_tbi_history_check CHECK (tbi_history >= 0 AND tbi_history <= 1);
ALTER TABLE patient_neuro_mental_metrics DROP CONSTRAINT IF EXISTS patient_neuro_mental_metrics_substance_abuse_check;
ALTER TABLE patient_neuro_mental_metrics ADD CONSTRAINT patient_neuro_mental_metrics_substance_abuse_check CHECK (substance_abuse >= 0 AND substance_abuse <= 1);
ALTER TABLE patient_neuro_mental_metrics DROP CONSTRAINT IF EXISTS patient_neuro_mental_metrics_family_history_neuro_psych_check;
ALTER TABLE patient_neuro_mental_metrics ADD CONSTRAINT patient_neuro_mental_metrics_family_history_neuro_psych_check CHECK (family_history_neuro_psych >= 0 AND family_history_neuro_psych <= 1);
ALTER TABLE patient_neuro_mental_metrics DROP CONSTRAINT IF EXISTS patient_neuro_mental_metrics_age_check;
ALTER TABLE patient_neuro_mental_metrics ADD CONSTRAINT patient_neuro_mental_metrics_age_check CHECK (age >= 18 AND age <= 100);

COMMIT;
