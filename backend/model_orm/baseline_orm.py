from datetime import datetime, timezone
from backend.dbconnect import db

class BaselineRecord(db.Model):
    """
    ORM Model for Two-Phase Longitudinal CDSS Architecture.
    Persists immutable cryptographic baselines and subsequent longitudinal trajectory updates
    for patients, ensuring tamper-evident clinical history tracking.
    """
    __tablename__ = 'baseline_records'

    record_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    # References patients.patient_id to match pat_orm.py
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.patient_id', ondelete='CASCADE'), nullable=False, index=True)
    encounter_id = db.Column(db.String(64), nullable=False, index=True)
    
    # Versioning & Type Control
    schema_version = db.Column(db.String(16), nullable=False, default="1.1.0")
    model_version = db.Column(db.String(32), nullable=False)
    record_type = db.Column(db.String(16), nullable=False)  # 'BASELINE' or 'TRAJECTORY'
    
    # Cryptographic Chain of Custody
    cryptographic_hash = db.Column(db.String(256), unique=True, nullable=False, index=True)
    parent_baseline_hash = db.Column(db.String(256), nullable=True, index=True)
    
    # Clinical Payloads (Stored as JSON / JSONB)
    fhrs_payload = db.Column(db.JSON, nullable=False)
    biomarker_payload = db.Column(db.JSON, nullable=False)
    inference_results = db.Column(db.JSON, nullable=False)
    
    # Audit & Approval Metadata
    reanchor_reason = db.Column(db.String(255), nullable=True)
    approved_by = db.Column(db.String(64), nullable=True)  # Clinician license number
    approved_at_utc = db.Column(db.DateTime(timezone=True), nullable=True)
    submitted_at_utc = db.Column(db.DateTime(timezone=True), server_default=db.func.now(), nullable=False)


class AuditLedger(db.Model):
    """
    ORM Model for immutable CDSS operation logging.
    Records system-level events, model inferences, and algorithmic fairness audits.
    """
    __tablename__ = 'audit_ledger'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    audit_id = db.Column(db.String(64), unique=True, nullable=False, index=True)  # UUID
    timestamp_utc = db.Column(db.DateTime(timezone=True), server_default=db.func.now(), nullable=False, index=True)
    
    event_type = db.Column(db.String(64), nullable=False, index=True)
    payload = db.Column(db.JSON, nullable=False)
    
    # Fast-query indexing columns (Soft Foreign Keys to avoid cascade-locking the ledger)
    patient_id = db.Column(db.String(64), nullable=True, index=True)
    doctor_id = db.Column(db.String(64), nullable=True, index=True)