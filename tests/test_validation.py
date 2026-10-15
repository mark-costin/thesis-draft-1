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


class FamilyHistoryEntryTests(unittest.TestCase):
    """
    validate_family_history: tier and onset are fixed categories from the FHRS Guide and the
    weights are looked up from cdss_spec.json, never typed in. Only staff can mark verified.
    """

    def entry(self, role="DOCTOR", **data):
        from backend.validation import validate_family_history
        body = {"disease_domain": "cvd", "relationship_tier": 1, "onset_classification": "early"}
        body.update(data)
        return validate_family_history(role, body)

    def rejected(self, field, role="DOCTOR", **data):
        from backend.validation import ValidationError
        with self.assertRaises(ValidationError) as ctx:
            self.entry(role, **data)
        self.assertIn(field, ctx.exception.fields)

    def test_weights_come_from_the_spec(self):
        e = self.entry(relationship_tier=2, onset_classification="severe_early")
        self.assertEqual((e["relationship_weight"], e["onset_weight"]), (0.25, 3.0))
        self.assertEqual((e["relationship_tier"], e["onset_classification"]), ("2", "severe_early"))

    def test_typed_in_weights_are_ignored_for_everyone(self):
        e = self.entry(relationship_weight=99, onset_weight=99)
        self.assertEqual((e["relationship_weight"], e["onset_weight"]), (0.5, 2.0))

    def test_older_spellings_are_accepted(self):
        e = self.entry(disease_domain="CVD", relationship_tier="Tier 3", onset_classification="Late onset")
        self.assertEqual((e["disease_domain"], e["relationship_tier"], e["onset_classification"]), ("cvd", "3", "late"))

    def test_disease_names_are_mapped_to_the_four_models(self):
        for name, code in (("Diabetes", "t2d"), ("respiratory", "resp"), ("Mental health", "neuro")):
            self.assertEqual(self.entry(disease_domain=name)["disease_domain"], code)

    def test_tier_and_onset_are_required(self):
        from backend.validation import ValidationError, validate_family_history
        with self.assertRaises(ValidationError) as ctx:
            validate_family_history("DOCTOR", {"disease_domain": "cvd"})
        self.assertEqual(sorted(ctx.exception.fields), ["onset_classification", "relationship_tier"])

    def test_unknown_values_are_rejected_by_field(self):
        self.rejected("relationship_tier", relationship_tier=4)
        self.rejected("onset_classification", onset_classification="sudden")
        self.rejected("disease_domain", disease_domain="kidney")
        self.rejected("age_at_diagnosis", age_at_diagnosis=-1)

    def test_only_staff_can_mark_verified(self):
        self.assertTrue(self.entry("DOCTOR", is_verified=True)["is_verified"])
        self.assertFalse(self.entry("PATIENT", is_verified=True)["is_verified"])
        self.assertFalse(self.entry("DOCTOR")["is_verified"])


class SexAndHazardTests(unittest.TestCase):
    def test_biological_sex_uses_the_dictionary_spelling(self):
        from backend.validation import parse_biological_sex
        self.assertEqual(parse_biological_sex(" male "), "Male")
        self.assertEqual(parse_biological_sex("FEMALE"), "Female")

    def test_other_sex_values_are_rejected(self):
        from backend.validation import ValidationError, parse_biological_sex
        for value in ("F", "Prefer not to say", None, 1):
            with self.assertRaises(ValidationError):
                parse_biological_sex(value)

    def test_hazard_must_be_on_that_diseases_list(self):
        from backend.validation import ValidationError, validate_hazard
        self.assertEqual(validate_hazard({"disease_domain": "Respiratory", "hazard_code": "biomass_heating"}),
                         ("resp", "biomass_heating"))
        with self.assertRaises(ValidationError):
            validate_hazard({"disease_domain": "cvd", "hazard_code": "biomass_heating"})
        with self.assertRaises(ValidationError):
            validate_hazard({"disease_domain": "neuro", "hazard_code": "stress"})


if __name__ == "__main__":
    unittest.main()
