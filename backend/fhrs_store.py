"""
FHRS from the database: reads a patient's family history and environmental hazards for one
disease, scores them with backend/cdss/fhrs.py, and records the result.

Older rows typed as free text ("Tier 1", "Typical onset", "CVD") are still read. A row whose
tier or onset cannot be understood is left out and listed in "skipped_records", so a doctor
can fix it instead of it silently changing the score.
"""
from backend.cdss.fhrs import HAZARDS, Relative, compute
from backend.validation import parse_disease, parse_onset, parse_tier


def fhrs_inputs(patient_id, disease):
    """(relatives, hazard_codes, skipped_record_ids) for one patient and disease."""
    from backend.model_orm.clinic_orm import EnvironmentalHazard, FamilyHistory

    relatives, skipped = [], []
    for row in FamilyHistory.query.filter_by(patient_id=patient_id).order_by(FamilyHistory.record_id).all():
        if parse_disease(row.disease_domain) != disease:
            continue
        tier, onset = parse_tier(row.relationship_tier), parse_onset(row.onset_classification)
        if tier is None or onset is None:
            skipped.append(row.record_id)
            continue
        relatives.append(Relative(tier=tier, onset=onset, verified=bool(row.is_verified)))

    hazards = [h.hazard_code for h in EnvironmentalHazard.query
               .filter_by(patient_id=patient_id, disease_domain=disease)
               .order_by(EnvironmentalHazard.id).all()
               if h.hazard_code in HAZARDS[disease]]
    return relatives, hazards, skipped


def patient_fhrs(patient_id, disease):
    """The FHRS breakdown for one patient and disease (see backend/cdss/fhrs.py compute())."""
    relatives, hazards, skipped = fhrs_inputs(patient_id, disease)
    result = compute(disease, relatives, hazards)
    result["skipped_records"] = skipped
    return result


def record_fhrs(patient_id, result):
    """Add a patient_fhrs_stratification row for this result (committed by the caller)."""
    from backend.dbconnect import db
    from backend.model_orm.clinic_orm import FHRSStratification

    row = FHRSStratification(
        patient_id=patient_id,
        disease_domain=result["disease"],
        clustering_score=_r(result["clustering"]),
        environmental_modifier=_r(result["environmental_modifier"]),
        calculated_fhrs=_r(result["adjusted_fhrs"]),
        risk_code=result["band"],
        risk_category=result["band_label"],
    )
    db.session.add(row)
    return row


def _r(x):
    """Round for display. Rounding to 9 places first removes float noise (3.625 * 1.15 is
    4.16874999...), so John's score shows as 4.1688, matching the dictionary's 4.17."""
    return round(round(x, 9), 4)


def fhrs_summary(result):
    """The fields shown in API responses and the audit log (the model gets the unrounded score)."""
    return {
        "bio_fhrs": _r(result["bio_fhrs"]),
        "pedigree_sum": _r(result["pedigree_sum"]),
        "clustering": _r(result["clustering"]),
        "environmental_modifier": _r(result["environmental_modifier"]),
        "adjusted_fhrs": _r(result["adjusted_fhrs"]),
        "band": result["band"],
        "band_label": result["band_label"],
        "relatives_counted": result["relatives_counted"],
        "hazards": result["hazards"],
        "skipped_records": result.get("skipped_records", []),
    }
