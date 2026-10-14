# Evaluation record (notebook 02)

Generated 2026-10-13 22:04 UTC · cohort `23d28b00c57b…` · 1000 bootstrap resamples · bundles CVD `84e20c012900…`, T2D `529335855f75…`, RESP `a5c5b67b2609…`, NEURO `2db52e4522bc…`

## 1. Data

| partition | patients | visits |
| --- | --- | --- |
| train | 10500 | 16826 |
| calib_iso | 1125 | 1843 |
| calib_conf | 1125 | 1761 |
| holdout | 2250 | 3566 |

## 2. Gates on calib_conf

| head | 1 Discrimination | 2 Calibration | 3 Clinical utility | 4 Subgroup fairness | 5 Stability | all gates |
| --- | --- | --- | --- | --- | --- | --- |
| CVD | FAIL | pass | pass | pass | pass | FAIL |
| T2D | pass | pass | pass | FAIL | pass | FAIL |
| RESP | FAIL | FAIL | pass | FAIL | pass | FAIL |
| NEURO | pass | FAIL | FAIL | FAIL | pass | FAIL |

- **CVD** (1,125 patients, 97 with the disease): fails AUROC 0.771 (95% CI 0.711 to 0.825), target ≥ 0.80.
- **T2D** (1,125 patients, 115 with the disease): fails Subgroup ΔAUROC (sex, age) 0.071 (95% CI 0.042 to 0.211), target < 0.05.
- **RESP** (1,125 patients, 140 with the disease): fails AUROC 0.711 (95% CI 0.658 to 0.760), target ≥ 0.75; Calibration slope 0.698 (95% CI 0.380 to 1.080), target 0.90–1.10; Subgroup ΔAUROC (sex, age) 0.071 (95% CI 0.037 to 0.201), target < 0.05.
- **NEURO** (1,125 patients, 79 with the disease): fails Calibration slope 0.840 (95% CI 0.672 to 1.040), target 0.90–1.10; DCA net-benefit margin -0.004 (95% CI -0.012 to 0.005), target ≥ 0 for every p_t in 0.10–0.40; Subgroup ΔAUROC (sex, age) 0.064 (95% CI 0.029 to 0.236), target < 0.05.

Every metric:

