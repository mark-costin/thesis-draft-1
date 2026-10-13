import numpy as np

try:
    from .spec import FHRS_SPEC
except ImportError:
    from spec import FHRS_SPEC

DISEASES = ['cvd', 't2d', 'resp', 'neuro']

# ---------------------------------------------------------------------------
# Clinical constants: CDSS_Data_Dictionary.pdf, via cdss_spec.json
# ---------------------------------------------------------------------------
TIER_KINSHIP = {int(k): v for k, v in FHRS_SPEC["kinship_by_tier"].items()}            # R_i
TIER_WEIGHT = {int(k): v for k, v in FHRS_SPEC["clustering_weight_by_tier"].items()}   # W_k
VERIF_FACTOR = {True: FHRS_SPEC["verification"]["verified"],                           # S_i
                False: FHRS_SPEC["verification"]["unverified"]}
ONSET_VALUES = FHRS_SPEC["onset_multipliers"]                                          # O_i
HAZARD_RANGE = tuple(FHRS_SPEC["environmental_hazard_range"])                          # e_j
BAND_EDGES = FHRS_SPEC["band_edges"]                                                   # [1.76, 3.51, 6.00]

# ---------------------------------------------------------------------------
# Simulation assumptions: NOT in the dictionary (confirm with physician)
# ---------------------------------------------------------------------------
TIER_RATE = {1: 0.6, 2: 0.5, 3: 0.4}     # mean affected relatives per tier (Poisson)
MAX_PER_TIER = 6                          # cap on affected relatives per tier
VERIFIED_P = 0.5                          # P(a relative's diagnosis is verified)
ONSET_PROBS = {"severe_early": 0.10, "early": 0.25, "typical": 0.50, "late": 0.15}
ONSET_BRACKETS = {ONSET_VALUES[k]: p for k, p in ONSET_PROBS.items()}   # value: probability
MAX_HAZARDS = 3                           # 0-3 shared domestic hazards per patient

# The dictionary formula has no random term: Band 0 = score 0.0 (no affected relatives).
# True restores the previous uniform(0, 1.5) noise (not spec-compliant).
FHRS_BASELINE_NOISE = False
NOISE_RANGE = (0.0, 1.5)


def assign_band(fhrs):
    """FHRS bands (CDSS FHRS Guide, Section 5), applied to the Adjusted FHRS:
    0: score == 0.0 | 1: 0 < score < 1.76 | 2: 1.76-3.50 | 3: 3.51-6.00 | 4: > 6.00"""
    x = np.asarray(fhrs, dtype=float)
    e1, e2, e3 = BAND_EDGES
    return np.select([x <= 0.0, x < e1, x < e2, x <= e3], [0, 1, 2, 3], 4)


def _sample_onset(size):
    values = np.array(list(ONSET_BRACKETS.keys()), dtype=float)
    probs = np.array(list(ONSET_BRACKETS.values()), dtype=float)
    return np.random.choice(values, size=size, p=probs / probs.sum())


def _pedigree_score(n):
    """Per-relative sampling by tier.
    Returns sum(R_i * O_i * S_i) and the clustering factor C_d."""
    score = np.zeros(n)
    clustering = np.zeros(n)
    slots = np.arange(MAX_PER_TIER)[None, :]

    for tier in (1, 2, 3):
        n_k = np.minimum(np.random.poisson(TIER_RATE[tier], size=n), MAX_PER_TIER)
        present = slots < n_k[:, None]                                    # (n, MAX)
        onset = _sample_onset((n, MAX_PER_TIER))
        verified = np.random.rand(n, MAX_PER_TIER) < VERIFIED_P
        verif = np.where(verified, VERIF_FACTOR[True], VERIF_FACTOR[False])

        score += (TIER_KINSHIP[tier] * onset * verif * present).sum(axis=1)

        # C_d term: W_k * max(0, N_k,verified - 1)
        n_verified = (verified & present).sum(axis=1)
        clustering += TIER_WEIGHT[tier] * np.maximum(0, n_verified - 1)

    return score, clustering


def compute_bio_fhrs(df):
    n = len(df)
    hazard_slots = np.arange(MAX_HAZARDS)[None, :]

    for d in DISEASES:
        score, C_d = _pedigree_score(n)

        # Always draw the noise so toggling the flag doesn't shift the RNG stream
        noise = np.random.uniform(*NOISE_RANGE, size=n)
        if not FHRS_BASELINE_NOISE:
            noise = np.zeros(n)

        base_fhrs = score + C_d + noise
        df[f'bio_fhrs_{d}'] = base_fhrs

        # Environmental modifier E_d = 1.0 + sum(e_j)
        n_hazards = np.random.randint(0, MAX_HAZARDS + 1, size=n)
        contrib = np.random.uniform(*HAZARD_RANGE, size=(n, MAX_HAZARDS))
        E_d = 1.0 + (contrib * (hazard_slots < n_hazards[:, None])).sum(axis=1)
        adjusted_fhrs = base_fhrs * E_d
        df[f'adjusted_fhrs_{d}'] = adjusted_fhrs

        # Spec: bands are assigned from the Adjusted FHRS
        df[f'fhrs_band_{d}'] = assign_band(adjusted_fhrs)

    return df
