"""
Clinical min/max for every stored biomarker.

Source: CDSS_Data_Dictionary.pdf, "Parameter Ingestion Tables (CDSS Specification)"
(physician-validated; Harrison's Principles of Internal Medicine, 19th ed.).
The synthetic cohort generator reads the same numbers from
experiment/data/reference/cdss_spec.json for the features it produces;
tests/test_biomarker_ranges.py checks that the two agree.

Keys are the database column names in clinic_orm.py. Both limits are allowed.
"""
import math

# modality -> column -> (minimum, maximum, unit)
RANGES = {
    "cvd": {
        "age": (18, 100, "years"),
        "sbp": (70, 220, "mmHg"),
        "dbp": (40, 130, "mmHg"),
        "resting_hr": (40, 180, "bpm"),
        "bmi": (12.0, 60.0, "kg/m²"),
        "total_cholesterol": (100, 400, "mg/dL"),
        "hdl": (15, 120, "mg/dL"),
        "ldl": (30, 300, "mg/dL"),
        "triglycerides": (40, 1000, "mg/dL"),
        "hs_crp": (0.1, 50.0, "mg/L"),
        "serum_creatinine": (0.4, 10.0, "mg/dL"),
        "egfr": (5, 140, "mL/min/1.73m²"),
        "lvef": (15, 75, "%"),
        "ctni": (0.01, 50.0, "ng/mL"),
        "nt_probnp": (10, 35000, "pg/mL"),
        "smoking_history": (0, 120, "pack-years"),
        "daily_sodium": (500, 10000, "mg/day"),
        "family_history_premature_cvd": (0, 1, "0 = no, 1 = yes"),
        "physical_activity": (0, 1050, "mins/week"),
    },
    "t2d": {
        "fpg": (50, 450, "mg/dL"),
        "postprandial_glucose_2h": (60, 600, "mg/dL"),
        "hba1c": (4.0, 15.0, "%"),
        "fasting_insulin": (1.0, 100.0, "µIU/mL"),
        "c_peptide": (0.1, 12.0, "ng/mL"),
        "homa_ir": (0.2, 25.0, "score"),
        "bmi": (12.0, 60.0, "kg/m²"),
        "waist_circumference": (50, 160, "cm"),
        "whr": (0.60, 1.40, "ratio"),
        "sbp": (70, 220, "mmHg"),
        "dbp": (40, 130, "mmHg"),
        "triglycerides": (40, 1000, "mg/dL"),
        "hdl": (15, 120, "mg/dL"),
        "uacr": (1, 3500, "mg/g"),
        "serum_uric_acid": (1.5, 14.0, "mg/dL"),
        "gestational_diabetes": (0, 1, "0 = no, 1 = yes"),
        "family_history_diabetes": (0, 1, "0 = no, 1 = yes"),
        "acanthosis_nigricans": (0, 1, "0 = no, 1 = yes"),
        "daily_carbs": (50, 600, "g/day"),
        "sedentary_duration": (1.0, 18.0, "hours/day"),
    },
    "resp": {
        "fev1": (0.5, 5.5, "L"),
        "fvc": (1.0, 7.0, "L"),
        "fev1_fvc_ratio": (25.0, 95.0, "%"),
        "post_bd_fev1_pred": (15.0, 120.0, "%"),
        "pef": (50, 800, "L/min"),
        "eosinophil_count": (0, 2500, "cells/µL"),
        "feno": (5, 150, "ppb"),
        "spo2": (65.0, 100.0, "%"),
        "pao2": (40, 110, "mmHg"),
        "paco2": (25, 90, "mmHg"),
        "mmrc_score": (0, 4, "score"),
        "act_score": (5, 25, "score"),
        "cat_score": (0, 40, "score"),
        "serum_ige": (2, 3000, "IU/mL"),
        "annual_exacerbations": (0, 15, "episodes/year"),
        "tobacco_exposure": (0, 120, "pack-years"),
        "occupational_dust": (0, 1, "0 = no, 1 = yes"),
        "allergic_rhinitis": (0, 1, "0 = no, 1 = yes"),
        "childhood_asthma": (0, 1, "0 = no, 1 = yes"),
        "bmi": (12.0, 60.0, "kg/m²"),
    },
    "neuro": {
        "phq9": (0, 27, "score"),
        "gad7": (0, 21, "score"),
        "mmse": (0, 30, "score"),
        "moca": (0, 30, "score"),
        "ham_d": (0, 52, "score"),
        "updrs_part3": (0, 132, "score"),
        "daily_sleep": (1.0, 16.0, "hours"),
        "psqi": (0, 21, "score"),
        "seizure_frequency": (0, 100, "episodes/month"),
        "hrv_sdnn": (5.0, 250.0, "ms"),
        "serum_cortisol": (1.0, 45.0, "µg/dL"),
        "vitamin_b12": (50, 2000, "pg/mL"),
        "serum_folate": (1.0, 25.0, "ng/mL"),
        "tsh": (0.01, 100.0, "mIU/L"),
        "faq_score": (0, 30, "score"),
        "tremor_rating": (0, 4, "score"),
        "tbi_history": (0, 1, "0 = no, 1 = yes"),
        "substance_abuse": (0, 1, "0 = no, 1 = yes"),
        "family_history_neuro_psych": (0, 1, "0 = no, 1 = yes"),
        "age": (18, 100, "years"),
    },
}

# modality -> column -> allowed values (stored in this spelling)
CHOICES = {
    "cvd": {"biological_sex": ("Female", "Male")},
}

# Model feature name -> database column, for /infer payloads that use the training names
FEATURE_TO_COLUMN = {
    "systolic_bp": "sbp",
    "diastolic_bp": "dbp",
    "tg": "triglycerides",
    "sleep_hours": "daily_sleep",
}


def range_message(field, low, high, unit, value):
    return f"{field} must be between {low} and {high} {unit} (got {value})"


def out_of_range(modality, payload):
    """
    {field: message} for numeric values outside the dictionary range.
    Field names may be database columns or model feature names. Text, booleans and
    names without a range are skipped; the inference engine reports those itself.
    """
    ranges = RANGES.get(modality, {})
    errors = {}
    for field, value in (payload or {}).items():
        limits = ranges.get(FEATURE_TO_COLUMN.get(field, field))
        if limits is None or isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        if not math.isfinite(value):
            continue
        low, high, unit = limits
        if not low <= value <= high:
            errors[field] = range_message(field, low, high, unit, value)
    return errors
