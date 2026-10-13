"""Visual verification of the synthetic cohort (baseline visit only).
Saves figures to experiment/data/processed/figures/ and prints the key numbers."""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")                     # save to files; no window needed
import matplotlib.pyplot as plt

DATA = "experiment/data/raw/cohort.parquet"
OUT = "experiment/data/processed/figures"
os.makedirs(OUT, exist_ok=True)

df = pd.read_parquet(DATA)
base = df[df["visit_number"] == 1]
print(f"Cohort: {df.shape[0]} visits, {base.shape[0]} patients, {df.shape[1]} columns")

# 1. Missingness per column (all visits)
miss = df.isna().mean().sort_values(ascending=False) * 100
miss = miss[miss > 0]
fig, ax = plt.subplots(figsize=(10, 5))
ax.barh(miss.index[::-1], miss.values[::-1], color="#3b6ea5")
ax.axvline(40, ls="--", c="grey"); ax.axvline(60, ls="--", c="grey")
ax.set_xlabel("% missing (all visits)"); ax.set_title("Missingness by column (expected 40% / 60%)")
fig.tight_layout(); fig.savefig(f"{OUT}/01_missingness.png", dpi=120); plt.close(fig)
print("\nMissing %:", miss.round(1).to_dict())

# 2. Distribution shapes (baseline)
panels = [
    ("age", "Age: three strata (32 / 54 / 74)"),
    ("bmi", "BMI: right-skewed, median ~28.5"),
    ("hba1c", "HbA1c: main peak ~5.5 + tail/bump ~7-8"),
    ("fpg", "FPG: tail above 126"),
    ("spo2", "SpO2: left tail below 90"),
    ("fev1_fvc_ratio", "FEV1/FVC: left tail below 60"),
    ("mmse", "MMSE: left tail below 18"),
    ("phq9", "PHQ-9: right tail at 15+"),
]
fig, axes = plt.subplots(2, 4, figsize=(18, 8))
for ax, (col, title) in zip(axes.ravel(), panels):
    s = base[col].dropna()
    ax.hist(s, bins=40, color="#3b6ea5", alpha=0.85)
    ax.axvline(s.median(), c="black", ls="--", lw=1)
    ax.set_title(title, fontsize=10); ax.set_xlabel(col)
fig.suptitle("Baseline distributions (dashed line = median)")
fig.tight_layout(); fig.savefig(f"{OUT}/02_distributions.png", dpi=120); plt.close(fig)

# 3. Correlation heatmap (baseline)
cols = ["age", "systolic_bp", "diastolic_bp", "bmi", "hba1c", "fpg", "hdl", "tg",
        "fev1_fvc_ratio", "spo2", "mmse", "phq9"]
corr = base[cols].corr()
fig, ax = plt.subplots(figsize=(10, 8))
im = ax.imshow(corr, cmap="coolwarm", vmin=-1, vmax=1)
ax.set_xticks(range(len(cols))); ax.set_xticklabels(cols, rotation=60, ha="right")
ax.set_yticks(range(len(cols))); ax.set_yticklabels(cols)
for i in range(len(cols)):
    for j in range(len(cols)):
        ax.text(j, i, f"{corr.iloc[i, j]:.2f}", ha="center", va="center", fontsize=7)
fig.colorbar(im); ax.set_title("Biomarker correlations (baseline)")
fig.tight_layout(); fig.savefig(f"{OUT}/03_correlations.png", dpi=120); plt.close(fig)

# 4. Biomarker by outcome (baseline)
pairs = [("y_t2d", "hba1c"), ("y_resp", "fev1_fvc_ratio"), ("y_resp", "spo2"),
         ("y_neuro", "mmse"), ("y_neuro", "phq9"), ("y_cvd", "systolic_bp")]
fig, axes = plt.subplots(1, 6, figsize=(20, 4))
for ax, (y, col) in zip(axes, pairs):
    data = [base.loc[base[y] == k, col].dropna() for k in (0, 1)]
    ax.boxplot(data)                                   # works on every matplotlib version
    ax.set_xticks([1, 2])
    ax.set_xticklabels(["no disease", "disease"])
    ax.set_title(f"{col} by {y}", fontsize=10)
fig.tight_layout(); fig.savefig(f"{OUT}/04_biomarker_by_outcome.png", dpi=120); plt.close(fig)

# Key numbers
print("\nKey numbers (baseline):")
print(f"  BMI quartiles: {np.percentile(base['bmi'].dropna(), [25, 50, 75]).round(1).tolist()}")
print(f"  HbA1c >= 6.5%: {(base['hba1c'] >= 6.5).mean() * 100:.1f}%")
print(f"  corr(HbA1c, FPG): {base[['hba1c', 'fpg']].dropna().corr().iloc[0, 1]:.2f}")
print(f"  SpO2 < 90: {(base['spo2'].dropna() < 90).mean() * 100:.1f}%")
print(f"  MMSE < 18: {(base['mmse'].dropna() < 18).mean() * 100:.1f}%")
print(f"\nFigures saved to {OUT}/")
for f in sorted(os.listdir(OUT)):
    print("  ", f)
