# backend/model_orm/__init__.py
# Importing this package registers every table, so db.create_all() creates them all.
from backend.dbconnect import db
from .usr_orm import User
from .adm_orm import Admin
from .doc_orm import Doctor
from .pat_orm import Patient
from .clinic_orm import (
    IdempotencyCache,
    FamilyHistory,
    EnvironmentalHazard,
    FHRSStratification,
    CVDMetrics,
    T2DMetrics,
    RespiratoryMetrics,
    NeuroMentalMetrics,
    Encounter,
)
from .clinical_vector import ClinicalVector
from .audit_orm import AuditLedger

__all__ = [
    "db",
    "User",
    "Admin",
    "Doctor",
    "Patient",
    "IdempotencyCache",
    "FamilyHistory",
    "EnvironmentalHazard",
    "FHRSStratification",
    "CVDMetrics",
    "T2DMetrics",
    "RespiratoryMetrics",
    "NeuroMentalMetrics",
    "Encounter",
    "ClinicalVector",
    "AuditLedger",
]
