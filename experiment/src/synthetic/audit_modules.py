import hashlib
import json
import os
import time

BASE = "experiment/src/synthetic"
COHORT = "experiment/data/raw/cohort.parquet"
SPEC_JSON = "experiment/data/reference/cdss_spec.json"
MANIFEST = "experiment/data/processed/module_manifest.json"

# Code that must be present in the current version of each file
REQUIRED = {
    "spec.py":            ["cdss_spec.json", "def clip_to_spec"],
    "distributions.py":   ['clip_to_spec("fev1_fvc_ratio"', "np.random.lognormal(BMI_LOG_MEDIAN",
                           "95 + 25 * (df['hba1c'] - 5.6)", "resp_imp", "neuro_imp", "glyc_imp"],
    "fhrs.py":            ["def _pedigree_score", "FHRS_BASELINE_NOISE = False", "ONSET_BRACKETS",
                           "assign_band(adjusted_fhrs)", "FHRS_SPEC"],
    "dag.py":             ["COEFS = {", "def update_outcomes_longitudinal", "def _solve_intercept",
                           '"fev1_fvc_ratio": -0.06', '"mmse": -0.12', '"bmi": 0.08, "hba1c": 1.8'],
    "longitudinal.py":    ["df.index.repeat(visit_counts)", 'clip_to_spec("age"'],
    "missingness.py":     ['"spirometry": ["fev1", "fvc", "fev1_fvc_ratio"]', "SPECIALIZED_RATE = 0.60",
                           "ROUTINE_RATE = 0.40"],
    "generate_cohort.py": ["COHORT_OUT", "df_long = update_outcomes_longitudinal(df_long)"],
    "validate.py":        ["from dag import COEFS", "StratifiedKFold", "VERIFY_PATH", "NMI < 0.5",
                           "bmi_reference_quartiles.json"],
    "check_fixes.py":     ["uses all 5 bands", "within CDSS range", "Band 0 ⇔ score 0.0",
                           "Realism |", "Diagnostic HbA1c"],
    "__init__.py":        [],
}

# Code from superseded versions that must NOT be present
FORBIDDEN = {
    "__init__.py":      ['print("sample")'],
    "fhrs.py":          ["randint(0, 5", "num_relatives", "assign_band(base_fhrs)"],
    "dag.py":           ["LINEAR = {", "- 9.3", "- 10.3"],
    "validate.py":      ["ks_2samp", "stdout=subprocess.DEVNULL", "nhanes_bmi_2017_2020.json"],
    "distributions.py": ["40, 140)", "60, 300)", "3, 12)",
                         "4.0 + (df['bmi'] * 0.1)", "np.random.normal(29.7, 6.8"],
    "longitudinal.py":  ["70, 220)"],
    "missingness.py":   ["'diastolic_bp', 'bmi']", "'resting_hr'"],
}

def sha16(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:16]

all_ok = True
manifest = {}
print(f"{'File':<20} {'SHA-256 (16)':<18} {'Modified':<20} Status")
print("-" * 78)

for fname, required in REQUIRED.items():
    path = os.path.join(BASE, fname)
    if not os.path.exists(path):
        print(f"{fname:<20} {'-':<18} {'-':<20} ❌ MISSING")
        all_ok = False
        continue
    with open(path, encoding="utf-8") as f:
        src = f.read()
    missing = [s for s in required if s not in src]
    stale = [s for s in FORBIDDEN.get(fname, []) if s in src]
    if fname == "generate_cohort.py":
        n = src.count("update_outcomes_longitudinal")
        if n != 2:
            missing.append(f"update_outcomes_longitudinal x2 (found {n})")
    mtime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(path)))
    h = sha16(path)
    ok = not missing and not stale
    all_ok = all_ok and ok
    status = "✅ current" if ok else "❌ " + "; ".join(
        [f"missing: {m}" for m in missing] + [f"stale code: {s}" for s in stale])
    print(f"{fname:<20} {h:<18} {mtime:<20} {status}")
    manifest[fname] = {"sha256_16": h, "modified": mtime}

if os.path.exists(SPEC_JSON):
    try:
        with open(SPEC_JSON, encoding="utf-8") as f:
            spec = json.load(f)
        n_feat = len(spec["feature_bounds"])
        h = sha16(SPEC_JSON)
        print(f"{'cdss_spec.json':<20} {h:<18} {'':<20} ✅ valid ({n_feat} feature bounds)")
        manifest["cdss_spec.json"] = {"sha256_16": h}
    except Exception as e:
        print(f"{'cdss_spec.json':<20} {'-':<18} {'-':<20} ❌ invalid JSON: {e}")
        all_ok = False
else:
    print(f"{'cdss_spec.json':<20} {'-':<18} {'-':<20} ❌ MISSING")
    all_ok = False

if os.path.exists(COHORT):
    with open(COHORT, "rb") as f:
        manifest["cohort.parquet"] = {"sha256": hashlib.sha256(f.read()).hexdigest()}

os.makedirs(os.path.dirname(MANIFEST), exist_ok=True)
with open(MANIFEST, "w") as f:
    json.dump(manifest, f, indent=2)

print("-" * 78)
print(f"📁 Manifest saved: {MANIFEST}")
print("🏆 ALL MODULES CURRENT" if all_ok else "🚨 STALE OR MISSING CODE FOUND")
