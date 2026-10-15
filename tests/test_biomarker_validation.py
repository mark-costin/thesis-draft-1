"""validate_biomarkers: only real columns, right types, values that fit the column."""
import unittest

from tests._helpers import ROOT  # noqa: F401

# The same shapes as the columns in clinic_orm.py
SPEC = {
    "sbp": ("numeric", None, None),          # db.Numeric
    "hba1c": ("numeric", 4, 1),              # db.Numeric(4, 1): max 999.9
    "fev1": ("numeric", 3, 1),               # db.Numeric(3, 1): max 99.9
    "phq9": ("integer",),                    # db.Integer
    "biological_sex": ("string", 20),        # db.String(20)
}


class BiomarkerValidationTests(unittest.TestCase):
    def validate(self, values):
        from backend.validation import validate_biomarkers
        return validate_biomarkers(SPEC, values)

    def assertRejected(self, field, values):
        from backend.validation import ValidationError
        with self.assertRaises(ValidationError) as ctx:
            self.validate(values)
        self.assertIn(field, ctx.exception.fields)

    def test_valid_values_pass(self):
        out = self.validate({"sbp": 130, "hba1c": 6.4, "phq9": 7, "biological_sex": "Female"})
        self.assertEqual(out, {"sbp": 130, "hba1c": 6.4, "phq9": 7, "biological_sex": "Female"})

    def test_unknown_field_is_rejected_by_name(self):
        self.assertRejected("systolic", {"systolic": 130})

    def test_text_in_numeric_field_is_rejected(self):
        self.assertRejected("sbp", {"sbp": "high"})

    def test_boolean_in_numeric_field_is_rejected(self):
        self.assertRejected("sbp", {"sbp": True})

    def test_infinite_value_is_rejected(self):
        self.assertRejected("sbp", {"sbp": float("inf")})

    def test_value_too_large_for_column_is_rejected(self):
        # Numeric(4, 1) holds at most 999.9; Postgres would raise "numeric field overflow"
        self.assertRejected("hba1c", {"hba1c": 1000})

    def test_largest_value_that_fits_is_accepted(self):
        self.assertEqual(self.validate({"fev1": 99.9})["fev1"], 99.9)

    def test_negative_overflow_is_rejected(self):
        self.assertRejected("fev1", {"fev1": -100})

    def test_unbounded_numeric_accepts_large_values(self):
        self.assertEqual(self.validate({"sbp": 123456})["sbp"], 123456)

    def test_fraction_in_integer_field_is_rejected(self):
        self.assertRejected("phq9", {"phq9": 7.5})

    def test_whole_float_in_integer_field_is_accepted(self):
        self.assertEqual(self.validate({"phq9": 7.0})["phq9"], 7)

    def test_too_long_string_is_rejected(self):
        self.assertRejected("biological_sex", {"biological_sex": "x" * 21})

    def test_null_values_are_dropped(self):
        self.assertEqual(self.validate({"sbp": 130, "hba1c": None}), {"sbp": 130})

    def test_empty_payload_is_rejected(self):
        from backend.validation import ValidationError
        with self.assertRaises(ValidationError):
            self.validate({})

    def test_non_object_payload_is_rejected(self):
        from backend.validation import ValidationError
        with self.assertRaises(ValidationError):
            self.validate([130])


if __name__ == "__main__":
    unittest.main()