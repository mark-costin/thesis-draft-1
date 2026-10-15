"""
Clinic triage queue with per-role visibility.

Patients see and cancel only their own ticket. Triage fields (urgency, watch flag) are
set by staff only. Ticket numbers come from a counter, so a cancel never causes a
duplicate number. Thread-safe within one server process.

Still in memory: the queue is lost on restart and is not shared between server workers.
Run a single worker, or move it to a database table later.
"""
import threading
from datetime import datetime

DEFAULT_URGENCY = "🟢 Routine"
DEFAULT_WATCH_FLAG = "None declared"


class TriageQueue:
    def __init__(self):
        self._lock = threading.Lock()
        self._tickets = []
        self._next_number = 1

    def checkin(self, patient_id, fields, by_staff=False):
        """Add a ticket. Returns (ticket, created); an existing ticket is returned unchanged."""
        fields = fields or {}
        with self._lock:
            for ticket in self._tickets:
                if ticket["patient_id"] == patient_id:
                    return dict(ticket), False

            ticket = {
                "queue_no": f"Q-{self._next_number:02d}",
                "patient_id": patient_id,
                "name": fields.get("name", f"Patient #{patient_id}"),
                "time_in": datetime.now().strftime("%I:%M %p"),
                "urgency": fields.get("urgency", DEFAULT_URGENCY) if by_staff else DEFAULT_URGENCY,
                "complaint": fields.get("complaint", "Routine follow-up"),
                "vitals": fields.get("vitals", "Not recorded"),
                "watch_flag": fields.get("watch_flag", DEFAULT_WATCH_FLAG) if by_staff else DEFAULT_WATCH_FLAG,
                "lifecycle_status": "In Waiting Room",
            }
            self._next_number += 1
            self._tickets.append(ticket)
            return dict(ticket), True

    def list_for(self, role, patient_id=None):
        """Patients get only their own ticket; staff get the whole queue."""
        with self._lock:
            if role == "PATIENT":
                return [dict(t) for t in self._tickets if patient_id is not None and t["patient_id"] == patient_id]
            return [dict(t) for t in self._tickets]

    def cancel(self, patient_id, role, caller_patient_id=None):
        """Returns "cancelled", "forbidden" or "not_found"."""
        with self._lock:
            if role == "PATIENT" and caller_patient_id != patient_id:
                return "forbidden"
            before = len(self._tickets)
            self._tickets = [t for t in self._tickets if t["patient_id"] != patient_id]
            return "cancelled" if len(self._tickets) < before else "not_found"
