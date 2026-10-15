"""
Translates incoming biomarker payloads (database / API names) into the exact feature
names each trained model expects. Training and serving must agree on names AND encodings,
otherwise inputs silently become NaN.

TO FILL IN (must match your training pipeline):
  * SEX_ENCODING — how biological_sex was encoded when the models were trained.
  * FEATURE_RENAMES for t2d / resp / neuro — compare each model's feature_columns
    (ml/models/<disease>_head_latest.json) with the database columns in clinic_orm.py.
  * Derived features (adjusted_fhrs_cvd, fhrs_band_cvd, m_*, v_*) are NOT computed here;
    they must be computed with the same code the training pipeline used.
"""


class FeatureError(ValueError):
    """Raised when a payload value cannot be turned into a model feature."""


# database / API name -> model feature name
FEATURE_RENAMES = {
    "cvd": {
        "sbp": "systolic_bp",
        "dbp": "diastolic_bp",
        "triglycerides": "tg",
    },
}

# Set this to the encoding used in training, e.g. {"male": 1, "female": 0}.
# Left as None on purpose: guessing it would silently flip every prediction's sex input.
SEX_ENCODING = None


def normalize_payload(disease: str, payload: dict) -> dict:
    """Return a copy of `payload` with model feature names and numeric encodings."""
    out = dict(payload or {})

    for source, target in FEATURE_RENAMES.get(disease, {}).items():
        if source in out:
            value = out.pop(source)
            out.setdefault(target, value)

    sex = out.get("biological_sex")
    if isinstance(sex, str):
        if SEX_ENCODING is None:
            raise FeatureError(
                "biological_sex was sent as text but SEX_ENCODING is not configured in "
                "backend/cdss/features.py. Set it to the encoding used in training."
            )
        key = sex.strip().lower()
        if key not in SEX_ENCODING:
            raise FeatureError(f"Unknown biological_sex value {sex!r}; expected one of {sorted(SEX_ENCODING)}.")
        out["biological_sex"] = SEX_ENCODING[key]

    return out
