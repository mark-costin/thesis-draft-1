from typing import Any, Dict, List, Union

SENSITIVE_FIELDS = {
    "password_hash", 
    "password", 
    "secret_key", 
    "token", 
    "reset_token"
}

def sanitize_response(data: Union[Dict[str, Any], List[Dict[str, Any]], Any], role: str = None) -> Any:
    """
    Recursively strips internal/sensitive database attributes before returning JSON payloads.
    Can be expanded to filter fields based on user role (e.g., PATIENT vs DOCTOR vs ADMIN).
    """
    if isinstance(data, dict):
        sanitized = {}
        for key, value in data.items():
            if key.lower() in SENSITIVE_FIELDS:
                continue
            sanitized[key] = sanitize_response(value, role)
        return sanitized
    elif isinstance(data, list):
        return [sanitize_response(item, role) for item in data]
    return data