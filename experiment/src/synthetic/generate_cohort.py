import os
import hashlib
import numpy as np

from distributions import generate_demographics, generate_biomarkers
from fhrs import compute_bio_fhrs
from dag import generate_outcomes, update_outcomes_longitudinal
from longitudinal import expand_longitudinal
from missingness import inject_missingness

print("🚀 INITIATING MODULAR SYNTHETIC COHORT GENERATION PIPELINE...")

os.makedirs("experiment/data/raw", exist_ok=True)
os.makedirs("experiment/data/reference", exist_ok=True)

SEED = 42
np.random.seed(SEED)
N_PATIENTS = 15000

print("🧬 Generating Demographics and Biomarkers...")
df = generate_demographics(N_PATIENTS)
df = generate_biomarkers(df)

print("🧬 Computing FHRS Scores...")
df = compute_bio_fhrs(df)

print("🦠 Injecting Disease Logits & Outcomes...")
df = generate_outcomes(df)

print("⏳ Expanding to Longitudinal Visits...")
df_long = expand_longitudinal(df)

print("🔁 Updating Outcomes Across Visits (incident diagnosis)...")
df_long = update_outcomes_longitudinal(df_long)

print("🕳️ Injecting Clinical Missingness...")
df_final = inject_missingness(df_long)

# Output path can be overridden (used by Gate 10 to write a temp copy)
output_path = os.environ.get("COHORT_OUT", "experiment/data/raw/cohort.parquet")
df_final.to_parquet(output_path, index=False)

with open(output_path, "rb") as f:
    file_hash = hashlib.sha256(f.read()).hexdigest()

print("\n" + "=" * 50)
print("✅ MODULAR SYNTHESIS COMPLETE!")
print(f"📊 Total Encounters: {len(df_final)} | Unique Patients: {N_PATIENTS}")
print(f"📁 Output: {output_path}")
print(f"🔒 SHA-256 Digest: {file_hash}")
print("=" * 50)
