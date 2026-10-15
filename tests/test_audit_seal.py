"""Audit ledger entries: sealed with the server key, so an edited entry is detectable."""
import unittest
from datetime import datetime, timedelta, timezone

from tests._helpers import ROOT  # noqa: F401

CREATED = datetime(2026, 10, 15, 1, 30, 0, 250000, tzinfo=timezone.utc)


def entry(**overrides):
    base = {
        "audit_id": "6f1c2a3e-0000-4000-8000-000000000001",
        "created_at": CREATED,
        "event_type": "INFERENCE",
        "payload": {"modality": "cvd", "tier": "HIGH", "score": 61.2},
        "patient_id": 5,
        "doctor_id": 1,
        "actor_user_id": 10,
    }
    base.update(overrides)
    return base


class AuditSealTests(unittest.TestCase):
    def setUp(self):
        from backend.audit import seal_audit
        self.seal = seal_audit
        self.original = seal_audit(**entry())

    def assertChanges(self, **override):
        self.assertNotEqual(self.seal(**entry(**override)), self.original, f"seal ignored {list(override)}")

    def test_same_entry_gives_same_seal(self):
        self.assertEqual(self.seal(**entry()), self.original)

    def test_payload_is_sealed(self):
        self.assertChanges(payload={"modality": "cvd", "tier": "LOW", "score": 61.2})

    def test_event_type_is_sealed(self):
        self.assertChanges(event_type="MODELS_RELOADED")

    def test_patient_is_sealed(self):
        self.assertChanges(patient_id=6)

    def test_actor_is_sealed(self):
        self.assertChanges(actor_user_id=11)

    def test_audit_id_is_sealed(self):
        self.assertChanges(audit_id="6f1c2a3e-0000-4000-8000-000000000002")

    def test_same_instant_in_another_timezone_gives_same_seal(self):
        manila = CREATED.astimezone(timezone(timedelta(hours=8)))
        self.assertEqual(self.seal(**entry(created_at=manila)), self.original)

    def test_seal_uses_the_server_key(self):
        self.assertNotEqual(self.seal(**entry(), key="another-key"), self.original)

    def test_seal_is_64_hex_characters(self):
        self.assertEqual(len(self.original), 64)
        int(self.original, 16)


class AuditVerifyTests(unittest.TestCase):
    def test_untouched_entry_verifies(self):
        from backend.audit import seal_audit, verify_audit_fields
        self.assertTrue(verify_audit_fields(seal_audit(**entry()), **entry()))

    def test_edited_payload_fails_verification(self):
        from backend.audit import seal_audit, verify_audit_fields
        sealed = seal_audit(**entry())
        self.assertFalse(verify_audit_fields(sealed, **entry(payload={"tier": "LOW"})))

    def test_missing_seal_fails_verification(self):
        from backend.audit import verify_audit_fields
        self.assertFalse(verify_audit_fields(None, **entry()))


if __name__ == "__main__":
    unittest.main()
