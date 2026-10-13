import numpy as np

# Missingness is applied per clinical TEST: values from the same test are
# measured together or not at all, and share one *_measured flag.
#   Routine (40% missing):     single-value labs and anthropometrics
#   Specialized (60% missing): spirometry (one test, three values), oximetry, questionnaires
# Vital signs (SBP, DBP, resting HR) are recorded at every encounter and are never missing.
# Baseline demographics, FHRS columns and outcomes are never missing.

ROUTINE_TESTS = {
    "ldl": ["ldl"],
    "tg": ["tg"],
    "fpg": ["fpg"],
    "total_cholesterol": ["total_cholesterol"],
    "bmi": ["bmi"],
}

SPECIALIZED_TESTS = {
    "spirometry": ["fev1", "fvc", "fev1_fvc_ratio"],
    "spo2": ["spo2"],
    "phq9": ["phq9"],
    "gad7": ["gad7"],
}

ROUTINE_RATE = 0.40
SPECIALIZED_RATE = 0.60


def _apply(df, tests, rate):
    for test, cols in tests.items():
        present = [c for c in cols if c in df.columns]
        if not present:
            continue
        mask = np.random.rand(len(df)) < rate          # one draw per test, shared by its values
        df[f"{test}_measured"] = (~mask).astype(int)
        df.loc[mask, present] = np.nan
    return df


def inject_missingness(df):
    df = _apply(df, ROUTINE_TESTS, ROUTINE_RATE)
    df = _apply(df, SPECIALIZED_TESTS, SPECIALIZED_RATE)
    return df
