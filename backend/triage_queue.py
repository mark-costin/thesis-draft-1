"""
Clinic triage queue, stored in the queue_tickets table.

Patients see and cancel only their own ticket. Triage fields (urgency, watch flag) are set
by staff only. Numbers restart each day and never repeat within a day, because cancelled and
finished tickets stay in the table as history. Being in the database, the queue survives a
server restart and is the same for every worker.
"""
from datetime import date, datetime, timezone

DEFAULT_URGENCY = "🟢 Routine"
DEFAULT_WATCH_FLAG = "None declared"
STATUS_LABELS = {"WAITING": "In Waiting Room", "DONE": "Seen", "CANCELLED": "Cancelled"}
MAX_NUMBER_ATTEMPTS = 3


def format_queue_no(number):
    return f"Q-{number:02d}"


def lifecycle_label(status):
    return STATUS_LABELS.get(status, status)


def _text(value, default, limit=None):
    text = str(value).strip() if value is not None else ""
    text = text or default
    return text[:limit] if limit else text


def ticket_fields(patient_id, fields, by_staff=False):
    """The stored fields of a new ticket. Only staff may set urgency and the watch flag."""
    fields = fields or {}
    return {
        "name": _text(fields.get("name"), f"Patient #{patient_id}", 150),
        "urgency": _text(fields.get("urgency"), DEFAULT_URGENCY, 40) if by_staff else DEFAULT_URGENCY,
        "complaint": _text(fields.get("complaint"), "Routine follow-up"),
        "vitals": _text(fields.get("vitals"), "Not recorded", 255),
        "watch_flag": _text(fields.get("watch_flag"), DEFAULT_WATCH_FLAG, 150) if by_staff else DEFAULT_WATCH_FLAG,
    }


def _as_utc(moment):
    # SQLite gives back naive values; they were stored as UTC.
    return moment.replace(tzinfo=timezone.utc) if moment.tzinfo is None else moment


def ticket_dict(row):
    """A ticket as the API returns it (same keys the frontend already uses, plus ticket_id)."""
    return {
        "ticket_id": row.id,
        "queue_no": format_queue_no(row.queue_number),
        "queue_date": row.queue_date.isoformat(),
        "patient_id": row.patient_id,
        "name": row.name,
        "time_in": _as_utc(row.checked_in_at).astimezone().strftime("%I:%M %p"),
        "urgency": row.urgency,
        "complaint": row.complaint,
        "vitals": row.vitals,
        "watch_flag": row.watch_flag,
        "status": row.status,
        "lifecycle_status": lifecycle_label(row.status),
    }


class TriageQueue:
    """The queue for one clinic day. `today` can be replaced in tests."""

    def __init__(self, today=None):
        self._today = today or date.today

    def _waiting(self, patient_id=None):
        from backend.model_orm.clinic_orm import QueueTicket
        query = QueueTicket.query.filter_by(queue_date=self._today(), status="WAITING")
        if patient_id is not None:
            query = query.filter_by(patient_id=patient_id)
        return query.order_by(QueueTicket.queue_number)

    def checkin(self, patient_id, fields, by_staff=False):
        """Add a ticket. Returns (ticket, created); an existing waiting ticket is returned unchanged."""
        from sqlalchemy import func
        from sqlalchemy.exc import IntegrityError
        from backend.dbconnect import db
        from backend.model_orm.clinic_orm import QueueTicket

        existing = self._waiting(patient_id).first()
        if existing is not None:
            return ticket_dict(existing), False

        today = self._today()
        for _ in range(MAX_NUMBER_ATTEMPTS):
            last = (db.session.query(func.max(QueueTicket.queue_number))
                    .filter(QueueTicket.queue_date == today).scalar())
            row = QueueTicket(queue_date=today, queue_number=(last or 0) + 1, patient_id=patient_id,
                              status="WAITING", checked_in_at=datetime.now(timezone.utc),
                              **ticket_fields(patient_id, fields, by_staff))
            db.session.add(row)
            try:
                db.session.commit()
                return ticket_dict(row), True
            except IntegrityError:
                db.session.rollback()     # another check-in took this number at the same moment
        raise RuntimeError("Could not assign a queue number; please retry.")

    def list_for(self, role, patient_id=None):
        """Today's waiting tickets: patients get only their own, staff get all, by number."""
        if role == "PATIENT":
            if patient_id is None:
                return []
            return [ticket_dict(t) for t in self._waiting(patient_id)]
        return [ticket_dict(t) for t in self._waiting()]

    def cancel(self, patient_id, role, caller_patient_id=None):
        """Returns "cancelled", "forbidden" or "not_found". The ticket is kept as CANCELLED."""
        from backend.dbconnect import db
        if role == "PATIENT" and caller_patient_id != patient_id:
            return "forbidden"
        row = self._waiting(patient_id).first()
        if row is None:
            return "not_found"
        row.status, row.closed_at = "CANCELLED", datetime.now(timezone.utc)
        db.session.commit()
        return "cancelled"

    def close_for_patient(self, patient_id):
        """Mark today's waiting ticket DONE (after a consultation). The caller commits."""
        row = self._waiting(patient_id).first()
        if row is None:
            return False
        row.status, row.closed_at = "DONE", datetime.now(timezone.utc)
        return True
