# ML Pipeline Runbook

How to run the CDSS machine-learning pipeline from a clean start, in order.
Run every command from the project root: `~/Desktop/thesis draft-1`.

---

## Target folder structure

```
thesis draft-1/
├── pyproject.toml / uv.lock
├── backend/
│   └── cdss/model_loader.py          MODEL_DIR → experiment/data/models
└── experiment/
    ├── RUNBOOK.md                    this file
    ├── data/
    │   ├── raw/cohort.parquet        frozen v11 (never edit)
    │   ├── reference/                generator reference files (cdss_spec.json, quartiles, _archive/)
    │   ├── processed/partitions.csv  written by data.py
    │   └── models/                   written by train.py
    │       ├── {head}_head_latest.joblib / .json   ← backend loads these
    │       ├── {head}_head_v1.joblib / .json       ← archive copy
    │       └── {head}_trials.csv                   ← Optuna history (one row per trial)
    ├── docs/
    │   └── SYNTHETIC_ISSUES_REGISTER.md
    ├── mlruns/mlflow.db              written by train.py (MLflow tracking)
    ├── notebooks/
    │   ├── 00_generate_and_validate.ipynb   synthetic cohort (done)
    │   ├── 01_training.ipynb                walkthrough of data → model → calibration
    │   └── 02_gate_evaluation.ipynb         8 gates, ablation, baselines, holdout (last)
    ├── reports/figures/              Chapter 4 plots saved by 02
    └── src/
        ├── synthetic/                generator (frozen)
        └── ml/
            ├── profile_cohort.py     one-time cohort check
            ├── data.py               features, labels, partitions (also used by backend)
            ├── train.py              train + calibrate + save one head
            └── evaluate.py           gate functions used by 02
```

---

## Step 0 — Clean up the folders (once)

These commands only remove empty folders or exact duplicates; each checks first.

```bash
# 0.1  Top-level experiment/models/ is not used (models live in experiment/data/models/)
ls -la experiment/models/
rmdir experiment/models          # fails safely with "Directory not empty" if anything is inside

# 0.2  The issues register exists twice; keep the docs/ copy if they are identical
diff experiment/docs/SYNTHETIC_ISSUES_REGISTER.md experiment/data/reference/SYNTHETIC_ISSUES_REGISTER.md \
  && echo "IDENTICAL"
grep -rn "SYNTHETIC_ISSUES_REGISTER" experiment/src
# only if the first command printed IDENTICAL and the grep printed nothing:
rm experiment/data/reference/SYNTHETIC_ISSUES_REGISTER.md

# 0.3  Number the notebooks so they sort in run order
mv experiment/notebooks/syn_generate_and_validate.ipynb experiment/notebooks/00_generate_and_validate.ipynb

# 0.4  Folder for Chapter 4 figures
mkdir -p experiment/reports/figures
```

If 0.1 says "not empty", stop and check what is inside before moving anything.
If the generator code reads the register from `data/reference/`, skip 0.2.

---

## Step 1 — Install dependencies (once)

```bash
uv add xgboost optuna mlflow scipy matplotlib ipykernel pingouin fairlearn
uv add shap        # optional, see note
uv sync
```

| Package | Used for |
| --- | --- |
| xgboost, optuna | model and tuning (train.py) |
| mlflow | run tracking (train.py) |
| scipy | DeLong test, bootstrap (evaluate.py) |
| matplotlib | plots in the notebooks |
| ipykernel | lets VS Code run the notebooks with this `.venv` |
| pingouin | ICC(2,1) for the stability gate |
| fairlearn | subgroup metrics |
| shap | SHAP plots |

**If `uv add shap` fails** (SHAP can lag behind new Python versions): skip it. XGBoost computes the
same exact TreeSHAP values itself with `booster.predict(dmatrix, pred_contribs=True)`, and the
notebooks use that if `shap` is missing.

**Check:**
```bash
uv run python -c "import xgboost, optuna, mlflow, scipy, matplotlib, pingouin; print('ok')"
```

In VS Code, open any notebook → **Select Kernel** → choose `.venv (thesis-draft-1)`.

---

## Step 2 — Verify the frozen cohort

```bash
sha256sum experiment/data/raw/cohort.parquet
```
Expected: `23d28b00c57b3895f914526d446e8623b4a96b8adc0996a51e6306821fbcb5e3`.
If it differs, stop: the cohort is not the frozen v11 file.

---

## Step 3 — Profile the cohort (optional, already done)

