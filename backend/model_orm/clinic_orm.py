from backend.dbconnect import db
from backend.model_orm.clinical_vector import ClinicalVector

# ==============================================================================
# 1. CORE TRANSACTION & IDEMPOTENCY
# ==============================================================================
class IdempotencyCache(db.Model):
    __tablename__ = 'idempotency_cache'
    
    key = db.Column(db.String(255), primary_key=True)
    data = db.Column(db.JSON, nullable=False)
    status = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.Float, nullable=False)


# ==============================================================================
# 2. HEREDITARY RISK & EPIDEMIOLOGICAL STRATIFICATION
# ==============================================================================
class FamilyHistory(db.Model):
    __tablename__ = 'patient_family_history'
    
    record_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.patient_id', ondelete='CASCADE'), nullable=False, index=True)
    
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
    
    fhrs_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.patient_id', ondelete='CASCADE'), nullable=False, index=True)
    
    disease_domain = db.Column(db.String(100), nullable=False)
    clustering_score = db.Column(db.Numeric, nullable=False)
    environmental_modifier = db.Column(db.Numeric, nullable=False)
    calculated_fhrs = db.Column(db.Numeric, nullable=False)
    risk_code = db.Column(db.Integer, nullable=False)
    risk_category = db.Column(db.String(50), nullable=False)
    evaluated_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now())


# ==============================================================================
# 3. MODALITY 1: CARDIOVASCULAR DISEASES (patient_cvd_metrics)
# ==============================================================================
class CVDMetrics(db.Model):
    __tablename__ = 'patient_cvd_metrics'
    
    metric_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.patient_id', ondelete='CASCADE'), nullable=False, index=True)
    
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


# ==============================================================================
# 4. MODALITY 2: TYPE 2 DIABETES (patient_t2d_metrics)
# ==============================================================================
class T2DMetrics(db.Model):
    __tablename__ = 'patient_t2d_metrics'
    
    metric_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.patient_id', ondelete='CASCADE'), nullable=False, index=True)
    
    fpg = db.Column(db.Numeric(5, 1))
    postprandial_glucose_2h = db.Column(db.Numeric(5, 1))
    hba1c = db.Column(db.Numeric(4, 1))
    fasting_insulin = db.Column(db.Numeric(5, 1))
    c_peptide = db.Column(db.Numeric(4, 1))
    homa_ir = db.Column(db.Numeric(4, 1))
    bmi = db.Column(db.Numeric(4, 1))
    waist_circumference = db.Column(db.Numeric(5, 1))
    whr = db.Column(db.Numeric(4, 2))
    sbp = db.Column(db.Numeric(5, 1))
    dbp = db.Column(db.Numeric(5, 1))
    triglycerides = db.Column(db.Numeric(6, 1))
    hdl = db.Column(db.Numeric(5, 1))
    uacr = db.Column(db.Numeric(6, 1))
    serum_uric_acid = db.Column(db.Numeric(4, 1))
    gestational_diabetes = db.Column(db.Integer)
    family_history_diabetes = db.Column(db.Integer)
    acanthosis_nigricans = db.Column(db.Integer)
    daily_carbs = db.Column(db.Numeric(5, 1))
    sedentary_duration = db.Column(db.Numeric(4, 1))
    recorded_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now())


