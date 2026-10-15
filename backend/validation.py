"""
Request validation shared by the routes. No database access, so it is unit-tested directly.
"""
import math
from datetime import date

# bcrypt only uses the first 72 bytes of a password; longer ones would be silently truncated.
PASSWORD_MIN_CHARS = 8
PASSWORD_MAX_BYTES = 72

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


# Names people use for the four disease models (family history and hazards are per model)
DISEASE_ALIASES = {
    "cvd": "cvd", "cardiovascular": "cvd", "heart": "cvd", "heart disease": "cvd", "hypertension": "cvd",
    "t2d": "t2d", "diabetes": "t2d", "type 2 diabetes": "t2d",
    "resp": "resp", "respiratory": "resp", "lung": "resp", "copd": "resp", "asthma": "resp",
    "neuro": "neuro", "neurological": "neuro", "mental health": "neuro", "neuro/mental": "neuro",
}
SEX_VALUES = ("Female", "Male")   # CDSS_Data_Dictionary.pdf: Female (0), Male (1)


def parse_disease(value):
    """cvd / t2d / resp / neuro, or None when the name is not one of the four models."""
    if not isinstance(value, str):
        return None
    return DISEASE_ALIASES.get(" ".join(value.strip().lower().replace("_", " ").split()))


def parse_tier(value):
    """1, "1", "Tier 1" -> 1; None if not a valid tier."""
    from backend.cdss.fhrs import TIER_KINSHIP
    if isinstance(value, bool):
        return None
    text = str(value).strip().lower().replace("tier", "").strip() if value is not None else ""
    return int(text) if text.isdigit() and int(text) in TIER_KINSHIP else None


def parse_onset(value):
    """"early", "Early onset", "severe-early" -> spec key; None if unknown."""
    from backend.cdss.fhrs import ONSET_MULTIPLIER
    if not isinstance(value, str):
        return None
    key = value.strip().lower().replace("onset", "").strip().replace("-", " ").replace(" ", "_").strip("_")
    return key if key in ONSET_MULTIPLIER else None


def validate_family_history(role, data):
    """
    One family history entry, with weights looked up from cdss_spec.json (CDSS FHRS Guide).
    Weights are never taken from the request. Only staff can mark a diagnosis verified:
    a patient's own report counts as unverified (x0.5) until a doctor confirms it.
    """
    from backend.cdss.fhrs import ONSET_MULTIPLIER, TIER_KINSHIP
    bad = []
    disease = parse_disease(data.get("disease_domain"))
    tier = parse_tier(data.get("relationship_tier"))
    onset = parse_onset(data.get("onset_classification"))
    if disease is None:
        bad.append("disease_domain")
    if tier is None:
        bad.append("relationship_tier")
    if onset is None:
        bad.append("onset_classification")

    age = data.get("age_at_diagnosis")
    if age is not None and (isinstance(age, bool) or not isinstance(age, int) or not 0 <= age <= 120):
        bad.append("age_at_diagnosis")
    if bad:
        raise ValidationError(
            "Invalid or missing: " + ", ".join(bad) + ". disease_domain is cvd, t2d, resp or neuro; "
            f"relationship_tier is 1, 2 or 3; onset_classification is one of {', '.join(ONSET_MULTIPLIER)}.", bad)

    diagnosis = data.get("specific_diagnosis")
    return {
        "disease_domain": disease,
        "specific_diagnosis": str(diagnosis).strip()[:150] if diagnosis else disease,
        "relationship_tier": str(tier),
        "relationship_weight": TIER_KINSHIP[tier],
        "onset_classification": onset,
        "onset_weight": ONSET_MULTIPLIER[onset],
        "age_at_diagnosis": age,
        "shared_environment": bool(data.get("shared_environment", False)),
        "is_verified": role in STAFF_ROLES and data.get("is_verified") is True,
    }


def parse_biological_sex(value):
    """'female' / ' MALE ' -> 'Female' / 'Male'."""
    match = next((s for s in SEX_VALUES if isinstance(value, str) and value.strip().lower() == s.lower()), None)
    if match is None:
        raise ValidationError("biological_sex must be Female or Male.", ["biological_sex"])
    return match


def validate_hazard(data):
    """(disease, hazard_code) for an environmental hazard on that disease's fixed list."""
    from backend.cdss.fhrs import HAZARDS
    disease = parse_disease(data.get("disease_domain"))
    if disease is None:
        raise ValidationError("disease_domain must be cvd, t2d, resp or neuro.", ["disease_domain"])
    code = data.get("hazard_code")
    if code not in HAZARDS[disease]:
        allowed = ", ".join(HAZARDS[disease]) or "none yet"
        raise ValidationError(f"hazard_code for {disease} must be one of: {allowed}.", ["hazard_code"])
    return disease, code


def _numeric_limit(precision, scale):
    """Largest absolute value a Numeric(precision, scale) column can store."""
    scale = scale or 0
    return 10 ** (precision - scale) - 10 ** (-scale)


def validate_biomarkers(spec, values, ranges=None, choices=None):
    """
    Check a biomarker payload against a column spec before it reaches the database.

    spec maps field -> ("numeric", precision, scale) | ("integer",) | ("string", length);
    precision None means unbounded. Unknown fields, wrong types and values that do not
    fit the column are rejected (instead of a database overflow error). None is dropped.

    ranges maps field -> (minimum, maximum, unit) and choices maps field -> allowed
    strings (backend/biomarker_ranges.py). Values outside them are rejected with the limits
    in the message; allowed strings are stored in the spelling given in choices.
    """
    if not isinstance(values, dict):
        raise ValidationError("values must be a JSON object of biomarker fields.", ["values"])

    unknown = sorted(k for k in values if k not in spec)
    if unknown:
        raise ValidationError(f"Unknown biomarker fields: {', '.join(unknown)}", unknown)

    ranges, choices = ranges or {}, choices or {}
    cleaned, bad, outside = {}, [], {}
    for field, value in values.items():
        if value is None:
            continue
        kind = spec[field][0]
        if kind == "string":
            length = spec[field][1]
            if not isinstance(value, str) or (length and len(value) > length):
                bad.append(field)
                continue
            if field in choices:
                match = next((c for c in choices[field] if c.lower() == value.strip().lower()), None)
                if match is None:
                    outside[field] = f"{field} must be one of {', '.join(choices[field])} (got {value!r})"
                    continue
                value = match
            cleaned[field] = value
            continue

        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            bad.append(field)
            continue
        if kind == "integer":
            if value != int(value):
                bad.append(field)
                continue
            cleaned[field] = int(value)
            continue

        precision, scale = spec[field][1], spec[field][2]
        if precision is not None and abs(value) > _numeric_limit(precision, scale):
            bad.append(field)
            continue
        cleaned[field] = value

    # Integers were converted above, so check ranges on what would be stored.
    from backend.biomarker_ranges import range_message
    for field in list(cleaned):
        if field in ranges and spec[field][0] != "string":
            low, high, unit = ranges[field]
            if not low <= cleaned[field] <= high:
                outside[field] = range_message(field, low, high, unit, cleaned.pop(field))

    if bad or outside:
        parts = []
        if bad:
            parts.append(f"Invalid value for: {', '.join(bad)} (wrong type or does not fit the column)")
        parts.extend(outside.values())
        raise ValidationError("; ".join(parts), bad + list(outside))
    if not cleaned:
        raise ValidationError("values must contain at least one biomarker.", ["values"])
    return cleaned