| head | gate | metric | estimate | 95% CI | target | pass |
| --- | --- | --- | --- | --- | --- | --- |
| CVD | 1 Discrimination | AUROC | 0.771 | 0.711 – 0.825 | ≥ 0.80 | FAIL |
| CVD | 1 Discrimination | AUPRC | 0.287 | 0.203 – 0.394 | ≥ 2π = 0.165 | pass |
| CVD | 2 Calibration | ECE | 0.014 | 0.013 – 0.036 | ≤ 0.05 | pass |
| CVD | 2 Calibration | Brier | 0.0676 | 0.0554 – 0.0814 | < π(1−π) = 0.0756 | pass |
| CVD | 2 Calibration | Calibration slope | 0.970 | 0.761 – 1.196 | 0.90–1.10 | pass |
| CVD | 3 Clinical utility | DCA net-benefit margin | 0.000 | -0.006 – 0.006 | ≥ 0 for every p_t in 0.10–0.40 | pass |
| CVD | 4 Subgroup fairness | Subgroup ΔAUROC (sex, age) | 0.040 | 0.037 – 0.281 | < 0.05 | pass |
| CVD | 5 Stability | ICC(2,1) under ±2% lab noise | 0.996 | 0.994 – 0.997 | ≥ 0.85 | pass |
| T2D | 1 Discrimination | AUROC | 0.859 | 0.800 – 0.909 | ≥ 0.80 | pass |
| T2D | 1 Discrimination | AUPRC | 0.562 | 0.450 – 0.662 | ≥ 2π = 0.196 | pass |
| T2D | 2 Calibration | ECE | 0.020 | 0.016 – 0.041 | ≤ 0.05 | pass |
| T2D | 2 Calibration | Brier | 0.0585 | 0.0469 – 0.0709 | < π(1−π) = 0.0886 | pass |
| T2D | 2 Calibration | Calibration slope | 0.905 | 0.605 – 1.220 | 0.90–1.10 | pass |
| T2D | 3 Clinical utility | DCA net-benefit margin | 0.034 | 0.016 – 0.050 | ≥ 0 for every p_t in 0.10–0.40 | pass |
| T2D | 4 Subgroup fairness | Subgroup ΔAUROC (sex, age) | 0.071 | 0.042 – 0.211 | < 0.05 | FAIL |
| T2D | 5 Stability | ICC(2,1) under ±2% lab noise | 0.981 | 0.973 – 0.986 | ≥ 0.85 | pass |
| RESP | 1 Discrimination | AUROC | 0.711 | 0.658 – 0.760 | ≥ 0.75 | FAIL |
| RESP | 1 Discrimination | AUPRC | 0.298 | 0.235 – 0.375 | ≥ 2π = 0.251 | pass |
| RESP | 2 Calibration | ECE | 0.026 | 0.021 – 0.049 | ≤ 0.05 | pass |
| RESP | 2 Calibration | Brier | 0.1007 | 0.0864 – 0.1164 | < π(1−π) = 0.1097 | pass |
| RESP | 2 Calibration | Calibration slope | 0.698 | 0.380 – 1.080 | 0.90–1.10 | FAIL |
| RESP | 3 Clinical utility | DCA net-benefit margin | 0.004 | -0.004 – 0.013 | ≥ 0 for every p_t in 0.10–0.40 | pass |
| RESP | 4 Subgroup fairness | Subgroup ΔAUROC (sex, age) | 0.071 | 0.037 – 0.201 | < 0.05 | FAIL |
| RESP | 5 Stability | ICC(2,1) under ±2% lab noise | 0.956 | 0.946 – 0.965 | ≥ 0.85 | pass |
| NEURO | 1 Discrimination | AUROC | 0.806 | 0.753 – 0.854 | ≥ 0.70 | pass |
| NEURO | 1 Discrimination | AUPRC | 0.259 | 0.181 – 0.366 | ≥ 2π = 0.135 | pass |
| NEURO | 2 Calibration | ECE | 0.022 | 0.014 – 0.043 | ≤ 0.05 | pass |
| NEURO | 2 Calibration | Brier | 0.0588 | 0.0467 – 0.0719 | < π(1−π) = 0.0630 | pass |
| NEURO | 2 Calibration | Calibration slope | 0.840 | 0.672 – 1.040 | 0.90–1.10 | FAIL |
| NEURO | 3 Clinical utility | DCA net-benefit margin | -0.004 | -0.012 – 0.005 | ≥ 0 for every p_t in 0.10–0.40 | FAIL |
| NEURO | 4 Subgroup fairness | Subgroup ΔAUROC (sex, age) | 0.064 | 0.029 – 0.236 | < 0.05 | FAIL |
| NEURO | 5 Stability | ICC(2,1) under ±2% lab noise | 0.994 | 0.992 – 0.996 | ≥ 0.85 | pass |

## 3. Subgroup diagnosis (training partition, cross-validated)

| head | XGBoost gap (sex) | XGBoost gap (age) | Domain LR gap (sex) | Domain LR gap (age) | largest gap, XGBoost | largest gap, Domain LR |
| --- | --- | --- | --- | --- | --- | --- |
| CVD | 0.015 | 0.04 | 0.011 | 0.025 | 0.04 | 0.025 |
| T2D | 0.005 | 0.03 | 0.002 | 0.026 | 0.03 | 0.026 |
| RESP | 0.012 | 0.04 | 0.012 | 0.035 | 0.04 | 0.035 |
| NEURO | 0.032 | 0.045 | 0.036 | 0.041 | 0.045 | 0.041 |

- **CVD**: largest gap 0.040 (XGBoost) vs 0.025 (domain LR); below the 0.05 target on this larger sample; about the same as logistic regression, so it comes from the data.
- **T2D**: largest gap 0.030 (XGBoost) vs 0.026 (domain LR); below the 0.05 target on this larger sample; about the same as logistic regression, so it comes from the data.
- **RESP**: largest gap 0.040 (XGBoost) vs 0.035 (domain LR); below the 0.05 target on this larger sample; about the same as logistic regression, so it comes from the data.
- **NEURO**: largest gap 0.045 (XGBoost) vs 0.041 (domain LR); below the 0.05 target on this larger sample; about the same as logistic regression, so it comes from the data.

## 4. Baselines and FHRS ablation (calib_conf)

