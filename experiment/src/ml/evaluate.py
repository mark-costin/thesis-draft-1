"""Gate evaluation for the four CDSS disease heads (Chapter 3, §3.7). Used by 02_gate_evaluation.ipynb.

Place at: experiment/src/ml/evaluate.py

What is here:
  - the eight metrics of §3.7.1, grouped into the five gates, each with a patient-clustered bootstrap CI
  - the stability check: ±2% noise on lab values, ICC(2,1) of the risk scores
  - subgroup AUROC tables (sex, age brackets) with case counts
  - comparators: three logistic-regression baselines (§3.7.3) and the FHRS ablation (§3.7.2),
    compared by ΔAUROC (DeLong test + bootstrap CI), ΔAUPRC and tier NRI
  - conformal coverage by class

Nothing here trains the heads or touches the saved bundles.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit, logit
from scipy.stats import norm, rankdata
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

try:
    from . import data as D
    from . import train as T
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import data as D
    import train as T

# §3.7.1 targets
AUROC_TARGET = {"cvd": 0.80, "t2d": 0.80, "resp": 0.75, "neuro": 0.70}
ECE_MAX = 0.05
SLOPE_RANGE = (0.90, 1.10)
DCA_THRESHOLDS = np.round(np.arange(0.10, 0.4001, 0.01), 2)
SUBGROUP_MAX_GAP = 0.05
ICC_MIN = 0.85
NOISE = 0.02                    # ±2% lab noise
N_REPLICATES = 10               # noisy copies per row for the ICC
NONINFERIORITY_MARGIN = -0.02   # §3.7.3
PLANTED_FHRS_DROP = (0.015, 0.035)   # validation gate 7 (§3.7.2)
N_BOOT = 1000

BASELINES = ["Domain LR", "FHRS-only LR", "Biomarker-only LR"]
ABLATION = "XGBoost without FHRS"
REFERENCE = "Domain LR + BioFHRS (reference only)"


# ---------------------------------------------------------------------------
# Data for one head and one partition
# ---------------------------------------------------------------------------

def eval_rows(df: pd.DataFrame, labels: pd.DataFrame, row_part: pd.Series, disease: str,
              partition: str, columns: list[str]) -> dict:
    """Rows of one partition with everything the gates need."""
    sub = df.loc[(row_part == partition).to_numpy()]
    return {
        "disease": disease,
        "partition": partition,
        "rows": sub,
        "X": sub[columns].astype(float),
        "y": sub["patient_id"].map(labels[f"y_{disease}"]).to_numpy(int),
        "groups": sub["patient_id"].to_numpy(),
        "sex": sub["biological_sex"].to_numpy(float),
        "age": sub["age"].to_numpy(float),
    }


# ---------------------------------------------------------------------------
# Patient-clustered bootstrap
# ---------------------------------------------------------------------------

def cluster_bootstrap(stat, groups, n_boot: int = N_BOOT, seed: int = D.SEED):
    """Resample patients with replacement; every row of a sampled patient comes along.

    stat(idx) returns a 1-D array of statistics for the rows idx.
    Returns (point, ci_low, ci_high) as arrays (95% percentile interval).
    """
    codes, uniq = pd.factorize(pd.Series(groups))
    n_pat, rows = len(uniq), np.arange(len(codes))
    rng = np.random.default_rng(seed)
    point = np.atleast_1d(np.asarray(stat(rows), float))
    reps = np.full((n_boot, point.size), np.nan)
    for b in range(n_boot):
        counts = np.bincount(rng.integers(0, n_pat, n_pat), minlength=n_pat)
        idx = np.repeat(rows, counts[codes])
        try:
            reps[b] = stat(idx)
        except ValueError:          # e.g. a resample with only one class
            pass
    lo, hi = np.nanpercentile(reps, [2.5, 97.5], axis=0)
    return point, lo, hi


# ---------------------------------------------------------------------------
# Metrics not in train.py
# ---------------------------------------------------------------------------

def calibration_slope(y, p, eps: float = 1e-4) -> float:
    """Slope β of the logistic recalibration y ~ a + β·logit(p). β = 1 is ideal (§3.7.1)."""
    y = np.asarray(y, float)
    x = logit(np.clip(np.asarray(p, float), eps, 1 - eps))
    X = np.column_stack([np.ones_like(x), x])
    beta = np.zeros(2)
    for _ in range(100):                                   # Newton–Raphson
        mu = expit(X @ beta)
        w = mu * (1 - mu)
        step = np.linalg.solve((X * w[:, None]).T @ X + 1e-9 * np.eye(2), X.T @ (y - mu))
        beta += step
        if np.abs(step).max() < 1e-8:
            break
    return float(beta[1])


def net_benefit(y, p, thresholds=DCA_THRESHOLDS):
    """Decision-curve net benefit of the model and of treat-all at each threshold p_t."""
    y, p = np.asarray(y), np.asarray(p)
    pt = np.asarray(thresholds, float)
    n = len(y)
    treat = p[None, :] >= pt[:, None]
    tp = (treat & (y == 1)).sum(1) / n
    fp = (treat & (y == 0)).sum(1) / n
    odds = pt / (1 - pt)
    prev = y.mean()
    return tp - fp * odds, prev - (1 - prev) * odds


def dca_margin(y, p, thresholds=DCA_THRESHOLDS) -> float:
    """Smallest gap between the model and the better of treat-all / treat-none over the range.
    0 or above means the model is never worse than either strategy. At a high threshold where the
    model flags no one, its net benefit equals treat-none (0): a tie, not a loss."""
    nb, nb_all = net_benefit(y, p, thresholds)
    return float(np.min(nb - np.maximum(nb_all, 0.0)))


def dca_share_better(y, p, thresholds=DCA_THRESHOLDS) -> float:
    """Share of thresholds in the range where the model is strictly better than both strategies."""
    nb, nb_all = net_benefit(y, p, thresholds)
    return float(np.mean(nb > np.maximum(nb_all, 0.0) + 1e-12))


def icc_2_1(Y) -> float:
    """ICC(2,1): two-way random effects, absolute agreement, single measurement (Koo & Li, 2016).
    Rows are encounters, columns are repeated measurements (original + noisy copies)."""
    Y = np.asarray(Y, float)
    n, k = Y.shape
    gm = Y.mean()
    row_m, col_m = Y.mean(1), Y.mean(0)
    msr = k * ((row_m - gm) ** 2).sum() / (n - 1)
    msc = n * ((col_m - gm) ** 2).sum() / (k - 1)
    mse = ((Y - row_m[:, None] - col_m[None, :] + gm) ** 2).sum() / ((n - 1) * (k - 1))
    return float((msr - mse) / (msr + (k - 1) * mse + k * (msc - mse) / n))


def tier_index(p):
    return np.digitize(p, T.TIER_CUTOFFS)       # 0 Low, 1 Moderate, 2 High (same rule as train.risk_tier)


def tier_nri(y, p_new, p_old) -> float:
    """Categorical NRI over the three risk tiers: events should move up, non-events down."""
    y = np.asarray(y)
    new, old = tier_index(p_new), tier_index(p_old)
    up, down, ev = new > old, new < old, y == 1
    return float((up[ev].mean() - down[ev].mean()) + (down[~ev].mean() - up[~ev].mean()))


def delong_test(y, p1, p2):
    """Paired DeLong test for AUROC(p1) - AUROC(p2). Returns (difference, two-sided p-value).

    DeLong treats rows as independent; encounters of the same patient are not, so the
    patient-clustered bootstrap CI is the primary interval and this p-value is reported alongside.
    """
    y = np.asarray(y)
    pos = y == 1
    m, n = pos.sum(), (~pos).sum()
    aucs, v10, v01 = [], [], []
    for p in (np.asarray(p1, float), np.asarray(p2, float)):
        x, z = p[pos], p[~pos]
        tx, tz, txz = rankdata(x), rankdata(z), rankdata(np.concatenate([x, z]))
        aucs.append((txz[:m].sum() / m - (m + 1) / 2) / n)
        v10.append((txz[:m] - tx) / n)
        v01.append(1 - (txz[m:] - tz) / m)
    s = np.cov(np.vstack(v10)) / m + np.cov(np.vstack(v01)) / n
    diff = aucs[0] - aucs[1]
    var = s[0, 0] + s[1, 1] - 2 * s[0, 1]
    pval = float(2 * norm.sf(abs(diff) / np.sqrt(var))) if var > 0 else 1.0
    return float(diff), pval


# ---------------------------------------------------------------------------
# Gate 5: stability under lab noise
# ---------------------------------------------------------------------------

def noisy_predictions(bundle: dict, rows: pd.DataFrame, vel: list[str],
                      n_rep: int = N_REPLICATES, noise: float = NOISE, seed: int = D.SEED) -> np.ndarray:
    """Column 0: risk on the original rows. Columns 1..n_rep: risk after multiplying every domain lab
    value by an independent factor in [1 - noise, 1 + noise]; velocity is recomputed from the noisy values."""
    cols = bundle["feature_columns"]
    labs = [c for c in D.MASKS[bundle["disease"]] if c in rows.columns]
    rng = np.random.default_rng(seed)

    def predict(frame):
        derived, _ = D.add_derived(frame, vel)
        return bundle["calibrated"].predict_proba(derived[cols].astype(float))[:, 1]

    out = [predict(rows)]
    for _ in range(n_rep):
        noisy = rows.copy()
        for c in labs:
            noisy[c] = noisy[c] * (1 + rng.uniform(-noise, noise, len(noisy)))
        out.append(predict(noisy))
    return np.column_stack(out)


# ---------------------------------------------------------------------------
# All gates for one head
# ---------------------------------------------------------------------------

def evaluate_gates(bundle: dict, ev: dict, vel: list[str], n_boot: int = N_BOOT):
    """Eight metrics in five gates, each with a 95% patient-clustered bootstrap CI.
    'pass' compares the point estimate with the target; the CI shows how sure that is."""
    d = bundle["disease"]
    y, sex, age, groups = ev["y"], ev["sex"], ev["age"], ev["groups"]
    p = bundle["calibrated"].predict_proba(ev["X"])[:, 1]
    prev = float(y.mean())

    def stat(idx):
        yy, pp = y[idx], p[idx]
        return [roc_auc_score(yy, pp), average_precision_score(yy, pp), T.ece(yy, pp),
                brier_score_loss(yy, pp), calibration_slope(yy, pp), dca_margin(yy, pp),
                T.subgroup_auroc_gap(yy, pp, sex[idx], age[idx])]

    point, lo, hi = cluster_bootstrap(stat, groups, n_boot)

    P = noisy_predictions(bundle, ev["rows"], vel)
    i_pt, i_lo, i_hi = cluster_bootstrap(lambda idx: [icc_2_1(P[idx])], groups, n_boot)
    tiers = tier_index(P)
    tier_change = float((tiers != tiers[:, [0]]).any(axis=1).mean())

    auprc_t, brier_t = 2 * prev, prev * (1 - prev)
    spec = [
        ("1 Discrimination", "AUROC", f"≥ {AUROC_TARGET[d]:.2f}", lambda v: v >= AUROC_TARGET[d]),
        ("1 Discrimination", "AUPRC", f"≥ 2π = {auprc_t:.3f}", lambda v: v >= auprc_t),
        ("2 Calibration", "ECE", f"≤ {ECE_MAX}", lambda v: v <= ECE_MAX),
        ("2 Calibration", "Brier", f"< π(1−π) = {brier_t:.4f}", lambda v: v < brier_t),
        ("2 Calibration", "Calibration slope", "0.90–1.10", lambda v: SLOPE_RANGE[0] <= v <= SLOPE_RANGE[1]),
        ("3 Clinical utility", "DCA net-benefit margin", "≥ 0 for every p_t in 0.10–0.40", lambda v: v >= 0),
        ("4 Subgroup fairness", "Subgroup ΔAUROC (sex, age)", f"< {SUBGROUP_MAX_GAP}", lambda v: v < SUBGROUP_MAX_GAP),
    ]
    rows = [{"gate": g, "metric": m, "estimate": point[i], "ci_low": lo[i], "ci_high": hi[i],
             "target": t, "pass": bool(ok(point[i]))} for i, (g, m, t, ok) in enumerate(spec)]
    rows.append({"gate": "5 Stability", "metric": "ICC(2,1) under ±2% lab noise", "estimate": i_pt[0],
                 "ci_low": i_lo[0], "ci_high": i_hi[0], "target": f"≥ {ICC_MIN}", "pass": bool(i_pt[0] >= ICC_MIN)})
    table = pd.DataFrame(rows)
    info = {"p": p, "prevalence": prev, "tier_change_rate": tier_change,
            "dca_share_better": dca_share_better(y, p),
            "n_rows": int(len(y)), "n_patients": int(pd.Series(groups).nunique()),
            "n_case_patients": int(pd.Series(groups[y == 1]).nunique())}
    return table, info


def gate_summary(gates: pd.DataFrame) -> pd.DataFrame:
    """Heads × five gates: a gate passes only if all of its metrics pass."""
    s = gates.groupby(["head", "gate"])["pass"].all().unstack("gate").reindex(gates["head"].unique())
    s = s.map(lambda ok: "pass" if ok else "FAIL")
    s["all gates"] = s.apply(lambda r: "pass" if (r == "pass").all() else "FAIL", axis=1)
    return s


def fmt_gates(gates: pd.DataFrame) -> pd.DataFrame:
    """Readable gate table: estimate, 95% CI, target, pass."""
    def f(v, metric):
        return f"{v:.4f}" if metric == "Brier" else f"{v:.3f}"
    out = gates.copy()
    out["estimate"] = [f(v, m) for v, m in zip(gates["estimate"], gates["metric"])]
    out["95% CI"] = [f"{f(a, m)} – {f(b, m)}" for a, b, m in zip(gates["ci_low"], gates["ci_high"], gates["metric"])]
    out["pass"] = out["pass"].map({True: "pass", False: "FAIL"})
    keys = [c for c in ("head", "gate", "metric") if c in out.columns]
    return out.set_index(keys)[["estimate", "95% CI", "target", "pass"]]


# ---------------------------------------------------------------------------
# Subgroups
# ---------------------------------------------------------------------------

def subgroups(sex, age):
    """(attribute, label, boolean mask) for each sex value and each §3.7.1 age bracket."""
    sex, age = np.asarray(sex), np.asarray(age)
    out = [("sex", f"sex = {s:g}", sex == s) for s in np.unique(sex)]
    out += [("age", f"age {lo}–{hi}", (age >= lo) & (age <= hi)) for lo, hi in T.AGE_BRACKETS]
    return out


def subgroup_table(y, scores: dict, groups, sex, age, n_boot: int = N_BOOT) -> pd.DataFrame:
    """AUROC with 95% CI per subgroup for each model in `scores` ({name: probabilities}),
    plus the size of each subgroup and its number of patients with the disease."""
    y, groups = np.asarray(y), np.asarray(groups)
    rows = []
    for attr, label, m in subgroups(sex, age):
        yy, gg = y[m], groups[m]
        row = {"attribute": attr, "subgroup": label, "rows": int(m.sum()),
               "patients": int(pd.Series(gg).nunique()),
               "case patients": int(pd.Series(gg[yy == 1]).nunique()),
               "prevalence": round(float(yy.mean()), 3)}
        for name, p in scores.items():
            pp = np.asarray(p)[m]
            pt, lo, hi = cluster_bootstrap(lambda idx: [roc_auc_score(yy[idx], pp[idx])], gg, n_boot)
            row[f"{name} AUROC"] = round(pt[0], 3)
            row[f"{name} 95% CI"] = f"{lo[0]:.3f} – {hi[0]:.3f}"
        rows.append(row)
    return pd.DataFrame(rows)


def subgroup_gaps(table: pd.DataFrame, names: list[str]) -> dict:
    """Best minus worst AUROC within sex and within age, per model."""
    out = {}
    for name in names:
        for attr in ("sex", "age"):
            v = table.loc[table["attribute"] == attr, f"{name} AUROC"]
            out[f"{name} gap ({attr})"] = round(float(v.max() - v.min()), 3)
    return out


# ---------------------------------------------------------------------------
# Comparators: baselines (§3.7.3), ablation (§3.7.2), reference
# ---------------------------------------------------------------------------

def make_lr():
    """Logistic regression with training-median imputation and scaling (LR cannot take NaN)."""
    return make_pipeline(SimpleImputer(strategy="median", keep_empty_features=True),
                         StandardScaler(), LogisticRegression(max_iter=5000))


def comparator_columns(disease: str, feature_columns: list[str]) -> dict:
    fh = [f"adjusted_fhrs_{disease}", f"fhrs_band_{disease}"]
    no_fh = [c for c in feature_columns if c not in fh]
    return {
        "Domain LR": list(feature_columns),
        "FHRS-only LR": fh,
        "Biomarker-only LR": no_fh,
        ABLATION: no_fh,
        REFERENCE: list(feature_columns) + [f"bio_fhrs_{disease}"],
    }


def fit_comparators(bundle: dict, record: dict, train_rows: pd.DataFrame, y_train) -> dict:
    """Fit every comparator on the training partition. Returns {name: (columns, fitted model)}.

    The ablation reuses the head's tuned XGBoost settings, so the only difference is the
    two FHRS inputs. The reference LR adds BioFHRS, the score the generator used to make
    the labels: it shows roughly how high AUROC can go on this cohort and is never deployable.
    """
    out = {}
    for name, cols in comparator_columns(bundle["disease"], bundle["feature_columns"]).items():
        X = train_rows[cols].astype(float)
        model = T.make_model(record["best_params"]) if name == ABLATION else make_lr()
        out[name] = (cols, model.fit(X, y_train))
    return out


def comparator_scores(comparators: dict, rows: pd.DataFrame) -> dict:
    return {name: m.predict_proba(rows[cols].astype(float))[:, 1] for name, (cols, m) in comparators.items()}


def compare(y, p_new, p_old, groups, n_boot: int = N_BOOT, with_nri: bool = True) -> dict:
    """ΔAUROC and ΔAUPRC (new − old) with clustered-bootstrap CIs, DeLong p-value, tier NRI."""
    y = np.asarray(y)

    def stat(idx):
        out = [roc_auc_score(y[idx], p_new[idx]) - roc_auc_score(y[idx], p_old[idx]),
               average_precision_score(y[idx], p_new[idx]) - average_precision_score(y[idx], p_old[idx])]
        if with_nri:
            out.append(tier_nri(y[idx], p_new[idx], p_old[idx]))
        return out

    pt, lo, hi = cluster_bootstrap(stat, groups, n_boot)
    _, pval = delong_test(y, p_new, p_old)
    res = {"dAUROC": pt[0], "dAUROC_lo": lo[0], "dAUROC_hi": hi[0], "DeLong p": pval,
           "dAUPRC": pt[1], "dAUPRC_lo": lo[1], "dAUPRC_hi": hi[1]}
    if with_nri:
        res.update({"NRI": pt[2], "NRI_lo": lo[2], "NRI_hi": hi[2]})
    return res


def comparison_table(bundle: dict, comparators: dict, ev: dict, n_boot: int = N_BOOT) -> pd.DataFrame:
    """XGBoost head vs each baseline (calibrated ŷ) and vs its FHRS ablation (raw scores)."""
    y, groups = ev["y"], ev["groups"]
    p_cal = bundle["calibrated"].predict_proba(ev["X"])[:, 1]
    p_raw = bundle["raw"].predict_proba(ev["X"])[:, 1]
    scores = comparator_scores(comparators, ev["rows"])
    rows = []
    for name in BASELINES + [ABLATION]:
        is_abl = name == ABLATION
        new = p_raw if is_abl else p_cal
        r = compare(y, new, scores[name], groups, n_boot, with_nri=not is_abl)
        lo, hi = r["dAUROC_lo"], r["dAUROC_hi"]
        if is_abl:
            verdict = ("drop within planted 0.015–0.035" if PLANTED_FHRS_DROP[0] <= r["dAUROC"] <= PLANTED_FHRS_DROP[1]
                       else "drop outside planted 0.015–0.035")
        elif name == "Domain LR":
            verdict = "non-inferior" if lo > NONINFERIORITY_MARGIN else "non-inferiority NOT shown"
        else:
            verdict = "XGBoost higher" if lo > 0 else ("XGBoost lower" if hi < 0 else "no clear difference")
        rows.append({
            "comparison": f"XGBoost vs {name}" if not is_abl else "Full XGBoost vs without FHRS",
            "comparator AUROC": round(roc_auc_score(y, scores[name]), 3),
            "head AUROC": round(roc_auc_score(y, new), 3),
            "ΔAUROC": round(r["dAUROC"], 3), "ΔAUROC 95% CI": f"{lo:.3f} – {hi:.3f}",
            "DeLong p": round(r["DeLong p"], 4),
            "ΔAUPRC": round(r["dAUPRC"], 3), "ΔAUPRC 95% CI": f"{r['dAUPRC_lo']:.3f} – {r['dAUPRC_hi']:.3f}",
            "tier NRI": round(r["NRI"], 3) if not is_abl else None,
            "NRI 95% CI": f"{r['NRI_lo']:.3f} – {r['NRI_hi']:.3f}" if not is_abl else "",
            "verdict": verdict,
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Cross-validated predictions (for the subgroup diagnosis)
# ---------------------------------------------------------------------------

def oof_predictions(make_model, X: pd.DataFrame, y: pd.Series, folds) -> np.ndarray:
    """Out-of-fold probabilities: each training row is scored by a model that never saw its patient."""
    p = np.full(len(y), np.nan)
    for tr, va in folds:
        m = make_model().fit(X.iloc[tr], y.iloc[tr])
        p[va] = m.predict_proba(X.iloc[va])[:, 1]
    return p


# ---------------------------------------------------------------------------
# Conformal coverage
# ---------------------------------------------------------------------------

def conformal_summary(p, y, q_hat: dict) -> dict:
    """Share of sick / healthy rows whose true label is in the prediction set (target ≈ 0.90 each)."""
    y = np.asarray(y)
    sets = [T.prediction_set(v, q_hat) for v in p]
    has0 = np.array([0 in s for s in sets])
    has1 = np.array([1 in s for s in sets])
    return {
        "coverage, sick": round(float(has1[y == 1].mean()), 3),
        "coverage, healthy": round(float(has0[y == 0].mean()), 3),
        "Uncertain {0,1} share": round(float((has0 & has1).mean()), 3),
        "empty-set share": round(float((~has0 & ~has1).mean()), 3),
    }