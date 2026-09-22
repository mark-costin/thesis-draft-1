from backend.dbconnect import db
from datetime import datetime
from pgvector.sqlalchemy import Vector  # <-- Must import Vector

# ... keep existing models: IdempotencyCache, FamilyHistory, FHRSStratification, CVDMetrics, etc. ...

class ClinicalVector(db.Model):
    __tablename__ = 'patient_clinical_vectors'

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.patient_id', ondelete='CASCADE'), unique=True, nullable=False)
    disease_narrative = db.Column(db.Text, nullable=True)
    embedding = db.Column(Vector(384), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)