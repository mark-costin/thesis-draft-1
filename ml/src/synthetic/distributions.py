import numpy as np
import pandas as pd
#taga gawa ng edad, sex, at blood tests
def generate_demographics(n_patients):
    patient_ids = [f"PT-{20260000 + i}" for i in range(n_patients)]
    sex = np.random.choice([0, 1], size=n_patients)
    age = np.random.uniform(18, 85, size=n_patients)
    return pd.DataFrame({'patient_id': patient_ids, 'biological_sex': sex, 'age': age})

def generate_biomarkers(df):
    n = len(df)
    bmi = np.random.normal(26, 4, size=n)
    hdl = np.random.normal(50, 12, size=n)
    systolic_bp = 100 + (df['age'] * 0.3) + np.random.normal(0, 10, size=n)
    hba1c = 4.0 + (bmi * 0.12) + np.random.normal(0, 0.5, size=n)
    tg = 180 - (hdl * 1.2) + np.random.normal(0, 15, size=n)
    
    df['bmi'] = bmi
    df['hdl'] = hdl
    df['systolic_bp'] = systolic_bp
    df['hba1c'] = hba1c
    df['tg'] = tg
    return df