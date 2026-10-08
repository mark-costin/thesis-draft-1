import pandas as pd
import numpy as np
import hashlib
import os

print("🚀 INITIATING SYNTHETIC COHORT GENERATION PIPELINE...")

# ==========================================
# 1. SCAFFOLDING & DETERMINISM (GATE 10)
# ==========================================
SEED = 42
np.random.seed(SEED)
N_PATIENTS = 15000

# ==========================================
# 2. FEATURE SAMPLING & DAG (GATES 3, 9)
# ==========================================
print("🧬 Generating Demographics and Biomarkers...")
patient_ids = [f"PT-{20260000 + i}" for i in range(N_PATIENTS)]
sex = np.random.choice([0, 1], size=N_PATIENTS)
age = np.random.uniform(18, 85, size=N_PATIENTS) 

bmi = np.random.normal(26, 4, size=N_PATIENTS)
hdl = np.random.normal(50, 12, size=N_PATIENTS)

sbp = 100 + (age * 0.3) + np.random.normal(0, 10, size=N_PATIENTS)
hba1c = 4.0 + (bmi * 0.12) + np.random.normal(0, 0.5, size=N_PATIENTS)
tg = 180 - (hdl * 1.2) + np.random.normal(0, 15, size=N_PATIENTS)

fhrs = np.random.uniform(0, 3, size=N_PATIENTS)

# ==========================================
# 3. OUTCOMES & PREVALENCE (GATE 4, 6, 7)
# ==========================================
print("🦠 Injecting Disease Logits & Outcomes...")
def assign_disease(target_pct, logit_formula):
    prob = 1 / (1 + np.exp(-logit_formula))
    threshold = np.percentile(prob, 100 - (target_pct * 100))
    return (prob >= threshold).astype(int)

# GATE 6 FIX: Ang "Sweet Spot" noise ay 1.8 para pumatak sa gitna ng 0.78 at 0.86
cvd_logit = (age * 0.05) + (sbp * 0.02) + (fhrs * 0.8) - 5 + np.random.normal(0, 1.8, size=N_PATIENTS)
cvd_y = assign_disease(0.08, cvd_logit)

t2d_logit = (bmi * 0.2) + (hba1c * 1.5) + (fhrs * 0.7) - 10 + np.random.normal(0, 1.8, size=N_PATIENTS)
t2d_y = assign_disease(0.10, t2d_logit)

resp_logit = (age * 0.03) - (bmi * 0.05) + np.random.normal(0, 1.8, size=N_PATIENTS)
resp_y = assign_disease(0.12, resp_logit)

neuro_logit = (age * 0.06) + (cvd_y * 1.2) + np.random.normal(0, 1.8, size=N_PATIENTS)
neuro_y = assign_disease(0.07, neuro_logit)

base_df = pd.DataFrame({
    'patient_id': patient_ids, 'biological_sex': sex, 'age': age,
    'bmi': bmi, 'sbp': sbp, 'hba1c': hba1c, 'hdl': hdl, 'tg': tg, 'fhrs': fhrs,
    'y_cvd': cvd_y, 'y_t2d': t2d_y, 'y_resp': resp_y, 'y_neuro': neuro_y
})

# ==========================================
# 4. LONGITUDINAL DRIFT (VISITS 1-4)
# ==========================================
print("⏳ Expanding to Longitudinal Visits...")
visit_counts = np.random.choice([1, 2, 3, 4], size=N_PATIENTS, p=[0.60, 0.25, 0.10, 0.05])
longitudinal_data = []

for idx, row in base_df.iterrows():
    v_count = visit_counts[idx]
    for v in range(v_count):
        drift_multiplier = v
        new_row = row.copy()
        new_row['visit_number'] = v + 1
        new_row['days_since_baseline'] = v * 365
        
        new_row['age'] += drift_multiplier
        new_row['sbp'] += (0.6 * drift_multiplier)
        new_row['bmi'] += (0.15 * drift_multiplier)
        new_row['hba1c'] += (0.02 * drift_multiplier)
        
        longitudinal_data.append(new_row)

df_long = pd.DataFrame(longitudinal_data)

# ==========================================
# 5. MISSINGNESS MASKING (GATE 8)
# ==========================================
print("🕳️ Injecting Clinical Missingness...")
biomarkers = ['bmi', 'sbp', 'hba1c', 'hdl', 'tg']
for col in biomarkers:
    mask = np.random.rand(len(df_long)) < 0.40
    df_long[f'{col}_measured'] = (~mask).astype(int)
    df_long.loc[mask, col] = np.nan

# ==========================================
# 6. EXPORT & HASH VERIFICATION
# ==========================================
os.makedirs("ml/data/raw", exist_ok=True)
output_path = "ml/data/raw/cohort.parquet"
df_long.to_parquet(output_path, index=False)

# Hash calculation
with open(output_path, "rb") as f:
    file_hash = hashlib.sha256(f.read()).hexdigest()

print("\n" + "="*50)
print("✅ SYNTHESIS COMPLETE!")
print(f"📊 Total Encounters: {len(df_long)} | Unique Patients: {N_PATIENTS}")
print(f"🔒 SHA-256 Digest: {file_hash}")
print("="*50)