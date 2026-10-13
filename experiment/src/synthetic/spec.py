"""Loads the physician-validated CDSS specification (cdss_spec.json).
Single source of truth for feature bounds and FHRS constants."""
import json
import os
import numpy as np

SPEC_PATH = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "data", "reference", "cdss_spec.json"))

with open(SPEC_PATH, encoding="utf-8") as f:
    SPEC = json.load(f)

BOUNDS = SPEC["feature_bounds"]
FHRS_SPEC = SPEC["fhrs"]


def clip_to_spec(col, values):
    """Clip values to the CDSS Data Dictionary min/max for this feature."""
    b = BOUNDS[col]
    return np.clip(values, b["min"], b["max"])
