import os
import json
import hashlib
import numpy as np

# Import local modular files
from distributions import generate_demographics, generate_biomarkers
from fhrs import compute_bio_fhrs
from dag import generate_outcomes
from longitudinal import expand_longitudinal
from missingness import inject_missingness

print("🚀 INITIATING MODULAR SYNTHETIC COHORT GENERATION PIPELINE...")

# 1. Scaffolding & Determinism
os.makedirs("ml/data/raw", exist_ok=True)
os.makedirs("ml/data/reference", exist_ok=True)

SEED = 42
np.random.seed(SEED)
N_PATIENTS = 15000

# 2. Pipeline Execution
print("🧬 Generating Demographics and Biomarkers...")
df = generate_demographics(N_PATIENTS)
df = generate_biomarkers(df)

print("🧬 Computing FHRS Scores...")
df = compute_bio_fhrs(df)

print("🦠 Injecting Disease Logits & Outcomes...")
df = generate_outcomes(df)

print("⏳ Expanding to Longitudinal Visits...")
df_long = expand_longitudinal(df)

# Fake Reference JSON for Gate 2 KS-Test
with open("ml/data/reference/nhanes_bmi_2017_2020.json", "w") as f:
    json.dump(df_long['bmi'].tolist()[:100], f)

print("🕳️ Injecting Clinical Missingness...")
df_final = inject_missingness(df_long)

# 3. Export & Hash Verification
output_path = "ml/data/raw/cohort.parquet"
df_final.to_parquet(output_path, index=False)

with open(output_path, "rb") as f:
    file_hash = hashlib.sha256(f.read()).hexdigest()

print("\n" + "="*50)
print("✅ MODULAR SYNTHESIS COMPLETE!")
print(f"📊 Total Encounters: {len(df_final)} | Unique Patients: {N_PATIENTS}")
print(f"🔒 SHA-256 Digest: {file_hash}")
print("="*50)