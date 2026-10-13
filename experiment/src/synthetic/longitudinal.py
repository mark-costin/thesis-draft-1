import numpy as np
import pandas as pd

try:
    from .spec import clip_to_spec
except ImportError:
    from spec import clip_to_spec


def expand_longitudinal(df):
    n = len(df)
    visit_counts = np.random.choice([1, 2, 3, 4], size=n, p=[0.60, 0.25, 0.10, 0.05])

    # Vectorized expansion
    df_expanded = df.loc[df.index.repeat(visit_counts)].copy()
    df_expanded['visit_number'] = df_expanded.groupby(level=0).cumcount() + 1
    df_expanded['days_since_baseline'] = (df_expanded['visit_number'] - 1) * 365

    # Annual biological drift, kept within CDSS Data Dictionary bounds
    v_minus_1 = df_expanded['visit_number'] - 1
    df_expanded['age'] = clip_to_spec("age", df_expanded['age'] + v_minus_1)
    df_expanded['systolic_bp'] = clip_to_spec("systolic_bp", df_expanded['systolic_bp'] + (0.6 * v_minus_1))
    df_expanded['bmi'] = clip_to_spec("bmi", df_expanded['bmi'] + (0.15 * v_minus_1))

    if 'hba1c' in df_expanded.columns:
        df_expanded['hba1c'] = clip_to_spec("hba1c", df_expanded['hba1c'] + (0.02 * v_minus_1))

    if 'egfr' in df_expanded.columns:
        df_expanded['egfr'] = clip_to_spec("egfr", df_expanded['egfr'] - (0.8 * v_minus_1))

    return df_expanded.reset_index(drop=True)
