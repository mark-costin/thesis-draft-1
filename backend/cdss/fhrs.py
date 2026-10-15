"""
Family History Risk Score (FHRS), as defined in the CDSS FHRS Guide (CDSS_Data_Dictionary.pdf)
and computed by the cohort generator (experiment/src/synthetic/fhrs.py):

    BioFHRS_d      = sum(R_i * O_i * S_i) + C_d
    AdjustedFHRS_d = BioFHRS_d * E_d,      E_d = 1.0 + sum(e_j)
    C_d            = sum over tiers k of W_k * max(0, verified relatives in tier k - 1)

R_i kinship by tier, O_i onset multiplier, S_i verification factor, e_j environmental hazards.
Every constant is read from backend/cdss/cdss_spec.json (a copy of the generator's spec;
tests/test_fhrs.py checks the two are identical). No randomness: no relatives means 0.0.
"""
import json
from dataclasses import dataclass
from pathlib import Path

SPEC_PATH = Path(__file__).resolve().parent / "cdss_spec.json"
SPEC = json.loads(SPEC_PATH.read_text(encoding="utf-8"))["fhrs"]

DISEASES = ("cvd", "t2d", "resp", "neuro")
TIER_KINSHIP = {int(k): v for k, v in SPEC["kinship_by_tier"].items()}               # R_i
CLUSTER_WEIGHT = {int(k): v for k, v in SPEC["clustering_weight_by_tier"].items()}   # W_k
ONSET_MULTIPLIER = dict(SPEC["onset_multipliers"])                                   # O_i
VERIFICATION = {True: SPEC["verification"]["verified"], False: SPEC["verification"]["unverified"]}  # S_i
HAZARD_RANGE = tuple(SPEC["environmental_hazard_range"])
BAND_EDGES = SPEC["band_edges"]
BAND_LABELS = {b["band"]: b["label"] for b in SPEC["bands"]}
HAZARDS = {d: {h["code"]: h for h in SPEC["environmental_hazards"].get(d, [])} for d in DISEASES}


class FhrsError(ValueError):
    """An input the FHRS formula cannot use (unknown tier, onset, disease or hazard)."""


@dataclass(frozen=True)
class Relative:
    tier: int        # 1 immediate, 2 extended, 3 distant
    onset: str       # severe_early | early | typical | late
    verified: bool   # medical records / lab results exist


def relative_term(r: Relative) -> float:
    if r.tier not in TIER_KINSHIP:
        raise FhrsError(f"relationship tier must be one of {sorted(TIER_KINSHIP)}, got {r.tier!r}")
    if r.onset not in ONSET_MULTIPLIER:
        raise FhrsError(f"onset must be one of {sorted(ONSET_MULTIPLIER)}, got {r.onset!r}")
    return TIER_KINSHIP[r.tier] * ONSET_MULTIPLIER[r.onset] * VERIFICATION[bool(r.verified)]


def clustering(relatives) -> float:
    total = 0.0
    for tier, weight in CLUSTER_WEIGHT.items():
        verified = sum(1 for r in relatives if r.tier == tier and r.verified)
        total += weight * max(0, verified - 1)
    return total


def environmental_modifier(disease, hazard_codes) -> float:
    allowed = HAZARDS.get(disease, {})
    total = 0.0
    for code in dict.fromkeys(hazard_codes):          # each hazard counts once
        if code not in allowed:
            raise FhrsError(f"hazard {code!r} is not on the {disease} list {sorted(allowed) or '(none)'}")
        total += allowed[code]["e_j"]
    return 1.0 + total


def assign_band(score: float) -> int:
    """0: score 0 | 1: 0 < score < 1.76 | 2: < 3.51 | 3: <= 6.00 | 4: above (same rule as the generator)."""
    e1, e2, e3 = BAND_EDGES
    if score <= 0.0:
        return 0
    if score < e1:
        return 1
    if score < e2:
        return 2
    if score <= e3:
        return 3
    return 4


def compute(disease, relatives, hazard_codes) -> dict:
    """The full breakdown for one disease. Raises FhrsError for unusable input."""
    if disease not in DISEASES:
        raise FhrsError(f"disease must be one of {DISEASES}, got {disease!r}")
    relatives = list(relatives)
    pedigree = sum(relative_term(r) for r in relatives)
    cluster = clustering(relatives)
    bio = pedigree + cluster
    modifier = environmental_modifier(disease, hazard_codes)
    adjusted = bio * modifier
    band = assign_band(adjusted)
    return {
        "disease": disease,
        "relatives_counted": len(relatives),
        "pedigree_sum": pedigree,
        "clustering": cluster,
        "bio_fhrs": bio,
        "hazards": list(dict.fromkeys(hazard_codes)),
        "environmental_modifier": modifier,
        "adjusted_fhrs": adjusted,
        "band": band,
        "band_label": BAND_LABELS.get(band),
    }
