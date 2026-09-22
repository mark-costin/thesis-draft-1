import os
from functools import wraps
from flask import request, jsonify
import jwt

# Configuration fallback for JWT Secret Key
JWT_SECRET = os.environ.get("JWT_SECRET", "clinical-platform-default-jwt-secret-key")
JWT_ALGORITHM = "HS256"

def role_required(allowed_roles):
    """
    Flask decorator to enforce role-based access control (RBAC) via JWT Bearer tokens.
    
    Args:
        allowed_roles (list or str): List of roles permitted to access the endpoint.
        
    Returns:
        JSON response with HTTP 401 (Unauthorized) or HTTP 403 (Forbidden) on failure.
    """
    if isinstance(allowed_roles, str):
        allowed_roles = [allowed_roles]

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            auth_header = request.headers.get("Authorization")
            
            # Check for missing or malformed Authorization header
            if not auth_header or not auth_header.startswith("Bearer "):
                return jsonify({"error": "Unauthorized"}), 401
            
            token = auth_header.split(" ")[1]
            
            try:
                # Decode and verify the JWT signature and expiration
                payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
                return jsonify({"error": "Unauthorized"}), 401
            
            # Extract and validate role permissions
            user_role = payload.get("role")
            if not user_role or user_role not in allowed_roles:
                return jsonify({"error": "Forbidden"}), 403
            
            # Optionally attach decoded claims to the request context for downstream handlers
            request.current_user = payload
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator