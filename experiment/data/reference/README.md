# Reference Data — Synthetic Cohort Pipeline

Reference files for the synthetic cohort pipeline, and which module reads each one.

## Active files

| File | What it holds | Read by code? |
|---|---|---|
| `cdss_spec.json` | Feature bounds and FHRS constants from `CDSS_Data_Dictionary.pdf` (physician-validated) | Yes — `spec.py` (all generator modules, `check_fixes.py`) |
| `bmi_reference_quartiles.json` | Approximate adult BMI quartiles 24.8 / 28.5 / 33.2 (provenance unverified; not cited as NHANES) | Yes — `validate.py`, Gate 2 |
| `SYNTHETIC_ISSUES_REGISTER.md` | Current issues register (v8) | — |

## Archived files (`_archive/`)

Kept for history only; not read by any module and not cited in the thesis.

| File | Note |
|---|---|
| `nhanes_sbp_2017_2020.json` | Summary values, no source |
| `nhanes_lipids_2017_2020.json` | Summary values, no source |
| `nhanes_hba1c_2017_2020.json` | Summary values, no source |
| `framingham_cvd_coefficients.json` | Names the Framingham Heart Study (D'Agostino et al., 2008); not checked against the paper |
| `aric_longitudinal_drift.json` | Names the ARIC Study; not checked against the source |

## How parameters are actually set

- **Feature bounds and FHRS constants** come from `cdss_spec.json` via `spec.py`.
- **Biomarker distributions** (means, SDs, impaired subgroups) are written in `distributions.py`.
  BMI is lognormal, fitted to the quartiles in `bmi_reference_quartiles.json`, so **Gate 2 is a
  calibration check, not independent validation**.
- **Outcome coefficients** in `dag.py` (`COEFS`) are calibration parameters tuned to meet
  Gates 4, 6 and 7.
- **Annual drift rates** are written in `longitudinal.py`.

## Provenance

`bmi_reference_quartiles.json` was previously named `nhanes_bmi_2017_2020.json`. It was renamed
because its quartiles have not been matched to a published NHANES table. `check_reference.py`
confirms it was not written by the old generator bug (audit item C6).

    uv run python experiment/src/synthetic/check_reference.py
