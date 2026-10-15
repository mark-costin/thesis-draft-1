"""
Builds each model's input from the database, the same way experiment/src/ml/data.py built
the training data:

  * values        database column names -> training names (sbp -> systolic_bp, ...)
  * age           as recorded with the biomarkers, else from the date of birth
  * sex           patient profile, else the CVD record; Female = 0, Male = 1 (CDSS dictionary)
  * m_<test>      1 when that test is missing in the latest record (M = 1 means missing)
  * v_<marker>    (latest - first record) / months; blank when under 30 days or not measured
  * m_velocity    1 when under 30 days since the first record (including a single record)
  * FHRS          adjusted_fhrs_<d> and fhrs_band_<d> from backend/cdss/fhrs.py

assemble_features() is pure (no database) so it is unit-tested directly; build_model_input()
reads the rows and calls it. Every possible input is produced; each model uses its own list.
"""
from datetime import date, datetime

DAYS_PER_MONTH = 30.4375        # data.py
MIN_VELOCITY_DAYS = 30          # data.py, thesis §3.5.2

COLUMN_TO_FEATURE = {"sbp": "systolic_bp", "dbp": "diastolic_bp", "triglycerides": "tg", "daily_sleep": "sleep_hours"}
SEX_CODE = {"Female": 0, "Male": 1}

# m_<name> -> the columns that make up that test (data.py MEASURED_FLAG_FOR; spirometry is one test)
MISSING_FLAGS = {
    "m_total_cholesterol": ("total_cholesterol",),
    "m_ldl": ("ldl",),
    "m_tg": ("triglycerides",),
    "m_fpg": ("fpg",),
    "m_bmi": ("bmi",),
    "m_spirometry": ("fev1", "fvc", "fev1_fvc_ratio"),
    "m_spo2": ("spo2",),
    "m_phq9": ("phq9",),
    "m_gad7": ("gad7",),
}
NOT_A_VALUE = {"age", "biological_sex"}


def _number(value):
    if value is None or isinstance(value, (bool, str)):
        return None
    return float(value)


def _age_on(dob, when):
    if dob is None:
        return None
    day = when.date() if isinstance(when, datetime) else (when or date.today())
    return day.year - dob.year - ((day.month, day.day) < (dob.month, dob.day))


def assemble_features(modality, *, latest, earliest, latest_at, earliest_at, date_of_birth, profile_sex, fhrs):
    """{training feature name: value or None} for one patient and modality."""
    earliest = earliest if earliest is not None else latest
    out = {}

    for column, value in latest.items():
        if column in NOT_A_VALUE:
            continue
        out[COLUMN_TO_FEATURE.get(column, column)] = _number(value)

    age = _number(latest.get("age"))
    out["age"] = age if age is not None else _age_on(date_of_birth, latest_at)

    sex = profile_sex or latest.get("biological_sex")
    out["biological_sex"] = SEX_CODE.get(sex)

    for flag, columns in MISSING_FLAGS.items():
        if all(c in latest for c in columns):
            out[flag] = int(all(latest[c] is None for c in columns))

    days = (latest_at - earliest_at).total_seconds() / 86400 if latest_at and earliest_at else 0.0
    too_soon = days < MIN_VELOCITY_DAYS
    for column, value in latest.items():
        if column in NOT_A_VALUE or isinstance(value, str):
            continue
        now, first = _number(value), _number(earliest.get(column))
        name = "v_" + COLUMN_TO_FEATURE.get(column, column)
        out[name] = None if too_soon or now is None or first is None else (now - first) / (days / DAYS_PER_MONTH)
    out["m_velocity"] = int(too_soon)

    out[f"adjusted_fhrs_{modality}"] = fhrs["adjusted_fhrs"] if fhrs else None
    out[f"fhrs_band_{modality}"] = fhrs["band"] if fhrs else None
    return out


# --- database -------------------------------------------------------------------

def _row_dict(row):
    from backend.biomarker_store import row_values
    return {c.name: None for c in row.__table__.columns
            if c.name not in ("metric_id", "patient_id", "recorded_at")} | row_values(row)


def build_model_input(modality, patient_id):
    """
    {"features": {...}, "fhrs": breakdown, "records": n} from the patient's stored rows,
    or None when the patient has no biomarkers for this modality.
    """
    from backend.biomarker_store import metric_model
    from backend.fhrs_store import patient_fhrs
    from backend.model_orm.pat_orm import Patient
    from backend.dbconnect import db

    model = metric_model(modality)
    rows = (model.query.filter_by(patient_id=patient_id)
            .order_by(model.recorded_at.asc(), model.metric_id.asc()).all())
    if not rows:
        return None
    first, last = rows[0], rows[-1]
    patient = db.session.get(Patient, patient_id)
    fhrs = patient_fhrs(patient_id, modality)
    features = assemble_features(
        modality, latest=_row_dict(last), earliest=_row_dict(first),
        latest_at=last.recorded_at, earliest_at=first.recorded_at,
        date_of_birth=patient.date_of_birth if patient else None,
        profile_sex=getattr(patient, "biological_sex", None), fhrs=fhrs)
    return {"features": features, "fhrs": fhrs, "records": len(rows)}
