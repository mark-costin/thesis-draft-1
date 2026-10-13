import numpy as np
import pandas as pd

try:
    from .spec import clip_to_spec
except ImportError:
    from spec import clip_to_spec

# BMI: right-skewed lognormal fitted to the reference quartiles 24.8 / 28.5 / 33.2
#   median = exp(mu) = 28.5 ; sigma = ln(33.2 / 24.8) / 1.349 = 0.216
BMI_LOG_MEDIAN = np.log(28.5)
BMI_LOG_SIGMA = 0.216
BMI_CENTER = 28.5          # BMI effects are centred so they add correlation without shifting means

# BMI effects on cardiometabolic markers (per kg/m² above/below the median)
BMI_TO_SBP = 0.5           # mmHg     -> corr(BMI, SBP) ~ +0.2
BMI_TO_HDL = -0.6          # mg/dL    -> corr(BMI, HDL) ~ -0.25
BMI_TO_TG = 1.0            # mg/dL    -> total BMI->TG slope 1.9 (incl. +0.9 via HDL), corr ~ +0.3

# Impaired subgroups (simulation assumptions)
#   GLYC:  dysglycaemic subgroup, rises with BMI and age (~10% overall)
#   RESP:  8% at 18 -> ~15% at 53 -> ~19% at 74
#   NEURO: 6% at 18 -> ~15% at 53 -> ~20% at 74
GLYC_IMPAIRED_BASE, GLYC_PER_BMI, GLYC_PER_YEAR = 0.02, 0.003, 0.0015
RESP_IMPAIRED_BASE, RESP_IMPAIRED_PER_YEAR = 0.08, 0.002
NEURO_IMPAIRED_BASE, NEURO_IMPAIRED_PER_YEAR = 0.06, 0.0025


def generate_demographics(n_patients):
    patient_ids = [f"PT-{20260000 + i}" for i in range(n_patients)]
    sex = np.random.choice([0, 1], size=n_patients)

    # Balanced age strata (Gate 9)
    strata = np.random.choice([0, 1, 2], size=n_patients, p=[0.34, 0.33, 0.33])
    age = np.where(strata == 0, np.random.normal(32, 6, n_patients),
          np.where(strata == 1, np.random.normal(54, 6, n_patients),
                                np.random.normal(74, 8, n_patients)))

    age = clip_to_spec("age", age).astype(int)
    return pd.DataFrame({'patient_id': patient_ids, 'biological_sex': sex, 'age': age})


def generate_biomarkers(df):
    n = len(df)
    age = df['age'].to_numpy(dtype=float)

    # --- CVD panel (bounds: CDSS Data Dictionary) ---
    df['bmi'] = clip_to_spec("bmi", np.random.lognormal(BMI_LOG_MEDIAN, BMI_LOG_SIGMA, size=n))
    bmi_c = df['bmi'] - BMI_CENTER
    df['systolic_bp'] = clip_to_spec("systolic_bp",
                                     100 + (df['age'] * 0.5) + BMI_TO_SBP * bmi_c
                                     + np.random.normal(0, 10, size=n))
    # DBP follows SBP partially (corr ~0.7), mean ~78 mmHg
    df['diastolic_bp'] = clip_to_spec("diastolic_bp",
                                      0.5 * df['systolic_bp'] + 15 + np.random.normal(0, 7, size=n))
    df['resting_hr'] = clip_to_spec("resting_hr", np.random.normal(75, 12, size=n))

    df['total_cholesterol'] = clip_to_spec("total_cholesterol", np.random.normal(190, 40, size=n))
    df['hdl'] = clip_to_spec("hdl", np.random.normal(53.4, 15.1, size=n) + BMI_TO_HDL * bmi_c)
    df['ldl'] = clip_to_spec("ldl", df['total_cholesterol'] - df['hdl'] - 20)
    df['tg'] = clip_to_spec("tg", 220 - (df['hdl'] * 1.5) + BMI_TO_TG * bmi_c
                            + np.random.normal(0, 30, size=n))
    df['egfr'] = clip_to_spec("egfr", np.random.normal(90, 20, size=n))

    # --- T2D panel: dysglycaemic subgroup; FPG tied to HbA1c ---
    bmi = df['bmi'].to_numpy(dtype=float)
    p_glyc = np.clip(GLYC_IMPAIRED_BASE + GLYC_PER_BMI * (bmi - 20) + GLYC_PER_YEAR * (age - 18), 0.0, 0.9)
    glyc_imp = np.random.rand(n) < p_glyc
    hba1c = np.where(glyc_imp,
                     np.random.normal(7.4, 1.1, n),
                     4.0 + (bmi * 0.05) + np.random.normal(0, 0.33, n))
    df['hba1c'] = clip_to_spec("hba1c", hba1c)
    df['fpg'] = clip_to_spec("fpg", 95 + 25 * (df['hba1c'] - 5.6) + np.random.normal(0, 15, size=n))

    # --- RESP panel: age-dependent impaired subgroup (obstruction + hypoxaemia) ---
    p_resp = np.clip(RESP_IMPAIRED_BASE + RESP_IMPAIRED_PER_YEAR * (age - 18), 0.0, 0.9)
    resp_imp = np.random.rand(n) < p_resp
    fev1 = np.where(resp_imp, np.random.normal(1.8, 0.6, n), np.random.normal(3.0, 0.8, n))
    df['fev1'] = clip_to_spec("fev1", fev1)
    fvc_gap = np.where(resp_imp, np.random.normal(1.2, 0.3, n), np.random.normal(0.8, 0.2, n))
    df['fvc'] = clip_to_spec("fvc", df['fev1'] + fvc_gap)
    df['fev1_fvc_ratio'] = clip_to_spec("fev1_fvc_ratio", (df['fev1'] / df['fvc']) * 100)
    spo2 = np.where(resp_imp, np.random.normal(91, 3.5, n), np.random.normal(97, 1.5, n))
    df['spo2'] = clip_to_spec("spo2", spo2)

    # --- NEURO panel: age-dependent impaired subgroup (cognitive + mood) ---
    p_neuro = np.clip(NEURO_IMPAIRED_BASE + NEURO_IMPAIRED_PER_YEAR * (age - 18), 0.0, 0.9)
    neuro_imp = np.random.rand(n) < p_neuro
    phq9 = np.where(neuro_imp, np.random.normal(13, 5, n), np.random.normal(4, 3, n))
    gad7 = np.where(neuro_imp, np.random.normal(11, 4, n), np.random.normal(3, 2.5, n))
    mmse = np.where(neuro_imp, np.random.normal(20, 4.5, n), np.random.normal(28, 1.8, n))
    df['phq9'] = clip_to_spec("phq9", phq9).astype(int)
    df['gad7'] = clip_to_spec("gad7", gad7).astype(int)
    df['mmse'] = clip_to_spec("mmse", mmse).astype(int)
    df['sleep_hours'] = clip_to_spec("sleep_hours", np.random.normal(7, 1.5, size=n))

    # Impairment flags are NOT stored: outcomes must depend on the biomarkers, not on the flag
    return df
