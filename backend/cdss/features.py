"""
Translates incoming biomarker payloads (database / API names) into the exact feature
names each trained model expects. Training and serving must agree on names AND encodings,
otherwise inputs silently become NaN.

Configured to match the training pipeline:
  * SEX_ENCODING and FEATURE_RENAMES are set from the CDSS dictionary and each model's
    feature_columns (ml/models/<disease>_head_latest.json).
  * Derived features (adjusted_fhrs_<d>, fhrs_band_<d>, m_*, v_*) are computed in
    backend/cdss/feature_builder.py, the same way experiment/src/ml/data.py did.
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
    "t2d": {"triglycerides": "tg"},
    "neuro": {"daily_sleep": "sleep_hours"},
}

# CDSS_Data_Dictionary.pdf (pages 11 and 21): Female (0), Male (1). The generator draws 0/1
# without a label, so the dictionary is the authority for which is which.
SEX_ENCODING = {"female": 0, "male": 1}


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
