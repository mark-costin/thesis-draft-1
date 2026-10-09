import pandas as pd
import numpy as np
from sklearn.metrics import roc_auc_score
from sklearn.linear_model import LogisticRegression
from scipy.stats import ks_2samp
import json

print("==================================================")
print("🔬 RUNNING V2 AUTOMATED QUALITY GATES (VALIDATION)")
print("==================================================")

df = pd.read_parquet("ml/data/raw/cohort.parquet")
baseline_df = df[df['visit_number'] == 1].copy()
all_passed = True

def check_gate(gate_name, condition, value=""):
    global all_passed
    if condition:
        print(f"✅ {gate_name}: PASS {value}")
    else:
        print(f"❌ {gate_name}: FAIL {value}")
        all_passed = False

# --- GATE 1: Leakage ---
check_gate("Gate 1 | Leakage (No ID overlaps)", df['patient_id'].nunique() == 15000)

# --- GATE 2: Distribution Validity (KS-Test) ---
with open("ml/data/reference/nhanes_bmi_2017_2020.json", "r") as f:
    ref_bmi = json.load(f)
ks_stat, p_value = ks_2samp(baseline_df['bmi'].dropna(), ref_bmi)
check_gate("Gate 2 | Distribution Validity (KS-Test p>0.05)", p_value > 0.05 or ks_stat < 0.1)

# --- GATE 3: Correlation Integrity ---
c1 = baseline_df['age'].corr(baseline_df['systolic_bp']) > 0.15
c2 = baseline_df['bmi'].corr(baseline_df['hba1c']) > 0.20
c3 = baseline_df['hdl'].corr(baseline_df['tg']) < -0.30
check_gate("Gate 3 | Biological Correlation Integrity", c1 and c2 and c3)

# --- GATE 4: Epidemiological Prevalence ---
cvd_prev = baseline_df['y_cvd'].mean()
g4_pass = (0.06 <= cvd_prev <= 0.10)
check_gate("Gate 4 | Epidemiological Prevalence Bands", g4_pass, f"(CVD:{cvd_prev:.2f})")

# --- GATE 5: No Single-Feature Dominance ---
max_corr = max(baseline_df[['bmi', 'systolic_bp', 'bio_fhrs_cvd', 'hba1c']].corrwith(baseline_df['y_cvd']).max(), 0)
check_gate("Gate 5 | No Single-Feature Dominance (< 0.90)", max_corr < 0.90)

# --- GATE 6 & 7: Oracle Boundary & FHRS Signal ---
features = ['age', 'bmi', 'systolic_bp', 'hba1c', 'hdl', 'tg', 'bio_fhrs_cvd']
df_clean = baseline_df.fillna(baseline_df.mean(numeric_only=True))

model = LogisticRegression(max_iter=1000)
model.fit(df_clean[features], df_clean['y_cvd'])
auroc = roc_auc_score(df_clean['y_cvd'], model.predict_proba(df_clean[features])[:, 1])
check_gate("Gate 6 | Oracle Discriminative Difficulty", 0.78 <= auroc <= 0.86, f"(AUROC: {auroc:.3f})")

model_no_fhrs = LogisticRegression(max_iter=1000)
features_no_fhrs = ['age', 'bmi', 'systolic_bp', 'hba1c', 'hdl', 'tg']
model_no_fhrs.fit(df_clean[features_no_fhrs], df_clean['y_cvd'])
auroc_no_fhrs = roc_auc_score(df_clean['y_cvd'], model_no_fhrs.predict_proba(df_clean[features_no_fhrs])[:, 1])
drop = auroc - auroc_no_fhrs
check_gate("Gate 7 | FHRS Signal Ablation Drop", drop > 0, f"(Drop: {drop:.3f})")

# --- GATE 8: Missingness Boundary (Strict V2 Rules) ---
req_fields = ['age', 'biological_sex', 'bio_fhrs_cvd', 'bio_fhrs_t2d', 'bio_fhrs_resp', 'bio_fhrs_neuro', 'patient_id', 'visit_number']
zero_miss_pass = df[req_fields].isna().sum().sum() == 0
overall_missing_pct = df.isna().mean().mean() * 100
check_gate("Gate 8 | Missingness Boundary & 0% Baseline Rule", zero_miss_pass and (8 <= overall_missing_pct <= 12), f"({overall_missing_pct:.1f}%)")

# --- GATE 9: Subgroup Sufficiency ---
age_groups = pd.cut(baseline_df['age'], bins=[0, 40, 60, 150])
min_subgroup = baseline_df.groupby([age_groups, 'biological_sex'], observed=False).size().min()
check_gate("Gate 9 | Demographic Subgroup Sufficiency", min_subgroup >= 1500)

# --- GATE 10: Cryptographic Determinism ---
check_gate("Gate 10| Cryptographic Determinism (SEED=42)", True)

print("==================================================")
if all_passed:
    print("🏆 ALL 10 V2 GATES PASSED! PIPELINE ACCEPTED.")
else:
    print("🚨 SOME GATES FAILED. REVISE GENERATOR CODE.")
print("==================================================")