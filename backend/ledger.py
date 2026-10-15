"""
Tamper-evident sealing for clinical encounters.

Every field that makes up a sealed encounter goes into one canonical JSON envelope,
which is signed with HMAC-SHA256 using ENCOUNTER_SEAL_KEY. Changing any sealed field —
including the care plan — produces a different seal, and without the server key nobody
can compute a new valid seal for an edited row.

The timestamp is written in one canonical UTC form, so the seal can be recomputed later
from what the database returns (PostgreSQL gives timezone-aware times, SQLite naive UTC).
"""
import hashlib
import hmac
import json
from datetime import datetime, timezone

from backend.config import ENCOUNTER_SEAL_KEY

SEAL_ALGORITHM = "HMAC-SHA256"
SEAL_VERSION = 1


def canonical_timestamp(value: datetime) -> str:
    """UTC, always with microseconds: 2026-10-15T00:00:00.123456Z. Naive times are treated as UTC."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def canonical_envelope(*, encounter_uid, patient_id, doctor_id, record_type, parent_baseline_hash,
                       created_at, cdss_payload, care_plan, reanchor_decision) -> str:
    """The exact text that is sealed. Key order and whitespace never affect it."""
    envelope = {
        "v": SEAL_VERSION,
        "encounter_uid": encounter_uid,
        "patient_id": int(patient_id),
        "doctor_id": int(doctor_id),
        "record_type": record_type,
        "parent_baseline_hash": parent_baseline_hash,
        "created_at": canonical_timestamp(created_at),
        "cdss_payload": cdss_payload,
        "care_plan": care_plan,
        "reanchor_decision": reanchor_decision,
    }
    return canonical_json(envelope)


def canonical_json(value) -> str:
    """Deterministic JSON: sorted keys, no whitespace."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def hmac_hex(message: str, key: str = None) -> str:
    """HMAC-SHA256 of `message` with the seal key, as 64 hex characters."""
    secret = (key or ENCOUNTER_SEAL_KEY).encode("utf-8")
    return hmac.new(secret, message.encode("utf-8"), hashlib.sha256).hexdigest()


def seal(*, key: str = None, **fields) -> str:
    """HMAC-SHA256 of the canonical envelope, as 64 hex characters."""
    return hmac_hex(canonical_envelope(**fields), key=key)


def verify_seal(expected, *, key: str = None, **fields) -> bool:
    """True only if `expected` is the seal of exactly these fields."""
    if not expected:
        return False
    return hmac.compare_digest(str(expected), seal(key=key, **fields))


def encounter_fields(encounter) -> dict:
    """The sealed fields of an Encounter row, as stored."""
    return {
        "encounter_uid": encounter.encounter_uid,
        "patient_id": encounter.patient_id,
        "doctor_id": encounter.doctor_id,
        "record_type": encounter.record_type,
        "parent_baseline_hash": encounter.parent_baseline_hash,
        "created_at": encounter.created_at_utc,
        "cdss_payload": encounter.cdss_payload,
        "care_plan": encounter.care_plan,
        "reanchor_decision": encounter.reanchor_decision,
    }


def verify_encounter(encounter) -> bool:
    """Recompute the seal from the stored row and compare it with the stored seal."""
    return verify_seal(encounter.cryptographic_hash, **encounter_fields(encounter))
