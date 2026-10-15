"""
Triage queue stored in PostgreSQL (batch 5b). Before, the queue was a Python list: a server
restart emptied it, and a second worker saw a different queue.

Patients see and cancel only their own ticket; numbers never repeat within a day; cancelled
and finished tickets stay in the table as history.
Needs: flask_sqlalchemy (runs on your machine; skipped where missing).
"""
import os
import unittest
from datetime import date, timedelta

from tests._helpers import has_modules

DB_STACK = has_modules("flask_sqlalchemy", "pgvector")
TODAY = date(2026, 10, 15)


def _person(prefix):
    return dict(first_name=f"{prefix}First", last_name=f"{prefix}Last", address="1 Test St",
                contact_number="0900-000-0000", email=f"{prefix.lower()}@example.com",
                emergency_contact_name="Contact", emergency_contact_number="0900-000-0001",
                emergency_relation="Sibling")


@unittest.skipUnless(DB_STACK, "needs flask_sqlalchemy + pgvector (runs on your machine)")
class TriageQueueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["DATABASE_URL"] = "sqlite://"
        from flask import Flask
        from backend.dbconnect import db, init_db
        import backend.model_orm  # noqa: F401
        cls.app = Flask(__name__)
        init_db(cls.app)
        cls.db = db
        with cls.app.app_context():
            db.create_all()

    def setUp(self):
        from backend.model_orm import Patient, User
        from backend.model_orm.clinic_orm import QueueTicket
        self.QueueTicket = QueueTicket
        self.ctx = self.app.app_context()
        self.ctx.push()
        s = self.db.session
        for model in (QueueTicket, Patient, User):
            s.query(model).delete()
        for uid, pid in ((20, 1), (21, 2), (22, 3)):
            s.add(User(user_id=uid, username=f"u{uid}", role="PATIENT", password_hash="x"))
            s.flush()
            s.add(Patient(patient_id=pid, user_id=uid, date_of_birth=date(1980, 1, 1), gender="Female",
                          hipaa_consent=True, **_person(f"P{pid}")))
        s.commit()
        self.day = TODAY
        self.q = self.queue()

    def tearDown(self):
        self.db.session.rollback()
        self.ctx.pop()

    def queue(self):
        from backend.triage_queue import TriageQueue
        return TriageQueue(today=lambda: self.day)

    def checkin(self, pid, by_staff=False, **fields):
        return self.q.checkin(pid, fields, by_staff=by_staff)

    # --- visibility -------------------------------------------------------
    def test_patient_sees_only_own_ticket(self):
        self.checkin(1)
        self.checkin(2)
        self.assertEqual([t["patient_id"] for t in self.q.list_for("PATIENT", 1)], [1])

    def test_staff_see_every_ticket_in_number_order(self):
        self.checkin(2)
        self.checkin(1)
        self.assertEqual([t["queue_no"] for t in self.q.list_for("DOCTOR")], ["Q-01", "Q-02"])

    def test_patient_without_ticket_sees_empty_queue(self):
        self.checkin(1)
        self.assertEqual(self.q.list_for("PATIENT", 2), [])

    # --- cancelling -------------------------------------------------------
    def test_patient_cannot_cancel_another_patients_ticket(self):
        self.checkin(2)
        self.assertEqual(self.q.cancel(2, role="PATIENT", caller_patient_id=1), "forbidden")
        self.assertEqual(len(self.q.list_for("DOCTOR")), 1)

    def test_patient_can_cancel_own_ticket(self):
        self.checkin(1)
        self.assertEqual(self.q.cancel(1, role="PATIENT", caller_patient_id=1), "cancelled")
        self.assertEqual(self.q.list_for("DOCTOR"), [])

    def test_staff_can_cancel_any_ticket(self):
        self.checkin(2)
        self.assertEqual(self.q.cancel(2, role="DOCTOR"), "cancelled")

    def test_cancel_missing_ticket_is_not_found(self):
        self.assertEqual(self.q.cancel(3, role="DOCTOR"), "not_found")

    def test_cancelled_ticket_is_kept_as_history(self):
        self.checkin(1)
        self.q.cancel(1, role="DOCTOR")
        row = self.QueueTicket.query.one()
        self.assertEqual(row.status, "CANCELLED")
        self.assertIsNotNone(row.closed_at)

    # --- numbering --------------------------------------------------------
    def test_ticket_numbers_never_repeat_after_cancel(self):
        self.checkin(1)
        self.checkin(2)
        self.q.cancel(2, role="DOCTOR")
        ticket, _ = self.checkin(3)
        self.assertEqual(ticket["queue_no"], "Q-03")

    def test_numbering_starts_again_each_day(self):
        self.checkin(1)
        self.day = TODAY + timedelta(days=1)
        ticket, _ = self.queue().checkin(2, {})
        self.assertEqual(ticket["queue_no"], "Q-01")

    def test_yesterdays_waiting_ticket_is_not_in_todays_queue(self):
        self.checkin(1)
        self.day = TODAY + timedelta(days=1)
        q = self.queue()
        self.assertEqual(q.list_for("DOCTOR"), [])
        ticket, created = q.checkin(1, {})
        self.assertTrue(created)

    # --- check-in ---------------------------------------------------------
    def test_second_checkin_returns_existing_ticket(self):
        first, created = self.checkin(1)
        second, created_again = self.checkin(1, complaint="new")
        self.assertTrue(created)
        self.assertFalse(created_again)
        self.assertEqual(first["queue_no"], second["queue_no"])

    def test_patient_cannot_set_own_urgency(self):
        ticket, _ = self.checkin(1, urgency="🔴 Emergency")
        self.assertEqual(ticket["urgency"], "🟢 Routine")

    def test_staff_can_set_urgency(self):
        ticket, _ = self.checkin(1, by_staff=True, urgency="🔴 Emergency")
        self.assertEqual(ticket["urgency"], "🔴 Emergency")

    def test_ticket_has_the_fields_the_frontend_shows(self):
        ticket, _ = self.checkin(1, complaint="chest pain")
        for key in ("ticket_id", "queue_no", "patient_id", "name", "time_in", "urgency", "complaint",
                    "vitals", "watch_flag", "lifecycle_status"):
            self.assertIn(key, ticket)
        self.assertEqual((ticket["complaint"], ticket["lifecycle_status"]), ("chest pain", "In Waiting Room"))

    # --- stored, not in memory -------------------------------------------
    def test_queue_survives_a_server_restart(self):
        self.checkin(1)
        restarted = self.queue()               # a new object, as after a restart
        self.assertEqual([t["patient_id"] for t in restarted.list_for("DOCTOR")], [1])

    def test_finishing_a_patient_removes_their_ticket_from_the_queue(self):
        self.checkin(1)
        self.assertTrue(self.q.close_for_patient(1))
        self.db.session.commit()
        self.assertEqual(self.q.list_for("DOCTOR"), [])
        self.assertEqual(self.QueueTicket.query.one().status, "DONE")

    def test_finishing_without_a_ticket_is_harmless(self):
        self.assertFalse(self.q.close_for_patient(3))


if __name__ == "__main__":
    unittest.main()