| head | comparison | comparator AUROC | head AUROC | ΔAUROC | ΔAUROC 95% CI | DeLong p | tier NRI | NRI 95% CI | verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CVD | XGBoost vs Domain LR | 0.774 | 0.771 | -0.003 | -0.012 – 0.007 | 0.4146 | -0.001 | -0.062 – 0.056 | non-inferior |
| CVD | XGBoost vs FHRS-only LR | 0.613 | 0.771 | 0.158 | 0.083 – 0.229 | 0.0 | 0.223 | 0.112 – 0.336 | XGBoost higher |
| CVD | XGBoost vs Biomarker-only LR | 0.74 | 0.771 | 0.032 | 0.001 – 0.065 | 0.0048 | 0.114 | 0.021 – 0.209 | XGBoost higher |
| CVD | Full XGBoost vs without FHRS | 0.738 | 0.771 | 0.033 | 0.005 – 0.066 | 0.002 |  |  | drop within planted 0.015–0.035 |
| T2D | XGBoost vs Domain LR | 0.873 | 0.859 | -0.015 | -0.024 – -0.005 | 0.0004 | 0.07 | 0.007 – 0.139 | non-inferiority NOT shown |
| T2D | XGBoost vs FHRS-only LR | 0.558 | 0.859 | 0.3 | 0.232 – 0.369 | 0.0 | 0.582 | 0.472 – 0.684 | XGBoost higher |
| T2D | XGBoost vs Biomarker-only LR | 0.873 | 0.859 | -0.015 | -0.029 – -0.001 | 0.0038 | 0.131 | 0.054 – 0.213 | XGBoost lower |
| T2D | Full XGBoost vs without FHRS | 0.868 | 0.865 | -0.003 | -0.013 – 0.008 | 0.5118 |  |  | drop outside planted 0.015–0.035 |
| RESP | XGBoost vs Domain LR | 0.714 | 0.711 | -0.003 | -0.014 – 0.009 | 0.5983 | 0.057 | 0.011 – 0.114 | non-inferior |
| RESP | XGBoost vs FHRS-only LR | 0.489 | 0.711 | 0.222 | 0.138 – 0.302 | 0.0 | 0.304 | 0.222 – 0.392 | XGBoost higher |
| RESP | XGBoost vs Biomarker-only LR | 0.716 | 0.711 | -0.004 | -0.016 – 0.006 | 0.3972 | 0.047 | 0.001 – 0.103 | no clear difference |
| RESP | Full XGBoost vs without FHRS | 0.716 | 0.715 | -0.0 | -0.003 – 0.002 | 0.6937 |  |  | drop outside planted 0.015–0.035 |
| NEURO | XGBoost vs Domain LR | 0.818 | 0.806 | -0.012 | -0.025 – 0.003 | 0.0291 | -0.103 | -0.220 – 0.009 | non-inferiority NOT shown |
| NEURO | XGBoost vs FHRS-only LR | 0.687 | 0.806 | 0.119 | 0.049 – 0.183 | 0.0 | 0.097 | -0.053 – 0.249 | XGBoost higher |
| NEURO | XGBoost vs Biomarker-only LR | 0.695 | 0.806 | 0.111 | 0.035 – 0.186 | 0.0 | 0.133 | 0.037 – 0.247 | XGBoost higher |
| NEURO | Full XGBoost vs without FHRS | 0.681 | 0.806 | 0.125 | 0.049 – 0.203 | 0.0 |  |  | drop outside planted 0.015–0.035 |

## 5. AUROC ceiling check (calib_conf)

| head | target | XGBoost head | Domain LR | Reference LR + BioFHRS |
| --- | --- | --- | --- | --- |
| CVD | 0.8 | 0.771 | 0.774 | 0.774 |
| T2D | 0.8 | 0.859 | 0.873 | 0.875 |
| RESP | 0.75 | 0.711 | 0.714 | 0.714 |
| NEURO | 0.7 | 0.806 | 0.818 | 0.816 |

- **CVD** is below its target (0.771 < 0.80); even the reference model stays below it, so the shortfall is a property of the cohort.
- **RESP** is below its target (0.711 < 0.75); even the reference model stays below it, so the shortfall is a property of the cohort.

## 6. Remediation

| head | failed metrics | decision / cycles tried | status |
| --- | --- | --- | --- |
| CVD | AUROC | (not recorded yet) | eligible, failures reported |
| T2D | Subgroup ΔAUROC (sex, age) | (not recorded yet) | eligible, failures reported |
| RESP | AUROC, Calibration slope, Subgroup ΔAUROC (sex, age) | (not recorded yet) | eligible, failures reported |
| NEURO | Calibration slope, DCA net-benefit margin, Subgroup ΔAUROC (sex, age) | (not recorded yet) | eligible, failures reported |

## 7. Holdout

Not run yet. The holdout stays untouched until `RUN_HOLDOUT = True`.

Figures: `experiment/reports/figures/` — `02_dca_calib_conf.png`, `02_subgroup_auroc.png`