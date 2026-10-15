"""
Biomarker storage: maps each AI modality to its metric table and moves values in and out.

The column spec used for validation is read from the SQLAlchemy model itself, so it always
matches the database schema in clinic_orm.py.
"""
MODALITIES = ("cvd", "t2d", "resp", "neuro")
_SYSTEM_COLUMNS = {"metric_id", "patient_id", "recorded_at"}


def metric_model(modality):
    """The ORM class for a modality, or None for an unknown one."""
    from backend.model_orm.clinic_orm import CVDMetrics, NeuroMentalMetrics, RespiratoryMetrics, T2DMetrics
    return {"cvd": CVDMetrics, "t2d": T2DMetrics, "resp": RespiratoryMetrics, "neuro": NeuroMentalMetrics}.get(modality)


def column_spec(model):
    """{field: spec} for validate_biomarkers(), from the model's column types."""
    from sqlalchemy import Integer, Numeric, String

    spec = {}
    for column in model.__table__.columns:
        if column.name in _SYSTEM_COLUMNS:
            continue
        col_type = column.type
        if isinstance(col_type, Integer):
            spec[column.name] = ("integer",)
        elif isinstance(col_type, Numeric):
            spec[column.name] = ("numeric", col_type.precision, col_type.scale)
        elif isinstance(col_type, String):
            spec[column.name] = ("string", col_type.length)
    return spec


def _to_json(value):
    from decimal import Decimal
    return float(value) if isinstance(value, Decimal) else value


def row_values(row):
    """Non-empty biomarker values of a stored row, JSON-ready (Decimal -> float)."""
    return {
        column.name: _to_json(getattr(row, column.name))
        for column in row.__table__.columns
        if column.name not in _SYSTEM_COLUMNS and getattr(row, column.name) is not None
    }


def patient_exists(patient_id):
    from backend.dbconnect import db
    from backend.model_orm.pat_orm import Patient
    return db.session.get(Patient, patient_id) is not None


def latest_row(modality, patient_id):
    model = metric_model(modality)
    if model is None:
        return None
    return (model.query.filter_by(patient_id=patient_id)
            .order_by(model.recorded_at.desc(), model.metric_id.desc())
            .first())


def latest_biomarkers(modality, patient_id):
    """The patient's most recent stored values for a modality, or None."""
    row = latest_row(modality, patient_id)
    return row_values(row) if row is not None else None


def store_biomarkers(modality, patient_id, cleaned_values):
    """Insert one row of already-validated values. Returns the new row (committed)."""
    from backend.dbconnect import db
    model = metric_model(modality)
    row = model(patient_id=patient_id, **cleaned_values)
    db.session.add(row)
    db.session.commit()
    return row
