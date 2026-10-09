import numpy as np
#Dito nilagay yung 1.8 sweet spot noise natin para pumasok sa Gate 6 AUROC
def assign_disease(target_pct, logit_formula):
    prob = 1 / (1 + np.exp(-logit_formula))
    threshold = np.percentile(prob, 100 - (target_pct * 100))
    return (prob >= threshold).astype(int)

def generate_outcomes(df):
    n = len(df)
    cvd_logit = (df['age'] * 0.05) + (df['systolic_bp'] * 0.02) + (df['bio_fhrs_cvd'] * 0.8) - 5 + np.random.normal(0, 1.8, size=n)
    df['y_cvd'] = assign_disease(0.08, cvd_logit)

    t2d_logit = (df['bmi'] * 0.2) + (df['hba1c'] * 1.5) + (df['bio_fhrs_t2d'] * 0.7) - 10 + np.random.normal(0, 1.8, size=n)
    df['y_t2d'] = assign_disease(0.10, t2d_logit)

    resp_logit = (df['age'] * 0.03) - (df['bmi'] * 0.05) + np.random.normal(0, 1.8, size=n)
    df['y_resp'] = assign_disease(0.12, resp_logit)

    neuro_logit = (df['age'] * 0.06) + (df['y_cvd'] * 1.2) + np.random.normal(0, 1.8, size=n)
    df['y_neuro'] = assign_disease(0.07, neuro_logit)
    return df