```bash
uv run python experiment/src/ml/profile_cohort.py
```
Prints shape, missingness, follow-up and label behaviour. Rerun only if the cohort changes.

---

## Step 4 — Build and check the data

```bash
uv run python experiment/src/ml/data.py
```
Expected, at the end:
- velocity markers: `['bmi', 'egfr', 'hba1c', 'systolic_bp']`
- features: CVD 18, T2D 15, RESP 10, NEURO 10; nothing dropped by the missingness rule
- `ALL CHECKS PASSED` and `Partitions saved to: …/processed/partitions.csv`

---

## Step 5 — Train the four heads (final run)

Run once more with the updated `train.py`, so every head also saves its tuning history and
logs to MLflow. The earlier runs produced valid models but no history and no MLflow record.

```bash
for d in cvd t2d resp neuro; do
  uv run python experiment/src/ml/train.py --disease $d --trials 100
done
```

Expected per head: `best CV: …`, the calibration method, the conformal thresholds, then
`tuning history: …_trials.csv`, `saved …_head_latest.joblib` and `logged to MLflow`.

Results from the first run, for comparison (CV on the training partition):

| Head | AUROC | Calibration |
| --- | --- | --- |
| CVD | 0.810 | sigmoid |
| T2D | 0.875 | isotonic |
| RESP | 0.736 | isotonic |
| NEURO | 0.813 | sigmoid |

Same seed and data, so the rerun should give the same numbers.

**Check:**
```bash
ls experiment/data/models/
```
Expected: 4 × (`_latest.joblib`, `_latest.json`, `_v1.joblib`, `_v1.json`, `_trials.csv`) = 20 files.

---

## Step 6 — View runs in MLflow (optional)

```bash
uv run mlflow ui --backend-store-uri "sqlite:///$(pwd)/experiment/mlruns/mlflow.db"
```
Open http://127.0.0.1:5000. Stop it with Ctrl+C before starting the backend, which also uses port 5000.

---

## Step 7 — Walk through training: `01_training.ipynb`

Open `experiment/notebooks/01_training.ipynb` and run all cells. It does not retrain; it loads the
data and the saved bundles and shows each step: one patient's features, partitions, tuning history,
calibration before/after, and the conformal thresholds on the risk scale.

---

## Step 8 — Gate evaluation: `02_gate_evaluation.ipynb`

Run top to bottom. Order inside the notebook follows §3.7.1:

1. Gates on CV and calibration-partition predictions (no holdout).
2. Subgroup breakdown (sex, age brackets) with case counts and confidence intervals.
3. FHRS ablation and logistic-regression baselines.
4. Remediation decision per head (at most 3 cycles; failing heads are quarantined).
5. **Holdout, once.** The last section. Never rerun it after changing a model.

Figures are saved to `experiment/reports/figures/`.

---

## Step 9 — Connect the backend

1. In `backend/cdss/model_loader.py`, build `MODEL_DIR` from the project root:
   ```python
   PROJECT_ROOT = Path(__file__).resolve().parents[2]
   MODEL_DIR = Path(os.environ.get("CDSS_MODEL_DIR", PROJECT_ROOT / "experiment" / "data" / "models"))
   ```
2. Load `{head}_head_latest.joblib`; it is a dict with `calibrated`, `raw`, `q_hat`,
   `feature_columns` and `tier_cutoffs`. Check its SHA-256 against `artifact_sha256` in the matching
   `.json` before loading.
3. Build request features with `data.add_derived` and `data.feature_columns`, never a second copy.
4. Start the backend, then:
   ```bash
   curl -X POST http://127.0.0.1:5000/api/v1/predictions/models/reload -H "Authorization: Bearer $TOKEN"
   curl http://127.0.0.1:5000/api/v1/predictions/models/status -H "Authorization: Bearer $TOKEN"
   ```
   Expected: all four heads `loaded: true`.
5. Send one `/infer` request. The score must not be `50.0`; if it is, the stub is still serving.

---

## If something fails

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `Cohort SHA-256 mismatch` | cohort file changed | restore the frozen v11 file |
| `ModuleNotFoundError: xgboost` (or optuna, mlflow) | Step 1 skipped | `uv add …`, then `uv sync` |
| `mlflow not installed; skipping run log` | mlflow missing | `uv add mlflow`, rerun Step 5 |
| Notebook can't import `data` | wrong kernel | select the `.venv` kernel |
| Backend score always 50.0 | stub fallback | check `MODEL_DIR` and file names (Step 9) |
