"""
Feature builder: stored rows -> the exact inputs each model was trained on (experiment/src/ml/data.py).

  m_<test>   = 1 when that test is missing in the record (data.py: M = 1 means missing)
  v_<marker> = (current - first visit) / months, blank when under 30 days
  m_velocity = 1 when under 30 days since the first visit
  age from the record, else from date of birth; sex Female 0 / Male 1 (CDSS dictionary)
"""
import json
import unittest
from datetime import date, datetime, timedelta, timezone

from tests._helpers import ROOT

T0 = datetime(2026, 8, 1, 9, 0, tzinfo=timezone.utc)
DOB = date(1970, 1, 1)
FHRS = {"adjusted_fhrs": 4.16875, "band": 3}

CVD_FULL = {"age": 58, "biological_sex": None, "sbp": 142, "dbp": 88, "bmi": 27.5, "resting_hr": 72,
            "total_cholesterol": 210, "hdl": 45, "ldl": 130, "triglycerides": 160, "hs_crp": 2.1,
            "serum_creatinine": 1.0, "egfr": 85, "lvef": 60, "ctni": 0.01, "nt_probnp": 100,
            "smoking_history": 10, "daily_sodium": 3000, "family_history_premature_cvd": 1,
            "physical_activity": 120}
FULL_ROWS = {
    "cvd": CVD_FULL,
    "t2d": {"fpg": 110, "hba1c": 6.1, "bmi": 29.0, "triglycerides": 170, "hdl": 42},
    "resp": {"fev1": 2.9, "fvc": 3.8, "fev1_fvc_ratio": 76.0, "spo2": 97.0},
    "neuro": {"mmse": 28, "phq9": 6, "gad7": 4, "daily_sleep": 7.0, "age": 58},
}


def build(modality="cvd", latest=None, earliest=None, days=0, profile_sex=None, dob=DOB, fhrs=FHRS):
    from backend.cdss.feature_builder import assemble_features
    latest = dict(CVD_FULL if latest is None else latest)
    return assemble_features(
        modality, latest=latest, earliest=earliest if earliest is not None else latest,
        latest_at=T0 + timedelta(days=days), earliest_at=T0,
        date_of_birth=dob, profile_sex=profile_sex, fhrs=fhrs)


class NamesAndCoreTests(unittest.TestCase):
    def test_database_columns_get_the_training_names(self):
        f = build()
        self.assertEqual((f["systolic_bp"], f["diastolic_bp"], f["tg"]), (142, 88, 160))
        self.assertNotIn("sbp", f)

    def test_neuro_sleep_uses_the_training_name(self):
        self.assertEqual(build("neuro", FULL_ROWS["neuro"])["sleep_hours"], 7.0)

    def test_sex_comes_from_the_patient_profile(self):
        self.assertEqual(build(profile_sex="Male")["biological_sex"], 1)
        self.assertEqual(build(profile_sex="Female")["biological_sex"], 0)

    def test_sex_falls_back_to_the_cvd_record_then_blank(self):
        self.assertEqual(build(latest={**CVD_FULL, "biological_sex": "Female"})["biological_sex"], 0)
        self.assertIsNone(build()["biological_sex"])

    def test_recorded_age_is_used_otherwise_date_of_birth(self):
        self.assertEqual(build()["age"], 58)
        self.assertEqual(build("t2d", FULL_ROWS["t2d"])["age"], 56)      # 1970-01-01 to 2026-08-01

    def test_fhrs_inputs_are_named_per_disease(self):
        f = build("t2d", FULL_ROWS["t2d"])
        self.assertEqual((f["adjusted_fhrs_t2d"], f["fhrs_band_t2d"]), (4.16875, 3))

    def test_without_fhrs_the_inputs_are_blank(self):
        f = build(fhrs=None)
        self.assertIsNone(f["adjusted_fhrs_cvd"])


class MissingFlagTests(unittest.TestCase):
    def test_flag_is_1_only_when_the_test_is_missing(self):
        f = build(latest={**CVD_FULL, "ldl": None})
        self.assertEqual((f["m_ldl"], f["m_total_cholesterol"], f["m_tg"]), (1, 0, 0))

    def test_spirometry_is_one_test(self):
        none = {"fev1": None, "fvc": None, "fev1_fvc_ratio": None, "spo2": 97.0}
        self.assertEqual(build("resp", none)["m_spirometry"], 1)
        self.assertEqual(build("resp", {**none, "fev1": 2.9})["m_spirometry"], 0)


class VelocityTests(unittest.TestCase):
    def test_change_per_month_since_the_first_record(self):
        f = build(latest={**CVD_FULL, "sbp": 142}, earliest={**CVD_FULL, "sbp": 130}, days=60)
        self.assertAlmostEqual(f["v_systolic_bp"], 12 / (60 / 30.4375))
        self.assertEqual(f["m_velocity"], 0)

    def test_single_record_has_no_velocity(self):
        f = build()
        self.assertIsNone(f["v_systolic_bp"])
        self.assertEqual(f["m_velocity"], 1)

    def test_under_30_days_has_no_velocity(self):
        f = build(latest={**CVD_FULL, "sbp": 142}, earliest={**CVD_FULL, "sbp": 130}, days=29)
        self.assertIsNone(f["v_systolic_bp"])
        self.assertEqual(f["m_velocity"], 1)

    def test_no_velocity_when_the_first_value_was_not_measured(self):
        f = build(latest=CVD_FULL, earliest={**CVD_FULL, "egfr": None}, days=90)
        self.assertIsNone(f["v_egfr"])
        self.assertIsNotNone(f["v_systolic_bp"])


class ModelCoverageTests(unittest.TestCase):
    """Every input each trained model expects is produced from a full record."""

    def test_all_model_inputs_are_produced(self):
        from backend.cdss.model_loader import MODEL_DIR   # the folder the backend loads models from
        checked = 0
        for disease, row in FULL_ROWS.items():
            path = MODEL_DIR / f"{disease}_head_latest.json"
            if not path.exists():
                continue
            expected = json.loads(path.read_text(encoding="utf-8"))["feature_columns"]
            f = build(disease, row, earliest=row, days=60, profile_sex="Female")
            self.assertEqual([c for c in expected if c not in f], [], disease)
            self.assertEqual([c for c in expected if f[c] is None], [], disease)
            checked += 1
        self.assertGreater(checked, 0, f"no model metadata found in {MODEL_DIR}")


if __name__ == "__main__":
    unittest.main()
