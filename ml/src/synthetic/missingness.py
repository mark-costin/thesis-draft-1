import numpy as np
#Ito yung piliting i-0% missing ang mga required fields, at 40% blanko naman sa lab tests (Gate 8).
def inject_missingness(df):
    biomarkers = ['bmi', 'systolic_bp', 'hba1c', 'hdl', 'tg']
    for col in biomarkers:
        mask = np.random.rand(len(df)) < 0.40
        df[f'{col}_measured'] = (~mask).astype(int)
        df.loc[mask, col] = np.nan
    return df