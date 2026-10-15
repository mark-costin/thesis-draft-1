"""
Batch 5b rules that need no database: ticket numbers, who may set triage fields,
and what a consultation must contain.
"""
import unittest

from tests._helpers import ROOT  # noqa: F401


class TicketRuleTests(unittest.TestCase):
    def test_ticket_numbers_are_two_digits_or_more(self):
        from backend.triage_queue import format_queue_no
        self.assertEqual((format_queue_no(1), format_queue_no(12), format_queue_no(105)), ("Q-01", "Q-12", "Q-105"))

    def fields(self, by_staff, **data):
        from backend.triage_queue import ticket_fields
        return ticket_fields(5, data, by_staff=by_staff)

    def test_patient_cannot_set_urgency_or_watch_flag(self):
        f = self.fields(False, urgency="🔴 Emergency", watch_flag="Sepsis")
        self.assertEqual((f["urgency"], f["watch_flag"]), ("🟢 Routine", "None declared"))

    def test_staff_can_set_urgency_and_watch_flag(self):
        f = self.fields(True, urgency="🔴 Emergency", watch_flag="Sepsis")
        self.assertEqual((f["urgency"], f["watch_flag"]), ("🔴 Emergency", "Sepsis"))

    def test_defaults_when_nothing_is_sent(self):
        f = self.fields(False)
        self.assertEqual((f["name"], f["complaint"], f["vitals"]), ("Patient #5", "Routine follow-up", "Not recorded"))

    def test_text_is_cut_to_the_column_size(self):
        f = self.fields(True, vitals="x" * 300, name="n" * 200, complaint="c" * 2000)
        self.assertEqual((len(f["vitals"]), len(f["name"]), len(f["complaint"])), (255, 150, 2000))

    def test_waiting_status_keeps_the_label_the_frontend_shows(self):
        from backend.triage_queue import lifecycle_label
        self.assertEqual(lifecycle_label("WAITING"), "In Waiting Room")


class ConsultationValidationTests(unittest.TestCase):
    def validate(self, **data):
        from backend.validation import validate_consultation
        return validate_consultation(data)

    def rejected(self, field, **data):
        from backend.validation import ValidationError
        with self.assertRaises(ValidationError) as ctx:
            self.validate(**data)
        self.assertIn(field, ctx.exception.fields)

    def test_valid_consultation_is_cleaned(self):
        out = self.validate(patient_id="5", directives={"medication": "Amlodipine 5 mg daily"}, notes=" Recheck BP ")
        self.assertEqual(out, {"patient_id": 5, "directives": {"medication": "Amlodipine 5 mg daily"},
                               "notes": "Recheck BP"})

    def test_directives_may_be_a_list_or_text(self):
        self.assertEqual(self.validate(patient_id=5, directives=["Low-salt diet"])["directives"], ["Low-salt diet"])
        self.assertEqual(self.validate(patient_id=5, directives=" Rest ")["directives"], "Rest")

    def test_notes_are_optional(self):
        self.assertIsNone(self.validate(patient_id=5, directives="Rest")["notes"])

    def test_missing_or_empty_directives_are_rejected(self):
        self.rejected("directives", patient_id=5)
        self.rejected("directives", patient_id=5, directives={})
        self.rejected("directives", patient_id=5, directives="  ")
        self.rejected("directives", patient_id=5, directives=42)

    def test_bad_patient_id_is_rejected(self):
        self.rejected("patient_id", patient_id="abc", directives="Rest")

    def test_overlong_notes_are_rejected(self):
        self.rejected("notes", patient_id=5, directives="Rest", notes="x" * 5001)


if __name__ == "__main__":
    unittest.main()
