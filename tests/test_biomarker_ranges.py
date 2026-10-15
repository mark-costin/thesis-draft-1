"""
Clinical ranges for stored biomarkers (CDSS_Data_Dictionary.pdf, Parameter Ingestion Tables).

Before this change only the column size was checked, so hba1c 3.5 or sbp 900 passed
validation. PostgreSQL then rejected the T2D / respiratory / neuro values with a CHECK
constraint (a 500 STORE_FAILED), and CVD stored them without complaint.
"""
import json
import unittest

from tests._helpers import ROOT, has_modules

SPEC_FILE = ROOT / "experiment" / "data" / "reference" / "cdss_spec.json"

# Generator name -> database column name, where they differ
SPEC_TO_COLUMN = {"systolic_bp": "sbp", "diastolic_bp": "dbp", "tg": "triglycerides", "sleep_hours": "daily_sleep"}


class RangeTableTests(unittest.TestCase):
    def setUp(self):
        from backend.biomarker_ranges import CHOICES, RANGES
        self.RANGES, self.CHOICES = RANGES, CHOICES

    def test_every_modality_has_twenty_checked_fields(self):
        for modality in ("cvd", "t2d", "resp", "neuro"):
            fields = set(self.RANGES[modality]) | set(self.CHOICES.get(modality, {}))
            self.assertEqual(len(fields), 20, modality)

    def test_minimum_is_below_maximum(self):
        for modality, fields in self.RANGES.items():
            for field, (low, high, _unit) in fields.items():
                self.assertLess(low, high, f"{modality}.{field}")

    def test_neuro_age_follows_the_dictionary_not_the_old_database_check(self):
        # The live table allowed 18-90; the dictionary and cdss_spec.json say 18-100.
        self.assertEqual(self.RANGES["neuro"]["age"][:2], (18, 100))
        self.assertEqual(self.RANGES["cvd"]["age"][:2], (18, 100))

    def test_cvd_fields_missing_from_cdss_spec_have_dictionary_ranges(self):
        cvd = self.RANGES["cvd"]
        self.assertEqual(cvd["lvef"][:2], (15, 75))
        self.assertEqual(cvd["nt_probnp"][:2], (10, 35000))
        self.assertEqual(cvd["ctni"][:2], (0.01, 50.0))
        self.assertEqual(self.CHOICES["cvd"]["biological_sex"], ("Female", "Male"))

    @unittest.skipUnless(SPEC_FILE.exists(), "experiment/data/reference/cdss_spec.json not present")
    def test_agrees_with_the_generator_spec_used_for_training(self):
        bounds = json.loads(SPEC_FILE.read_text(encoding="utf-8"))["feature_bounds"]
        checked = 0
        for spec_name, b in bounds.items():
            column = SPEC_TO_COLUMN.get(spec_name, spec_name)
            for modality, fields in self.RANGES.items():
                if column in fields:
                    self.assertEqual(fields[column][:2], (b["min"], b["max"]), f"{modality}.{column}")
                    checked += 1
        self.assertGreaterEqual(checked, 20)

    @unittest.skipUnless(has_modules("sqlalchemy", "flask_sqlalchemy"), "SQLAlchemy not installed")
    def test_every_stored_column_has_a_range_or_allowed_values(self):
        from backend.biomarker_store import column_spec, metric_model
        for modality in ("cvd", "t2d", "resp", "neuro"):
            columns = set(column_spec(metric_model(modality)))
            checked = set(self.RANGES[modality]) | set(self.CHOICES.get(modality, {}))
            self.assertEqual(columns, checked, modality)

    @unittest.skipUnless(has_modules("sqlalchemy", "flask_sqlalchemy"), "SQLAlchemy not installed")
    def test_models_carry_the_same_checks_as_postgresql(self):
        # Same constraint names PostgreSQL already uses, so SQLite tests enforce them too.
        from backend.biomarker_store import metric_model
        names = {c.name for c in metric_model("t2d").__table__.constraints}
        self.assertIn("patient_t2d_metrics_hba1c_check", names)
        names = {c.name for c in metric_model("cvd").__table__.constraints}
        self.assertIn("patient_cvd_metrics_sbp_check", names)
        self.assertIn("patient_cvd_metrics_biological_sex_check", names)


