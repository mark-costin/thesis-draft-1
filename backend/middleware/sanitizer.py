from typing import Any, Dict, List, Union

SENSITIVE_FIELDS = {
    "password_hash",
    "password",
    "secret_key",
    "token",
    "reset_token"
}

# Model internals hidden from patients. These are the keys the CDSS actually returns
# (see routes/predictions.py). SHAP drivers and the risk tier stay visible.
# Review this list when you decide what the patient portal should show.
PATIENT_RESTRICTED_FIELDS = {
    "model_version",
    "fairness",
    "fairness_audit",
    "calibration",
}


def sanitize_response(data: Union[Dict[str, Any], List[Dict[str, Any]], Any], role: str = None) -> Any:
    """
    Recursively strips internal/sensitive database attributes before returning JSON payloads.
    Also strips model internals (PATIENT_RESTRICTED_FIELDS) if the requesting role is 'PATIENT'.
    """
    restricted_fields = SENSITIVE_FIELDS.copy()

    if role and role.upper() == "PATIENT":
        restricted_fields.update(PATIENT_RESTRICTED_FIELDS)

    if isinstance(data, dict):
        sanitized = {}
        for key, value in data.items():
            if key.lower() in restricted_fields:
                continue
            sanitized[key] = sanitize_response(value, role)
        return sanitized
    elif isinstance(data, list):
        return [sanitize_response(item, role) for item in data]

    return data
