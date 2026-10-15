from backend.dbconnect import db


class AuditLedger(db.Model):
    """
    Append-only log of CDSS events: model inferences, encounter commits, model reloads.

    patient_id / doctor_id / actor_user_id are plain integers with no foreign keys on
    purpose, so deleting a patient or user never deletes or blocks their audit history.
    entry_seal is an HMAC-SHA256 over the whole entry (see backend/audit.py).
    Replaces the never-created AuditLedger in baseline_orm.py.
    """
    __tablename__ = 'audit_ledger'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    audit_id = db.Column(db.String(64), unique=True, nullable=False, index=True)  # UUID
    timestamp_utc = db.Column(db.DateTime(timezone=True), nullable=False, index=True)

    event_type = db.Column(db.String(64), nullable=False, index=True)
    payload = db.Column(db.JSON, nullable=False)

    patient_id = db.Column(db.Integer, nullable=True, index=True)
    doctor_id = db.Column(db.Integer, nullable=True, index=True)
    actor_user_id = db.Column(db.Integer, nullable=True, index=True)

    entry_seal = db.Column(db.String(64), nullable=False)
