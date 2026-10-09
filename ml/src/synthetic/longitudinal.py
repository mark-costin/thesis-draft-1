import numpy as np
import pandas as pd
#Ito yung nagpapa-progress ng edad at sakit ng mga pasyente kada taon (1-4 visits).
def expand_longitudinal(df):
    n = len(df)
    visit_counts = np.random.choice([1, 2, 3, 4], size=n, p=[0.60, 0.25, 0.10, 0.05])
    longitudinal_data = []

    for idx, row in df.iterrows():
        v_count = visit_counts[idx]
        for v in range(v_count):
            new_row = row.copy()
            new_row['visit_number'] = v + 1
            new_row['days_since_baseline'] = v * 365
            
            new_row['age'] += v
            new_row['systolic_bp'] += (0.6 * v)
            new_row['bmi'] += (0.15 * v)
            new_row['hba1c'] += (0.02 * v)
            longitudinal_data.append(new_row)

    return pd.DataFrame(longitudinal_data)