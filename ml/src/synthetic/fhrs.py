import numpy as np
#para sa Family History Risk Scores na hinati sa apat na sakit
def compute_bio_fhrs(df):
    n = len(df)
    df['bio_fhrs_cvd'] = np.random.uniform(0, 3, size=n)
    df['bio_fhrs_t2d'] = np.random.uniform(0, 3, size=n)
    df['bio_fhrs_resp'] = np.random.uniform(0, 3, size=n)
    df['bio_fhrs_neuro'] = np.random.uniform(0, 3, size=n)
    return df