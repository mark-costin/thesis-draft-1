from backend.dbconnect import db
from backend.model_orm.clinical_vector import ClinicalVector

class IdempotencyCache(db.Model):
    __tablename__ = 'idempotency_cache'
    
    key = db.Column(db.String(255), primary_key=True)
    data = db.Column(db.JSON, nullable=False)
    status = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.Float, nullable=False)

class FamilyHistory(db.Model):
    __tablename__ = 'patient_family_history'
    
    record_id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.patient_id', ondelete='CASCADE'), nullable=False)
    
    disease_domain = db.Column(db.String(100), nullable=False)
    specific_diagnosis = db.Column(db.String(150), nullable=False)
    relationship_tier = db.Column(db.String(50), nullable=False)
    relationship_weight = db.Column(db.Numeric, nullable=False)
    onset_classification = db.Column(db.String(50), nullable=False)
    onset_weight = db.Column(db.Numeric, nullable=False)
    age_at_diagnosis = db.Column(db.Integer)
    shared_environment = db.Column(db.Boolean, default=False)
    recorded_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now())

class FHRSStratification(db.Model):
    __tablename__ = 'patient_fhrs_stratification'
    
    fhrs_id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.patient_id', ondelete='CASCADE'), nullable=False)
    
    disease_domain = db.Column(db.String(100), nullable=False)
    clustering_score = db.Column(db.Numeric, nullable=False)
    environmental_modifier = db.Column(db.Numeric, nullable=False)
    calculated_fhrs = db.Column(db.Numeric, nullable=False)
    risk_code = db.Column(db.Integer, nullable=False)
    risk_category = db.Column(db.String(50), nullable=False)
    evaluated_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now())

class CVDMetrics(db.Model):
    __tablename__ = 'patient_cvd_metrics'
    
    metric_id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.patient_id', ondelete='CASCADE'), nullable=False)
    
    age = db.Column(db.Numeric)
    biological_sex = db.Column(db.String(20))
    sbp = db.Column(db.Numeric)
    dbp = db.Column(db.Numeric)
    bmi = db.Column(db.Numeric)
    resting_hr = db.Column(db.Numeric)
    total_cholesterol = db.Column(db.Numeric)
    hdl = db.Column(db.Numeric)
    ldl = db.Column(db.Numeric)
    triglycerides = db.Column(db.Numeric)
    hs_crp = db.Column(db.Numeric)
    serum_creatinine = db.Column(db.Numeric)
    egfr = db.Column(db.Numeric)
    lvef = db.Column(db.Numeric)
    ctni = db.Column(db.Numeric)
    nt_probnp = db.Column(db.Numeric)
    smoking_history = db.Column(db.Numeric)
    daily_sodium = db.Column(db.Numeric)
    family_history_premature_cvd = db.Column(db.Integer)
    physical_activity = db.Column(db.Numeric)
    recorded_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now())