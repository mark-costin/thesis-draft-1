import os
import sys
import json
import hashlib
import subprocess
import numpy as np
import pandas as pd
from sklearn.feature_selection import mutual_info_classif
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import make_pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dag import COEFS  # outcome drivers: single source of truth

DATA_PATH = "experiment/data/raw/cohort.parquet"
VERIFY_PATH = "experiment/data/raw/cohort_verify.parquet"
GEN_SCRIPT = "experiment/src/synthetic/generate_cohort.py"
N_PATIENTS = 15000

print("==================================================")
print("🔬 RUNNING V2 AUTOMATED QUALITY GATES (VALIDATION)")
print("==================================================")

df = pd.read_parquet(DATA_PATH)
baseline_df = df[df['visit_number'] == 1].copy()
all_passed = True

def check_gate(gate_name, condition, value=""):
    global all_passed
    if condition:
        print(f"✅ {gate_name}: PASS {value}")
    else:
        print(f"❌ {gate_name}: FAIL {value}")
        all_passed = False

# --- GATE 1: Patient ID Integrity (sanity check) ---
unique_ok = baseline_df['patient_id'].nunique() == N_PATIENTS
visits_ok = (df.groupby('patient_id').cumcount() + 1 == df['visit_number']).all()
check_gate("Gate 1 | Patient ID Integrity", unique_ok and visits_ok)

# --- GATE 2: Distribution Validity (NHANES quantiles, ±10%) ---
with open("experiment/data/reference/bmi_reference_quartiles.json", "r") as f:
    ref_bmi = json.load(f)
p25, p50, p75 = np.percentile(baseline_df['bmi'].dropna(), [25, 50, 75])
within_10_pct = (
    abs(p25 - ref_bmi['p25']) / ref_bmi['p25'] < 0.10 and
    abs(p50 - ref_bmi['p50']) / ref_bmi['p50'] < 0.10 and
    abs(p75 - ref_bmi['p75']) / ref_bmi['p75'] < 0.10
)
check_gate("Gate 2 | Distribution Validity (Quantiles)", within_10_pct,
           f"(p25:{p25:.1f}, p50:{p50:.1f}, p75:{p75:.1f})")

# --- GATE 3: Correlation Sign Check (by construction) ---
c1 = baseline_df['age'].corr(baseline_df['systolic_bp']) > 0.15
c2 = baseline_df['bmi'].corr(baseline_df['hba1c']) > 0.20
c3 = baseline_df['hdl'].corr(baseline_df['tg']) < -0.30
check_gate("Gate 3 | Correlation Sign Check (by construction)", c1 and c2 and c3)

# --- GATE 4: Epidemiological Prevalence Bands (baseline) ---
cvd = baseline_df['y_cvd'].mean()
t2d = baseline_df['y_t2d'].mean()
resp = baseline_df['y_resp'].mean()
neuro = baseline_df['y_neuro'].mean()
g4_pass = (0.06 <= cvd <= 0.10) and (0.08 <= t2d <= 0.12) and (0.10 <= resp <= 0.14) and (0.05 <= neuro <= 0.09)
check_gate("Gate 4 | Epidemiological Prevalence Bands", g4_pass,
           f"(CVD:{cvd:.2f}, T2D:{t2d:.2f}, RESP:{resp:.2f}, NEURO:{neuro:.2f})")

# --- GATE 5: No Single-Feature Dominance (normalized MI < 0.5) ---
# Features = the actual outcome drivers defined in dag.COEFS
def entropy_nats(y):
    p = float(np.mean(y))
    return -(p * np.log(p) + (1 - p) * np.log(1 - p))

MI_FEATURES = {f"y_{d}": list(feats) for d, feats in COEFS.items()}
max_nmi, max_name = 0.0, ""
for target, feats in MI_FEATURES.items():
    for feat in feats:
        sub = baseline_df[[feat, target]].dropna()
        mi = mutual_info_classif(sub[[feat]], sub[target], random_state=42)[0]
        nmi = mi / entropy_nats(sub[target])
        if nmi > max_nmi:
            max_nmi, max_name = nmi, f"{feat}->{target}"
