# Synthetic Cohort — Issues Register (v8)

> **Status:** Code-complete. All 10 quality gates and all fix checks pass.
> **Accepted cohort:** `experiment/data/raw/cohort.parquet`
> **SHA-256 (v8):** `e98d963a4ff54e9f664cf5dfe8afce7204adbb8510cc9a7f5cf2661742f7bfb2`
> **Spec file:** `experiment/data/reference/cdss_spec.json` (from CDSS_Data_Dictionary.pdf)
> **Module manifest:** `experiment/data/processed/module_manifest.json`
> **Last verified:** 2026-10-13

This is the only register for the synthetic cohort. Earlier registers (v3–v5) are superseded.

---

## Gate results (v8)

| Gate | Result | Type |
|---|---|---|
| 1. Patient ID Integrity | PASS | By construction |
| 2. BMI quantiles (24.6 / 28.5 / 33.0) | PASS | Calibration (BMI fitted to reference) |
| 3. Correlation sign check | PASS | By construction |
| 4. Prevalence (CVD 0.08, T2D 0.10, RESP 0.12, NEURO 0.07) | PASS | Calibration (intercepts solved) |
| 5. No single-feature dominance (max NMI 0.325, hba1c→y_t2d) | PASS | **Independent** |
| 6. CVD oracle AUROC 0.815 (5-fold CV) | PASS | Calibration |
| 7. FHRS ablation drop 0.027 | PASS | Calibration |
| 8. Missingness 10.2% | PASS | Calibration |
| 9. Subgroup sufficiency (min cell 2,185) | PASS | By construction |
| 10. Determinism (SEED=42) | PASS | **Independent** |

## Key realism results (v8)

| Item | Value |
|---|---|
| HbA1c mean / ≥ 6.5% | 5.65% / 9.1% (T2D prevalence 10.1%) |
| T2D cases with HbA1c ≥ 6.5% | 51.4% |
| FPG–HbA1c correlation | 0.80 |
| SpO₂ < 90 / FEV1/FVC < 60 | 5.9% / 8.9% of measured patients |
| MMSE < 18 / PHQ-9 ≥ 15 | 4.6% / 6.0% |
| FHRS Band 0 (CVD) | 22.3% |
| FHRS Band 4 per disease | 22–39 |

---

## Closed issues (summary by version)

| Version | Fix |
|---|---|
| v3 | Incident-diagnosis labels; contiguous FHRS bands; normalized-MI Gate 5; CV Gates 6/7; temp-file Gate 10 |
| v4 | Per-relative pedigree engine with clustering factor C_d (Band 4 reachable) |
| v5 | Spec onset brackets 3.00 / 2.00 / 1.00 / 0.75; module audit + manifest |
| v6 | CDSS Data Dictionary alignment: bands from Adjusted FHRS, no FHRS noise (Band 0 = score 0.0), dictionary clip bounds, age clipped at follow-up |
| v7 | HbA1c recentred, FPG tied to HbA1c, RESP/NEURO driven by their biomarkers with impaired subgroups, lognormal BMI |
| v8 | Dysglycaemic subgroup closes the T2D/HbA1c gap; T2D BMI weight 0.12 → 0.08 |

---

## Open items

| Item | Belongs to | Status |
|---|---|---|
| BMI reference provenance | Thesis claim | Closed (Option C): file kept as approximate reference; NHANES not named in Chapter 3; Gate 2 described as calibration |
| Visual notebook check | Verification | Open |
| Onset bracket probabilities (0.10 / 0.25 / 0.50 / 0.15) | Physician | Open |
| Impaired-subgroup sizes (RESP ~15%, NEURO ~15%, dysglycaemic ~10%) | Physician | Open |
| Off-dictionary assumptions (tier 2/3 weights 0.5 / 0.25, hazard range 0.05–0.35, relative counts) | Physician | Open |
| Feature count ~22 of ~73 | ML phase | Deferred |

## Chapter 3 limitations

- Gates 2, 4, 6, 7, 8 are calibration targets; 1, 3, 9 hold by construction; only 5 and 10 are independent.
- AUROC is gated for CVD only; T2D, RESP and NEURO discrimination is first tested in the ML phase.
- No cardiac injury or heart-failure markers are generated; lipids do not reach high-risk ranges.
- 51.4% of T2D cases have a diagnostic HbA1c (consistent with treated patients).
- One NEURO impairment subgroup combines cognitive and mood impairment.
- Clipping creates small spikes at feature bounds.
- Band 4 holds 22–39 patients per disease; no per-band metrics.

---

## How to re-verify

```bash
uv run python experiment/src/synthetic/audit_modules.py
uv run python experiment/src/synthetic/generate_cohort.py
uv run python experiment/src/synthetic/validate.py
uv run python experiment/src/synthetic/check_fixes.py
uv run python experiment/src/synthetic/check_reference.py
```
