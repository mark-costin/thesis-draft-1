# Synthetic Cohort — Issues Register (v5, Closed)

> **Status:** Synthetic data creation complete. All 10 quality gates and all 19 fix checks pass.
> **Accepted cohort:** `experiment/data/raw/cohort.parquet`
> **SHA-256 (v5):** `dc2f85606c396536e7e7f7ed1ca1db5724ed17bf7002df37ee8797a08952999d`
> **Module manifest:** `experiment/data/processed/module_manifest.json`
> **Last verified:** 2026-10-13

This is the only register for the synthetic cohort. Earlier registers (v3, v4) existed only as notes
and are superseded by this file; their history is summarised below.

---

## Final results (v5)

| Gate | Result | Target |
|---|---|---|
| 1. Patient ID Integrity | PASS | unique IDs, visits 1..k |
| 2. Distribution Validity (BMI quantiles) | PASS (p25 25.1, p50 29.7, p75 34.3) | ±10% of NHANES |
| 3. Correlation Sign Check (by construction) | PASS | sanity check |
| 4. Prevalence | PASS (CVD 0.08, T2D 0.10, RESP 0.12, NEURO 0.07) | disease bands |
| 5. No Single-Feature Dominance | PASS (max NMI 0.191, bmi→y_t2d) | NMI < 0.5 |
| 6. Oracle AUROC (5-fold CV) | PASS (0.825) | 0.78–0.86 |
| 7. FHRS Ablation Drop (5-fold CV) | PASS (0.027) | 0.015–0.035 |
| 8. Missingness | PASS (10.2%) | 8–12% |
| 9. Subgroup Sufficiency | PASS (min cell 2,185) | ≥ 1,500 |
| 10. Determinism | PASS | identical second run |

FHRS bands at baseline (15,000 patients):

| Disease | Band 0 | Band 1 | Band 2 | Band 3 | Band 4 | Max FHRS |
|---|---|---|---|---|---|---|
| CVD | 247 | 11,402 | 3,008 | 334 | 9 | 7.91 |
| T2D | 216 | 11,432 | 3,038 | 311 | 3 | 7.54 |
| RESP | 223 | 11,398 | 3,042 | 321 | 16 | 8.44 |
| NEURO | 218 | 11,557 | 2,907 | 309 | 9 | 8.39 |

---

## Closed issues

### v3 review
| # | Issue | Resolution |
|---|---|---|
| 1 | Band 4 unreachable (old max 5.5 < 6.00) | Per-relative pedigree engine + clustering factor C_d. Option A (`randint(0, 11)`) rejected: unrealistic relative counts, ~2× FHRS scale |
| 3 | Duplicate comment in `fhrs.py` | Removed in rewrite |
| 4 | Gate 5 features ≠ outcome drivers | `dag.COEFS` is the single source; `validate.py` reads it |

### v4 review
| # | Issue | Resolution |
|---|---|---|
| A | Superseded register on disk | No old register file existed; this file is the single register |
| B | Confirm `FHRS_BASELINE_NOISE` exists | Confirmed by `audit_modules.py` |
| C | Stale-file audit | `audit_modules.py`: content checks for all 9 modules + hash manifest — all current |
| E | Onset was uniform 1.0–2.0, spec has brackets | Discrete brackets 3.00 / 2.00 / 1.00 / 0.75 (`ONSET_MODE = "brackets"`) |

---

## Out of scope for synthetic data creation

| Item | Belongs to | Note |
|---|---|---|
| Band 0 share (~1.6%) | Physician review | `FHRS_BASELINE_NOISE = False` removes noise for all patients → Band 0 ≈ 22% or slightly more |
| Onset bracket probabilities (0.10 / 0.25 / 0.50 / 0.15) | Physician review | Values follow the spec; probabilities are an assumption |
| Pedigree constants (kinship, verification, clustering weights) | Physician review | Confirm against `CDSS_Data_Dictionary.pdf` |
| Feature count ~22 vs ~73 | ML phase | Revisit only if model AUROC targets fail |
| Band 4 sample size (3–16 per disease) | Thesis (Chapter 3) | Do not report per-band metrics for Band 4 |
| Gates 4, 6, 7, 8 are calibration targets | Thesis (Chapter 3) | Disclose; generator was tuned to meet them |

---

## Digest history

| Version | Digest (first 8) | What changed |
|---|---|---|
| v5 (accepted) | `dc2f8560` | Onset brackets per spec |
| v4 | `efa755eb` | Per-relative pedigree engine, Band 4 reachable |
| v3 | `7cba6802` | Incident-diagnosis labels, CV gates, temp-file Gate 10 |
| v2 | `81eeebb5` | Self-calibrating intercepts, all fixes live |
| v1 | `d1539d7e` | First 10/10 (old generator code) |

---

## How to re-verify

```bash
uv run python experiment/src/synthetic/audit_modules.py
uv run python experiment/src/synthetic/generate_cohort.py
uv run python experiment/src/synthetic/validate.py
uv run python experiment/src/synthetic/check_fixes.py
```

Expected: `ALL MODULES CURRENT`, `ALL 10 V2 GATES PASSED`, `ALL FIX CHECKS PASSED`, digest `dc2f8560…`.
