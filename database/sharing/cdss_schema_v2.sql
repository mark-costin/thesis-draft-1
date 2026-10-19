--
-- PostgreSQL database dump
--


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
    is_verified boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
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
-- Name: consultations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.consultations (
    id integer NOT NULL,
    consultation_uid character varying(64) NOT NULL,
    patient_id integer NOT NULL,
    doctor_id integer NOT NULL,
    directives json NOT NULL,
    notes text,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: consultations_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.consultations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: consultations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.consultations_id_seq OWNED BY public.consultations.id;


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
    is_verified boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
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
-- Name: documents; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.documents (
    document_id integer NOT NULL,
    patient_id integer NOT NULL,
    encounter_id integer,
    uploaded_by integer NOT NULL,
    document_type character varying(50) DEFAULT 'medical_record'::character varying NOT NULL,
    file_path text NOT NULL,
    mime_type character varying(100),
    file_sha256 character(64),
    ocr_engine character varying(50),
    ocr_text text,
    ocr_confidence numeric(5,2),
    status character varying(20) DEFAULT 'pending'::character varying NOT NULL,
    verified_by integer,
    verified_at timestamp with time zone,
    uploaded_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT documents_check CHECK ((((status)::text <> 'verified'::text) OR ((verified_by IS NOT NULL) AND (verified_at IS NOT NULL)))),
    CONSTRAINT documents_ocr_confidence_check CHECK (((ocr_confidence >= (0)::numeric) AND (ocr_confidence <= (100)::numeric))),
    CONSTRAINT documents_status_check CHECK (((status)::text = ANY ((ARRAY['pending'::character varying, 'verified'::character varying, 'rejected'::character varying])::text[])))
);


--
-- Name: TABLE documents; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.documents IS 'Uploaded medical records, their OCR output, and physician verification status.';


--
-- Name: documents_document_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.documents ALTER COLUMN document_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.documents_document_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


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
-- Name: migration_v2_fk_changes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.migration_v2_fk_changes (
    table_name regclass NOT NULL,
    constraint_name name NOT NULL,
    original_def text NOT NULL
);


--
-- Name: model_versions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.model_versions (
    model_version_id integer NOT NULL,
    disease_domain character varying(10) NOT NULL,
    version character varying(30) NOT NULL,
    algorithm character varying(50) DEFAULT 'XGBoost'::character varying NOT NULL,
    artifact_path text NOT NULL,
    artifact_sha256 character(64),
    feature_list jsonb,
    metrics jsonb,
    trained_at timestamp with time zone,
    is_active boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT model_versions_disease_domain_check CHECK (((disease_domain)::text = ANY ((ARRAY['CVD'::character varying, 'T2D'::character varying, 'CRD'::character varying, 'NEURO'::character varying])::text[])))
);


--
-- Name: TABLE model_versions; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.model_versions IS 'Trained XGBoost models; each risk result points to the model that produced it.';


--
-- Name: model_versions_model_version_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.model_versions ALTER COLUMN model_version_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.model_versions_model_version_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: patient_clinical_vectors; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.patient_clinical_vectors (
    id integer NOT NULL,
    patient_id integer NOT NULL,
    disease_narrative text,
    embedding public.vector(384),
    updated_at timestamp with time zone DEFAULT now()
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
    encounter_id integer,
    CONSTRAINT patient_cvd_metrics_age_check CHECK (((age >= (18)::numeric) AND (age <= (100)::numeric))),
    CONSTRAINT patient_cvd_metrics_biological_sex_check CHECK (((biological_sex)::text = ANY (ARRAY[('Female'::character varying)::text, ('Male'::character varying)::text]))),
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
-- Name: patient_environmental_hazards; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.patient_environmental_hazards (
    id integer NOT NULL,
    patient_id integer NOT NULL,
    disease_domain character varying(10) NOT NULL,
    hazard_code character varying(50) NOT NULL,
    recorded_at timestamp with time zone DEFAULT now()
);


--
-- Name: patient_environmental_hazards_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.patient_environmental_hazards_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: patient_environmental_hazards_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.patient_environmental_hazards_id_seq OWNED BY public.patient_environmental_hazards.id;


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
    recorded_at timestamp with time zone DEFAULT now(),
    is_verified boolean DEFAULT false NOT NULL
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
    evaluated_at timestamp with time zone DEFAULT now(),
    encounter_id integer
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
    phq9 integer,
    gad7 integer,
    mmse integer,
    moca integer,
    ham_d integer,
    updrs_part3 integer,
    daily_sleep numeric(4,1),
    psqi integer,
    seizure_frequency numeric(5,1),
    hrv_sdnn numeric(5,1),
    serum_cortisol numeric(4,1),
    vitamin_b12 numeric(6,1),
    serum_folate numeric(4,1),
    tsh numeric(5,2),
    faq_score integer,
    tremor_rating integer,
    tbi_history integer,
    substance_abuse integer,
    family_history_neuro_psych integer,
    age numeric(4,1),
    recorded_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    encounter_id integer,
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
    fev1 numeric(3,1),
    fvc numeric(3,1),
    fev1_fvc_ratio numeric(4,1),
    post_bd_fev1_pred numeric(5,1),
    pef numeric(5,1),
    eosinophil_count numeric(6,1),
    feno numeric(5,1),
    spo2 numeric(4,1),
    pao2 numeric(5,1),
    paco2 numeric(4,1),
    mmrc_score integer,
    act_score integer,
    cat_score integer,
    serum_ige numeric(6,1),
    annual_exacerbations integer,
    tobacco_exposure numeric(5,1),
    occupational_dust integer,
    allergic_rhinitis integer,
    childhood_asthma integer,
    bmi numeric(4,1),
    recorded_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    encounter_id integer,
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
    fpg numeric(5,1),
    postprandial_glucose_2h numeric(5,1),
    hba1c numeric(4,1),
    fasting_insulin numeric(5,1),
    c_peptide numeric(4,1),
    homa_ir numeric(4,1),
    bmi numeric(4,1),
    waist_circumference numeric(5,1),
    whr numeric(4,2),
    sbp numeric(5,1),
    dbp numeric(5,1),
    triglycerides numeric(6,1),
    hdl numeric(5,1),
    uacr numeric(6,1),
    serum_uric_acid numeric(4,1),
    gestational_diabetes integer,
    family_history_diabetes integer,
    acanthosis_nigricans integer,
    daily_carbs numeric(5,1),
    sedentary_duration numeric(4,1),
    recorded_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    encounter_id integer,
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
    is_active boolean DEFAULT true NOT NULL,
    updated_at timestamp with time zone DEFAULT now(),
    created_at timestamp with time zone DEFAULT now(),
    biological_sex character varying(10),
    CONSTRAINT patients_biological_sex_check CHECK (((biological_sex)::text = ANY (ARRAY[('Female'::character varying)::text, ('Male'::character varying)::text])))
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
-- Name: queue_tickets; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.queue_tickets (
    id integer NOT NULL,
    queue_date date NOT NULL,
    queue_number integer NOT NULL,
    patient_id integer NOT NULL,
    name character varying(150) NOT NULL,
    urgency character varying(40) NOT NULL,
    complaint text NOT NULL,
    vitals character varying(255) NOT NULL,
    watch_flag character varying(150) NOT NULL,
    status character varying(12) NOT NULL,
    checked_in_at timestamp with time zone NOT NULL,
    closed_at timestamp with time zone,
    CONSTRAINT queue_tickets_status_check CHECK (((status)::text = ANY (ARRAY[('WAITING'::character varying)::text, ('DONE'::character varying)::text, ('CANCELLED'::character varying)::text])))
);


--
-- Name: queue_tickets_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.queue_tickets_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: queue_tickets_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.queue_tickets_id_seq OWNED BY public.queue_tickets.id;


--
-- Name: risk_results; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.risk_results (
    result_id integer NOT NULL,
    encounter_id integer NOT NULL,
    model_version_id integer NOT NULL,
    disease_domain character varying(10) NOT NULL,
    risk_probability numeric(5,4) NOT NULL,
    risk_level character varying(20) NOT NULL,
    shap_base_value numeric,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT risk_results_disease_domain_check CHECK (((disease_domain)::text = ANY ((ARRAY['CVD'::character varying, 'T2D'::character varying, 'CRD'::character varying, 'NEURO'::character varying])::text[]))),
    CONSTRAINT risk_results_risk_level_check CHECK (((risk_level)::text = ANY ((ARRAY['Low'::character varying, 'Moderate'::character varying, 'High'::character varying])::text[]))),
    CONSTRAINT risk_results_risk_probability_check CHECK (((risk_probability >= (0)::numeric) AND (risk_probability <= (1)::numeric)))
);


--
-- Name: TABLE risk_results; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.risk_results IS 'Predicted risk per disease per encounter (four rows per screening).';


--
-- Name: risk_results_result_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.risk_results ALTER COLUMN result_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.risk_results_result_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: schema_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.schema_version (
    version integer NOT NULL,
    description text NOT NULL,
    applied_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: shap_explanations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.shap_explanations (
    explanation_id integer NOT NULL,
    result_id integer NOT NULL,
    feature_name character varying(100) NOT NULL,
    feature_value numeric,
    shap_value numeric NOT NULL,
    rank smallint NOT NULL,
    CONSTRAINT shap_explanations_rank_check CHECK ((rank >= 1))
);


--
-- Name: TABLE shap_explanations; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.shap_explanations IS 'SHAP feature contributions explaining each risk result, ranked by absolute impact.';


--
-- Name: shap_explanations_explanation_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.shap_explanations ALTER COLUMN explanation_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.shap_explanations_explanation_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    user_id integer NOT NULL,
    username character varying(150) NOT NULL,
    password_hash character varying(255) NOT NULL,
    role character varying(20) NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    is_locked boolean DEFAULT false NOT NULL,
    failed_attempts integer DEFAULT 0 NOT NULL,
    token_version integer DEFAULT 0 NOT NULL,
    CONSTRAINT users_failed_attempts_check CHECK ((failed_attempts >= 0))
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
-- Name: consultations id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.consultations ALTER COLUMN id SET DEFAULT nextval('public.consultations_id_seq'::regclass);


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
-- Name: patient_environmental_hazards id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.patient_environmental_hazards ALTER COLUMN id SET DEFAULT nextval('public.patient_environmental_hazards_id_seq'::regclass);


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
-- Name: queue_tickets id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.queue_tickets ALTER COLUMN id SET DEFAULT nextval('public.queue_tickets_id_seq'::regclass);


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
-- Name: consultations consultations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.consultations
    ADD CONSTRAINT consultations_pkey PRIMARY KEY (id);


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
-- Name: documents documents_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT documents_pkey PRIMARY KEY (document_id);


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
-- Name: migration_v2_fk_changes migration_v2_fk_changes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.migration_v2_fk_changes
    ADD CONSTRAINT migration_v2_fk_changes_pkey PRIMARY KEY (table_name, constraint_name);


--
-- Name: model_versions model_versions_disease_domain_version_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.model_versions
    ADD CONSTRAINT model_versions_disease_domain_version_key UNIQUE (disease_domain, version);


--
-- Name: model_versions model_versions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.model_versions
    ADD CONSTRAINT model_versions_pkey PRIMARY KEY (model_version_id);


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
-- Name: patient_environmental_hazards patient_environmental_hazards_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.patient_environmental_hazards
    ADD CONSTRAINT patient_environmental_hazards_pkey PRIMARY KEY (id);


--
-- Name: patient_environmental_hazards patient_environmental_hazards_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.patient_environmental_hazards
    ADD CONSTRAINT patient_environmental_hazards_unique UNIQUE (patient_id, disease_domain, hazard_code);


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
-- Name: patient_neuro_mental_metrics patient_neuro_mental_metrics_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.patient_neuro_mental_metrics
    ADD CONSTRAINT patient_neuro_mental_metrics_pkey PRIMARY KEY (metric_id);


--
-- Name: patient_respiratory_metrics patient_respiratory_metrics_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.patient_respiratory_metrics
    ADD CONSTRAINT patient_respiratory_metrics_pkey PRIMARY KEY (metric_id);


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
-- Name: queue_tickets queue_tickets_number_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.queue_tickets
    ADD CONSTRAINT queue_tickets_number_unique UNIQUE (queue_date, queue_number);


--
-- Name: queue_tickets queue_tickets_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.queue_tickets
    ADD CONSTRAINT queue_tickets_pkey PRIMARY KEY (id);


--
-- Name: risk_results risk_results_encounter_id_disease_domain_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.risk_results
    ADD CONSTRAINT risk_results_encounter_id_disease_domain_key UNIQUE (encounter_id, disease_domain);


--
-- Name: risk_results risk_results_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.risk_results
    ADD CONSTRAINT risk_results_pkey PRIMARY KEY (result_id);


--
-- Name: schema_version schema_version_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schema_version
    ADD CONSTRAINT schema_version_pkey PRIMARY KEY (version);


--
-- Name: shap_explanations shap_explanations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shap_explanations
    ADD CONSTRAINT shap_explanations_pkey PRIMARY KEY (explanation_id);


--
-- Name: shap_explanations shap_explanations_result_id_feature_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shap_explanations
    ADD CONSTRAINT shap_explanations_result_id_feature_name_key UNIQUE (result_id, feature_name);


--
-- Name: shap_explanations shap_explanations_result_id_rank_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shap_explanations
    ADD CONSTRAINT shap_explanations_result_id_rank_key UNIQUE (result_id, rank);


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
-- Name: ix_consultations_consultation_uid; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_consultations_consultation_uid ON public.consultations USING btree (consultation_uid);


--
-- Name: ix_consultations_doctor_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_consultations_doctor_id ON public.consultations USING btree (doctor_id);


--
-- Name: ix_consultations_patient_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_consultations_patient_id ON public.consultations USING btree (patient_id);


--
-- Name: ix_cvd_metrics_encounter_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_cvd_metrics_encounter_id ON public.patient_cvd_metrics USING btree (encounter_id);


--
-- Name: ix_cvd_metrics_patient_recorded; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_cvd_metrics_patient_recorded ON public.patient_cvd_metrics USING btree (patient_id, recorded_at DESC);


--
-- Name: ix_documents_encounter_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_documents_encounter_id ON public.documents USING btree (encounter_id);


--
-- Name: ix_documents_patient_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_documents_patient_id ON public.documents USING btree (patient_id);


--
-- Name: ix_documents_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_documents_status ON public.documents USING btree (status);


--
-- Name: ix_encounters_cryptographic_hash; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_encounters_cryptographic_hash ON public.encounters USING btree (cryptographic_hash);


--
-- Name: ix_encounters_doctor_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_encounters_doctor_id ON public.encounters USING btree (doctor_id);


--
-- Name: ix_encounters_encounter_uid; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_encounters_encounter_uid ON public.encounters USING btree (encounter_uid);


--
-- Name: ix_encounters_patient_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_encounters_patient_id ON public.encounters USING btree (patient_id);


--
-- Name: ix_family_history_patient_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_family_history_patient_id ON public.patient_family_history USING btree (patient_id);


--
-- Name: ix_fhrs_encounter_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_fhrs_encounter_id ON public.patient_fhrs_stratification USING btree (encounter_id);


--
-- Name: ix_fhrs_patient_evaluated; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_fhrs_patient_evaluated ON public.patient_fhrs_stratification USING btree (patient_id, evaluated_at DESC);


--
-- Name: ix_neuro_metrics_encounter_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_neuro_metrics_encounter_id ON public.patient_neuro_mental_metrics USING btree (encounter_id);


--
-- Name: ix_neuro_metrics_patient_recorded; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_neuro_metrics_patient_recorded ON public.patient_neuro_mental_metrics USING btree (patient_id, recorded_at DESC);


--
-- Name: ix_patient_environmental_hazards_patient_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_patient_environmental_hazards_patient_id ON public.patient_environmental_hazards USING btree (patient_id);


--
-- Name: ix_queue_tickets_patient_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_queue_tickets_patient_id ON public.queue_tickets USING btree (patient_id);


--
-- Name: ix_queue_tickets_queue_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_queue_tickets_queue_date ON public.queue_tickets USING btree (queue_date);


--
-- Name: ix_resp_metrics_encounter_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_resp_metrics_encounter_id ON public.patient_respiratory_metrics USING btree (encounter_id);


--
-- Name: ix_resp_metrics_patient_recorded; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_resp_metrics_patient_recorded ON public.patient_respiratory_metrics USING btree (patient_id, recorded_at DESC);


--
-- Name: ix_risk_results_disease_level; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_risk_results_disease_level ON public.risk_results USING btree (disease_domain, risk_level);


--
-- Name: ix_risk_results_model_version; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_risk_results_model_version ON public.risk_results USING btree (model_version_id);


--
-- Name: ix_t2d_metrics_encounter_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_t2d_metrics_encounter_id ON public.patient_t2d_metrics USING btree (encounter_id);


--
-- Name: ix_t2d_metrics_patient_recorded; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_t2d_metrics_patient_recorded ON public.patient_t2d_metrics USING btree (patient_id, recorded_at DESC);


--
-- Name: ux_model_versions_one_active; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ux_model_versions_one_active ON public.model_versions USING btree (disease_domain) WHERE is_active;


--
-- Name: admins admins_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admins
    ADD CONSTRAINT admins_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE RESTRICT;


--
-- Name: consultations consultations_doctor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.consultations
    ADD CONSTRAINT consultations_doctor_id_fkey FOREIGN KEY (doctor_id) REFERENCES public.doctors(doctor_id);


--
-- Name: consultations consultations_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.consultations
    ADD CONSTRAINT consultations_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(patient_id) ON DELETE RESTRICT;


--
-- Name: doctors doctors_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.doctors
    ADD CONSTRAINT doctors_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE RESTRICT;


--
-- Name: documents documents_encounter_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT documents_encounter_id_fkey FOREIGN KEY (encounter_id) REFERENCES public.encounters(id) ON DELETE RESTRICT;


--
-- Name: documents documents_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT documents_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(patient_id) ON DELETE RESTRICT;


--
-- Name: documents documents_uploaded_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT documents_uploaded_by_fkey FOREIGN KEY (uploaded_by) REFERENCES public.users(user_id) ON DELETE RESTRICT;


--
-- Name: documents documents_verified_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT documents_verified_by_fkey FOREIGN KEY (verified_by) REFERENCES public.users(user_id) ON DELETE RESTRICT;


--
-- Name: encounters encounters_doctor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.encounters
    ADD CONSTRAINT encounters_doctor_id_fkey FOREIGN KEY (doctor_id) REFERENCES public.doctors(doctor_id);


--
-- Name: encounters encounters_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.encounters
    ADD CONSTRAINT encounters_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(patient_id) ON DELETE RESTRICT;


--
-- Name: patient_neuro_mental_metrics fk_neuro_patient; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.patient_neuro_mental_metrics
    ADD CONSTRAINT fk_neuro_patient FOREIGN KEY (patient_id) REFERENCES public.patients(patient_id) ON DELETE RESTRICT;


--
-- Name: patient_respiratory_metrics fk_resp_patient; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.patient_respiratory_metrics
    ADD CONSTRAINT fk_resp_patient FOREIGN KEY (patient_id) REFERENCES public.patients(patient_id) ON DELETE RESTRICT;


--
-- Name: patient_t2d_metrics fk_t2d_patient; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.patient_t2d_metrics
    ADD CONSTRAINT fk_t2d_patient FOREIGN KEY (patient_id) REFERENCES public.patients(patient_id) ON DELETE RESTRICT;


--
-- Name: patient_clinical_vectors patient_clinical_vectors_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.patient_clinical_vectors
    ADD CONSTRAINT patient_clinical_vectors_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(patient_id) ON DELETE RESTRICT;


--
-- Name: patient_cvd_metrics patient_cvd_metrics_encounter_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.patient_cvd_metrics
    ADD CONSTRAINT patient_cvd_metrics_encounter_id_fkey FOREIGN KEY (encounter_id) REFERENCES public.encounters(id) ON DELETE RESTRICT;


--
-- Name: patient_cvd_metrics patient_cvd_metrics_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.patient_cvd_metrics
    ADD CONSTRAINT patient_cvd_metrics_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(patient_id) ON DELETE RESTRICT;


--
-- Name: patient_environmental_hazards patient_environmental_hazards_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.patient_environmental_hazards
    ADD CONSTRAINT patient_environmental_hazards_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(patient_id) ON DELETE RESTRICT;


--
-- Name: patient_family_history patient_family_history_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.patient_family_history
    ADD CONSTRAINT patient_family_history_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(patient_id) ON DELETE RESTRICT;


--
-- Name: patient_fhrs_stratification patient_fhrs_stratification_encounter_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.patient_fhrs_stratification
    ADD CONSTRAINT patient_fhrs_stratification_encounter_id_fkey FOREIGN KEY (encounter_id) REFERENCES public.encounters(id) ON DELETE RESTRICT;


--
-- Name: patient_fhrs_stratification patient_fhrs_stratification_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.patient_fhrs_stratification
    ADD CONSTRAINT patient_fhrs_stratification_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(patient_id) ON DELETE RESTRICT;


--
-- Name: patient_neuro_mental_metrics patient_neuro_mental_metrics_encounter_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.patient_neuro_mental_metrics
    ADD CONSTRAINT patient_neuro_mental_metrics_encounter_id_fkey FOREIGN KEY (encounter_id) REFERENCES public.encounters(id) ON DELETE RESTRICT;


--
-- Name: patient_respiratory_metrics patient_respiratory_metrics_encounter_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.patient_respiratory_metrics
    ADD CONSTRAINT patient_respiratory_metrics_encounter_id_fkey FOREIGN KEY (encounter_id) REFERENCES public.encounters(id) ON DELETE RESTRICT;


--
-- Name: patient_t2d_metrics patient_t2d_metrics_encounter_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.patient_t2d_metrics
    ADD CONSTRAINT patient_t2d_metrics_encounter_id_fkey FOREIGN KEY (encounter_id) REFERENCES public.encounters(id) ON DELETE RESTRICT;


--
-- Name: patients patients_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.patients
    ADD CONSTRAINT patients_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE RESTRICT;


--
-- Name: queue_tickets queue_tickets_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.queue_tickets
    ADD CONSTRAINT queue_tickets_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(patient_id) ON DELETE RESTRICT;


--
-- Name: risk_results risk_results_encounter_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.risk_results
    ADD CONSTRAINT risk_results_encounter_id_fkey FOREIGN KEY (encounter_id) REFERENCES public.encounters(id) ON DELETE RESTRICT;


--
-- Name: risk_results risk_results_model_version_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.risk_results
    ADD CONSTRAINT risk_results_model_version_id_fkey FOREIGN KEY (model_version_id) REFERENCES public.model_versions(model_version_id) ON DELETE RESTRICT;


--
-- Name: shap_explanations shap_explanations_result_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shap_explanations
    ADD CONSTRAINT shap_explanations_result_id_fkey FOREIGN KEY (result_id) REFERENCES public.risk_results(result_id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--


--
-- PostgreSQL database dump
--


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
-- Data for Name: migration_v2_fk_changes; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.migration_v2_fk_changes VALUES ('public.consultations', 'consultations_patient_id_fkey', 'FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE');
INSERT INTO public.migration_v2_fk_changes VALUES ('public.admins', 'admins_user_id_fkey', 'FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE');
INSERT INTO public.migration_v2_fk_changes VALUES ('public.doctors', 'doctors_user_id_fkey', 'FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE');
INSERT INTO public.migration_v2_fk_changes VALUES ('public.encounters', 'encounters_patient_id_fkey', 'FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE');
INSERT INTO public.migration_v2_fk_changes VALUES ('public.patient_neuro_mental_metrics', 'fk_neuro_patient', 'FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE');
INSERT INTO public.migration_v2_fk_changes VALUES ('public.patient_respiratory_metrics', 'fk_resp_patient', 'FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE');
INSERT INTO public.migration_v2_fk_changes VALUES ('public.patient_t2d_metrics', 'fk_t2d_patient', 'FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE');
INSERT INTO public.migration_v2_fk_changes VALUES ('public.patient_clinical_vectors', 'patient_clinical_vectors_patient_id_fkey', 'FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE');
INSERT INTO public.migration_v2_fk_changes VALUES ('public.patient_cvd_metrics', 'patient_cvd_metrics_patient_id_fkey', 'FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE');
INSERT INTO public.migration_v2_fk_changes VALUES ('public.patient_environmental_hazards', 'patient_environmental_hazards_patient_id_fkey', 'FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE');
INSERT INTO public.migration_v2_fk_changes VALUES ('public.patient_family_history', 'patient_family_history_patient_id_fkey', 'FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE');
INSERT INTO public.migration_v2_fk_changes VALUES ('public.patient_fhrs_stratification', 'patient_fhrs_stratification_patient_id_fkey', 'FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE');
INSERT INTO public.migration_v2_fk_changes VALUES ('public.patients', 'patients_user_id_fkey', 'FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE');
INSERT INTO public.migration_v2_fk_changes VALUES ('public.queue_tickets', 'queue_tickets_patient_id_fkey', 'FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE');


--
-- Data for Name: schema_version; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.schema_version VALUES (2, 'Repeat screenings, optional inputs, RESTRICT deletes, risk/SHAP/model tables, OCR documents', '2026-10-18 15:16:33.975352+08');


--
-- PostgreSQL database dump complete
--


