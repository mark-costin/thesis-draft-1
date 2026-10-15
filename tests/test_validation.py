"""Input validation for registration, provisioning, patient ids and FHRS weights."""
import unittest
from datetime import date, timedelta

from tests._helpers import ROOT  # noqa: F401

VALID_REGISTRATION = {
    "username": "jane",
    "password": "correct-horse-1",
    "first_name": "Jane", "last_name": "Cruz",
    "date_of_birth": "1990-05-14", "gender": "Female",
    "address": "1 Test St", "contact_number": "0900-000-0000", "email": "jane@example.com",
    "emergency_contact_name": "Ana", "emergency_contact_number": "0900-000-0001",
    "emergency_relation": "Sister", "hipaa_consent": True,
}


class RegistrationValidationTests(unittest.TestCase):
    def validate(self, **overrides):
        from backend.validation import validate_registration
        return validate_registration({**VALID_REGISTRATION, **overrides})

    def assertRejected(self, field_hint, **overrides):
        from backend.validation import ValidationError
        with self.assertRaises(ValidationError) as ctx:
            self.validate(**overrides)
        self.assertIn(field_hint, str(ctx.exception))

    def test_valid_registration_parses_date(self):
        self.assertEqual(self.validate()["date_of_birth"], date(1990, 5, 14))

    def test_consent_is_required(self):
        self.assertRejected("hipaa_consent", hipaa_consent=False)

    def test_consent_string_false_is_not_consent(self):
        self.assertRejected("hipaa_consent", hipaa_consent="false")

    def test_missing_consent_is_rejected(self):
        from backend.validation import ValidationError, validate_registration
        data = {k: v for k, v in VALID_REGISTRATION.items() if k != "hipaa_consent"}
        with self.assertRaises(ValidationError):
            validate_registration(data)

    def test_bad_date_is_rejected(self):
        self.assertRejected("date_of_birth", date_of_birth="14/05/1990")

    def test_future_birth_date_is_rejected(self):
        self.assertRejected("date_of_birth", date_of_birth=(date.today() + timedelta(days=1)).isoformat())

    def test_short_password_is_rejected(self):
        self.assertRejected("password", password="short")

    def test_password_over_bcrypt_limit_is_rejected(self):
        # bcrypt silently ignores everything after 72 bytes
        self.assertRejected("password", password="x" * 73)

    def test_missing_required_field_is_named(self):
        self.assertRejected("emergency_relation", emergency_relation="")

    def test_role_cannot_be_chosen_by_client(self):
        self.assertNotIn("role", self.validate(role="ADMIN"))


VALID_PROVISION = {
    "username": "dr_reyes", "password": "correct-horse-2",
    "first_name": "Luis", "last_name": "Reyes", "address": "2 Clinic Rd",
    "specialization": "Cardiology", "license_number": "PRC-0042",
    "contact_number": "0900-000-0002", "email": "reyes@example.com",
    "emergency_contact_name": "Maria", "emergency_contact_number": "0900-000-0003",
    "emergency_relation": "Spouse",
}


class ProvisionValidationTests(unittest.TestCase):
    def test_valid_provision_passes(self):
        from backend.validation import validate_provision
        self.assertEqual(validate_provision(VALID_PROVISION)["license_number"], "PRC-0042")

    def test_license_number_is_required(self):
        from backend.validation import ValidationError, validate_provision
        with self.assertRaises(ValidationError) as ctx:
            validate_provision({**VALID_PROVISION, "license_number": ""})
        self.assertIn("license_number", str(ctx.exception))


class PatientIdTests(unittest.TestCase):
    def test_numeric_string_is_accepted(self):
        from backend.validation import parse_patient_id
        self.assertEqual(parse_patient_id("12"), 12)

    def test_non_numeric_is_a_validation_error_not_a_crash(self):
        from backend.validation import ValidationError, parse_patient_id
        with self.assertRaises(ValidationError):
            parse_patient_id("abc")

    def test_zero_or_negative_is_rejected(self):
        from backend.validation import ValidationError, parse_patient_id
        with self.assertRaises(ValidationError):
            parse_patient_id("0")


class FhrsWeightTests(unittest.TestCase):
    def weights(self, role, **data):
        from backend.validation import family_history_weights
        return family_history_weights(role, data)

    def test_patient_supplied_weights_are_ignored(self):
        from backend.validation import DEFAULT_ONSET_WEIGHT, DEFAULT_RELATIONSHIP_WEIGHT
        self.assertEqual(self.weights("PATIENT", relationship_weight=99, onset_weight=99),
                         (DEFAULT_RELATIONSHIP_WEIGHT, DEFAULT_ONSET_WEIGHT))

    def test_doctor_supplied_weights_are_used(self):
        self.assertEqual(self.weights("DOCTOR", relationship_weight=0.25, onset_weight=1.5), (0.25, 1.5))

    def test_doctor_defaults_when_weights_missing(self):
        from backend.validation import DEFAULT_ONSET_WEIGHT, DEFAULT_RELATIONSHIP_WEIGHT
        self.assertEqual(self.weights("DOCTOR"), (DEFAULT_RELATIONSHIP_WEIGHT, DEFAULT_ONSET_WEIGHT))

    def test_negative_weight_is_rejected(self):
        from backend.validation import ValidationError
        with self.assertRaises(ValidationError):
            self.weights("DOCTOR", relationship_weight=-1)

    def test_non_numeric_weight_is_rejected(self):
        from backend.validation import ValidationError
        with self.assertRaises(ValidationError):
            self.weights("ADMIN", onset_weight="high")

    def test_infinite_weight_is_rejected(self):
        from backend.validation import ValidationError
        with self.assertRaises(ValidationError):
            self.weights("DOCTOR", onset_weight=float("inf"))


if __name__ == "__main__":
    unittest.main()
