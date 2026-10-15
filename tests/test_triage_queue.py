"""Triage queue: patients see and cancel only their own ticket; numbers never repeat."""
import unittest

from tests._helpers import ROOT  # noqa: F401


class TriageQueueTests(unittest.TestCase):
    def setUp(self):
        from backend.triage_queue import TriageQueue
        self.q = TriageQueue()

    def checkin(self, pid, by_staff=False, **fields):
        return self.q.checkin(pid, fields, by_staff=by_staff)

    # --- visibility -------------------------------------------------------
    def test_patient_sees_only_own_ticket(self):
        self.checkin(1, name="Ana", complaint="chest pain")
        self.checkin(2, name="Ben", complaint="cough")
        visible = self.q.list_for(role="PATIENT", patient_id=1)
        self.assertEqual([t["patient_id"] for t in visible], [1])

    def test_staff_see_every_ticket(self):
        self.checkin(1)
        self.checkin(2)
        self.assertEqual(len(self.q.list_for(role="DOCTOR")), 2)
        self.assertEqual(len(self.q.list_for(role="ADMIN")), 2)

    def test_patient_without_ticket_sees_empty_queue(self):
        self.checkin(2)
        self.assertEqual(self.q.list_for(role="PATIENT", patient_id=1), [])

    # --- cancel -----------------------------------------------------------
    def test_patient_cannot_cancel_another_patients_ticket(self):
        self.checkin(2)
        self.assertEqual(self.q.cancel(2, role="PATIENT", caller_patient_id=1), "forbidden")
        self.assertEqual(len(self.q.list_for(role="DOCTOR")), 1)

    def test_patient_can_cancel_own_ticket(self):
        self.checkin(1)
        self.assertEqual(self.q.cancel(1, role="PATIENT", caller_patient_id=1), "cancelled")
        self.assertEqual(self.q.list_for(role="DOCTOR"), [])

    def test_staff_can_cancel_any_ticket(self):
        self.checkin(2)
        self.assertEqual(self.q.cancel(2, role="DOCTOR"), "cancelled")

    def test_cancel_missing_ticket_is_not_found(self):
        self.assertEqual(self.q.cancel(9, role="DOCTOR"), "not_found")

    # --- numbering --------------------------------------------------------
    def test_ticket_numbers_never_repeat_after_cancel(self):
        self.checkin(1)
        self.checkin(2)
        self.q.cancel(1, role="DOCTOR")
        self.checkin(3)
        numbers = [t["queue_no"] for t in self.q.list_for(role="DOCTOR")]
        self.assertEqual(len(numbers), len(set(numbers)), numbers)
        self.assertEqual(numbers, ["Q-02", "Q-03"])

    def test_second_checkin_returns_existing_ticket(self):
        first, created_first = self.checkin(1)
        second, created_second = self.checkin(1)
        self.assertTrue(created_first)
        self.assertFalse(created_second)
        self.assertEqual(first["queue_no"], second["queue_no"])

    # --- triage fields ----------------------------------------------------
    def test_patient_cannot_set_own_urgency(self):
        ticket, _ = self.checkin(1, urgency="🔴 Emergency", watch_flag="VIP")
        self.assertEqual(ticket["urgency"], "🟢 Routine")
        self.assertEqual(ticket["watch_flag"], "None declared")

    def test_staff_can_set_urgency(self):
        ticket, _ = self.checkin(1, by_staff=True, urgency="🔴 Emergency")
        self.assertEqual(ticket["urgency"], "🔴 Emergency")

    def test_patient_complaint_is_kept(self):
        ticket, _ = self.checkin(1, complaint="headache")
        self.assertEqual(ticket["complaint"], "headache")

    def test_returned_ticket_is_a_copy(self):
        ticket, _ = self.checkin(1)
        ticket["urgency"] = "changed outside"
        self.assertEqual(self.q.list_for(role="DOCTOR")[0]["urgency"], "🟢 Routine")


if __name__ == "__main__":
    unittest.main()