# ==============================================================================
# 5. MODALITY 3: RESPIRATORY (patient_respiratory_metrics)
# ==============================================================================
class RespiratoryMetrics(db.Model):
    __tablename__ = 'patient_respiratory_metrics'
    
    metric_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.patient_id', ondelete='CASCADE'), nullable=False, index=True)
    
    fev1 = db.Column(db.Numeric(3, 1))
    fvc = db.Column(db.Numeric(3, 1))
    fev1_fvc_ratio = db.Column(db.Numeric(4, 1))
    post_bd_fev1_pred = db.Column(db.Numeric(5, 1))
    pef = db.Column(db.Numeric(5, 1))
    eosinophil_count = db.Column(db.Numeric(6, 1))
    feno = db.Column(db.Numeric(5, 1))
    spo2 = db.Column(db.Numeric(4, 1))
    pao2 = db.Column(db.Numeric(5, 1))
    paco2 = db.Column(db.Numeric(4, 1))
    mmrc_score = db.Column(db.Integer)
    act_score = db.Column(db.Integer)
    cat_score = db.Column(db.Integer)
    serum_ige = db.Column(db.Numeric(6, 1))
    annual_exacerbations = db.Column(db.Integer)
    tobacco_exposure = db.Column(db.Numeric(5, 1))
    occupational_dust = db.Column(db.Integer)
    allergic_rhinitis = db.Column(db.Integer)
    childhood_asthma = db.Column(db.Integer)
    bmi = db.Column(db.Numeric(4, 1))
    recorded_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now())


# ==============================================================================
# 6. MODALITY 4: NEUROLOGICAL & MENTAL (patient_neuro_mental_metrics)
# ==============================================================================
class NeuroMentalMetrics(db.Model):
    __tablename__ = 'patient_neuro_mental_metrics'
    
    metric_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.patient_id', ondelete='CASCADE'), nullable=False, index=True)
    
    phq9 = db.Column(db.Integer)
    gad7 = db.Column(db.Integer)
    mmse = db.Column(db.Integer)
    moca = db.Column(db.Integer)
    ham_d = db.Column(db.Integer)
    updrs_part3 = db.Column(db.Integer)
    daily_sleep = db.Column(db.Numeric(4, 1))
    psqi = db.Column(db.Integer)
    seizure_frequency = db.Column(db.Numeric(5, 1))
    hrv_sdnn = db.Column(db.Numeric(5, 1))
    serum_cortisol = db.Column(db.Numeric(4, 1))
    vitamin_b12 = db.Column(db.Numeric(6, 1))
    serum_folate = db.Column(db.Numeric(4, 1))
    tsh = db.Column(db.Numeric(5, 2))
    faq_score = db.Column(db.Integer)
    tremor_rating = db.Column(db.Integer)
    tbi_history = db.Column(db.Integer)
    substance_abuse = db.Column(db.Integer)
    family_history_neuro_psych = db.Column(db.Integer)
    age = db.Column(db.Numeric(4, 1))
    recorded_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now())


# ==============================================================================
# 7. CORE ENCOUNTER & LONGITUDINAL LEDGER (D3)
# ==============================================================================
class Encounter(db.Model):
    __tablename__ = 'encounters'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    encounter_uid = db.Column(db.String(64), unique=True, nullable=False, index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.patient_id', ondelete='CASCADE'), nullable=False, index=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.doctor_id'), nullable=False)
    
    # Discriminator: 'BASELINE', 'FOLLOWUP', 'REANCHOR_BASELINE'
    record_type = db.Column(db.String(32), nullable=False, default='BASELINE')
    
    # Cryptographic Chain & Provenance
    parent_baseline_hash = db.Column(db.String(64), nullable=True)
    cryptographic_hash = db.Column(db.String(64), nullable=False, unique=True, index=True)
    
    # Snapshots & Directives
    cdss_payload = db.Column(db.JSON, nullable=False)
    care_plan = db.Column(db.JSON, nullable=False)
    reanchor_decision = db.Column(db.String(16), nullable=True)
    
    created_at_utc = db.Column(db.DateTime(timezone=True), server_default=db.func.now(), nullable=False)

    # Relationships
    patient = db.relationship('Patient', backref=db.backref('encounters', lazy=True, cascade='all, delete-orphan'))
    doctor = db.relationship('Doctor', backref=db.backref('authored_encounters', lazy=True))

    # Contract Compatibility Alias
    @property
    def cdss_payload_snapshot(self):
        """Attribute alias for API contract compatibility."""
        return self.cdss_payload

    @cdss_payload_snapshot.setter
    def cdss_payload_snapshot(self, value):
        self.cdss_payload = value