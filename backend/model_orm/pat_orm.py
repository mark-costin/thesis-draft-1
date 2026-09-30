from backend.dbconnect import db

class Patient(db.Model):
    __tablename__ = 'patients'

    patient_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='CASCADE'), unique=True, nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    middle_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100), nullable=False)
    suffix = db.Column(db.String(20), default='N/A')
    date_of_birth = db.Column(db.Date, nullable=False)
    gender = db.Column(db.String(20), nullable=False)
    religion = db.Column(db.String(50))
    address = db.Column(db.Text, nullable=False)
    contact_number = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    emergency_contact_name = db.Column(db.String(150), nullable=False)
    emergency_contact_number = db.Column(db.String(20), nullable=False)
    emergency_relation = db.Column(db.String(50), nullable=False)
    hipaa_consent = db.Column(db.Boolean, nullable=False, default=False)
    hipaa_consent_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now())
    is_active = db.Column(db.Boolean, default=True)
    updated_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now(), onupdate=db.func.now())

    # --- Hereditary & Vector AI Layer (clinic_orm.py & clinical_vector.py) ---
    family_history = db.relationship('FamilyHistory', backref='patient', cascade='all, delete-orphan', lazy=True)
    fhrs_records = db.relationship('FHRSStratification', backref='patient', cascade='all, delete-orphan', lazy=True)
    clinical_vector = db.relationship('ClinicalVector', backref='patient', uselist=False, cascade='all, delete-orphan')

    # --- 4 Chronic Disease Modality Relationships (clinic_orm.py) ---
    cvd_metrics = db.relationship('CVDMetrics', backref='patient', cascade='all, delete-orphan', lazy=True)
    t2d_metrics = db.relationship('T2DMetrics', backref='patient', cascade='all, delete-orphan', lazy=True)
    respiratory_metrics = db.relationship('RespiratoryMetrics', backref='patient', cascade='all, delete-orphan', lazy=True)
    neuro_mental_metrics = db.relationship('NeuroMentalMetrics', backref='patient', cascade='all, delete-orphan', lazy=True)