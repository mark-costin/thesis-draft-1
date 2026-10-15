"""
Append-only audit ledger for CDSS events (inferences, encounter commits, model reloads).

Each entry is sealed with HMAC-SHA256 using ENCOUNTER_SEAL_KEY, so editing an entry in
the database is detectable with verify_audit(). Deleting an entry is not detected by the
seal itself; the table has no foreign keys, so deleting a patient never removes it.
"""
import hmac
import uuid
from datetime import datetime, timezone

from backend.ledger import canonical_json, canonical_timestamp, hmac_hex

AUDIT_SEAL_VERSION = 1


def audit_envelope(*, audit_id, created_at, event_type, payload, patient_id, doctor_id, actor_user_id) -> str:
    return canonical_json({
        "v": AUDIT_SEAL_VERSION,
        "audit_id": audit_id,
        "created_at": canonical_timestamp(created_at),
        "event_type": event_type,
        "payload": payload,
        "patient_id": patient_id,
        "doctor_id": doctor_id,
        "actor_user_id": actor_user_id,
    })


def seal_audit(*, key: str = None, **fields) -> str:
    return hmac_hex(audit_envelope(**fields), key=key)


def verify_audit_fields(expected, *, key: str = None, **fields) -> bool:
    if not expected:
        return False
    return hmac.compare_digest(str(expected), seal_audit(key=key, **fields))


def verify_audit(entry) -> bool:
    """Recompute an AuditLedger row's seal from what is stored and compare."""
    return verify_audit_fields(
        entry.entry_seal,
        audit_id=entry.audit_id,
        created_at=entry.timestamp_utc,
        event_type=entry.event_type,
        payload=entry.payload,
        patient_id=entry.patient_id,
        doctor_id=entry.doctor_id,
        actor_user_id=entry.actor_user_id,
    )


def log_event(event_type, payload, *, patient_id=None, doctor_id=None, actor_user_id=None, commit=True) -> str:
    """
    Write one sealed audit entry and return its audit_id.

    commit=False adds it to the current session so it is saved in the same transaction
    as the caller's own changes (used by commit-encounter).
    """
    from backend.dbconnect import db
    from backend.model_orm.audit_orm import AuditLedger

    fields = {
        "audit_id": str(uuid.uuid4()),
        "created_at": datetime.now(timezone.utc),
        "event_type": event_type,
        "payload": payload,
        "patient_id": patient_id,
        "doctor_id": doctor_id,
        "actor_user_id": actor_user_id,
    }
    db.session.add(AuditLedger(
        audit_id=fields["audit_id"],
        timestamp_utc=fields["created_at"],
        event_type=event_type,
        payload=payload,
        patient_id=patient_id,
        doctor_id=doctor_id,
        actor_user_id=actor_user_id,
        entry_seal=seal_audit(**fields),
    ))
    if commit:
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
    return fields["audit_id"]