check_gate("Gate 5 | No Single-Feature Dominance (NMI < 0.5)", max_nmi < 0.5,
           f"(Max NMI: {max_nmi:.3f}, {max_name})")

# --- GATE 6 & 7: Oracle AUROC + FHRS Ablation (5-fold CV, shared folds) ---
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

def cv_auroc(cols):
    pipe = make_pipeline(SimpleImputer(strategy='mean'), StandardScaler(),
                         LogisticRegression(max_iter=1000))
    return cross_val_score(pipe, baseline_df[cols], baseline_df['y_cvd'],
                           cv=cv, scoring='roc_auc').mean()

features = ['age', 'bmi', 'systolic_bp', 'hba1c', 'hdl', 'tg', 'bio_fhrs_cvd']
features_no_fhrs = [f for f in features if f != 'bio_fhrs_cvd']

auroc = cv_auroc(features)
check_gate("Gate 6 | Oracle Discriminative Difficulty (5-fold CV)", 0.78 <= auroc <= 0.86, f"(AUROC: {auroc:.3f})")

drop = auroc - cv_auroc(features_no_fhrs)
check_gate("Gate 7 | FHRS Signal Ablation Drop (5-fold CV)", 0.015 <= drop <= 0.035, f"(Drop: {drop:.3f})")

# --- GATE 8: Missingness Boundary ---
req_fields = ['age', 'biological_sex', 'bio_fhrs_cvd', 'patient_id', 'visit_number']
zero_miss_pass = df[req_fields].isna().sum().sum() == 0
overall_missing_pct = df.isna().mean().mean() * 100
check_gate("Gate 8 | Missingness Boundary (8-12%)", zero_miss_pass and (8 <= overall_missing_pct <= 12),
           f"({overall_missing_pct:.1f}%)")

# --- GATE 9: Subgroup Sufficiency ---
age_groups = pd.cut(baseline_df['age'], bins=[18, 44, 64, 100], include_lowest=True)
min_subgroup = baseline_df.groupby([age_groups, 'biological_sex'], observed=False).size().min()
check_gate("Gate 9 | Demographic Subgroup Sufficiency", min_subgroup >= 1500, f"(Min cell: {min_subgroup})")

# --- GATE 10: Determinism (second run to a temp file; cohort never overwritten) ---
def data_hash(path):
    d = pd.read_parquet(path)
    h = hashlib.sha256()
    h.update("|".join(d.columns).encode())
    h.update(pd.util.hash_pandas_object(d, index=True).values.tobytes())
    return h.hexdigest()

print("   [Gate 10] Regenerating to temp file for comparison...")
env = dict(os.environ, COHORT_OUT=VERIFY_PATH)
result = subprocess.run(["uv", "run", "python", GEN_SCRIPT],
                        capture_output=True, text=True, env=env)
try:
    if result.returncode != 0:
        check_gate("Gate 10| Determinism", False, f"(Subprocess failed: {result.stderr[:200]})")
    elif not os.path.exists(VERIFY_PATH):
        check_gate("Gate 10| Determinism", False, "(Temp file not written: check COHORT_OUT in generate_cohort.py)")
    else:
        check_gate("Gate 10| Determinism (SEED=42)", data_hash(DATA_PATH) == data_hash(VERIFY_PATH))
finally:
    if os.path.exists(VERIFY_PATH):
        os.remove(VERIFY_PATH)

print("==================================================")
os.makedirs("experiment/data/processed", exist_ok=True)
with open("experiment/data/processed/gate_report.json", "w") as f:
    json.dump({"status": "passed" if all_passed else "failed",
               "cv_auroc": round(float(auroc), 4), "fhrs_drop": round(float(drop), 4),
               "max_nmi": round(float(max_nmi), 4),
               "missing_pct": round(float(overall_missing_pct), 2)}, f, indent=2)
if all_passed:
    print("🏆 ALL 10 V2 GATES PASSED! PIPELINE ACCEPTED.")
else:
    print("🚨 SOME GATES FAILED. REVISE GENERATOR CODE.")
print("==================================================")
