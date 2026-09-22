from typing import Any, Dict, List, Union

SENSITIVE_FIELDS = {
    "password_hash", 
    "password", 
    "secret_key", 
    "token", 
    "reset_token"
}

# Internal metrics restricted from patient visibility
PATIENT_RESTRICTED_FIELDS = {
    "ai_confidence_score",
    "model_version",
    "internal_risk_weight"
}

def sanitize_response(data: Union[Dict[str, Any], List[Dict[str, Any]], Any], role: str = None) -> Any:
    """
    Recursively strips internal/sensitive database attributes before returning JSON payloads.
    Strips out diagnostic metrics (e.g., ai_confidence_score, model_version, internal_risk_weight)
    if the requesting user role is 'PATIENT'.
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