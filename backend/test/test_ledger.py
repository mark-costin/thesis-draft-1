"""Encounter seal: covers every sealed field, survives a DB round trip, needs the server key."""
import os
import subprocess
import sys
import unittest
from datetime import datetime, timedelta, timezone

from tests._helpers import ROOT

MANILA = timezone(timedelta(hours=8))
CREATED = datetime(2026, 10, 15, 0, 0, 0, 123456, tzinfo=timezone.utc)


def fields(**overrides):
    base = {
        "encounter_uid": "ENC-ABC123",
        "patient_id": 7,
        "doctor_id": 3,
        "record_type": "FOLLOWUP",
        "parent_baseline_hash": "a" * 64,
        "created_at": CREATED,
        "cdss_payload": {"risk": {"tier": "HIGH", "score": 61.2}},
        "care_plan": {"directive": "Start statin", "prescriptions": ["atorvastatin 20mg"]},
        "reanchor_decision": None,
    }
    base.update(overrides)
    return base


class SealCoverageTests(unittest.TestCase):
    """Changing any sealed field must change the seal."""

    def setUp(self):
        from backend.ledger import seal
        self.seal = seal
        self.original = seal(**fields())

    def assertChanges(self, **override):
        self.assertNotEqual(self.seal(**fields(**override)), self.original, f"seal ignored {list(override)}")

    def test_same_fields_give_same_seal(self):
        self.assertEqual(self.seal(**fields()), self.original)

    def test_care_plan_is_sealed(self):
        self.assertChanges(care_plan={"directive": "Start statin", "prescriptions": ["atorvastatin 80mg"]})

    def test_record_type_is_sealed(self):
        self.assertChanges(record_type="REANCHOR_BASELINE")

    def test_encounter_uid_is_sealed(self):
        self.assertChanges(encounter_uid="ENC-OTHER")

    def test_reanchor_decision_is_sealed(self):
        self.assertChanges(reanchor_decision="ACCEPT")

    def test_doctor_is_sealed(self):
        self.assertChanges(doctor_id=4)

    def test_parent_hash_is_sealed(self):
        self.assertChanges(parent_baseline_hash="b" * 64)

    def test_cdss_payload_is_sealed(self):
        self.assertChanges(cdss_payload={"risk": {"tier": "LOW", "score": 61.2}})

    def test_key_order_does_not_matter(self):
        reordered = {"care_plan": {"prescriptions": ["atorvastatin 20mg"], "directive": "Start statin"}}
        self.assertEqual(self.seal(**fields(**reordered)), self.original)


class SealTimestampTests(unittest.TestCase):
    """The same instant must seal the same way however the database hands it back."""

    def setUp(self):
        from backend.ledger import seal
        self.seal = seal
        self.original = seal(**fields())

    def test_postgres_style_aware_time_in_another_zone_matches(self):
        self.assertEqual(self.seal(**fields(created_at=CREATED.astimezone(MANILA))), self.original)

    def test_sqlite_style_naive_utc_time_matches(self):
        self.assertEqual(self.seal(**fields(created_at=CREATED.replace(tzinfo=None))), self.original)

    def test_canonical_timestamp_keeps_microseconds_even_when_zero(self):
        from backend.ledger import canonical_timestamp
        whole = datetime(2026, 10, 15, 0, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(canonical_timestamp(whole), "2026-10-15T00:00:00.000000Z")


class SealKeyTests(unittest.TestCase):
    def test_seal_depends_on_server_key(self):
        from backend.ledger import seal
        self.assertNotEqual(seal(**fields()), seal(**fields(), key="some-other-key"))

    def test_seal_is_not_a_plain_sha256_anyone_can_recompute(self):
        import hashlib
        from backend.ledger import canonical_envelope, seal
        plain = hashlib.sha256(canonical_envelope(**fields()).encode("utf-8")).hexdigest()
        self.assertNotEqual(seal(**fields()), plain)

    def test_server_refuses_to_start_without_seal_key(self):
        env = {k: v for k, v in os.environ.items() if k != "ENCOUNTER_SEAL_KEY"}
        result = subprocess.run([sys.executable, "-c", "import backend.ledger"],
                                cwd=str(ROOT), env=env, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ENCOUNTER_SEAL_KEY", result.stderr)


class VerifyTests(unittest.TestCase):
    def test_untouched_fields_verify(self):
        from backend.ledger import seal, verify_seal
        self.assertTrue(verify_seal(seal(**fields()), **fields()))

    def test_edited_care_plan_fails_verification(self):
        from backend.ledger import seal, verify_seal
        sealed = seal(**fields())
        self.assertFalse(verify_seal(sealed, **fields(care_plan={"directive": "None"})))

    def test_missing_seal_fails_verification(self):
        from backend.ledger import verify_seal
        self.assertFalse(verify_seal(None, **fields()))


if __name__ == "__main__":
    unittest.main()