class MigrationTests(unittest.TestCase):
    """The SQL that brings the live PostgreSQL tables in line must use the same limits."""

    TABLES = {"cvd": "patient_cvd_metrics", "t2d": "patient_t2d_metrics",
              "resp": "patient_respiratory_metrics", "neuro": "patient_neuro_mental_metrics"}

    def setUp(self):
        self.sql = (ROOT / "database" / "migrations" / "2026-10-15_biomarker_ranges.sql").read_text(encoding="utf-8")

    def test_every_range_is_in_the_migration(self):
        from backend.biomarker_ranges import RANGES
        for modality, fields in RANGES.items():
            table = self.TABLES[modality]
            for col, (low, high, _unit) in fields.items():
                self.assertIn(f"ADD CONSTRAINT {table}_{col}_check CHECK ({col} >= {low} AND {col} <= {high});",
                              self.sql, f"{table}.{col}")

    def test_sex_values_are_in_the_migration(self):
        self.assertIn("ADD CONSTRAINT patient_cvd_metrics_biological_sex_check "
                      "CHECK (biological_sex IN ('Female', 'Male'));", self.sql)

    def test_runs_in_one_transaction_and_can_be_rerun(self):
        self.assertTrue(self.sql.lstrip().splitlines()[0].startswith("--"))
        self.assertIn("BEGIN;", self.sql)
        self.assertTrue(self.sql.rstrip().endswith("COMMIT;"))
        self.assertEqual(self.sql.count("DROP CONSTRAINT IF EXISTS"), self.sql.count("ADD CONSTRAINT"))


class RangeValidationTests(unittest.TestCase):
    """validate_biomarkers with the dictionary ranges, as the storage route calls it."""

    SPEC = {
        "sbp": ("numeric", None, None),
        "hba1c": ("numeric", 4, 1),
        "phq9": ("integer",),
        "biological_sex": ("string", 20),
    }
    RANGES = {"sbp": (70, 220, "mmHg"), "hba1c": (4.0, 15.0, "%"), "phq9": (0, 27, "score")}
    CHOICES = {"biological_sex": ("Female", "Male")}

    def validate(self, values):
        from backend.validation import validate_biomarkers
        return validate_biomarkers(self.SPEC, values, ranges=self.RANGES, choices=self.CHOICES)

    def rejected(self, values):
        from backend.validation import ValidationError
        with self.assertRaises(ValidationError) as ctx:
            self.validate(values)
        return ctx.exception

    def test_values_inside_the_range_pass(self):
        self.assertEqual(self.validate({"sbp": 130, "hba1c": 6.4}), {"sbp": 130, "hba1c": 6.4})

    def test_both_limits_are_allowed(self):
        self.assertEqual(self.validate({"hba1c": 4.0, "phq9": 27}), {"hba1c": 4.0, "phq9": 27})

    def test_below_minimum_is_rejected_with_the_limits_in_the_message(self):
        exc = self.rejected({"hba1c": 3.5})
        self.assertEqual(exc.fields, ["hba1c"])
        self.assertIn("4.0", str(exc))
        self.assertIn("15.0", str(exc))
        self.assertIn("%", str(exc))

    def test_above_maximum_is_rejected(self):
        self.assertEqual(self.rejected({"sbp": 900}).fields, ["sbp"])

    def test_every_out_of_range_field_is_listed(self):
        self.assertEqual(sorted(self.rejected({"sbp": 900, "hba1c": 3.5, "phq9": 5}).fields), ["hba1c", "sbp"])

    def test_wrong_type_and_out_of_range_are_both_reported(self):
        self.assertEqual(sorted(self.rejected({"sbp": "high", "hba1c": 3.5}).fields), ["hba1c", "sbp"])

    def test_sex_is_stored_in_the_dictionary_spelling(self):
        self.assertEqual(self.validate({"biological_sex": " female "}), {"biological_sex": "Female"})

    def test_unlisted_sex_value_is_rejected(self):
        self.assertEqual(self.rejected({"biological_sex": "F"}).fields, ["biological_sex"])

    def test_without_ranges_only_the_column_is_checked(self):
        from backend.validation import validate_biomarkers
        self.assertEqual(validate_biomarkers(self.SPEC, {"sbp": 900}), {"sbp": 900})


class InferenceRangeTests(unittest.TestCase):
    """out_of_range() for /infer payloads, which may use the model's feature names."""

    def errors(self, modality, payload):
        from backend.biomarker_ranges import out_of_range
        return out_of_range(modality, payload)

    def test_model_feature_names_are_checked_like_column_names(self):
        self.assertEqual(list(self.errors("cvd", {"systolic_bp": 900})), ["systolic_bp"])
        self.assertEqual(list(self.errors("cvd", {"sbp": 900})), ["sbp"])

    def test_in_range_payload_has_no_errors(self):
        self.assertEqual(self.errors("cvd", {"age": 50, "sbp": 130, "tg": 150}), {})

    def test_text_and_unknown_features_are_left_to_the_engine(self):
        self.assertEqual(self.errors("cvd", {"age": "fifty", "bio_fhrs_cvd": 99}), {})

    def test_booleans_are_not_treated_as_numbers(self):
        self.assertEqual(self.errors("cvd", {"family_history_premature_cvd": True}), {})


if __name__ == "__main__":
    unittest.main()
