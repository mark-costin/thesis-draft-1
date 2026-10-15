--
-- PostgreSQL database dump
--

\restrict tMXzQSqEFubsRtTYquKr8ZxEbINybHIQKradCMkZ4sBf4tGu7Ozmmybxqumu9Ov

-- Dumped from database version 18.6
-- Dumped by pg_dump version 18.6

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: vector; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;


--
-- Name: EXTENSION vector; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION vector IS 'vector data type and ivfflat and hnsw access methods';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: admins; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.admins (
    admin_id integer NOT NULL,
    user_id integer NOT NULL,
    first_name character varying(100) NOT NULL,
    middle_name character varying(100),
    last_name character varying(100) NOT NULL,
    suffix character varying(20),
    address text NOT NULL,
    specialization character varying(100) NOT NULL,
    hospital_affiliation character varying(255),
    license_number character varying(50) NOT NULL,
    contact_number character varying(20) NOT NULL,
    email character varying(150) NOT NULL,
    emergency_contact_name character varying(150) NOT NULL,
    emergency_contact_number character varying(20) NOT NULL,
    emergency_relation character varying(50) NOT NULL,
    is_verified boolean,
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    date_of_birth date
);


--
-- Name: admins_admin_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.admins_admin_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: admins_admin_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.admins_admin_id_seq OWNED BY public.admins.admin_id;


--
-- Name: audit_ledger; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audit_ledger (
    id integer NOT NULL,
    audit_id character varying(64) NOT NULL,
    timestamp_utc timestamp with time zone NOT NULL,
    event_type character varying(64) NOT NULL,
    payload json NOT NULL,
    patient_id integer,
    doctor_id integer,
    actor_user_id integer,
    entry_seal character varying(64) NOT NULL
);


--
-- Name: audit_ledger_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.audit_ledger_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: audit_ledger_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.audit_ledger_id_seq OWNED BY public.audit_ledger.id;


--
-- Name: doctors; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.doctors (
    doctor_id integer NOT NULL,
    user_id integer NOT NULL,
    first_name character varying(100) NOT NULL,
    middle_name character varying(100),
    last_name character varying(100) NOT NULL,
    suffix character varying(20),
    address text NOT NULL,
    specialization character varying(100) NOT NULL,
    hospital_affiliation character varying(255),
    license_number character varying(50) NOT NULL,
    contact_number character varying(20) NOT NULL,
    email character varying(150) NOT NULL,
    emergency_contact_name character varying(150) NOT NULL,
    emergency_contact_number character varying(20) NOT NULL,
    emergency_relation character varying(50) NOT NULL,
    is_verified boolean,
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    date_of_birth date
);


--
-- Name: doctors_doctor_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.doctors_doctor_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: doctors_doctor_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.doctors_doctor_id_seq OWNED BY public.doctors.doctor_id;


