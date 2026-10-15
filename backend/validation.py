"""
Request validation shared by the routes. No database access, so it is unit-tested directly.
"""
import math
from datetime import date

# bcrypt only uses the first 72 bytes of a password; longer ones would be silently truncated.
PASSWORD_MIN_CHARS = 8
PASSWORD_MAX_BYTES = 72

# FHRS weights used when no clinician-entered weight is given. These are the values the
# original route already used; replace them with your FHRS method's table (batch 2).
DEFAULT_RELATIONSHIP_WEIGHT = 0.5
DEFAULT_ONSET_WEIGHT = 1.0

STAFF_ROLES = {"DOCTOR", "CLINICIAN", "ADMIN", "SYSTEM_ADMIN"}

PATIENT_REQUIRED = (
    "username", "password", "first_name", "last_name", "date_of_birth", "gender",
    "address", "contact_number", "email",
    "emergency_contact_name", "emergency_contact_number", "emergency_relation",
)
PATIENT_OPTIONAL = ("middle_name", "religion")

DOCTOR_REQUIRED = (
    "username", "password", "first_name", "last_name", "address",
    "specialization", "license_number", "contact_number", "email",
    "emergency_contact_name", "emergency_contact_number", "emergency_relation",
)
DOCTOR_OPTIONAL = ("middle_name", "hospital_affiliation")


class ValidationError(ValueError):
    """Raised with a message naming the offending field(s)."""

    def __init__(self, message, fields=()):
        super().__init__(message)
        self.fields = list(fields)


def _blank(value):
    return value is None or (isinstance(value, str) and not value.strip())


def _require(data, required, optional):
    if not isinstance(data, dict):
        raise ValidationError("Request body must be a JSON object.")
    missing = [f for f in required if _blank(data.get(f))]
    if missing:
        raise ValidationError(f"Missing required fields: {', '.join(missing)}", missing)
    cleaned = {f: data[f].strip() if isinstance(data[f], str) else data[f] for f in required}
    for f in optional:
        if not _blank(data.get(f)):
            cleaned[f] = data[f].strip() if isinstance(data[f], str) else data[f]
    return cleaned


def validate_password(password, field="password"):
    if not isinstance(password, str) or len(password) < PASSWORD_MIN_CHARS:
        raise ValidationError(f"{field} must be at least {PASSWORD_MIN_CHARS} characters.", [field])
    if len(password.encode("utf-8")) > PASSWORD_MAX_BYTES:
        raise ValidationError(f"{field} must be at most {PASSWORD_MAX_BYTES} bytes.", [field])
    return password


def validate_registration(data):
    """Patient self-registration. Role is never taken from the client."""
    cleaned = _require(data, PATIENT_REQUIRED, PATIENT_OPTIONAL)
    validate_password(cleaned["password"])

    try:
        dob = date.fromisoformat(str(cleaned["date_of_birth"]))
    except ValueError:
        raise ValidationError("date_of_birth must be YYYY-MM-DD.", ["date_of_birth"])
    if dob > date.today():
        raise ValidationError("date_of_birth cannot be in the future.", ["date_of_birth"])
    cleaned["date_of_birth"] = dob

    if data.get("hipaa_consent") is not True:
        raise ValidationError("hipaa_consent must be true to register.", ["hipaa_consent"])
    cleaned["hipaa_consent"] = True
    return cleaned


def validate_provision(data):
    """Admin-created clinician account."""
    cleaned = _require(data, DOCTOR_REQUIRED, DOCTOR_OPTIONAL)
    validate_password(cleaned["password"])
    return cleaned


def parse_patient_id(value):
    try:
        pid = int(value)
    except (TypeError, ValueError):
        raise ValidationError("patient_id must be a positive integer.", ["patient_id"])
    if pid <= 0:
        raise ValidationError("patient_id must be a positive integer.", ["patient_id"])
    return pid


def _weight(data, field, default):
    if data.get(field) is None:
        return default
    value = data[field]
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValidationError(f"{field} must be a number >= 0.", [field])
    return float(value)


def family_history_weights(role, data):
    """
    (relationship_weight, onset_weight) for a family history entry.
    Patients cannot set weights; clinicians may, within a valid range.
    """
    if role not in STAFF_ROLES:
        return DEFAULT_RELATIONSHIP_WEIGHT, DEFAULT_ONSET_WEIGHT
    return (_weight(data, "relationship_weight", DEFAULT_RELATIONSHIP_WEIGHT),
            _weight(data, "onset_weight", DEFAULT_ONSET_WEIGHT))
