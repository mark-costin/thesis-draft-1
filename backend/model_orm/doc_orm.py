from datetime import datetime
from dbconnect import db

class Doctor(db.Model):
    __tablename__ = 'doctors'

    doctor_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='CASCADE'), unique=True, nullable=False)
    
    first_name = db.Column(db.String(100), nullable=False)
    middle_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100), nullable=False)
    suffix = db.Column(db.String(20), default='None')
    address = db.Column(db.Text, nullable=False)
    
    specialization = db.Column(db.String(100), nullable=False)
    hospital_affiliation = db.Column(db.String(255), default='Lucerna Medica Main Clinic')
    license_number = db.Column(db.String(50), unique=True, nullable=False)
    
    contact_number = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    
    emergency_contact_name = db.Column(db.String(150), nullable=False)
    emergency_contact_number = db.Column(db.String(20), nullable=False)
    emergency_relation = db.Column(db.String(50), nullable=False)
    
    is_verified = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)