--
-- Name: encounters; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.encounters (
    id integer NOT NULL,
    encounter_uid character varying(64) NOT NULL,
    patient_id integer NOT NULL,
    doctor_id integer NOT NULL,
    record_type character varying(32) NOT NULL,
    parent_baseline_hash character varying(64),
    cryptographic_hash character varying(64) NOT NULL,
    cdss_payload json NOT NULL,
    care_plan json NOT NULL,
    reanchor_decision character varying(16),
    created_at_utc timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: encounters_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.encounters_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: encounters_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.encounters_id_seq OWNED BY public.encounters.id;


--
-- Name: idempotency_cache; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.idempotency_cache (
    key character varying(255) NOT NULL,
    data json NOT NULL,
    status integer NOT NULL,
    "timestamp" double precision NOT NULL
);


--
-- Name: patient_clinical_vectors; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.patient_clinical_vectors (
    id integer NOT NULL,
    patient_id integer NOT NULL,
    disease_narrative text,
    embedding public.vector(384),
    updated_at timestamp without time zone
);


--
-- Name: patient_clinical_vectors_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.patient_clinical_vectors_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: patient_clinical_vectors_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.patient_clinical_vectors_id_seq OWNED BY public.patient_clinical_vectors.id;


--
-- Name: patient_cvd_metrics; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.patient_cvd_metrics (
    metric_id integer NOT NULL,
    patient_id integer NOT NULL,
    age numeric,
    biological_sex character varying(20),
    sbp numeric,
    dbp numeric,
    bmi numeric,
    resting_hr numeric,
    total_cholesterol numeric,
    hdl numeric,
    ldl numeric,
    triglycerides numeric,
    hs_crp numeric,
    serum_creatinine numeric,
    egfr numeric,
    lvef numeric,
    ctni numeric,
    nt_probnp numeric,
    smoking_history numeric,
    daily_sodium numeric,
    family_history_premature_cvd integer,
    physical_activity numeric,
    recorded_at timestamp with time zone DEFAULT now(),
    CONSTRAINT patient_cvd_metrics_age_check CHECK (((age >= (18)::numeric) AND (age <= (100)::numeric))),
    CONSTRAINT patient_cvd_metrics_biological_sex_check CHECK (((biological_sex)::text = ANY ((ARRAY['Female'::character varying, 'Male'::character varying])::text[]))),
    CONSTRAINT patient_cvd_metrics_bmi_check CHECK (((bmi >= 12.0) AND (bmi <= 60.0))),
    CONSTRAINT patient_cvd_metrics_ctni_check CHECK (((ctni >= 0.01) AND (ctni <= 50.0))),
    CONSTRAINT patient_cvd_metrics_daily_sodium_check CHECK (((daily_sodium >= (500)::numeric) AND (daily_sodium <= (10000)::numeric))),
    CONSTRAINT patient_cvd_metrics_dbp_check CHECK (((dbp >= (40)::numeric) AND (dbp <= (130)::numeric))),
    CONSTRAINT patient_cvd_metrics_egfr_check CHECK (((egfr >= (5)::numeric) AND (egfr <= (140)::numeric))),
    CONSTRAINT patient_cvd_metrics_family_history_premature_cvd_check CHECK (((family_history_premature_cvd >= 0) AND (family_history_premature_cvd <= 1))),
    CONSTRAINT patient_cvd_metrics_hdl_check CHECK (((hdl >= (15)::numeric) AND (hdl <= (120)::numeric))),
    CONSTRAINT patient_cvd_metrics_hs_crp_check CHECK (((hs_crp >= 0.1) AND (hs_crp <= 50.0))),
    CONSTRAINT patient_cvd_metrics_ldl_check CHECK (((ldl >= (30)::numeric) AND (ldl <= (300)::numeric))),
    CONSTRAINT patient_cvd_metrics_lvef_check CHECK (((lvef >= (15)::numeric) AND (lvef <= (75)::numeric))),
    CONSTRAINT patient_cvd_metrics_nt_probnp_check CHECK (((nt_probnp >= (10)::numeric) AND (nt_probnp <= (35000)::numeric))),
    CONSTRAINT patient_cvd_metrics_physical_activity_check CHECK (((physical_activity >= (0)::numeric) AND (physical_activity <= (1050)::numeric))),
    CONSTRAINT patient_cvd_metrics_resting_hr_check CHECK (((resting_hr >= (40)::numeric) AND (resting_hr <= (180)::numeric))),
    CONSTRAINT patient_cvd_metrics_sbp_check CHECK (((sbp >= (70)::numeric) AND (sbp <= (220)::numeric))),
    CONSTRAINT patient_cvd_metrics_serum_creatinine_check CHECK (((serum_creatinine >= 0.4) AND (serum_creatinine <= 10.0))),
    CONSTRAINT patient_cvd_metrics_smoking_history_check CHECK (((smoking_history >= (0)::numeric) AND (smoking_history <= (120)::numeric))),
    CONSTRAINT patient_cvd_metrics_total_cholesterol_check CHECK (((total_cholesterol >= (100)::numeric) AND (total_cholesterol <= (400)::numeric))),
    CONSTRAINT patient_cvd_metrics_triglycerides_check CHECK (((triglycerides >= (40)::numeric) AND (triglycerides <= (1000)::numeric)))
);


--
-- Name: patient_cvd_metrics_metric_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.patient_cvd_metrics_metric_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: patient_cvd_metrics_metric_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.patient_cvd_metrics_metric_id_seq OWNED BY public.patient_cvd_metrics.metric_id;


--
-- Name: patient_family_history; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.patient_family_history (
    record_id integer NOT NULL,
    patient_id integer NOT NULL,
    disease_domain character varying(100) NOT NULL,
    specific_diagnosis character varying(150) NOT NULL,
    relationship_tier character varying(50) NOT NULL,
    relationship_weight numeric NOT NULL,
    onset_classification character varying(50) NOT NULL,
    onset_weight numeric NOT NULL,
    age_at_diagnosis integer,
    shared_environment boolean,
    recorded_at timestamp with time zone DEFAULT now()
);


--
-- Name: patient_family_history_record_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.patient_family_history_record_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: patient_family_history_record_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.patient_family_history_record_id_seq OWNED BY public.patient_family_history.record_id;


--
-- Name: patient_fhrs_stratification; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.patient_fhrs_stratification (
    fhrs_id integer NOT NULL,
    patient_id integer NOT NULL,
    disease_domain character varying(100) NOT NULL,
    clustering_score numeric NOT NULL,
    environmental_modifier numeric NOT NULL,
    calculated_fhrs numeric NOT NULL,
    risk_code integer NOT NULL,
    risk_category character varying(50) NOT NULL,
    evaluated_at timestamp with time zone DEFAULT now()
);


--
-- Name: patient_fhrs_stratification_fhrs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.patient_fhrs_stratification_fhrs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: patient_fhrs_stratification_fhrs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.patient_fhrs_stratification_fhrs_id_seq OWNED BY public.patient_fhrs_stratification.fhrs_id;


--
-- Name: patient_neuro_mental_metrics; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.patient_neuro_mental_metrics (
    metric_id integer NOT NULL,
    patient_id integer NOT NULL,
    phq9 integer NOT NULL,
    gad7 integer NOT NULL,
    mmse integer NOT NULL,
    moca integer NOT NULL,
    ham_d integer NOT NULL,
    updrs_part3 integer NOT NULL,
    daily_sleep numeric(4,1) NOT NULL,
    psqi integer NOT NULL,
    seizure_frequency numeric(5,1) NOT NULL,
    hrv_sdnn numeric(5,1) NOT NULL,
    serum_cortisol numeric(4,1) NOT NULL,
    vitamin_b12 numeric(6,1) NOT NULL,
    serum_folate numeric(4,1) NOT NULL,
    tsh numeric(5,2) NOT NULL,
    faq_score integer NOT NULL,
    tremor_rating integer NOT NULL,
    tbi_history integer NOT NULL,
    substance_abuse integer NOT NULL,
    family_history_neuro_psych integer CONSTRAINT patient_neuro_mental_metric_family_history_neuro_psych_not_null NOT NULL,
    age numeric(4,1) NOT NULL,
    recorded_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT patient_neuro_mental_metrics_age_check CHECK (((age >= (18)::numeric) AND (age <= (100)::numeric))),
    CONSTRAINT patient_neuro_mental_metrics_daily_sleep_check CHECK (((daily_sleep >= 1.0) AND (daily_sleep <= 16.0))),
    CONSTRAINT patient_neuro_mental_metrics_family_history_neuro_psych_check CHECK (((family_history_neuro_psych >= 0) AND (family_history_neuro_psych <= 1))),
    CONSTRAINT patient_neuro_mental_metrics_faq_score_check CHECK (((faq_score >= 0) AND (faq_score <= 30))),
    CONSTRAINT patient_neuro_mental_metrics_gad7_check CHECK (((gad7 >= 0) AND (gad7 <= 21))),
    CONSTRAINT patient_neuro_mental_metrics_ham_d_check CHECK (((ham_d >= 0) AND (ham_d <= 52))),
    CONSTRAINT patient_neuro_mental_metrics_hrv_sdnn_check CHECK (((hrv_sdnn >= 5.0) AND (hrv_sdnn <= 250.0))),
    CONSTRAINT patient_neuro_mental_metrics_mmse_check CHECK (((mmse >= 0) AND (mmse <= 30))),
    CONSTRAINT patient_neuro_mental_metrics_moca_check CHECK (((moca >= 0) AND (moca <= 30))),
    CONSTRAINT patient_neuro_mental_metrics_phq9_check CHECK (((phq9 >= 0) AND (phq9 <= 27))),
    CONSTRAINT patient_neuro_mental_metrics_psqi_check CHECK (((psqi >= 0) AND (psqi <= 21))),
    CONSTRAINT patient_neuro_mental_metrics_seizure_frequency_check CHECK (((seizure_frequency >= (0)::numeric) AND (seizure_frequency <= (100)::numeric))),
    CONSTRAINT patient_neuro_mental_metrics_serum_cortisol_check CHECK (((serum_cortisol >= 1.0) AND (serum_cortisol <= 45.0))),
    CONSTRAINT patient_neuro_mental_metrics_serum_folate_check CHECK (((serum_folate >= 1.0) AND (serum_folate <= 25.0))),
    CONSTRAINT patient_neuro_mental_metrics_substance_abuse_check CHECK (((substance_abuse >= 0) AND (substance_abuse <= 1))),
    CONSTRAINT patient_neuro_mental_metrics_tbi_history_check CHECK (((tbi_history >= 0) AND (tbi_history <= 1))),
    CONSTRAINT patient_neuro_mental_metrics_tremor_rating_check CHECK (((tremor_rating >= 0) AND (tremor_rating <= 4))),
    CONSTRAINT patient_neuro_mental_metrics_tsh_check CHECK (((tsh >= 0.01) AND (tsh <= 100.0))),
    CONSTRAINT patient_neuro_mental_metrics_updrs_part3_check CHECK (((updrs_part3 >= 0) AND (updrs_part3 <= 132))),
    CONSTRAINT patient_neuro_mental_metrics_vitamin_b12_check CHECK (((vitamin_b12 >= (50)::numeric) AND (vitamin_b12 <= (2000)::numeric)))
);


--
-- Name: patient_neuro_mental_metrics_metric_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.patient_neuro_mental_metrics_metric_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: patient_neuro_mental_metrics_metric_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.patient_neuro_mental_metrics_metric_id_seq OWNED BY public.patient_neuro_mental_metrics.metric_id;


--
-- Name: patient_respiratory_metrics; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.patient_respiratory_metrics (
    metric_id integer NOT NULL,
    patient_id integer NOT NULL,
    fev1 numeric(3,1) NOT NULL,
    fvc numeric(3,1) NOT NULL,
    fev1_fvc_ratio numeric(4,1) NOT NULL,
    post_bd_fev1_pred numeric(5,1) NOT NULL,
    pef numeric(5,1) NOT NULL,
    eosinophil_count numeric(6,1) NOT NULL,
    feno numeric(5,1) NOT NULL,
    spo2 numeric(4,1) NOT NULL,
    pao2 numeric(5,1) NOT NULL,
    paco2 numeric(4,1) NOT NULL,
    mmrc_score integer NOT NULL,
    act_score integer NOT NULL,
    cat_score integer NOT NULL,
    serum_ige numeric(6,1) NOT NULL,
    annual_exacerbations integer NOT NULL,
    tobacco_exposure numeric(5,1) NOT NULL,
    occupational_dust integer NOT NULL,
    allergic_rhinitis integer NOT NULL,
    childhood_asthma integer NOT NULL,
    bmi numeric(4,1) NOT NULL,
    recorded_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT patient_respiratory_metrics_act_score_check CHECK (((act_score >= 5) AND (act_score <= 25))),
    CONSTRAINT patient_respiratory_metrics_allergic_rhinitis_check CHECK (((allergic_rhinitis >= 0) AND (allergic_rhinitis <= 1))),
    CONSTRAINT patient_respiratory_metrics_annual_exacerbations_check CHECK (((annual_exacerbations >= 0) AND (annual_exacerbations <= 15))),
    CONSTRAINT patient_respiratory_metrics_bmi_check CHECK (((bmi >= 12.0) AND (bmi <= 60.0))),
    CONSTRAINT patient_respiratory_metrics_cat_score_check CHECK (((cat_score >= 0) AND (cat_score <= 40))),
    CONSTRAINT patient_respiratory_metrics_childhood_asthma_check CHECK (((childhood_asthma >= 0) AND (childhood_asthma <= 1))),
    CONSTRAINT patient_respiratory_metrics_eosinophil_count_check CHECK (((eosinophil_count >= (0)::numeric) AND (eosinophil_count <= (2500)::numeric))),
    CONSTRAINT patient_respiratory_metrics_feno_check CHECK (((feno >= (5)::numeric) AND (feno <= (150)::numeric))),
    CONSTRAINT patient_respiratory_metrics_fev1_check CHECK (((fev1 >= 0.5) AND (fev1 <= 5.5))),
    CONSTRAINT patient_respiratory_metrics_fev1_fvc_ratio_check CHECK (((fev1_fvc_ratio >= 25.0) AND (fev1_fvc_ratio <= 95.0))),
    CONSTRAINT patient_respiratory_metrics_fvc_check CHECK (((fvc >= 1.0) AND (fvc <= 7.0))),
    CONSTRAINT patient_respiratory_metrics_mmrc_score_check CHECK (((mmrc_score >= 0) AND (mmrc_score <= 4))),
    CONSTRAINT patient_respiratory_metrics_occupational_dust_check CHECK (((occupational_dust >= 0) AND (occupational_dust <= 1))),
    CONSTRAINT patient_respiratory_metrics_paco2_check CHECK (((paco2 >= (25)::numeric) AND (paco2 <= (90)::numeric))),
    CONSTRAINT patient_respiratory_metrics_pao2_check CHECK (((pao2 >= (40)::numeric) AND (pao2 <= (110)::numeric))),
    CONSTRAINT patient_respiratory_metrics_pef_check CHECK (((pef >= (50)::numeric) AND (pef <= (800)::numeric))),
    CONSTRAINT patient_respiratory_metrics_post_bd_fev1_pred_check CHECK (((post_bd_fev1_pred >= 15.0) AND (post_bd_fev1_pred <= 120.0))),
    CONSTRAINT patient_respiratory_metrics_serum_ige_check CHECK (((serum_ige >= (2)::numeric) AND (serum_ige <= (3000)::numeric))),
    CONSTRAINT patient_respiratory_metrics_spo2_check CHECK (((spo2 >= 65.0) AND (spo2 <= 100.0))),
    CONSTRAINT patient_respiratory_metrics_tobacco_exposure_check CHECK (((tobacco_exposure >= (0)::numeric) AND (tobacco_exposure <= (120)::numeric)))
);


--
-- Name: patient_respiratory_metrics_metric_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.patient_respiratory_metrics_metric_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: patient_respiratory_metrics_metric_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.patient_respiratory_metrics_metric_id_seq OWNED BY public.patient_respiratory_metrics.metric_id;


--
-- Name: patient_t2d_metrics; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.patient_t2d_metrics (
    metric_id integer NOT NULL,
    patient_id integer NOT NULL,
    fpg numeric(5,1) NOT NULL,
    postprandial_glucose_2h numeric(5,1) NOT NULL,
    hba1c numeric(4,1) NOT NULL,
    fasting_insulin numeric(5,1) NOT NULL,
    c_peptide numeric(4,1) NOT NULL,
    homa_ir numeric(4,1) NOT NULL,
    bmi numeric(4,1) NOT NULL,
    waist_circumference numeric(5,1) NOT NULL,
    whr numeric(4,2) NOT NULL,
    sbp numeric(5,1) NOT NULL,
    dbp numeric(5,1) NOT NULL,
    triglycerides numeric(6,1) NOT NULL,
    hdl numeric(5,1) NOT NULL,
    uacr numeric(6,1) NOT NULL,
    serum_uric_acid numeric(4,1) NOT NULL,
    gestational_diabetes integer NOT NULL,
    family_history_diabetes integer NOT NULL,
    acanthosis_nigricans integer NOT NULL,
    daily_carbs numeric(5,1) NOT NULL,
    sedentary_duration numeric(4,1) NOT NULL,
    recorded_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT patient_t2d_metrics_acanthosis_nigricans_check CHECK (((acanthosis_nigricans >= 0) AND (acanthosis_nigricans <= 1))),
    CONSTRAINT patient_t2d_metrics_bmi_check CHECK (((bmi >= 12.0) AND (bmi <= 60.0))),
    CONSTRAINT patient_t2d_metrics_c_peptide_check CHECK (((c_peptide >= 0.1) AND (c_peptide <= 12.0))),
    CONSTRAINT patient_t2d_metrics_daily_carbs_check CHECK (((daily_carbs >= (50)::numeric) AND (daily_carbs <= (600)::numeric))),
    CONSTRAINT patient_t2d_metrics_dbp_check CHECK (((dbp >= (40)::numeric) AND (dbp <= (130)::numeric))),
    CONSTRAINT patient_t2d_metrics_family_history_diabetes_check CHECK (((family_history_diabetes >= 0) AND (family_history_diabetes <= 1))),
    CONSTRAINT patient_t2d_metrics_fasting_insulin_check CHECK (((fasting_insulin >= 1.0) AND (fasting_insulin <= 100.0))),
    CONSTRAINT patient_t2d_metrics_fpg_check CHECK (((fpg >= (50)::numeric) AND (fpg <= (450)::numeric))),
    CONSTRAINT patient_t2d_metrics_gestational_diabetes_check CHECK (((gestational_diabetes >= 0) AND (gestational_diabetes <= 1))),
    CONSTRAINT patient_t2d_metrics_hba1c_check CHECK (((hba1c >= 4.0) AND (hba1c <= 15.0))),
    CONSTRAINT patient_t2d_metrics_hdl_check CHECK (((hdl >= (15)::numeric) AND (hdl <= (120)::numeric))),
    CONSTRAINT patient_t2d_metrics_homa_ir_check CHECK (((homa_ir >= 0.2) AND (homa_ir <= 25.0))),
    CONSTRAINT patient_t2d_metrics_postprandial_glucose_2h_check CHECK (((postprandial_glucose_2h >= (60)::numeric) AND (postprandial_glucose_2h <= (600)::numeric))),
    CONSTRAINT patient_t2d_metrics_sbp_check CHECK (((sbp >= (70)::numeric) AND (sbp <= (220)::numeric))),
    CONSTRAINT patient_t2d_metrics_sedentary_duration_check CHECK (((sedentary_duration >= 1.0) AND (sedentary_duration <= 18.0))),
    CONSTRAINT patient_t2d_metrics_serum_uric_acid_check CHECK (((serum_uric_acid >= 1.5) AND (serum_uric_acid <= 14.0))),
    CONSTRAINT patient_t2d_metrics_triglycerides_check CHECK (((triglycerides >= (40)::numeric) AND (triglycerides <= (1000)::numeric))),
    CONSTRAINT patient_t2d_metrics_uacr_check CHECK (((uacr >= (1)::numeric) AND (uacr <= (3500)::numeric))),
    CONSTRAINT patient_t2d_metrics_waist_circumference_check CHECK (((waist_circumference >= (50)::numeric) AND (waist_circumference <= (160)::numeric))),
    CONSTRAINT patient_t2d_metrics_whr_check CHECK (((whr >= 0.6) AND (whr <= 1.4)))
);


--
-- Name: patient_t2d_metrics_metric_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.patient_t2d_metrics_metric_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: patient_t2d_metrics_metric_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.patient_t2d_metrics_metric_id_seq OWNED BY public.patient_t2d_metrics.metric_id;


--
-- Name: patients; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.patients (
    patient_id integer NOT NULL,
    user_id integer NOT NULL,
    first_name character varying(100) NOT NULL,
    middle_name character varying(100),
    last_name character varying(100) NOT NULL,
    suffix character varying(20),
    date_of_birth date NOT NULL,
    gender character varying(20) NOT NULL,
    religion character varying(50),
    address text NOT NULL,
    contact_number character varying(20) NOT NULL,
    email character varying(150) NOT NULL,
    emergency_contact_name character varying(150) NOT NULL,
    emergency_contact_number character varying(20) NOT NULL,
    emergency_relation character varying(50) NOT NULL,
    hipaa_consent boolean NOT NULL,
    hipaa_consent_at timestamp with time zone DEFAULT now(),
    is_active boolean,
    updated_at timestamp with time zone DEFAULT now(),
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: patients_patient_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.patients_patient_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: patients_patient_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.patients_patient_id_seq OWNED BY public.patients.patient_id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    user_id integer NOT NULL,
    username character varying(150) NOT NULL,
    password_hash character varying(255) NOT NULL,
    role character varying(20) NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    is_locked boolean,
    failed_attempts integer,
    token_version integer
);


--
-- Name: users_user_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.users_user_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: users_user_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.users_user_id_seq OWNED BY public.users.user_id;


--
-- Name: admins admin_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admins ALTER COLUMN admin_id SET DEFAULT nextval('public.admins_admin_id_seq'::regclass);


--
-- Name: audit_ledger id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_ledger ALTER COLUMN id SET DEFAULT nextval('public.audit_ledger_id_seq'::regclass);


--
-- Name: doctors doctor_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.doctors ALTER COLUMN doctor_id SET DEFAULT nextval('public.doctors_doctor_id_seq'::regclass);


--
-- Name: encounters id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.encounters ALTER COLUMN id SET DEFAULT nextval('public.encounters_id_seq'::regclass);


--
-- Name: patient_clinical_vectors id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.patient_clinical_vectors ALTER COLUMN id SET DEFAULT nextval('public.patient_clinical_vectors_id_seq'::regclass);


--
-- Name: patient_cvd_metrics metric_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.patient_cvd_metrics ALTER COLUMN metric_id SET DEFAULT nextval('public.patient_cvd_metrics_metric_id_seq'::regclass);


--
-- Name: patient_family_history record_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.patient_family_history ALTER COLUMN record_id SET DEFAULT nextval('public.patient_family_history_record_id_seq'::regclass);


--
-- Name: patient_fhrs_stratification fhrs_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.patient_fhrs_stratification ALTER COLUMN fhrs_id SET DEFAULT nextval('public.patient_fhrs_stratification_fhrs_id_seq'::regclass);


--
-- Name: patient_neuro_mental_metrics metric_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.patient_neuro_mental_metrics ALTER COLUMN metric_id SET DEFAULT nextval('public.patient_neuro_mental_metrics_metric_id_seq'::regclass);


--
-- Name: patient_respiratory_metrics metric_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.patient_respiratory_metrics ALTER COLUMN metric_id SET DEFAULT nextval('public.patient_respiratory_metrics_metric_id_seq'::regclass);


--
-- Name: patient_t2d_metrics metric_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.patient_t2d_metrics ALTER COLUMN metric_id SET DEFAULT nextval('public.patient_t2d_metrics_metric_id_seq'::regclass);


--
-- Name: patients patient_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.patients ALTER COLUMN patient_id SET DEFAULT nextval('public.patients_patient_id_seq'::regclass);


--
-- Name: users user_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users ALTER COLUMN user_id SET DEFAULT nextval('public.users_user_id_seq'::regclass);


--
-- Name: admins admins_email_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admins
    ADD CONSTRAINT admins_email_key UNIQUE (email);


--
-- Name: admins admins_license_number_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admins
    ADD CONSTRAINT admins_license_number_key UNIQUE (license_number);


--
-- Name: admins admins_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admins
    ADD CONSTRAINT admins_pkey PRIMARY KEY (admin_id);


--
-- Name: admins admins_user_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admins
    ADD CONSTRAINT admins_user_id_key UNIQUE (user_id);


--
-- Name: audit_ledger audit_ledger_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_ledger
    ADD CONSTRAINT audit_ledger_pkey PRIMARY KEY (id);


--
-- Name: doctors doctors_email_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.doctors
    ADD CONSTRAINT doctors_email_key UNIQUE (email);


--
-- Name: doctors doctors_license_number_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.doctors
    ADD CONSTRAINT doctors_license_number_key UNIQUE (license_number);


--
-- Name: doctors doctors_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.doctors
    ADD CONSTRAINT doctors_pkey PRIMARY KEY (doctor_id);


--
-- Name: doctors doctors_user_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.doctors
    ADD CONSTRAINT doctors_user_id_key UNIQUE (user_id);


--
-- Name: encounters encounters_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.encounters
    ADD CONSTRAINT encounters_pkey PRIMARY KEY (id);


--
-- Name: idempotency_cache idempotency_cache_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.idempotency_cache
    ADD CONSTRAINT idempotency_cache_pkey PRIMARY KEY (key);


--
-- Name: patient_clinical_vectors patient_clinical_vectors_patient_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.patient_clinical_vectors
    ADD CONSTRAINT patient_clinical_vectors_patient_id_key UNIQUE (patient_id);


--
-- Name: patient_clinical_vectors patient_clinical_vectors_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.patient_clinical_vectors
    ADD CONSTRAINT patient_clinical_vectors_pkey PRIMARY KEY (id);


--
-- Name: patient_cvd_metrics patient_cvd_metrics_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.patient_cvd_metrics
    ADD CONSTRAINT patient_cvd_metrics_pkey PRIMARY KEY (metric_id);


--
-- Name: patient_family_history patient_family_history_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.patient_family_history
    ADD CONSTRAINT patient_family_history_pkey PRIMARY KEY (record_id);


--
-- Name: patient_fhrs_stratification patient_fhrs_stratification_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.patient_fhrs_stratification
    ADD CONSTRAINT patient_fhrs_stratification_pkey PRIMARY KEY (fhrs_id);


--
-- Name: patient_neuro_mental_metrics patient_neuro_mental_metrics_patient_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.patient_neuro_mental_metrics
    ADD CONSTRAINT patient_neuro_mental_metrics_patient_id_key UNIQUE (patient_id);


--
-- Name: patient_neuro_mental_metrics patient_neuro_mental_metrics_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.patient_neuro_mental_metrics
    ADD CONSTRAINT patient_neuro_mental_metrics_pkey PRIMARY KEY (metric_id);


--
-- Name: patient_respiratory_metrics patient_respiratory_metrics_patient_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.patient_respiratory_metrics
    ADD CONSTRAINT patient_respiratory_metrics_patient_id_key UNIQUE (patient_id);


--
-- Name: patient_respiratory_metrics patient_respiratory_metrics_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.patient_respiratory_metrics
    ADD CONSTRAINT patient_respiratory_metrics_pkey PRIMARY KEY (metric_id);


--
-- Name: patient_t2d_metrics patient_t2d_metrics_patient_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.patient_t2d_metrics
    ADD CONSTRAINT patient_t2d_metrics_patient_id_key UNIQUE (patient_id);


--
-- Name: patient_t2d_metrics patient_t2d_metrics_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.patient_t2d_metrics
    ADD CONSTRAINT patient_t2d_metrics_pkey PRIMARY KEY (metric_id);


--
-- Name: patients patients_email_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.patients
    ADD CONSTRAINT patients_email_key UNIQUE (email);


--
-- Name: patients patients_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.patients
    ADD CONSTRAINT patients_pkey PRIMARY KEY (patient_id);


--
-- Name: patients patients_user_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.patients
    ADD CONSTRAINT patients_user_id_key UNIQUE (user_id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (user_id);


--
-- Name: users users_username_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_username_key UNIQUE (username);


--
-- Name: ix_audit_ledger_actor_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_ledger_actor_user_id ON public.audit_ledger USING btree (actor_user_id);


--
-- Name: ix_audit_ledger_audit_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_audit_ledger_audit_id ON public.audit_ledger USING btree (audit_id);


--
-- Name: ix_audit_ledger_doctor_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_ledger_doctor_id ON public.audit_ledger USING btree (doctor_id);


--
-- Name: ix_audit_ledger_event_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_ledger_event_type ON public.audit_ledger USING btree (event_type);


--
-- Name: ix_audit_ledger_patient_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_ledger_patient_id ON public.audit_ledger USING btree (patient_id);


--
-- Name: ix_audit_ledger_timestamp_utc; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_ledger_timestamp_utc ON public.audit_ledger USING btree (timestamp_utc);


--
-- Name: ix_encounters_cryptographic_hash; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_encounters_cryptographic_hash ON public.encounters USING btree (cryptographic_hash);


--
-- Name: ix_encounters_encounter_uid; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_encounters_encounter_uid ON public.encounters USING btree (encounter_uid);


--
-- Name: ix_encounters_patient_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_encounters_patient_id ON public.encounters USING btree (patient_id);


--
-- Name: admins admins_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admins
    ADD CONSTRAINT admins_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: doctors doctors_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.doctors
    ADD CONSTRAINT doctors_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: encounters encounters_doctor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.encounters
    ADD CONSTRAINT encounters_doctor_id_fkey FOREIGN KEY (doctor_id) REFERENCES public.doctors(doctor_id);


--
-- Name: encounters encounters_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.encounters
    ADD CONSTRAINT encounters_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(patient_id) ON DELETE CASCADE;


--
-- Name: patient_neuro_mental_metrics fk_neuro_patient; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.patient_neuro_mental_metrics
    ADD CONSTRAINT fk_neuro_patient FOREIGN KEY (patient_id) REFERENCES public.patients(patient_id) ON DELETE CASCADE;


--
-- Name: patient_respiratory_metrics fk_resp_patient; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.patient_respiratory_metrics
    ADD CONSTRAINT fk_resp_patient FOREIGN KEY (patient_id) REFERENCES public.patients(patient_id) ON DELETE CASCADE;


--
-- Name: patient_t2d_metrics fk_t2d_patient; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.patient_t2d_metrics
    ADD CONSTRAINT fk_t2d_patient FOREIGN KEY (patient_id) REFERENCES public.patients(patient_id) ON DELETE CASCADE;


--
-- Name: patient_clinical_vectors patient_clinical_vectors_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.patient_clinical_vectors
    ADD CONSTRAINT patient_clinical_vectors_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(patient_id) ON DELETE CASCADE;


--
-- Name: patient_cvd_metrics patient_cvd_metrics_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.patient_cvd_metrics
    ADD CONSTRAINT patient_cvd_metrics_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(patient_id) ON DELETE CASCADE;


--
-- Name: patient_family_history patient_family_history_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.patient_family_history
    ADD CONSTRAINT patient_family_history_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(patient_id) ON DELETE CASCADE;


--
-- Name: patient_fhrs_stratification patient_fhrs_stratification_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.patient_fhrs_stratification
    ADD CONSTRAINT patient_fhrs_stratification_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(patient_id) ON DELETE CASCADE;


--
-- Name: patients patients_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.patients
    ADD CONSTRAINT patients_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict tMXzQSqEFubsRtTYquKr8ZxEbINybHIQKradCMkZ4sBf4tGu7Ozmmybxqumu9Ov

